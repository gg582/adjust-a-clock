"""박자 간격 추정, 틱 온셋 검출, 박자 모델 피팅."""
from dataclasses import dataclass, field

import numpy as np
import scipy.signal as s


def tick_level(env, sr):
    """틱 피크의 대표 높이. 포락선 백분위수는 틱이 아주 짧으면(듀티 1% 미만) 잡음 수준으로
    떨어지므로, 40 ms 간격 피크들 중 상위 5% 높이를 쓴다."""
    pk, _ = s.find_peaks(env, distance=int(0.04 * sr))
    return float(np.percentile(env[pk], 95)) if len(pk) else float(env.max())


def estimate_beat(env, sr):
    """한 박(틱 한 번) 간격 추정. 틱 크기가 강약으로 반복되면 자기상관은 여러 박을 한 박으로
    착각하므로, 촘촘히 잡은 피크들의 간격 최빈값을 우선 쓰고 실패할 때만 자기상관을 쓴다."""
    pk, _ = s.find_peaks(env, distance=int(0.04 * sr), height=tick_level(env, sr) * 0.2)
    d = np.diff(pk) / sr
    d = d[(d > 0.05) & (d < 1.2)]
    if len(d) >= 10:
        hist, edges = np.histogram(d, bins=np.arange(0.05, 1.2, 0.004))
        mode = edges[np.argmax(hist)] + 0.002
        near = d[np.abs(d / mode - 1) < 0.1]
        if len(near) >= 0.3 * len(d):
            return float(np.median(near))
    return _beat_autocorr(env, sr)


def _beat_autocorr(env, sr):
    dec = 200
    # 25 Hz로 뭉개서 틱/톡 간 수 ms 비대칭(비트 에러)이 자기상관을 깎지 않게 한다
    e = s.sosfiltfilt(s.butter(2, 25, fs=sr, output='sos'), env)
    e = s.resample_poly(e, 1, sr // dec)
    e = e - e.mean()
    ac = np.correlate(e, e, 'full')[len(e) - 1:]
    lo, hi = int(0.05 * dec), min(int(1.2 * dec), len(ac) - 1)
    pk, _ = s.find_peaks(ac[:hi])
    pk = pk[pk >= lo]
    if not len(pk):
        return (lo + np.argmax(ac[lo:hi])) / dec
    # 가장 짧은 반복 간격(= 한 박)이 첫 번째 강한 피크
    lag = pk[np.argmax(ac[pk] >= 0.5 * ac[pk].max())]
    y0, y1, y2 = ac[lag - 1:lag + 2]
    return (lag + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2 + 1e-30)) / dec


def detect_onsets(env, sr, beat):
    """포락선 피크마다, 피크 높이의 30%를 처음 넘는 지점을 서브샘플 정밀도로 온셋으로 잡는다."""
    pk, _ = s.find_peaks(env, distance=int(0.5 * beat * sr), height=tick_level(env, sr) * 0.2)
    on = []
    lim = int(min(0.02, 0.2 * beat) * sr)
    for p in pk:
        h = env[p] * 0.3; i = p
        while i > 0 and env[i] > h and p - i < lim:
            i -= 1
        on.append((i + (h - env[i]) / (env[i + 1] - env[i] + 1e-15)) / sr)
    return np.array(on)


@dataclass
class BeatFit:
    ticks: np.ndarray        # 사용한 틱 시각 (초)
    n: np.ndarray            # 박 번호
    parity: np.ndarray       # 박 번호 홀짝 (틱/톡)
    resid: np.ndarray        # 모델 잔차 (초)
    rejected: np.ndarray     # 제외한 잡음 클릭 시각
    beat: float              # 한 박 간격 (초)
    beat_se: float           # 표준오차 (초)
    beat_err: float          # 비트 에러 (초)
    jitter: float            # 잔차 표준편차 (초)
    filled: int = 0          # 처음엔 놓쳤다가 예측 위치에서 다시 찾은 틱 수

    @property
    def expected(self):
        return int(self.n[-1] - self.n[0] + 1)

    @property
    def missing(self):
        return self.expected - len(self.n)


def _lstsq_beat(t, n, par):
    A = np.c_[np.ones(len(t)), n, par]
    coef, *_ = np.linalg.lstsq(A, t, rcond=None)
    r = t - A @ coef
    cov = (r @ r) / max(len(t) - 3, 1) * np.linalg.pinv(A.T @ A)
    return coef, r, cov


def _robust_fit(tk, n, rejected, filled=0):
    """잔차가 큰 점(잡음 클릭)을 반복 제외하며 박자 모델을 푼다."""
    par = (n % 2).astype(float)
    A = np.c_[np.ones(len(tk)), n, par]
    keep = np.ones(len(tk), bool)
    for _ in range(8):
        coef, *_ = np.linalg.lstsq(A[keep], tk[keep], rcond=None)
        r = tk - A @ coef
        mad = np.median(np.abs(r[keep])) * 1.4826
        nk = np.abs(r) < max(0.003, 4 * mad)
        if (nk == keep).all():
            break
        keep = nk
    rejected = np.sort(np.r_[rejected, tk[~keep]])
    y, n, par = tk[keep], n[keep], par[keep]
    if len(y) < 6:
        return None
    coef, r, cov = _lstsq_beat(y, n, par)
    return BeatFit(ticks=y, n=n, parity=par, resid=r, rejected=rejected, beat=coef[1],
                   beat_se=float(np.sqrt(cov[1, 1])), beat_err=abs(coef[2]), jitter=float(np.std(r)),
                   filled=filled)


def fit_beats(tk, beat):
    """t = a + n·박간격 + c·(홀짝) 로 강건 피팅. 박자에서 벗어난 잡음 클릭은 제외.

    박 번호는 전체를 한 번에 나누면 긴 녹음에서 누적 오차로 밀리므로, 박자가 규칙적인
    지점에서 시작해 틱을 하나씩 따라가며 간격을 갱신한다.
    """
    if len(tk) < 6:
        return None
    d = np.diff(tk)
    reg = [np.abs(d[i:i + 4] / beat - 1).max() for i in range(len(d) - 3)]
    st = int(np.argmin(reg)) if reg else 0
    idx, nums = [st], [0]
    for j in range(st + 1, len(tk)):
        m = round((tk[j] - tk[idx[-1]]) / beat)
        if m < 1 or abs(tk[j] - tk[idx[-1]] - m * beat) > 0.2 * beat:
            continue
        idx.append(j); nums.append(nums[-1] + m)
        back = next((i for i in range(max(0, len(idx) - 21), len(idx) - 1)
                     if (nums[-1] - nums[i]) % 2 == 0), None)   # 짝수 박 간격이라 비트 에러 상쇄
        if back is not None and nums[-1] - nums[back] >= 2:
            beat = (tk[idx[-1]] - tk[idx[back]]) / (nums[-1] - nums[back])
    for j in range(st - 1, -1, -1):
        m = round((tk[idx[0]] - tk[j]) / beat)
        if m < 1 or abs(tk[idx[0]] - tk[j] - m * beat) > 0.2 * beat:
            continue
        idx.insert(0, j); nums.insert(0, nums[0] - m)
    return _robust_fit(tk[idx], np.array(nums), np.setdiff1d(tk, tk[idx]))


def _match(sig, sr, t, par, pre=0.004, post=0.012, search=0.003, iters=3):
    """틱/톡별 평균 템플릿과 상호상관해 각 틱 시각을 서브샘플로 보정한다.
    반환: (보정된 시각, 정규화 상관계수)"""
    a, b, m = int(pre * sr), int(post * sr), int(search * sr)
    out, ncc = t.copy(), np.zeros(len(t))
    for _ in range(iters):
        for p in (0, 1):
            idx = np.where(par == p)[0]
            cut = [sig[int(round(out[i] * sr)) - a:int(round(out[i] * sr)) + b] for i in idx]
            good = [v for v in cut if len(v) == a + b]
            if len(good) < 3:
                continue
            tmpl = np.mean(good, 0); tmpl -= tmpl.mean()
            tn = np.linalg.norm(tmpl) + 1e-30
            for i in idx:
                c0 = int(round(out[i] * sr))
                w = sig[c0 - a - m:c0 + b + m]
                if c0 - a - m < 0 or len(w) != a + b + 2 * m:
                    continue
                w = w - w.mean()
                cc = np.correlate(w, tmpl, 'valid')
                k = int(np.argmax(cc))
                d = 0.0
                if 0 < k < len(cc) - 1:
                    y0, y1, y2 = cc[k - 1:k + 2]
                    d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2 + 1e-30)
                out[i] = (c0 + k - m + d) / sr
                seg = w[k:k + a + b]
                ncc[i] = cc[k] / (tn * (np.linalg.norm(seg - seg.mean()) + 1e-30))
    return out, ncc


def refine_beats(fit, clean, sr, min_ncc=0.6):
    """1차 검출 결과를 템플릿 매칭으로 다듬는다.

    - 놓친 박은 모델이 예측한 위치에서 다시 찾아, 틱 모양과 충분히 닮았으면(상관 0.6 이상) 채운다.
    - 모든 틱 시각을 틱/톡별 평균 템플릿과의 상호상관으로 보정한다
      (30% 문턱 방식보다 잡음에 강함: 잡음 많은 녹음에서 지터 약 60% 감소).
    """
    sig = s.sosfiltfilt(s.butter(2, 1000, fs=sr, output='sos'), np.abs(s.hilbert(clean)))
    a, beat, c = np.linalg.lstsq(np.c_[np.ones(len(fit.n)), fit.n, fit.parity], fit.ticks, rcond=None)[0]
    have = set(fit.n.tolist())
    gaps = np.array([k for k in range(fit.n[0], fit.n[-1] + 1) if k not in have], dtype=int)
    n = np.r_[fit.n, gaps]
    t = np.r_[fit.ticks, a + gaps * beat + (gaps % 2) * c]
    order = np.argsort(n); n, t = n[order], t[order]
    is_gap = np.isin(n, gaps)
    t2, ncc = _match(sig, sr, t, (n % 2).astype(float))
    keep = ~is_gap | (ncc >= min_ncc)
    filled = int((is_gap & keep).sum())
    return _robust_fit(t2[keep], n[keep], fit.rejected, filled) or fit

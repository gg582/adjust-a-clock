"""박자 간격 추정, 틱 온셋 검출, 박자 모델 피팅."""
from dataclasses import dataclass, field

import numpy as np
import scipy.ndimage as ndimage
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
            mode_beat = float(np.median(near))
            # 비트 에러가 한 박의 수 %를 넘으면 틱-톡 간격이 짧은 쪽/긴 쪽 두 봉우리로 갈라져
            # 최빈값이 한 박이 아니라 한쪽 간격을 가리킨다. 최빈값의 1.2~1.75배(또는 0.55~0.85배)에
            # 짝 봉우리가 비슷한 빈도로 있으면(놓친 박의 정수배 간격과는 다름) 두 봉우리의
            # 평균이 진짜 한 박이다.
            lo = d[(d > 0.55 * mode_beat) & (d < 0.85 * mode_beat)]
            hi = d[(d > 1.2 * mode_beat) & (d < 1.75 * mode_beat)]
            if len(hi) >= max(10, 0.5 * len(near)):
                return float((mode_beat + np.median(hi)) / 2)
            if len(lo) >= max(10, 0.5 * len(near)):
                return float((np.median(lo) + mode_beat) / 2)
            return mode_beat
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


LOST_TICKS = 16      # 이만큼의 온셋을 보고 박자를 놓쳤는지 판단한다
CLICK_DEV = 0.04     # 추세에서 한 박의 이만큼도 벗어나지 않으면 잡음 클릭으로 보지 않는다
LOCAL_TICKS = 11     # 주변 추세를 구하는 틱(또는 톡) 수


def _local_trend(n, r, at):
    """at번째 박들에서의 주변 추세. 잔차의 느린 흔들림·계단(시계를 건드려 박자가 밀린 경우)을 따라간다.
    비트 에러도 녹음 중에 변할 수 있으므로 틱과 톡을 따로 본다."""
    out = np.zeros(len(at))
    for p in (0, 1):
        k, q = n % 2 == p, at % 2 == p
        if k.sum() >= 3:
            med = ndimage.median_filter(r[k], size=min(LOCAL_TICKS, (k.sum() - 1) // 2 * 2 + 1), mode='mirror')
            out[q] = np.interp(at[q], n[k], med)
    return out


def _robust_fit(tk, n, rejected, filled=0):
    """주변 틱들의 추세에서 벗어난 점(잡음 클릭)을 반복 제외하며 박자 모델을 푼다.
    전체 직선에서 벗어났는지로 고르면, 속도가 변하거나 박자가 밀린 구간의 진짜 틱을 통째로 버린다."""
    par = (n % 2).astype(float)
    A = np.c_[np.ones(len(tk)), n, par]
    keep = np.ones(len(tk), bool)
    for _ in range(8):
        coef, *_ = np.linalg.lstsq(A[keep], tk[keep], rcond=None)
        r = tk - A @ coef
        r = r - _local_trend(n, r, n)     # 제외한 점까지 포함해야 한 구간이 연쇄로 버려지지 않는다
        mad_all = np.median(np.abs(r[keep])) * 1.4826
        nk = np.zeros(len(tk), bool)
        for p in (0, 1):                # 한쪽(틱 또는 톡)만 흔들리는 시계가 있어 따로 판단한다
            k = n % 2 == p
            mad = np.median(np.abs(r[k & keep])) * 1.4826 if (k & keep).any() else 0.0
            nk |= k & (np.abs(r) < max(0.003, CLICK_DEV * coef[1], 4 * mad, 4 * mad_all))
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
    near = (d > 0.55 * beat) & (d < 1.45 * beat)
    two = (d[:-1] + d[1:])[near[:-1] & near[1:]]       # 두 박의 합은 비트 에러와 무관하다
    two = two[np.abs(two / (2 * beat) - 1) < 0.15]
    if len(two) >= 5:
        beat = float(np.median(two)) / 2
    reg = [max(abs(d[i] + d[i + 1] - 2 * beat), abs(d[i + 1] + d[i + 2] - 2 * beat),
               abs(d[i + 2] - d[i]), abs(d[i + 3] - d[i + 1])) for i in range(len(d) - 3)]
    st = int(np.argmin(reg)) if reg else 0
    c = float(np.clip((d[st] - d[st + 1]) / 2, -0.35 * beat, 0.35 * beat)) if reg else 0.0   # 홀수 박의 치우침

    def step(dt, odd, sign):
        """간격 dt에 맞는 박 수. odd: 기준 틱이 홀수 박인가, sign: +1 뒤로, -1 앞으로 따라감."""
        best = None
        for m in {int(dt // beat), int(dt // beat) + 1, int(dt // beat) + 2} - {0}:
            shift = (c if not odd else -c) * sign if m % 2 else 0.0
            e = abs(dt - m * beat - shift)
            if best is None or e < best[1]:
                best = (m, e)
        return best[0] if best[1] <= 0.2 * beat else 0

    def lost(seen):
        """최근 본 온셋 대부분이 모델과 안 맞는데 자기들끼리는 규칙적이면 박자가 크게 밀린 것이다.
        그 시작 번호를 돌려준다 (안 밀렸으면 None)."""
        miss = [j for j, ok in seen[-LOST_TICKS:] if not ok]
        if len(seen) < LOST_TICKS or len(miss) < 0.7 * LOST_TICKS:
            return None
        v = np.sort(tk[miss])
        regular = np.abs((v[1:] - v[:-1]) / beat - 1) < 0.45
        return miss[0] if regular.mean() > 0.7 else None

    # 박자가 크게 밀리면 몇 박이 지났는지 알 수 없으므로 거기서 멈추고, 이어지는 구간만 쓴다
    idx, nums, seen = [st], [0], []
    for j in range(st + 1, len(tk)):
        m = step(tk[j] - tk[idx[-1]], nums[-1] % 2, 1)
        seen.append((j, bool(m)))
        if not m:
            cut = lost(seen)
            if cut is not None:
                while idx[-1] > cut:
                    idx.pop(); nums.pop()
                break
            continue
        idx.append(j); nums.append(nums[-1] + m)
        back = next((i for i in range(max(0, len(idx) - 21), len(idx) - 1)
                     if (nums[-1] - nums[i]) % 2 == 0), None)   # 짝수 박 간격이라 비트 에러 상쇄
        if back is not None and nums[-1] - nums[back] >= 2:
            beat = (tk[idx[-1]] - tk[idx[back]]) / (nums[-1] - nums[back])
    seen = []
    for j in range(st - 1, -1, -1):
        m = step(tk[idx[0]] - tk[j], nums[0] % 2, -1)
        seen.append((j, bool(m)))
        if not m:
            cut = lost(seen)
            if cut is not None:
                while idx[0] < cut:
                    idx.pop(0); nums.pop(0)
                break
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
    trend = _local_trend(fit.n, fit.resid, gaps)   # 박자가 밀린 구간에서도 그 자리의 틱을 찾게
    t = np.r_[fit.ticks, a + gaps * beat + (gaps % 2) * c + trend]
    order = np.argsort(n); n, t = n[order], t[order]
    is_gap = np.isin(n, gaps)
    t2, ncc = _match(sig, sr, t, (n % 2).astype(float))
    keep = ~is_gap | (ncc >= min_ncc)
    filled = int((is_gap & keep).sum())
    return _robust_fit(t2[keep], n[keep], fit.rejected, filled) or fit

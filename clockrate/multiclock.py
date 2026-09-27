"""--여러시계: 주 시계의 틱 소리를 빼고 남은 소리에서 다른 시계(예: 배경의 쿼츠 시계)의 틱을 찾는다.

1. 여러 주파수 대역마다 소리 크기 곡선을 만들고, 이미 찾은 시계의 틱을 뺀다
   (두 박 단위 중앙값 모양을 박자 모델이 예측한 자리마다 빼므로 틱·톡 모양 차이도 같이 빠진다).
2. 남은 곡선의 자기상관에서 가장 짧은 반복 간격을 찾는다. 이미 찾은 시계가 덜 빠져 남긴 반복
   (그 시계 박간격의 배수)보다 뚜렷해야 새 시계로 인정한다.
3. 가장 뚜렷한 대역에서 틱을 검출하고, 주 시계와 같은 박자 모델로 하루 오차를 구한다.

주 시계와 다른 시계는 같은 녹음 장비 시계로 재므로, 두 시계의 오차 차이는 녹음 장비 시계 오차와 무관하다.
"""
from dataclasses import dataclass

import numpy as np
import scipy.signal as s

from .analysis import SECONDS_PER_DAY, guess_nominal_bph
from .ticks import _match, _robust_fit, detect_onsets, fit_beats

BANDS = [(200, 800), (800, 1500), (1500, 3000), (3000, 6000), (6000, 12000)]
ENV_RATE = 4000          # 다른 시계 찾기용 소리 크기 곡선의 샘플레이트 (Hz)
AC_RATE = 200            # 반복 간격 찾기용 (Hz)
BEAT_RANGE = (0.1, 2.5)  # 찾을 박간격 (초)
MIN_SCORE = 0.3          # 이만큼 뚜렷한 반복이 있어야 시계로 인정 (정규화 자기상관 차이)
MIN_DETECTION = 0.7      # 예상 틱의 이 비율 이상을 찾아야 인정
MAX_JITTER = 0.05        # 틱 시각 흔들림이 박간격의 이 비율보다 크면 시계가 아니라 잡음으로 본다
MAX_EXTRA = 3            # 주 시계 말고 찾을 시계 수 상한
QUARTZ_BPH = 3600        # 1초에 한 번 뛰는 쿼츠 초침


@dataclass
class OtherClock:
    band: tuple              # 찾은 주파수 대역 (Hz)
    score: float             # 반복의 뚜렷함
    fit: object              # BeatFit
    nominal_bph: float | None
    rate: float | None       # 초/일, 규격을 못 찾으면 None
    rate_se: float
    profile: tuple = ()      # 그래프용 (시각 ms, 틱 평균 소리 크기)

    @property
    def bph(self):
        return 3600 / self.fit.beat

    @property
    def quartz(self):
        return self.nominal_bph == QUARTZ_BPH


def _band_envelope(raw, sr, band):
    ds = max(1, sr // ENV_RATE)
    hi = min(band[1], sr / 2 - 500)
    xb = s.sosfiltfilt(s.butter(4, [band[0], hi], 'bandpass', fs=sr, output='sos'), raw)
    env = s.sosfiltfilt(s.butter(2, 300, fs=sr, output='sos'), np.abs(s.hilbert(xb)))[::ds]
    return env, sr / ds


def _predicted(fit, n):
    a, beat, c = np.linalg.lstsq(np.c_[np.ones(len(fit.n)), fit.n, fit.parity], fit.ticks, rcond=None)[0]
    return a + n * beat + (n % 2) * c


def _subtract(env, fs, fit):
    """fit 시계의 틱을 env에서 뺀다: 두 박 길이 중앙값 모양을 예측 자리마다 뺀다."""
    L = int(round(2 * fit.beat * fs))
    pre = int(0.01 * fs)
    n0 = fit.n[0] - fit.n[0] % 2
    starts = [int(round(t * fs)) - pre for t in _predicted(fit, np.arange(n0 - 2, fit.n[-1] + 3, 2))]
    starts = [i for i in starts if i >= 0 and i + L <= len(env)]
    if len(starts) < 3:
        return env
    tmpl = np.median(np.stack([env[i:i + L] for i in starts]), 0) - np.median(env)
    out = env.copy()
    for i in starts:
        out[i:i + L] -= tmpl
    return out


def _periodicity(r, fs, known_beats):
    """남은 곡선에서 새 시계의 박간격과 뚜렷함. 반환: (박간격, 점수) 또는 None"""
    q = s.sosfiltfilt(s.butter(2, 25, fs=fs, output='sos'), r)
    q = s.resample_poly(q, 1, max(1, int(round(fs / AC_RATE))))
    q = q - q.mean()
    ac = s.correlate(q, q, 'full', method='fft')[len(q) - 1:]
    if ac[0] <= 0:
        return None
    ac = ac / ac[0]
    lo, hi = int(BEAT_RANGE[0] * AC_RATE), min(int(BEAT_RANGE[1] * AC_RATE), len(ac) - 1)
    pk, _ = s.find_peaks(ac[:hi])
    pk = pk[pk >= lo]
    # 이미 찾은 시계의 한 박·한 주기 자체는 후보가 아니다
    pk = np.array([k for k in pk if all(abs(k / AC_RATE / (m * b) - 1) > 0.03 for b in known_beats for m in (1, 2))],
                  dtype=int)
    if not len(pk):
        return None
    lag = int(pk[np.argmax(ac[pk] >= 0.5 * ac[pk].max())])
    P = lag / AC_RATE
    # 이미 찾은 시계가 덜 빠져 남긴 반복(그 박간격의 배수)보다 뚜렷해야 한다
    left = [ac[max(int(m * b * AC_RATE * 0.97), 1):int(m * b * AC_RATE * 1.03) + 1].max()
            for b in known_beats for m in range(1, int(P / b) + 1) if m * b < 0.97 * P]
    return P, float(ac[lag] - max(left + [0.0]))


def _track(r, fs, beat):
    """남은 곡선에서 틱을 검출하고 틱·톡별 평균 모양으로 시각을 다듬는다.
    검색 폭을 좁히면 흔들림이 인위적으로 작아져 신뢰구간이 거짓으로 좁아지므로 넉넉히 둔다."""
    fit = fit_beats(detect_onsets(r, fs, beat), beat)
    if fit is None:
        return None
    t, _ = _match(r, fs, fit.ticks, fit.parity, pre=0.01, post=min(0.1, 0.5 * beat), search=min(0.03, 0.15 * beat))
    return _robust_fit(t, fit.n, fit.rejected) or fit


def _profile(r, fs, fit):
    a, b = int(0.02 * fs), int(min(0.15, 0.8 * fit.beat) * fs)
    idx = [int(round(t * fs)) for t in fit.ticks]
    cut = [r[i - a:i + b] for i in idx if i - a >= 0 and i + b <= len(r)]
    if not cut:
        return ()
    return np.arange(-a, b) / fs * 1000, np.median(np.stack(cut), 0)


def _rate(fit):
    """규격 기준 하루 오차와 표준오차. 규격을 못 찾으면 (None, None, 0).

    다른 시계는 소리가 작아 틱 시각 흔들림이 커서, 주 시계처럼 창별 값의 흩어짐을 쓰면 창마다
    기울기가 부정확해 오차를 크게 부풀린다. 대신 이웃 잔차의 상관만큼 회귀 오차를 늘린다."""
    nominal = guess_nominal_bph(3600 / fit.beat)
    if not nominal:
        return None, None, 0.0
    r = fit.resid
    rho = float(np.clip(np.corrcoef(r[:-1], r[1:])[0, 1], 0, 0.9)) if len(r) > 10 else 0.0
    se = SECONDS_PER_DAY * fit.beat_se / fit.beat * np.sqrt((1 + rho) / (1 - rho))
    return nominal, (3600 / nominal / fit.beat - 1) * SECONDS_PER_DAY, float(se)


def find_other_clocks(an, max_extra=MAX_EXTRA):
    """an: 주 시계 분석 결과(Analysis). 주 시계 말고 찾은 시계들 [OtherClock, ...]"""
    known = [sg.fit for sg in an.segments]
    envs = [_band_envelope(an.raw, an.sr, b) for b in BANDS]
    found = []
    for _ in range(max_extra):
        beats = [known[0].beat] + [o.fit.beat for o in found]
        best = None
        for band, (env, fs) in zip(BANDS, envs):
            r = env
            for f in known:
                r = _subtract(r, fs, f)
            r = np.clip(r - np.median(r), 0, None)
            p = _periodicity(r, fs, beats)
            if p and (best is None or p[1] > best[1]):
                best = (band, p[1], p[0], r, fs)
        if best is None or best[1] < MIN_SCORE:
            break
        band, score, beat, r, fs = best
        fit = _track(r, fs, beat)
        if fit is None or len(fit.ticks) < MIN_DETECTION * fit.expected or fit.jitter > MAX_JITTER * fit.beat:
            break
        nominal, rate, se = _rate(fit)
        found.append(OtherClock(band=band, score=score, fit=fit, nominal_bph=nominal, rate=rate, rate_se=se,
                                profile=_profile(r, fs, fit)))
        known.append(fit)
    return found

"""진폭 추정: 한 박 안의 언락(탈진기가 풀리는 소리) → 드롭(톱니가 떨어지는 큰 소리) 간격으로 계산한다.

밸런스가 θ(t) = A·sin(2πt/T) 로 흔들린다면, 리프트각 LA만큼 도는 데 걸리는 시간 Δt는
    Δt = (T/π)·asin(LA / 2A)   →   A = LA / (2·sin(π·Δt/T))
T는 한 주기(두 박). 리프트각은 무브먼트 고유값이라 모르면 가정해야 하고, 그만큼 절대값은 불확실하다.
하지만 A ≈ LA·T/(2π·Δt) 이므로 같은 시계의 녹음끼리 비교(진폭이 줄었는지)는 리프트각과 거의 무관하다.
"""
from dataclasses import dataclass, field

import numpy as np
import scipy.signal as s

DEFAULT_LIFT_ANGLE = 52.0          # 스위스 레버의 흔한 값. Slava 5671의 공식 값은 확인하지 못함
A_MIN, A_MAX = 140.0, 380.0
MIN_SNR = 8.0                      # 언락 피크가 바닥 흔들림의 이 배수를 넘어야 믿는다        # 물리적으로 가능한 진폭 범위 → 언락 소리를 찾을 시간 범위를 정한다


@dataclass
class Amplitude:
    deg: float                 # 틱·톡 평균 진폭 (도)
    lo: float                  # 95% 범위
    hi: float
    tick_deg: float | None
    tock_deg: float | None
    dt_ms: tuple               # (틱 Δt, 톡 Δt) ms
    lift: float
    reliable: bool             # 언락 소리가 뚜렷하고 틱·톡 값이 서로 맞으면 True
    note: str = ''
    profiles: list = field(default_factory=list, repr=False)   # 진단 그래프용 [(시각 배열, 곡선, 언락 시각, 드롭 시각)]


def amplitude_of(dt, period, lift):
    return float(np.degrees(np.radians(lift) / (2 * np.sin(np.pi * dt / period))))


def _dt_range(period, lift):
    dt = lambda a: period / np.pi * np.arcsin(np.radians(lift) / (2 * np.radians(a)))
    return dt(A_MAX), dt(A_MIN)


def _unlock_to_drop(env, sr, ticks, dt_lo, dt_hi, pick=None):
    """틱들을 겹쳐 만든 중앙값 소리 크기 곡선에서 드롭 피크와 그 앞 언락 피크 사이 시간.
    반환: (Δt 초, 언락 피크의 신호 대 잡음비, 진단용 곡선) 또는 None"""
    pre, post = int((dt_hi + .004) * sr), int(.006 * sr)
    idx = np.array([int(round(t * sr)) for t in ticks])
    idx = idx[(idx - pre > 0) & (idx + post < len(env))]
    if pick is not None:
        idx = idx[pick % len(idx)]
    if len(idx) < 8:
        return None
    m = np.median(np.stack([env[i - pre:i + post] for i in idx]), 0)
    tt = np.arange(-pre, post) / sr
    main = int(np.argmax(np.where((tt > -.001) & (tt < .005), m, 0)))
    win = (tt > tt[main] - dt_hi) & (tt < tt[main] - dt_lo)
    pk, pr = s.find_peaks(np.where(win, m, 0), prominence=0)
    if not len(pk):
        return None
    k = pk[np.argmax(pr['prominences'])]
    floor = m[: max(pre // 4, 8)]                                  # 언락보다 훨씬 앞의 조용한 바닥
    base = np.median(floor) + 1e-15
    noise = 1.4826 * np.median(np.abs(floor - base)) + 1e-15
    return tt[main] - tt[k], float((m[k] - base) / noise), (tt, m / base, tt[k], tt[main])


def estimate_amplitude(raw, sr, fit, lift=DEFAULT_LIFT_ANGLE, n_boot=60, seed=0):
    """fit: 템플릿 보정까지 끝난 BeatFit. 원본(raw)을 쓴다 — 스펙트럴 게이팅은 약한 언락 소리를 지운다."""
    hi = min(20000, sr / 2 - 500)
    xb = s.sosfiltfilt(s.butter(4, [2000, hi], 'bandpass', fs=sr, output='sos'), raw)
    env = s.sosfiltfilt(s.butter(2, 2000, fs=sr, output='sos'), np.abs(s.hilbert(xb)))
    period = 2 * fit.beat
    dt_lo, dt_hi = _dt_range(period, lift)
    rng = np.random.default_rng(seed)
    per, boots, ratios, profiles = [], [], [], []
    for p in (0, 1):
        tk = fit.ticks[fit.parity == p]
        r = _unlock_to_drop(env, sr, tk, dt_lo, dt_hi)
        if r is None:
            per.append(None); continue
        bs = [_unlock_to_drop(env, sr, tk, dt_lo, dt_hi, rng.integers(0, len(tk), len(tk))) for _ in range(n_boot)]
        bs = np.array([amplitude_of(b[0], period, lift) for b in bs if b])
        per.append((r[0], amplitude_of(r[0], period, lift)))
        boots.append(bs)
        ratios.append(r[1])
        profiles.append(r[2])
    got = [x for x in per if x]
    if not got:
        return None
    deg = float(np.mean([a for _, a in got]))
    allb = np.concatenate(boots) if boots else np.array([deg])
    spread = abs(got[0][1] - got[1][1]) if len(got) == 2 else np.inf
    lo, hi_ = float(np.percentile(allb, 2.5)), float(np.percentile(allb, 97.5))
    reliable = len(got) == 2 and min(ratios) >= MIN_SNR and spread <= 30 and hi_ - lo <= 40
    note = '' if reliable else ('언락 소리가 약하거나 틱·톡 값이 서로 달라 참고용입니다. '
                                '시계 뒷면에 마이크를 바짝 대고 조용한 곳에서 녹음하면 좋아집니다.')
    return Amplitude(deg=deg, lo=min(lo, deg), hi=max(hi_, deg),
                     tick_deg=per[0][1] if per[0] else None, tock_deg=per[1][1] if per[1] else None,
                     dt_ms=tuple(round(x[0] * 1000, 2) if x else None for x in per), lift=lift,
                     reliable=reliable, note=note, profiles=profiles)

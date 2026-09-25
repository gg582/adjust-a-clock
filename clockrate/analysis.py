"""녹음 한 개를 분석해 구간별 일오차를 계산한다 (그래프·파일 출력 없음)."""
from dataclasses import dataclass, field

import numpy as np

from .amplitude import DEFAULT_LIFT_ANGLE, Amplitude, estimate_amplitude
from .audio import denoise, envelope
from .segments import detect_swish, find_cuts, segments_between
from .ticks import BeatFit, detect_onsets, estimate_beat, fit_beats, refine_beats

STD_BPH = [3600, 7200, 9000, 10800, 11880, 12000, 12600, 14400, 16200, 18000, 19800, 21600, 25200, 28800, 36000]
DEFAULT_BPH = 18000        # Slava 5671 등 자명종·구형 손목시계에 흔한 값
BPH_MISMATCH = 0.01        # 규격과 측정이 이보다 더 다르면 규격을 잘못 넣은 것으로 본다
DEVICE_CLOCK_TOL = 3.0      # 녹음 장비 클럭 오차 (초/일, 휴대폰 기준 대략값)
SECONDS_PER_DAY = 86400

REF_AUTO = ('자동', 'auto')
REF_NOMINAL = ('규격', 'nominal')
REF_FIRST = ('구간1', 'first')


class AnalysisError(RuntimeError):
    pass


@dataclass
class Segment:
    name: str
    t0: float
    t1: float
    fit: BeatFit
    rate: float = 0.0        # 초/일, +면 빠름
    rate_se: float = 0.0
    is_reference: bool = False
    windows: list = field(default_factory=list)   # [(창 시작, 창 끝, 초/일), ...]
    amplitude: Amplitude | None = None

    @property
    def bph(self):
        return 3600 / self.fit.beat

    @property
    def significant(self):
        return abs(self.rate) > 2 * self.rate_se + DEVICE_CLOCK_TOL

    @property
    def verdict(self):
        if self.is_reference:
            return '기준'
        if not self.significant:
            return '오차 범위 안 (사실상 정확)'
        return '빠름' if self.rate > 0 else '느림'


@dataclass
class Analysis:
    sr: int
    raw: np.ndarray
    clean: np.ndarray
    duration: float
    split_mode: str
    cuts: list
    swish_t: np.ndarray
    swish_db: np.ndarray
    measured_bph: float
    nominal_bph: float | None
    reference: str             # 'nominal' | 'first'
    base_beat: float
    segments: list

    @property
    def bph_mismatch(self):
        """지정한 규격이 측정값과 1% 넘게 다르면 True (예: 28800 bph 시계를 기본값 18000으로 잰 경우)."""
        return bool(self.nominal_bph and abs(self.measured_bph / self.nominal_bph - 1) > BPH_MISMATCH)

    @property
    def reference_label(self):
        return f'규격 {self.nominal_bph:.0f} bph' if self.reference == 'nominal' else '구간 1'


def guess_nominal_bph(measured):
    near = min(STD_BPH, key=lambda b: abs(b / measured - 1))
    return near if abs(near / measured - 1) < BPH_MISMATCH else None


def rate_of(fit, base_beat):
    return (base_beat / fit.beat - 1) * SECONDS_PER_DAY


def window_rates(fit, base_beat, window):
    """구간을 window초씩 잘라 각각의 일오차를 구한다 (속도 안정성 확인용)."""
    y, n, p = fit.ticks, fit.n, fit.parity
    out = []
    for a in np.arange(y[0], y[-1], window):
        k = (y >= a) & (y < a + window)
        if y[-1] - a < 0.8 * window or k.sum() < 10 or len(np.unique(p[k])) < 2:
            continue
        A = np.c_[np.ones(k.sum()), n[k], p[k]]
        coef, *_ = np.linalg.lstsq(A, y[k], rcond=None)
        out.append((float(a), float(min(a + window, y[-1])), (base_beat / coef[1] - 1) * SECONDS_PER_DAY))
    return out


def analyze_signal(x, sr, split='없음', bph=DEFAULT_BPH, reference='자동', names=(), window=None,
                   lift=DEFAULT_LIFT_ANGLE):
    """
    split:     '없음'(기본) | '자동'(레버 소리로 분할) | '3.5,9.2'
    bph:       규격 진동수 (기본 18000). None이면 측정값에서 ±1% 이내의 표준값을 자동 선택
    reference: '자동'(규격이 있으면 규격, 자동 추정에 실패하면 구간 1) | '규격' | '구간1'
    window:    시간대별 안정성 창 길이(초). None이면 녹음 길이에 맞춰 자동, 0이면 끔
    lift:      진폭 계산용 리프트각(도). None이면 진폭을 계산하지 않음
    """
    duration = len(x) / sr
    if duration < 3:
        raise AnalysisError('녹음이 너무 짧습니다 (3초 이상 필요, 구간당 30초 이상 권장).')

    clean = denoise(x, sr)
    env = envelope(clean, sr)
    beat0 = estimate_beat(env, sr)
    onsets = detect_onsets(env, sr, beat0)

    swish_t, swish_db, events = detect_swish(x, sr)
    cuts = find_cuts(split, events, duration)

    segs = []
    for t0, t1 in segments_between(cuts, duration):
        fit = fit_beats(onsets[(onsets >= t0) & (onsets <= t1)], beat0)
        if fit is None:
            continue
        fit = refine_beats(fit, clean, sr)
        i = len(segs)
        label = f'구간 {i + 1}' + (f' · {names[i]}' if i < len(names) and names[i] else '')
        amp = estimate_amplitude(x, sr, fit, lift) if lift else None
        segs.append(Segment(name=label, t0=t0, t1=t1, fit=fit, amplitude=amp))
    if not segs:
        raise AnalysisError('틱을 충분히 찾지 못했습니다. 시계에 마이크를 더 가까이 대고 다시 녹음해 주세요.')

    measured = 3600 / np.median([sg.fit.beat for sg in segs])
    nominal = float(bph) if bph else guess_nominal_bph(measured)
    if reference in REF_NOMINAL and not nominal:
        raise AnalysisError(f'측정 진동수 {measured:.1f} bph에 맞는 표준 규격이 없습니다. --bph 로 지정해 주세요.')
    ref = 'first' if reference in REF_FIRST or not nominal else 'nominal'

    first = segs[0].fit
    base_beat = 3600 / nominal if ref == 'nominal' else first.beat
    for sg in segs:
        sg.rate = rate_of(sg.fit, base_beat)
        var = (sg.fit.beat_se / sg.fit.beat) ** 2
        if ref == 'first':
            sg.is_reference = sg is segs[0]
            if not sg.is_reference:
                var += (first.beat_se / first.beat) ** 2
        sg.rate_se = 0.0 if sg.is_reference else SECONDS_PER_DAY * float(np.sqrt(var))
        span = sg.fit.ticks[-1] - sg.fit.ticks[0]
        w = window if window is not None else (10 if span < 90 else 20)
        if w and span >= 2 * w:
            sg.windows = window_rates(sg.fit, base_beat, w)
        # 틱 시각 잔차는 시계 자체의 느린 흔들림 때문에 서로 독립이 아니다. 회귀 오차만 쓰면
        # 신뢰구간이 지나치게 좁아지므로, 창별 값의 흩어짐으로 구한 오차가 더 크면 그걸 쓴다.
        if not sg.is_reference and len(sg.windows) >= 3:
            wr = np.array([r for *_, r in sg.windows])
            sg.rate_se = max(sg.rate_se, float(wr.std(ddof=1) / np.sqrt(len(wr))))

    return Analysis(sr=sr, raw=x, clean=clean, duration=duration, split_mode=split, cuts=cuts,
                    swish_t=swish_t, swish_db=swish_db, measured_bph=measured, nominal_bph=nominal,
                    reference=ref, base_beat=base_beat, segments=segs)

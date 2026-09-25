"""레버 '스윽' 소리 검출과 구간 분할 모드."""
import numpy as np
import scipy.signal as s

SWISH_THRESHOLD_DB = 4.0
LEVER_GUARD = 0.06      # 레버 소리 앞뒤로 분석에서 빼는 여유 (초)
MIN_SEGMENT = 1.5       # 이보다 짧은 구간은 버림 (초)

SPLIT_AUTO = ('자동', 'auto')
SPLIT_NONE = ('없음', 'none')


def detect_swish(x, sr, thr=SWISH_THRESHOLD_DB):
    """짧은 틱은 120 ms 메디안 필터로 지우고, 남는 지속 마찰음(레버 '스윽')을 찾는다.

    반환: (프레임 시각, 기준 대비 지속음 에너지 dB, [(시작, 끝, 세기), ...])
    """
    f, t, Z = s.stft(x, sr, nperseg=1024, noverlap=768)
    band = (f > 1000) & (f < 16000)
    E = 10 * np.log10((np.abs(Z[band]) ** 2).sum(0) + 1e-12)
    hop = t[1] - t[0]
    sw = s.medfilt(E, int(0.12 / hop) | 1)
    sw -= np.median(sw)
    ev, i = [], 0
    while i < len(sw):
        if sw[i] > thr:
            j = i
            while j < len(sw) and sw[j] > thr:
                j += 1
            if t[j - 1] - t[i] > 0.08:
                ev.append((t[i], t[j - 1], float(np.clip(sw[i:j] - thr, 0, None).sum() * hop)))
            i = j
        else:
            i += 1
    return t, sw, ev


def find_cuts(mode, events, duration):
    """분할 모드에 따라 잘라낼 시간 구간 [(시작, 끝), ...] 을 돌려준다.

    '자동': 녹음 앞뒤 조작음을 뺀, 충분히 강한 지속음 이벤트
    '없음': 자르지 않음
    '3.5,9.2': 지정 시각 ±0.15초
    """
    if mode in SPLIT_AUTO:
        return [(a, b) for a, b, w in sorted(events) if a > 0.3 and b < duration - 0.5 and w > 0.15]
    if mode in SPLIT_NONE:
        return []
    try:
        return [(float(v) - 0.15, float(v) + 0.15) for v in str(mode).split(',')]
    except ValueError:
        raise ValueError(f"--분할 값은 '자동', '없음', 또는 쉼표로 구분한 초 단위 시각이어야 합니다: {mode}")


def segments_between(cuts, duration):
    edges = [0.15] + [v for a, b in cuts for v in (a - LEVER_GUARD, b + LEVER_GUARD)] + [duration - 0.3]
    return [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2) if edges[i + 1] - edges[i] > MIN_SEGMENT]

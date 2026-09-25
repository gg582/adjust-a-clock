"""측정값을 '시계를 어떻게 맞출지'로 바꾸는 판단 규칙."""
from dataclasses import dataclass

import numpy as np

DEFAULT_TOLERANCE = 10.0    # 이 안(초/일)이면 조정 완료로 본다


@dataclass
class Grade:
    key: str        # good | warning | serious | critical
    icon: str
    label: str


def fmt_duration(sec):
    """초 → '3분 47초', '1시간 53분' 같은 사람이 읽는 길이."""
    sec = abs(sec)
    if sec < 60:
        return f'{sec:.0f}초' if sec >= 10 else f'{sec:.1f}초'
    if sec < 3600:
        m, s = divmod(round(sec), 60)
        return f'{m}분 {s}초' if s else f'{m}분'
    h, m = divmod(round(sec / 60), 60)
    return f'{h}시간 {m}분' if m else f'{h}시간'


def fast_slow(rate):
    return '빠름' if rate > 0 else '느림'


def headline(rate):
    return f'하루 {fmt_duration(rate)} {fast_slow(rate)}'


def grade_rate(rate, tol=DEFAULT_TOLERANCE):
    a = abs(rate)
    if a <= tol:
        return Grade('good', '◎', '조정 완료')
    if a <= 3 * tol:
        return Grade('warning', '△', '미세 조정 권장')
    if a <= 60:
        return Grade('serious', '▲', '조정 필요')
    return Grade('critical', '✖', '크게 어긋남')


def lever_direction(rate, tol=DEFAULT_TOLERANCE):
    if abs(rate) <= tol:
        return '조속 레버는 그대로 두세요.'
    return '조속 레버를 느림(-, S) 쪽으로 옮기세요.' if rate > 0 else '조속 레버를 빠름(+, F) 쪽으로 옮기세요.'


def grade_beat_error(ms):
    if ms <= 3:
        return Grade('good', '◎', '양호')
    if ms <= 5:
        return Grade('warning', '△', '보통')
    return Grade('serious', '▲', '큼 — 비트 조정(밸런스 정지 위치 맞춤) 권장')


def grade_amplitude(amp):
    """손목시계에서 흔히 쓰는 기준. 리프트각을 가정한 값이라 경계 근처는 참고만 한다."""
    if amp is None:
        return Grade('warning', '△', '측정 못 함')
    a = amp.deg
    if a > 330:
        return Grade('serious', '▲', '너무 큼 — 뱅킹(과진폭) 주의')
    if a >= 250:
        return Grade('good', '◎', '좋음')
    if a >= 200:
        return Grade('warning', '△', '보통')
    return Grade('serious', '▲', '낮음 — 태엽 감김·주유·오염 확인')


def stability(windows):
    """창별 오차의 폭. 반환: (최소, 최대, 판정 문구) 또는 None."""
    if len(windows) < 2:
        return None
    r = [w[2] for w in windows]
    spread = max(r) - min(r)
    word = '안정' if spread <= 15 else ('약간 흔들림' if spread <= 40 else '불안정 — 태엽·자세·녹음 상태 확인')
    return min(r), max(r), spread, word


def quality(fit, span):
    """녹음 상태(길이·검출률·잡음)로 본 측정 신뢰도. 시계 자체의 흔들림은 여기서 보지 않는다.
    반환: (등급, 검출률, [이유], [할 일])"""
    det = len(fit.ticks) / fit.expected
    noise = len(fit.rejected) / max(fit.expected, 1)
    reasons, tips = [], []
    if span < 45:
        reasons.append(f'녹음이 짧음({span:.0f}초)')
        tips.append('1분 이상 녹음하면 더 정확해집니다.')
    if det < 0.9 or noise > 0.05:
        if det < 0.9:
            reasons.append(f'틱을 {det:.0%}만 찾음')
        if noise > 0.05:
            reasons.append(f'잡음 클릭 {len(fit.rejected)}개')
        tips.append('시계 뒷면에 마이크를 바짝 대고 조용한 곳에서 녹음하세요.')
    if not reasons:
        level = '높음'
    elif span >= 20 and det >= 0.8 and noise <= 0.15:
        level = '보통'
    else:
        level = '낮음'
    return level, det, reasons, tips


def next_step(prev_rate, prev_se, rate, se, tol=DEFAULT_TOLERANCE):
    """직전 녹음 → 이번 녹음 사이의 변화로 다음 이동량을 추정.

    레버를 움직인 만큼 속도가 비례해서 바뀐다고 가정한다.
    반환: (변화량 초/일, 안내 문구)
    """
    delta = rate - prev_rate
    if abs(rate) <= tol:
        return delta, '목표 범위 안입니다. 더 건드리지 마세요.'
    noise = max(3.0, 2 * np.hypot(se, prev_se))
    if abs(delta) < noise:
        return delta, ('직전 녹음과 속도 차이가 거의 없습니다. 레버를 움직였다면 헛돌았거나 '
                       '헤어스프링이 레버 핀에서 빠졌을 수 있습니다.')
    ratio = -rate / delta
    if ratio > 0:
        msg = f'직전에 옮긴 방향으로, 그때 옮긴 거리의 약 {ratio:.1f}배 더 옮기세요.'
    else:
        msg = f'직전과 반대 방향으로, 그때 옮긴 거리의 약 {-ratio:.1f}배 되돌리세요.'
    if abs(ratio) > 2.5:
        msg += ' 한 번에 다 옮기지 말고 나눠서 확인하세요.'
    return delta, msg

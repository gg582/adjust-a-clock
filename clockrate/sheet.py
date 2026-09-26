"""무브먼트 사양 시트(INI)를 읽고 측정값과 비교한다."""
import configparser
from dataclasses import dataclass, field

DEFAULT_BEAT_ERROR_MAX_MS = 5.0

PASS, BORDER, FAIL, NA = '합격', '경계', '불합격', '측정 불가'


class SheetError(ValueError):
    pass


@dataclass
class Sheet:
    path: str
    name: str
    bph: float | None
    lift: float | None
    tol: dict = field(default_factory=dict)       # 키 → (최소, 최대) — 한쪽 한계면 (None, 값) 등
    comments: dict = field(default_factory=dict)  # 키 → 출처 주석
    meta: dict = field(default_factory=dict)


@dataclass
class Check:
    item: str
    measured: str
    limit: str
    status: str
    note: str = ''
    key: str = ''       # 시트의 [tolerance] 키 — 출처 주석을 찾는 데 쓴다


def _num(s):
    s = s.strip()
    return float(s) if s else None


def _range(s):
    parts = [p.strip() for p in s.split(',') if p.strip()]
    if not parts:
        return None
    if len(parts) == 1:
        return (None, float(parts[0]))
    if len(parts) == 2:
        return (float(parts[0]), float(parts[1]))
    raise SheetError(f'범위는 "최소, 최대" 형식이어야 합니다: {s}')


def _source_comments(path):
    """값 뒤의 ; 주석을 키별 출처로 모은다 (configparser는 주석을 버리므로 직접 읽는다)."""
    out = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            if '=' in line and ';' in line and not line.lstrip().startswith(';'):
                key, rest = line.split('=', 1)
                out[key.strip()] = rest.split(';', 1)[1].strip()
    return out


def load_sheet(path):
    cp = configparser.ConfigParser(inline_comment_prefixes=(';',), interpolation=None)
    try:
        with open(path, encoding='utf-8') as f:
            cp.read_file(f)
    except (OSError, configparser.Error) as e:
        raise SheetError(f'시트를 읽을 수 없습니다: {path} ({e})')
    get = lambda sec, key: cp.get(sec, key, fallback='').strip()
    try:
        bph = _num(get('oscillator', 'bph'))
        period = _num(get('oscillator', 'period_s'))
        if bph is None and period:
            bph = 7200 / period
        lift = _num(get('oscillator', 'lift_angle_deg'))
        tol = {}
        if cp.has_section('tolerance'):
            for key, val in cp.items('tolerance'):
                r = _range(val)
                if r is not None:
                    tol[key] = r
    except ValueError as e:
        raise SheetError(f'시트 값 형식 오류: {path} ({e})')
    meta = dict(cp.items('meta')) if cp.has_section('meta') else {}
    return Sheet(path=path, name=meta.get('name') or path, bph=bph, lift=lift, tol=tol,
                 comments=_source_comments(path), meta=meta)


def _limit_text(r, unit):
    lo, hi = r
    if lo is None:
        return f'{hi:g}{unit} 이하'
    if lo == -hi:
        return f'±{hi:g}{unit}'
    return f'{lo:g}–{hi:g}{unit}'


def _judge(value, spread, r):
    """측정값과 불확실성(±spread)이 범위 r=(lo, hi) 안에 있는지."""
    lo, hi = r
    lo = -float('inf') if lo is None else lo
    if not lo <= value <= hi:
        return FAIL
    if lo <= value - spread and value + spread <= hi:
        return PASS
    return BORDER


def compare(sheet, sg, an):
    """구간 하나의 측정값을 시트 공차와 비교한다. 반환: [Check, ...]"""
    t = sheet.tol
    checks = []

    if sheet.bph:
        dev = (sg.bph / sheet.bph - 1) * 100
        checks.append(Check('진동수', f'{sg.bph:.1f} bph', f'{sheet.bph:.0f} bph',
                            PASS if abs(dev) < 1 else FAIL,
                            f'편차 {dev:+.3f}% (하루 오차로 환산한 값이 아래 항목)'))

    if 'rate_s_per_day' in t and an.reference == 'nominal':
        ci = 2 * sg.rate_se
        st = _judge(sg.rate, ci, t['rate_s_per_day'])
        temp = t.get('rate_temperature_c')
        note = f'95% 범위 {sg.rate - ci:+.1f} ~ {sg.rate + ci:+.1f}'
        if temp:
            note += f' · 사양은 {temp[0]:g}–{temp[1]:g}°C 기준'
        checks.append(Check('하루 오차', f'{sg.rate:+.1f} ± {ci:.1f} 초/일',
                            _limit_text(t['rate_s_per_day'], '초/일'), st, note, 'rate_s_per_day'))

    if 'regulator_range_s_per_day' in t and an.reference == 'nominal':
        lo, hi = t['regulator_range_s_per_day']
        ok = (lo if lo is not None else -hi) <= -sg.rate <= hi
        checks.append(Check('조속 레버로 보정 가능', f'필요 보정 {-sg.rate:+.1f} 초/일',
                            _limit_text(t['regulator_range_s_per_day'], '초/일'), PASS if ok else FAIL,
                            '레버가 가운데 있다고 볼 때 끝까지 옮겨 바꿀 수 있는 양'
                            + ('' if ok else ' — 레버 위치에 따라 부족할 수 있음'), 'regulator_range_s_per_day'))

    amp = sg.amplitude
    if 'amplitude_deg' in t:
        if amp is None:
            checks.append(Check('진폭', '측정 못 함', _limit_text(t['amplitude_deg'], '°'), NA,
                                '언락 소리를 찾지 못함', 'amplitude_deg'))
        else:
            st = _judge(amp.deg, (amp.hi - amp.lo) / 2, t['amplitude_deg'])
            note = f'리프트각 {amp.lift:g}° 기준, 95% 범위 {amp.lo:.0f}–{amp.hi:.0f}°'
            if not amp.reliable:
                note += ' · 틱·톡 값이 달라 참고용'
                if st in (PASS, FAIL):      # 참고용 값만으로는 합격·불합격을 단정하지 않는다
                    st = BORDER
            hi = t['amplitude_deg'][1]
            if amp.deg > hi:
                note += ' · 상한 초과 — 완전히 감은 상태에서 «пристук»(빨라짐) 확인 필요'
            checks.append(Check('진폭', f'약 {amp.deg:.0f}°', _limit_text(t['amplitude_deg'], '°'), st, note,
                                'amplitude_deg'))

    be_max = t.get('beat_error_ms_max', (None, DEFAULT_BEAT_ERROR_MAX_MS))
    be = sg.fit.beat_err * 1000
    checks.append(Check('비트 에러', f'{be:.1f} ms', _limit_text(be_max, ' ms'), PASS if be <= be_max[1] else FAIL,
                        '' if 'beat_error_ms_max' in t else '사양에 수치 없음 — 도구 기준값', 'beat_error_ms_max'))

    if 'wind_rate_difference_s_per_day' in t:
        checks.append(Check('태엽 상태별 오차 차이', '—', _limit_text(t['wind_rate_difference_s_per_day'], '초/일'), NA,
                            '완전히 감은 직후와 약 24시간 뒤를 각각 녹음해 두 하루 오차의 차이를 보세요', 'wind_rate_difference_s_per_day'))
    if 'amplitude_variation_deg' in t:
        checks.append(Check('진폭 변동', '—', _limit_text(t['amplitude_variation_deg'], '°'), NA,
                            '같은 조건에서 여러 번 녹음해 진폭 차이를 보세요', 'amplitude_variation_deg'))
    if 'power_reserve_h_min' in t:
        checks.append(Check('파워 리저브', '—', f'{t["power_reserve_h_min"][1]:g}시간 이상', NA,
                            '끝까지 감고 멈출 때까지의 시간을 직접 재세요', 'power_reserve_h_min'))
    if 'self_start_turns_max' in t:
        checks.append(Check('자동 출발', '—', f'태엽 {t["self_start_turns_max"][1]:g}바퀴 이내', NA,
                            '완전히 풀린 상태에서 1바퀴 감았을 때 스스로 가는지 보세요', 'self_start_turns_max'))
    return checks


def summary(checks):
    n = {s: sum(c.status == s for c in checks) for s in (PASS, BORDER, FAIL, NA)}
    if n[FAIL]:
        return f'공차 벗어남 {n[FAIL]}개'
    if n[BORDER]:
        return f'측정 가능한 항목 모두 공차 안 (경계 {n[BORDER]}개)'
    return '측정 가능한 항목 모두 공차 안'


def check_lines(sheet, checks):
    icon = {PASS: '◎', BORDER: '△', FAIL: '✖', NA: '·'}
    lines = ['', f' ▶ 사양 비교 — {sheet.name}: {summary(checks)}']
    w = max(len(c.item) for c in checks)
    for c in checks:
        lines.append(f'   {icon[c.status]} {c.status:<5} {c.item:<{w}}  {c.measured:<20} 사양 {c.limit}')
        if c.note:
            lines.append(f'{"":{w + 14}}{c.note}')
        if c.key in sheet.comments:
            lines.append(f'{"":{w + 14}}근거: {sheet.comments[c.key]}')
    src = sheet.meta.get('source_1')
    if src:
        lines.append(f'   출처: {src.split(" — ")[0]}')
    return lines


def to_json(sheet, checks):
    return dict(sheet=sheet.path, name=sheet.name, summary=summary(checks),
                checks=[dict(item=c.item, measured=c.measured, limit=c.limit, status=c.status, note=c.note,
                             source=sheet.comments.get(c.key, '')) for c in checks])

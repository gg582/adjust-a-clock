"""분석 결과를 '시계를 맞출 때 쓰는' 한국어 요약과 JSON으로 만든다."""
from .advice import (DEFAULT_TOLERANCE, fmt_duration, grade_amplitude, grade_beat_error, grade_rate, headline,
                     lever_direction, next_step, quality, stability)
from .analysis import guess_nominal_bph
from .segments import SPLIT_NONE

RULE = '━' * 44


def _signed(sec):
    return ('+' if sec > 0 else '-') + fmt_duration(sec)


def segment_facts(sg, prev=None, tol=DEFAULT_TOLERANCE, relative_to=None):
    """구간 하나에 대한 판단 결과 묶음 (텍스트·그래프·JSON이 같이 쓴다)."""
    f = sg.fit
    span = f.ticks[-1] - f.ticks[0]
    facts = dict(
        grade=grade_rate(sg.rate, tol),
        headline=headline(sg.rate) if relative_to is None else f'{relative_to}보다 {headline(sg.rate)}', lever=lever_direction(sg.rate, tol),
        drift={'1일': sg.rate, '1주': sg.rate * 7, '30일': sg.rate * 30},
        beat=grade_beat_error(f.beat_err * 1000), amp=grade_amplitude(sg.amplitude), stability=stability(sg.windows),
        quality=quality(f, span), step=None)
    if prev is not None:
        delta, msg = next_step(prev['rate'], prev['ci95'] / 2, sg.rate, sg.rate_se, tol)
        facts['step'] = (prev['file'], delta, msg)
        if prev.get('amplitude') and prev.get('amplitude_reliable') and sg.amplitude and sg.amplitude.reliable:
            facts['amp_change'] = (prev['file'], sg.amplitude.deg - prev['amplitude'])
    return facts


def amplitude_line(sg, facts):
    a = sg.amplitude
    if a is None:
        return '   진폭          측정 못 함 (언락 소리를 찾지 못함)'
    g = facts['amp']
    txt = (f'   진폭          약 {a.deg:.0f}° ({a.lo:.0f}–{a.hi:.0f}°, 틱 {a.tick_deg:.0f}° · 톡 {a.tock_deg:.0f}°)'
           if a.tick_deg and a.tock_deg else f'   진폭          약 {a.deg:.0f}°')
    txt += f'  {g.icon} {g.label}' if a.reliable else '  (참고용)'
    lines = [txt, f'                 리프트각 {a.lift:.0f}° 가정 — 같은 시계끼리 비교할 때 가장 정확']
    if 'amp_change' in facts:
        pf, d = facts['amp_change']
        lines.append(f'                 직전 녹음({pf}) 대비 {d:+.0f}°')
    if a.note:
        lines.append(f'                 ※ {a.note}')
    return lines


def _segment_block(sg, facts):
    f = sg.fit
    g = facts['grade']
    lines = [f' {g.icon} {g.label}   {facts["headline"]}   ({sg.rate:+.1f} ± {2 * sg.rate_se:.1f} 초/일)', '',
             ' ▶ 할 일', f'   {facts["lever"]}']
    if facts['step']:
        pf, delta, msg = facts['step']
        lines += [f'   직전 녹음({pf}) 대비 {delta:+.1f} 초/일 변화 →', f'   {msg}']
    lines += ['', ' ▶ 이대로 두면', '   ' + ' · '.join(f'{k} {_signed(v)}' for k, v in facts['drift'].items())]
    b = facts['beat']
    lines += ['', ' ▶ 시계 상태', f'   비트 에러     {f.beat_err * 1000:.1f} ms  {b.icon} {b.label}']
    lines += amplitude_line(sg, facts)
    st = facts['stability']
    if st:
        w = sg.windows[0][1] - sg.windows[0][0]
        lines.append(f'   속도 안정성   {st[0]:+.0f} ~ {st[1]:+.0f} 초/일 ({w:.0f}초 단위, 폭 {st[2]:.0f})  {st[3]}')
    else:
        lines.append('   속도 안정성   녹음이 짧아 확인 못 함 (20초 이상 필요)')
    level, det, reasons, tips = facts['quality']
    lines += ['', f' ▶ 측정 신뢰도  {level}' + (f' ({", ".join(reasons)})' if reasons else ''),
              f'   틱 {len(f.ticks)}/{f.expected}개 사용 ({det:.0%})'
              + (f', 놓친 틱 {f.filled}개 다시 찾음' if f.filled else '')
              + (f', 잡음 클릭 {len(f.rejected)}개 제외' if len(f.rejected) else ''),
              f'   틱 시각 흔들림 {f.jitter * 1e6:.0f} µs · 실측 진동수 {sg.bph:.1f} bph']
    lines += [f'   ※ {t}' for t in tips]
    return lines


def _relative_block(sg, first):
    """구간 1 기준 비교 모드: 절대 오차가 아니라 기준 구간 대비 변화만 말한다."""
    f = sg.fit
    ci = 2 * sg.rate_se
    if abs(sg.rate) <= ci:
        verdict = '변화 없음 (차이가 오차 범위 안)'
    else:
        verdict = f'{first.name}보다 {"빨라짐" if sg.rate > 0 else "느려짐"}'
    level, det, reasons, tips = quality(f, f.ticks[-1] - f.ticks[0])
    return [f' {sg.rate:+.1f} ± {ci:.1f} 초/일  →  {verdict}',
            f'   비트 에러 {f.beat_err * 1000:.1f} ms'
            + (f' · 진폭 약 {sg.amplitude.deg:.0f}°' if sg.amplitude else '') + f' · 측정 신뢰도 {level}'
            + (f' ({", ".join(reasons)})' if reasons else '') + f' · 틱 {len(f.ticks)}/{f.expected}개']


def summary_lines(name, an, prev=None, tol=DEFAULT_TOLERANCE):
    ref = f'{an.nominal_bph:.0f} bph 기준' if an.reference == 'nominal' else '구간 1 기준'
    lines = [RULE, f' {name}   (녹음 {an.duration:.0f}초 · {ref})', RULE]
    if an.bph_mismatch:
        near = guess_nominal_bph(an.measured_bph)
        lines += [f' ※ 주의: 실측 {an.measured_bph:.0f} bph가 규격 {an.nominal_bph:.0f} bph와 '
                  f'{abs(an.measured_bph / an.nominal_bph - 1) * 100:.1f}% 다릅니다. 규격을 잘못 넣은 것 같습니다 — '
                  + (f'--bph {near} 로 다시 실행하세요.' if near else '--bph 값을 확인하세요.'), '']
    segs = an.segments
    if len(segs) == 1:
        return lines + _segment_block(segs[0], segment_facts(segs[0], prev, tol))

    if an.split_mode not in SPLIT_NONE:
        lines.append(f' 레버 소리 {len(an.cuts)}개: ' + ', '.join(f'{a:.1f}초' for a, _ in an.cuts))
    for sg in segs:
        lines += ['', f' ── {sg.name} ({sg.t0:.0f}–{sg.t1:.0f}초) ──']
        if sg.is_reference:
            lines.append(' 기준 구간 (다른 구간을 이 구간과 비교)')
        elif an.reference == 'first':
            lines += _relative_block(sg, segs[0])
        else:
            lines += _segment_block(sg, segment_facts(sg, None, tol))
    if an.reference == 'first' and any(2 * sg.rate_se > 5 for sg in segs[1:]):
        lines += ['', ' ※ 구간이 짧아 작은 차이는 가려낼 수 없습니다. 레버 위치마다 1분 이상 녹음하세요.']
    lines += ['', ' ▶ 레버 효과 (앞 구간 대비)']
    for a, b in zip(segs, segs[1:]):
        lines.append(f'   {a.name} → {b.name}: {b.rate - a.rate:+.1f} 초/일')
    return lines


def _grade_json(g):
    return dict(key=g.key, label=g.label)


def to_json(path, an, prev=None, tol=DEFAULT_TOLERANCE):
    segs = []
    for sg in an.segments:
        fx = segment_facts(sg, prev if len(an.segments) == 1 else None, tol)
        level, det, reasons, tips = fx['quality']
        st = fx['stability']
        segs.append(dict(
            name=sg.name, start=round(sg.t0, 2), end=round(sg.t1, 2),
            rate_s_per_day=round(sg.rate, 1), ci95=round(2 * sg.rate_se, 1),
            headline=fx['headline'], grade=_grade_json(fx['grade']), action=fx['lever'],
            next_step=dict(previous=fx['step'][0], change=round(fx['step'][1], 1), advice=fx['step'][2])
            if fx['step'] else None,
            drift_s={k: round(v, 1) for k, v in fx['drift'].items()},
            beat_error_ms=round(sg.fit.beat_err * 1000, 2), beat_error_grade=_grade_json(fx['beat']),
            stability=dict(min=round(st[0], 1), max=round(st[1], 1), spread=round(st[2], 1), label=st[3]) if st else None,
            windows=[[round(a, 1), round(b, 1), round(r, 1)] for a, b, r in sg.windows],
            quality=dict(level=level, reasons=reasons, tips=tips, ticks_used=len(sg.fit.ticks), ticks_expected=sg.fit.expected,
                         recovered=sg.fit.filled, noise_clicks=len(sg.fit.rejected),
                         jitter_us=round(sg.fit.jitter * 1e6)),
            amplitude=dict(deg=round(sg.amplitude.deg), lo=round(sg.amplitude.lo), hi=round(sg.amplitude.hi),
                           tick_deg=round(sg.amplitude.tick_deg) if sg.amplitude.tick_deg else None,
                           tock_deg=round(sg.amplitude.tock_deg) if sg.amplitude.tock_deg else None,
                           unlock_to_drop_ms=list(sg.amplitude.dt_ms), lift_angle=sg.amplitude.lift,
                           reliable=sg.amplitude.reliable, grade=_grade_json(fx['amp'])) if sg.amplitude else None,
            measured_bph=round(sg.bph, 2)))
    return dict(file=path, duration=round(an.duration, 2), nominal_bph=an.nominal_bph, reference=an.reference,
                bph_mismatch=an.bph_mismatch, tolerance_s_per_day=tol,
                cuts=[[round(a, 2), round(b, 2)] for a, b in an.cuts], segments=segs)

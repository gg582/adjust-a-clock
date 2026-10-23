"""분석 결과를 '시계를 맞출 때 쓰는' 한국어 요약과 JSON으로 만든다."""
import numpy as np

from .advice import (DEFAULT_TOLERANCE, fmt_duration, grade_amplitude, grade_beat_error, grade_rate, headline,
                     lever_direction, next_step, quality, stability)
from .analysis import guess_nominal_bph
from .i18n import tr, use_lang
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
        headline=headline(sg.rate) if relative_to is None else tr('{name}보다 {headline}', name=relative_to,
                                                                  headline=headline(sg.rate)),
        lever=lever_direction(sg.rate, tol),
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
        return [tr('   진폭          측정 못 함 (언락 소리를 찾지 못함)')]
    g = facts['amp']
    txt = (tr('   진폭          약 {deg:.0f}° ({lo:.0f}–{hi:.0f}°, 틱 {tick:.0f}° · 톡 {tock:.0f}°)',
              deg=a.deg, lo=a.lo, hi=a.hi, tick=a.tick_deg, tock=a.tock_deg)
           if a.tick_deg and a.tock_deg else tr('   진폭          약 {deg:.0f}°', deg=a.deg))
    txt += f'  {g.icon} {g.label}' if a.reliable else tr('  (참고용)')
    lines = [txt, tr('                 리프트각 {lift:.0f}° 가정 — 같은 시계끼리 비교할 때 가장 정확', lift=a.lift)]
    if 'amp_change' in facts:
        pf, d = facts['amp_change']
        lines.append(tr('                 직전 녹음({pf}) 대비 {d:+.0f}°', pf=pf, d=d))
    if a.note:
        lines.append(f'                 ※ {a.note}')
    return lines


def _segment_block(sg, facts):
    f = sg.fit
    g = facts['grade']
    lines = [tr(' {icon} {label}   {headline}   ({rate:+.1f} ± {ci:.1f} 초/일)',
                icon=g.icon, label=g.label, headline=facts['headline'], rate=sg.rate, ci=2 * sg.rate_se), '',
             tr(' ▶ 할 일'), f'   {facts["lever"]}']
    if facts['step']:
        pf, delta, msg = facts['step']
        lines += [tr('   직전 녹음({pf}) 대비 {delta:+.1f} 초/일 변화 →', pf=pf, delta=delta), f'   {msg}']
    lines += ['', tr(' ▶ 이대로 두면'), '   ' + ' · '.join(f'{tr(k)} {_signed(v)}' for k, v in facts['drift'].items())]
    b = facts['beat']
    lines += ['', tr(' ▶ 시계 상태'),
              tr('   비트 에러     {be:.1f} ms  {icon} {label}', be=f.beat_err * 1000, icon=b.icon, label=b.label)]
    lines += amplitude_line(sg, facts)
    st = facts['stability']
    if st:
        w = sg.windows[0][1] - sg.windows[0][0]
        lines.append(tr('   속도 안정성   {lo:+.0f} ~ {hi:+.0f} 초/일 ({w:.0f}초 단위, 폭 {spread:.0f})  {word}',
                        lo=st[0], hi=st[1], w=w, spread=st[2], word=st[3]))
    else:
        lines.append(tr('   속도 안정성   녹음이 짧아 확인 못 함 (20초 이상 필요)'))
    level, det, reasons, tips = facts['quality']
    lines += ['', tr(' ▶ 측정 신뢰도  {level}', level=level) + (f' ({", ".join(reasons)})' if reasons else ''),
              tr('   틱 {used}/{expected}개 사용 ({det:.0%})', used=len(f.ticks), expected=f.expected, det=det)
              + (tr(', 놓친 틱 {n}개 다시 찾음', n=f.filled) if f.filled else '')
              + (tr(', 잡음 클릭 {n}개 제외', n=len(f.rejected)) if len(f.rejected) else ''),
              tr('   틱 시각 흔들림 {us:.0f} µs · 실측 진동수 {bph:.1f} bph', us=f.jitter * 1e6, bph=sg.bph)]
    lines += [f'   ※ {t}' for t in tips]
    return lines


def _relative_block(sg, first):
    """구간 1 기준 비교 모드: 절대 오차가 아니라 기준 구간 대비 변화만 말한다."""
    f = sg.fit
    ci = 2 * sg.rate_se
    if abs(sg.rate) <= ci:
        verdict = tr('변화 없음 (차이가 오차 범위 안)')
    else:
        verdict = tr('{name}보다 {dir}', name=first.name, dir=tr('빨라짐') if sg.rate > 0 else tr('느려짐'))
    level, det, reasons, tips = quality(f, f.ticks[-1] - f.ticks[0])
    return [tr(' {rate:+.1f} ± {ci:.1f} 초/일  →  {verdict}', rate=sg.rate, ci=ci, verdict=verdict),
            tr('   비트 에러 {be:.1f} ms', be=f.beat_err * 1000)
            + (tr(' · 진폭 약 {deg:.0f}°', deg=sg.amplitude.deg) if sg.amplitude else '')
            + tr(' · 측정 신뢰도 {level}', level=level)
            + (f' ({", ".join(reasons)})' if reasons else '')
            + tr(' · 틱 {used}/{expected}개', used=len(f.ticks), expected=f.expected)]


def summary_lines(name, an, prev=None, tol=DEFAULT_TOLERANCE):
    ref = tr('{bph:.0f} bph 기준', bph=an.nominal_bph) if an.reference == 'nominal' else tr('구간 1 기준')
    lines = [RULE, tr(' {name}   (녹음 {dur:.0f}초 · {ref})', name=name, dur=an.duration, ref=ref), RULE]
    if an.bph_mismatch:
        near = guess_nominal_bph(an.measured_bph)
        hint = tr('--bph {near} 로 다시 실행하세요.', near=near) if near else tr('--bph 값을 확인하세요.')
        lines += [tr(' ※ 주의: 실측 {meas:.0f} bph가 규격 {nom:.0f} bph와 {pct:.1f}% 다릅니다. '
                     '규격을 잘못 넣은 것 같습니다 — {hint}',
                     meas=an.measured_bph, nom=an.nominal_bph,
                     pct=abs(an.measured_bph / an.nominal_bph - 1) * 100, hint=hint), '']
    segs = an.segments
    if len(segs) == 1:
        return lines + _segment_block(segs[0], segment_facts(segs[0], prev, tol))

    if an.split_mode not in SPLIT_NONE:
        lines.append(tr(' 레버 소리 {n}개: ', n=len(an.cuts)) + ', '.join(tr('{v:.1f}초', v=a) for a, _ in an.cuts))
    for sg in segs:
        lines += ['', tr(' ── {name} ({t0:.0f}–{t1:.0f}초) ──', name=sg.name, t0=sg.t0, t1=sg.t1)]
        if sg.is_reference:
            lines.append(tr(' 기준 구간 (다른 구간을 이 구간과 비교)'))
        elif an.reference == 'first':
            lines += _relative_block(sg, segs[0])
        else:
            lines += _segment_block(sg, segment_facts(sg, None, tol))
    if an.reference == 'first' and any(2 * sg.rate_se > 5 for sg in segs[1:]):
        lines += ['', tr(' ※ 구간이 짧아 작은 차이는 가려낼 수 없습니다. 레버 위치마다 1분 이상 녹음하세요.')]
    lines += ['', tr(' ▶ 레버 효과 (앞 구간 대비)')]
    for a, b in zip(segs, segs[1:]):
        lines.append(tr('   {a} → {b}: {d:+.1f} 초/일', a=a.name, b=b.name, d=b.rate - a.rate))
    return lines


def _grade_json(g):
    return dict(key=g.key, label=g.label)


def to_json(path, an, prev=None, tol=DEFAULT_TOLERANCE):
    """기계용 데이터 — 언어 설정과 무관하게 항상 한국어 값을 유지한다."""
    with use_lang('ko'):
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


def _main_minus(an, o):
    """주 시계 − 다른 시계 오차 (초/일, 95%). 두 시계를 같은 녹음 장비 시계로 재므로 장비 오차가 상쇄된다."""
    if o.rate is None or len(an.segments) != 1 or an.reference != 'nominal':
        return None
    sg = an.segments[0]
    return sg.rate - o.rate, 2 * float(np.hypot(sg.rate_se, o.rate_se))


def other_clock_lines(others, an):
    """--여러시계: 주 시계 말고 찾은 시계들."""
    lines = ['', tr(' ▶ 다른 시계 (--여러시계)')]
    if not others:
        return lines + [tr('   찾지 못함 — 주 시계 말고는 규칙적인 틱 소리가 들리지 않습니다.')]
    for k, o in enumerate(others, 2):
        f = o.fit
        kind = (tr('쿼츠 시계(1초마다 뛰는 초침)로 보임') if o.quartz else
                tr('규격 {bph:.0f} bph', bph=o.nominal_bph) if o.nominal_bph else tr('맞는 표준 규격 없음'))
        lines.append(tr('   시계 {k}   {beat:.3f}초 간격 · 실측 {bph:.1f} bph · {kind}',
                        k=k, beat=f.beat, bph=o.bph, kind=kind))
        if o.rate is not None:
            ci = 2 * o.rate_se
            verdict = tr('오차 범위 안 (사실상 정확)') if abs(o.rate) <= ci else headline(o.rate)
            lines.append(tr('            {verdict}   ({rate:+.1f} ± {ci:.1f} 초/일)',
                            verdict=verdict, rate=o.rate, ci=ci))
        lines.append(tr('            틱 {used}/{expected}개 사용 ({det:.0%}) · 틱 시각 흔들림 {ms:.1f} ms · '
                        '{lo}–{hi} Hz 대역에서 찾음',
                        used=len(f.ticks), expected=f.expected, det=len(f.ticks) / f.expected,
                        ms=f.jitter * 1000, lo=o.band[0], hi=o.band[1]))
        mm = _main_minus(an, o)
        if mm:
            lines.append(tr('            주 시계 − 시계 {k}: {v:+.1f} ± {ci:.1f} 초/일 (녹음 장비 시계 오차와 무관)',
                            k=k, v=mm[0], ci=mm[1]))
    if any(o.quartz for o in others):
        lines.append(tr('   ※ 쿼츠 시계는 보통 하루 ±0.5초 안이라 기준으로 삼을 수 있습니다. "주 시계 − 쿼츠" 값이 '
                        '녹음 장비 시계를 거치지 않은 주 시계의 오차입니다.'))
    return lines


def other_clocks_json(others, an):
    out = []
    for o in others:
        mm = _main_minus(an, o)
        out.append(dict(
            band_hz=list(o.band), score=round(o.score, 2), beat_s=round(o.fit.beat, 6), measured_bph=round(o.bph, 2),
            nominal_bph=o.nominal_bph, quartz=o.quartz,
            rate_s_per_day=round(o.rate, 1) if o.rate is not None else None,
            ci95=round(2 * o.rate_se, 1) if o.rate is not None else None,
            main_minus_this=dict(rate_s_per_day=round(mm[0], 1), ci95=round(mm[1], 1)) if mm else None,
            beat_error_ms=round(o.fit.beat_err * 1000, 2),
            quality=dict(ticks_used=len(o.fit.ticks), ticks_expected=o.fit.expected,
                         noise_clicks=len(o.fit.rejected), jitter_us=round(o.fit.jitter * 1e6))))
    return out

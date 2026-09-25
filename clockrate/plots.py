"""한국어 그래프: 조정 리포트 한 장, 조정 기록, (선택) 진단 그래프."""
import numpy as np
import scipy.signal as s
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch

from .advice import DEFAULT_TOLERANCE, fmt_duration

SURF, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
STATUS = {'good': '#0ca30c', 'warning': '#fab219', 'serious': '#ec835a', 'critical': '#d03b3b'}
KOREAN_FONTS = ['NanumBarunGothic', 'NanumGothic', 'Noto Sans CJK KR', 'Noto Sans KR', 'Malgun Gothic', 'AppleGothic']
MS_PER_S_PER_DAY = 1000 / 86400      # 하루 1초 오차일 때 1초당 쌓이는 시간 (ms)


def setup_style():
    have = {f.name for f in fm.fontManager.ttflist}
    font = next((f for f in KOREAN_FONTS if f in have), 'DejaVu Sans')
    plt.rcParams.update({
        'font.family': font, 'axes.unicode_minus': False, 'figure.facecolor': SURF, 'axes.facecolor': SURF,
        'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2, 'text.color': INK,
        'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': .6, 'axes.spines.top': False,
        'axes.spines.right': False, 'font.size': 11, 'axes.titlesize': 12.5, 'axes.titleweight': 'bold',
        'axes.titlelocation': 'left', 'lines.linewidth': 2})


def color(k):
    return COLORS[k % len(COLORS)]


def _pill(ax, x, y, grade, size=13):
    """상태 배지: 색 + 아이콘 + 글자 (색만으로 뜻을 전하지 않는다)."""
    fg = INK if grade.key == 'warning' else 'white'
    ax.text(x, y, f' {grade.icon} {grade.label} ', transform=ax.transAxes, fontsize=size, fontweight='bold',
            color=fg, va='center', ha='left',
            bbox=dict(boxstyle='round,pad=0.35', fc=STATUS[grade.key], ec='none'))


# ---------------------------------------------------------------- 조정 리포트

def _banner(ax, name, an, facts_list):
    ax.axis('off')
    ax.text(0, 1.0, name, transform=ax.transAxes, fontsize=12, color=INK2, va='top')
    ref = f'{an.nominal_bph:.0f} bph 기준' if an.reference == 'nominal' else '구간 1 기준'
    ax.text(1, 1.0, f'녹음 {an.duration:.0f}초 · {ref}', transform=ax.transAxes, fontsize=11, color=INK2,
            va='top', ha='right')
    if len(facts_list) == 1:
        sg, fx = facts_list[0]
        _pill(ax, 0, .66, fx['grade'], 14)
        ax.text(.17, .66, fx['headline'], transform=ax.transAxes, fontsize=30, fontweight='bold', va='center')
        ax.text(.99, .66, f'{sg.rate:+.1f} ± {2 * sg.rate_se:.1f} 초/일', transform=ax.transAxes, fontsize=13,
                color=INK2, va='center', ha='right')
        action = fx['lever']
        if fx['step']:
            action += f'\n직전 녹음({fx["step"][0]}) 대비 {fx["step"][1]:+.1f} 초/일 → {fx["step"][2]}'
        ax.text(0, .36, '할 일  ' + action, transform=ax.transAxes, fontsize=13, fontweight='bold', va='top',
                linespacing=1.7)
    else:
        y = .78
        for k, (sg, fx) in enumerate(facts_list):
            ax.plot([0.005], [y], 's', ms=11, color=color(k), transform=ax.transAxes, clip_on=False)
            txt = f'{sg.name}   기준 구간' if sg.is_reference else \
                f'{sg.name}   {fx["headline"]}  ({sg.rate:+.1f} ± {2 * sg.rate_se:.1f} 초/일)'
            if not sg.is_reference and abs(sg.rate) <= 2 * sg.rate_se:
                txt += '  — 오차 범위 안'
            ax.text(.025, y, txt, transform=ax.transAxes, fontsize=14, fontweight='bold', va='center')
            y -= .22


def _gauge(ax, facts_list, tol, relative=False):
    ax.set_title('구간 1 대비 변화' if relative else '목표 범위와 지금 위치')
    worst = max(abs(sg.rate) + 2 * sg.rate_se for sg, _ in facts_list)
    R = max(90, worst * 1.15)
    edges = [0, tol, 3 * tol, 60, R]
    for (lo, hi), key in zip(zip(edges, edges[1:]), ('good', 'warning', 'serious', 'critical')):
        if relative or lo >= R:
            break
        for sgn in (1, -1):
            ax.axvspan(sgn * lo, sgn * min(hi, R), color=STATUS[key], alpha=.22, lw=0)
    ax.axvline(0, color=INK2, lw=1)
    ys = np.linspace(.8, .2, len(facts_list)) if len(facts_list) > 1 else [.45]
    for k, ((sg, fx), y) in enumerate(zip(facts_list, ys)):
        c = color(k)
        ax.errorbar(sg.rate, y, xerr=2 * sg.rate_se, fmt='o', color=c, ms=11, mec=SURF, mew=2, capsize=6, lw=2)
        if len(facts_list) == 1:
            ax.annotate(f'지금 {sg.rate:+.0f}', (sg.rate, y), xytext=(0, 14), textcoords='offset points',
                        ha='center', fontsize=11, fontweight='bold')
        else:
            ax.annotate(f'{sg.name}  {sg.rate:+.0f}', (sg.rate + 2 * sg.rate_se, y), xytext=(10, 0),
                        textcoords='offset points', va='center', fontsize=10.5, fontweight='bold')
    ax.set_xlim(-R, R); ax.set_ylim(0, 1); ax.set_yticks([]); ax.grid(axis='y', visible=False)
    ax.spines['left'].set_visible(False)
    ax.set_xlabel('하루 오차 (초/일)    ← 느림 | 빠름 →')
    for lim, txt in ((tol, f'목표 ±{tol:.0f}'), (60, '±1분')):
        if lim < R and not relative:
            ax.text(lim, .97, f' {txt}', fontsize=9.5, color=INK2, va='top')


def _facts_box(ax, sg, fx):
    ax.axis('off')
    ax.set_title('숫자로 보기')
    f = sg.fit
    d = fx['drift']
    level, det, reasons, _ = fx['quality']
    st = fx['stability']
    rows = [('이대로 두면', ''),
            ('   1일', ('+' if d['1일'] > 0 else '-') + fmt_duration(d['1일'])),
            ('   1주', ('+' if d['1주'] > 0 else '-') + fmt_duration(d['1주'])),
            ('   30일', ('+' if d['30일'] > 0 else '-') + fmt_duration(d['30일'])),
            ('비트 에러', f'{f.beat_err * 1000:.1f} ms  {fx["beat"].icon} {fx["beat"].label.split(" —")[0]}'),
            ('진폭', (f'약 {sg.amplitude.deg:.0f}°  ' + (f'{fx["amp"].icon} {fx["amp"].label.split(" —")[0]}'
                                                      if sg.amplitude.reliable else '(참고용)'))
             if sg.amplitude else '측정 못 함'),
            ('속도 안정성', f'폭 {st[2]:.0f} 초/일 · {st[3].split(" —")[0]}' if st else '녹음이 짧아 생략'),
            ('측정 신뢰도', f'{level} (틱 {len(f.ticks)}/{f.expected})'),
            ('실측 진동수', f'{sg.bph:.1f} bph')]
    y = .95
    for k, v in rows:
        ax.text(0, y, k, transform=ax.transAxes, fontsize=11.5, color=INK2 if k.startswith('   ') else INK,
                fontweight='normal' if k.startswith('   ') else 'bold', va='top')
        ax.text(1, y, v, transform=ax.transAxes, fontsize=11.5, va='top', ha='right')
        y -= .107


def _compare_box(ax, facts_list):
    ax.axis('off')
    ax.set_title('구간별 비교')
    y = .95
    for k, (sg, fx) in enumerate(facts_list):
        ax.plot([0.01], [y - .03], 's', ms=10, color=color(k), transform=ax.transAxes, clip_on=False)
        ax.text(.06, y, sg.name, transform=ax.transAxes, fontsize=11.5, fontweight='bold', va='top')
        if sg.is_reference:
            v = '기준'
        elif abs(sg.rate) <= 2 * sg.rate_se:
            v = f'{sg.rate:+.1f}±{2 * sg.rate_se:.1f} · 차이 없음'
        else:
            v = f'{sg.rate:+.1f}±{2 * sg.rate_se:.1f} · {"빨라짐" if sg.rate > 0 else "느려짐"}'
        ax.text(1, y - .11, v, transform=ax.transAxes, fontsize=11, va='top', ha='right')
        ax.text(.06, y - .11, f'비트 에러 {sg.fit.beat_err * 1000:.1f} ms', transform=ax.transAxes, fontsize=10.5,
                color=INK2, va='top')
        y -= .27


def _timegrapher(ax, an, tol):
    single = len(an.segments) == 1
    relative = an.reference == 'first'
    ax.set_title('타임그래퍼 — 선이 위로 가면 빠름, 아래로 가면 느림'
                 + ('' if relative else '. 회색 부채꼴 안이면 목표 범위'))
    for k, sg in enumerate(an.segments):
        f = sg.fit
        t0 = f.ticks[0]
        ahead = -((f.ticks - t0) - (f.n - f.n[0]) * an.base_beat) * 1000      # 기준보다 앞선 시간 (ms)
        if not single:                                   # 구간이 여럿이면 비트 에러를 빼서 한 줄로
            p = f.parity
            ahead[p != p[0]] -= np.mean(ahead[p != p[0]]) - np.mean(ahead[p == p[0]])
        ahead -= np.median(ahead[f.parity == f.parity[0]][:5])
        x = f.ticks if not single else f.ticks - t0
        if single:
            for p, c, lab in ((0, COLORS[0], '틱'), (1, COLORS[1], '톡')):
                m = f.parity == p
                ax.plot(x[m], ahead[m], 'o', ms=3.2 if len(x) > 200 else 5, color=c, mec='none', label=lab)
        else:
            ax.plot(x, ahead, 'o', ms=4, color=color(k), mec='none', label=sg.name)
        xx = np.array([x[0], x[-1]])
        ax.plot(xx, np.polyval(np.polyfit(x, ahead, 1), xx), color=INK, lw=1.2, ls=(0, (5, 3)))
        if not relative:
            cone = (xx - x[0]) * tol * MS_PER_S_PER_DAY
            ax.fill_between(xx, -cone, cone, color=INK2, alpha=.12, lw=0)
    ax.axhline(0, color=INK2, lw=1)
    ax.set_xlabel('녹음 시간 (초)'); ax.set_ylabel('기준보다 앞선 시간 (ms)')
    ax.legend(frameon=False, loc='best', markerscale=2)
    if single:
        be = an.segments[0].fit.beat_err * 1000
        top = an.segments[0].rate < 0                  # 점들이 내려가면 위쪽 빈 곳에 적는다
        ax.text(.99, .96 if top else .03, f'틱·톡 두 줄의 간격 = 비트 에러 {be:.1f} ms', transform=ax.transAxes,
                ha='right', va='top' if top else 'bottom', fontsize=10, color=INK2)


def _stability(ax, an, tol):
    ax.set_title('시간대별 오차 — 점들이 고르면 속도가 안정적')
    any_w = False
    for k, sg in enumerate(an.segments):
        if not sg.windows:
            continue
        any_w = True
        mid = [(a + b) / 2 for a, b, _ in sg.windows]
        r = [w[2] for w in sg.windows]
        c = color(k)
        ax.plot(mid, r, 'o-', color=c, ms=8, mec=SURF, mew=1.5, lw=1.5)
        for xm, v in zip(mid, r):
            ax.annotate(f'{v:+.0f}', (xm, v), xytext=(0, 9), textcoords='offset points', ha='center', fontsize=9.5)
        ax.hlines(sg.rate, sg.windows[0][0], sg.windows[-1][1], color=c, lw=1, ls=(0, (4, 3)))
    if not any_w:
        ax.text(.5, .5, '녹음이 20초 이상이어야 표시됩니다', transform=ax.transAxes, ha='center', va='center',
                color=INK2, fontsize=12)
        ax.set_xticks([]); ax.set_yticks([])
        return
    vals = np.array([w[2] for sg in an.segments for w in sg.windows])
    pad = max(10.0, (vals.max() - vals.min()) * .6)
    lo, hi = vals.min() - pad, vals.max() + pad
    if lo < tol and hi > -tol:                          # 목표 범위가 화면 안에 있으면 함께 표시
        lo, hi = min(lo, -tol * 1.5), max(hi, tol * 1.5)
        ax.axhspan(-tol, tol, color=STATUS['good'], alpha=.2, lw=0)
        ax.axhline(0, color=INK2, lw=1)
    else:
        ax.text(.99, .04, f'목표(±{tol:.0f})는 이 범위 {"아래" if lo > 0 else "위"}에 있음', transform=ax.transAxes,
                ha='right', fontsize=10, color=INK2)
    ax.set_ylim(lo, hi)
    ax.set_xlabel('녹음 시간 (초)'); ax.set_ylabel('하루 오차 (초/일)')


def plot_report(an, name, path, facts_list, tol=DEFAULT_TOLERANCE):
    """facts_list: [(Segment, report.segment_facts(...)), ...]"""
    setup_style()
    has_windows = any(sg.windows for sg in an.segments)
    ratios = [.72, .95, 1.6] + ([1.15] if has_windows else [])
    fig = plt.figure(figsize=(14, 13 if has_windows else 10.5))
    gs = GridSpec(len(ratios), 3, figure=fig, height_ratios=ratios, hspace=.42, wspace=.3)
    relative = an.reference == 'first'
    _banner(fig.add_subplot(gs[0, :]), name, an, facts_list)
    _gauge(fig.add_subplot(gs[1, :2]), facts_list, tol, relative)
    if relative:
        _compare_box(fig.add_subplot(gs[1, 2]), facts_list)
    else:
        main = next((p for p in facts_list if not p[0].is_reference), facts_list[0])
        _facts_box(fig.add_subplot(gs[1, 2]), *main)
    _timegrapher(fig.add_subplot(gs[2, :]), an, tol)
    if has_windows:
        _stability(fig.add_subplot(gs[3, :]), an, tol)
    fig.subplots_adjust(left=.07, right=.97, top=.97, bottom=.05 if has_windows else .065)
    fig.savefig(path, dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------- 조정 기록

def plot_history(entries, path, advice=None, tol=DEFAULT_TOLERANCE):
    """entries: history.load() 결과 (분석한 순서). advice: 마지막 녹음에 대한 다음 할 일 문구."""
    setup_style()
    amps = [e.get('amplitude') for e in entries]
    has_amp = any(a is not None for a in amps)
    if has_amp:
        fig, (ax, ax2) = plt.subplots(2, 1, figsize=(13, 8.6), sharex=True, gridspec_kw={'height_ratios': [2.3, 1]})
    else:
        fig, ax = plt.subplots(figsize=(13, 6.2))
    x = np.arange(len(entries))
    r = np.array([e['rate'] for e in entries])
    ci = np.array([e['ci95'] for e in entries])
    ax.axhspan(-tol, tol, color=STATUS['good'], alpha=.18, lw=0)
    ax.text(len(entries) - .5, tol, f'목표 ±{tol:.0f}초/일 ', ha='right', va='bottom', fontsize=10, color=INK2)
    ax.axhline(0, color=INK2, lw=1)
    ax.plot(x, r, '-', color=COLORS[0], lw=2)
    ax.errorbar(x, r, yerr=ci, fmt='o', color=COLORS[0], ms=10, mec=SURF, mew=2, capsize=5, lw=1.5)
    span = max(abs(r).max(), tol) * 1.35
    for xi, v in zip(x, r):
        ax.annotate(f'{v:+.1f}\n하루 {fmt_duration(v)} {"빠름" if v > 0 else "느림"}', (xi, v),
                    xytext=(0, 16 if v >= 0 else -16), textcoords='offset points', ha='center',
                    va='bottom' if v >= 0 else 'top', fontsize=10.5)
    ax.set_xticks(x, [e['file'] for e in entries], rotation=0)
    ax.set_xlim(-.5, len(entries) - .5); ax.set_ylim(-span, span)
    if has_amp:
        xa = [i for i, a in enumerate(amps) if a is not None]
        va = [amps[i] for i in xa]
        ok = [entries[i].get('amplitude_reliable', True) for i in xa]
        ax2.plot(xa, va, '-', color=COLORS[2], lw=1.8)
        for xi, v, good in zip(xa, va, ok):
            ax2.plot(xi, v, 'o', ms=9, mew=2, color=COLORS[2], mfc=COLORS[2] if good else SURF,
                     mec=SURF if good else COLORS[2])
            ax2.annotate(f'{v:.0f}°' + ('' if good else ' (참고용)'), (xi, v), xytext=(0, 10),
                         textcoords='offset points', ha='center', fontsize=10.5)
        ax2.set_ylim(min(va) - 40, max(va) + 45)
        ax2.set_ylabel('진폭 (°)')
        ax2.set_title('진폭 — 크게 줄면 태엽이 풀렸거나 무브먼트 상태를 확인 (빈 원은 참고용 값)', fontsize=11,
                      fontweight='normal', color=INK2)
        ax2.tick_params(labelbottom=True)
    ax.set_ylabel('하루 오차 (초/일)')
    ax.set_title('분석한 순서대로 · 위쪽이 빠름, 아래쪽이 느림 · 오차 막대 95% 신뢰구간', fontsize=11, fontweight='normal', color=INK2)
    fig.suptitle('조정 기록', fontsize=16, fontweight='bold', x=.01, ha='left')
    if advice:
        fig.text(.01, .015, '다음 할 일  ' + advice, fontsize=12, fontweight='bold', va='bottom')
    fig.tight_layout(rect=(0, .06 if advice else 0, 1, 1))
    fig.savefig(path, dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------- 진단 (--진단)

def plot_diagnostics(an, path):
    """소음 제거 전후와 구간·틱 검출 상태. 검출이 이상할 때 원인을 볼 때만 쓴다."""
    setup_style()
    tt = np.arange(len(an.raw)) / an.sr
    fig = plt.figure(figsize=(14, 16))
    gs = GridSpec(5, 2, figure=fig, height_ratios=[1, 1, 1, 1, 1.1], hspace=.55)
    ax = [fig.add_subplot(gs[0, :])]
    ax += [fig.add_subplot(gs[i, :], sharex=ax[0]) for i in (1, 2, 3)]
    ax[0].plot(tt, an.raw, lw=.4, color=INK2); ax[0].set_title('원본 파형'); ax[0].set_ylabel('진폭')
    f, t, Z = s.stft(an.clean, an.sr, nperseg=1024, noverlap=768)
    ax[1].pcolormesh(t, f / 1000, 20 * np.log10(np.abs(Z) + 1e-9), vmin=-115, vmax=-40, cmap='Greys',
                     shading='auto', rasterized=True)
    ax[1].set_ylim(0, 18); ax[1].set_ylabel('주파수 (kHz)'); ax[1].grid(False)
    ax[1].set_title('소음 제거 후 스펙트로그램 (세로줄 하나가 틱 하나)')
    ax[2].plot(an.swish_t, an.swish_db, color=INK, lw=1.3); ax[2].axhline(4, color=INK2, ls='--', lw=1)
    ax[2].set_ylabel('지속음 (dB)'); ax[2].set_title('레버 "스윽" 소리 검출 (점선 위로 0.08초 이상이면 레버로 봄)')
    ym = np.abs(an.clean).max()
    ax[3].plot(tt, an.clean, lw=.35, color=INK2, alpha=.6)
    for k, sg in enumerate(an.segments):
        ax[3].axvspan(sg.t0, sg.t1, color=color(k), alpha=.1, lw=0)
        ax[3].vlines(sg.fit.ticks, ym * .75, ym, color=color(k), lw=1)
    for a, b in an.cuts:
        for axx in ax[2:]:
            axx.axvspan(a, b, color=COLORS[1], alpha=.25, lw=0)
    rj = np.concatenate([sg.fit.rejected for sg in an.segments])
    if len(rj):
        ax[3].plot(rj, np.full(len(rj), -ym * .9), 'x', color=INK, ms=7, mew=1.5, label='잡음 클릭(제외)')
        ax[3].legend(loc='lower right', frameon=False)
    ax[3].set_title('소음 제거 후 파형과 사용한 틱 (위쪽 눈금)'); ax[3].set_ylabel('진폭')
    ax[-1].set_xlabel('시간 (초)'); ax[-1].set_xlim(0, an.duration)
    amp = an.segments[0].amplitude
    for p, lab in ((0, '틱'), (1, '톡')):
        a2 = fig.add_subplot(gs[4, p])
        if amp and p < len(amp.profiles):
            tt, m, tu, tm = amp.profiles[p]
            a2.semilogy(tt * 1000, m, color=INK, lw=1.2)
            for t_, name_, c in ((tu, '언락', COLORS[1]), (tm, '드롭', COLORS[0])):
                a2.axvline(t_ * 1000, color=c, lw=1.5, ls=(0, (4, 2)))
                a2.text(t_ * 1000, a2.get_ylim()[1], f' {name_}', color=INK, fontsize=10, va='top')
            a2.set_title(f'{lab} 소리 구조 (틱 {len(an.segments[0].fit.ticks) // 2}개 중앙값) · '
                         f'언락→드롭 {(tm - tu) * 1000:.1f} ms', fontsize=11)
            a2.set_xlabel('드롭 기준 시각 (ms)'); a2.set_ylabel('소리 크기 (바닥=1)')
        else:
            a2.axis('off'); a2.text(.5, .5, f'{lab}: 언락 소리를 찾지 못함', ha='center', transform=a2.transAxes)
    fig.suptitle('진단 — 소음 제거, 틱 검출, 진폭 계산에 쓴 소리 구조', fontsize=16, fontweight='bold', x=.01, ha='left')
    fig.subplots_adjust(left=.07, right=.97, top=.95, bottom=.05)
    fig.savefig(path, dpi=110)
    plt.close(fig)

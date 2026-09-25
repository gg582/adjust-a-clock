"""명령줄 진입점: clock-rate 녹음.mp3 [옵션]"""
import argparse
import json
import os
import sys

from . import history
from .advice import DEFAULT_TOLERANCE, headline
from .amplitude import DEFAULT_LIFT_ANGLE
from .analysis import DEFAULT_BPH, AnalysisError, analyze_signal
from .audio import AudioError, load_audio, write_wav
from .report import segment_facts, summary_lines, to_json

EPILOG = """\
시계를 맞추는 순서:
  1. 녹음(1분 이상) → clock-rate 녹음1.m4a
  2. 안내대로 조속 레버를 옮기고 다시 녹음 → clock-rate 녹음2.m4a
     직전 녹음과 비교해 '그때 옮긴 거리의 몇 배를 어느 쪽으로' 옮길지 알려 줍니다.
  3. '◎ 조정 완료'가 나올 때까지 반복. 기록은 <출력>/조정기록.json 에 쌓입니다.

분할 모드 (--분할):
  없음        녹음 전체를 한 구간으로 (기본값)
  자동        녹음 도중 레버를 민 경우, '스윽' 소리를 찾아 앞뒤를 나눠 비교
  3.5,9.2     지정한 시각(초)에서 나눔

기준 모드 (--기준):
  자동        --bph 규격 기준 절대 오차 (기본값). --bph 자동 에서 규격을 못 찾으면 구간 1 기준
  규격        규격 기준 절대 오차
  구간1       첫 구간을 0으로 두고 나머지 구간이 얼마나 빨라지고 느려졌는지 비교

규격 진동수 (--bph):
  18000       기본값 (Slava 5671 등)
  28800 ...   시계에 맞는 값을 숫자로 지정
  자동        측정값에서 ±1% 이내의 표준값(3600–36000)을 자동 선택

예:
  clock-rate recordings/시간조정4.mp3
  clock-rate recordings/시간조정*.mp3                    # 여러 파일을 순서대로 → 조정 기록
  clock-rate recordings/탈진기.mp3 --분할 자동 --기준 구간1 --이름 가운데,빠르게,느리게
"""


def parse_bph(v):
    if str(v).strip().lower() in ('자동', 'auto'):
        return None
    try:
        bph = float(v)
    except ValueError:
        raise argparse.ArgumentTypeError(f"숫자 또는 '자동'이어야 합니다: {v}")
    if not 1800 <= bph <= 72000:
        raise argparse.ArgumentTypeError(f'1800–72000 사이여야 합니다: {v}')
    return bph


def build_parser():
    ap = argparse.ArgumentParser(prog='clock-rate', description='기계식 시계 녹음으로 하루 오차를 재고, 조속 레버를 어떻게 옮길지 알려 줍니다.',
                                 epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('files', nargs='+', metavar='파일', help='ffmpeg가 읽는 오디오/동영상 파일 (mp3, m4a, wav, mp4 ...)')
    ap.add_argument('--분할', '--split', dest='split', default='없음', help="'없음'(기본) | '자동' | 쉼표로 구분한 시각(초)")
    ap.add_argument('--기준', '--reference', dest='reference', default='자동', help="'자동' | '규격' | '구간1'")
    ap.add_argument('--bph', '--vph', dest='bph', type=parse_bph, default=DEFAULT_BPH,
                    help=f"규격 진동수(시간당 박자 수). 기본 {DEFAULT_BPH}, '자동'이면 표준값에서 추정")
    ap.add_argument('--리프트각', '--lift-angle', dest='lift', type=float, default=DEFAULT_LIFT_ANGLE,
                    help=f'진폭 계산용 리프트각(도). 기본 {DEFAULT_LIFT_ANGLE:.0f}, 0이면 진폭 계산 안 함')
    ap.add_argument('--허용', '--tolerance', dest='tol', type=float, default=DEFAULT_TOLERANCE,
                    help=f'이 안(초/일)이면 조정 완료로 판정 (기본 {DEFAULT_TOLERANCE:.0f})')
    ap.add_argument('--이름', '--names', dest='names', default='', help='구간 이름, 쉼표로 구분 (예: 가운데,빠르게,느리게)')
    ap.add_argument('--창', '--window', dest='window', type=float,
                    help='시간대별 안정성 창 길이(초). 생략하면 자동(10 또는 20초), 0이면 끔')
    ap.add_argument('--출력', '--out', dest='out', default='results',
                    help='결과 상위 폴더 (기본: ./results). 파일마다 <출력>/<파일명>/ 에 저장')
    ap.add_argument('--기록끔', '--no-history', dest='history', action='store_false',
                    help='조정 기록에 남기지 않고 직전 녹음과 비교하지도 않음')
    ap.add_argument('--진단', '--diagnostics', dest='diag', action='store_true',
                    help='소음 제거·틱 검출 상태 그래프와 소음 제거 wav도 저장')
    ap.add_argument('--그래프없음', '--no-plots', dest='plots', action='store_false', help='요약만 만들고 그래프는 생략')
    return ap


def run_one(path, a, log):
    sr, x = load_audio(path)
    an = analyze_signal(x, sr, split=a.split, bph=a.bph, reference=a.reference,
                        names=[n.strip() for n in a.names.split(',')] if a.names else (), window=a.window,
                        lift=a.lift or None)
    name = os.path.basename(path)
    stem = os.path.splitext(name)[0]
    out = os.path.join(a.out, stem)
    os.makedirs(out, exist_ok=True)

    single = len(an.segments) == 1 and an.reference == 'nominal'
    prev = history.previous(log, stem, an.nominal_bph) if (a.history and single) else None
    lines = summary_lines(name, an, prev, a.tol)
    print('\n'.join(lines))
    with open(os.path.join(out, '요약.txt'), 'w') as f:
        f.write('\n'.join(lines) + '\n')
    with open(os.path.join(out, '요약.json'), 'w') as f:
        json.dump(to_json(path, an, prev, a.tol), f, ensure_ascii=False, indent=1)
    if a.plots:
        from .plots import plot_diagnostics, plot_report
        rel = an.segments[0].name if an.reference == 'first' else None
        facts = [(sg, segment_facts(sg, prev if single else None, a.tol, rel)) for sg in an.segments]
        plot_report(an, name, os.path.join(out, '리포트.png'), facts, a.tol)
        if a.diag:
            plot_diagnostics(an, os.path.join(out, '진단.png'))
            write_wav(os.path.join(out, '소음제거.wav'), sr, an.clean)
    print(f'→ {out}/')
    if a.history and single:
        history.upsert(log, stem, an.segments[0], an)
        return True
    return False


def main(argv=None):
    a = build_parser().parse_args(argv)
    log = history.load(a.out) if a.history else []
    failed, added = 0, False
    for i, path in enumerate(a.files):
        if i:
            print()
        try:
            added |= run_one(path, a, log)
        except (AudioError, AnalysisError, ValueError) as e:
            print(f'[{os.path.basename(path)}] 분석 실패: {e}', file=sys.stderr)
            failed += 1
    if added:
        history.save(a.out, log)
        if len(log) > 1:
            last = log[-1]
            prev = history.previous(log, last['file'], last['bph'])
            advice = None
            if prev:
                from .advice import next_step
                advice = next_step(prev['rate'], prev['ci95'] / 2, last['rate'], last['ci95'] / 2, a.tol)[1]
            print('\n━━ 조정 기록 ━━')
            for e in log:
                amp = (f"   진폭 {e['amplitude']}°" + ('' if e.get('amplitude_reliable', True) else ' (참고용)')
                       if e.get('amplitude') else '')
                print(f"  {e['file']:<16} {e['rate']:+8.1f} 초/일   {headline(e['rate'])}{amp}")
            if advice:
                print(f'  다음 할 일: {advice}')
            if a.plots:
                from .plots import plot_history
                plot_history(log, os.path.join(a.out, '조정기록.png'), advice, a.tol)
                print(f'→ {os.path.join(a.out, "조정기록.png")}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())

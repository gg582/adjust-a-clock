"""정답을 아는 합성 틱 소리로 측정 정확도를 검증한다."""
import json
import shutil
from pathlib import Path

import numpy as np
import pytest
import scipy.io.wavfile as wavfile

from clockrate import AnalysisError, analyze_signal
from clockrate.advice import fmt_duration, grade_rate, lever_direction, next_step
from clockrate.amplitude import amplitude_of
from clockrate.analysis import guess_nominal_bph
from clockrate.cli import main, parse_bph
from clockrate.sheet import BORDER, FAIL, NA, PASS, SheetError, compare, load_sheet
from clockrate.segments import find_cuts

SR = 48000


def synth(parts, duration, beat=0.2, beat_error=0.003, levers=(), accent=None, seed=1, unlock=None,
          drop_echo=None):
    """parts: [(시작, 끝, 초/일), ...] 구간마다 해당 일오차로 틱을 만든다.
    accent: 틱 크기 강약 반복 주기 (예: 4면 네 박마다 한 번 크게).
    unlock: 드롭(큰 소리) 몇 초 앞에 작은 언락 소리를 넣을지 (진폭 검증용).
    drop_echo: 드롭 몇 초 뒤에 더 큰 두 번째 봉우리를 넣을지 (갈라진 드롭 소리 재현)."""
    rng = np.random.default_rng(seed)
    n = int(SR * duration)
    x = rng.normal(0, 0.01, n)
    x += np.convolve(rng.normal(0, 0.05, n), np.ones(400) / 400, 'same')       # 저역 도시 소음
    k = np.arange(300)
    click = np.exp(-k / 40) * np.sin(2 * np.pi * 7000 * k / SR) * 0.08
    i = 0
    for t0, t1, rate in parts:
        b = beat / (1 + rate / 86400)
        t = t0
        while t < t1:
            amp = 1.0 if accent is None else (1.0 if i % accent == 0 else 0.35)
            tk = t + (beat_error if i % 2 else 0)
            j = int(tk * SR)
            if j + 300 < n:
                x[j:j + 300] += amp * np.interp(k - (tk * SR - j), k, click)
            if unlock and j - int(unlock * SR) > 0:
                ju = int((tk - unlock) * SR)
                x[ju:ju + 300] += 0.3 * amp * np.interp(k - ((tk - unlock) * SR - ju), k, click)
            if drop_echo and j + int(drop_echo * SR) + 300 < n:
                je = int((tk + drop_echo) * SR)
                x[je:je + 300] += 1.6 * amp * np.interp(k - ((tk + drop_echo) * SR - je), k, click)
            t += b; i += 1
    for c in levers:                                                           # 레버 '스윽'
        j = int(c * SR)
        x[j - 8000:j + 8000] += rng.normal(0, 0.04, 16000) * np.hanning(16000)
    return x


def test_auto_split_three_positions():
    x = synth([(0.5, 29.5, 45), (30.5, 59.5, 165), (60.5, 89.5, -75)], 90, levers=(30, 60))
    an = analyze_signal(x, SR, split='자동', names=['가운데', '빠르게', '느리게'])
    assert an.nominal_bph == 18000 and an.reference == 'nominal'
    assert len(an.cuts) == 2
    assert [sg.rate for sg in an.segments] == pytest.approx([45, 165, -75], abs=0.5)
    assert an.segments[1].name == '구간 2 · 빠르게'
    for sg in an.segments:
        assert sg.fit.beat_err == pytest.approx(0.003, abs=3e-4)


def test_manual_split_matches_auto():
    x = synth([(0.5, 29.5, 45), (30.5, 59.5, 165), (60.5, 89.5, -75)], 90, levers=(30, 60))
    an = analyze_signal(x, SR, split='30,60')
    assert [sg.rate for sg in an.segments] == pytest.approx([45, 165, -75], abs=0.5)


def test_reference_first_segment():
    x = synth([(0.5, 29.5, 45), (30.5, 59.5, 165), (60.5, 89.5, -75)], 90, levers=(30, 60))
    an = analyze_signal(x, SR, split='자동', reference='구간1')
    assert an.reference == 'first' and an.segments[0].is_reference
    assert [sg.rate for sg in an.segments] == pytest.approx([0, 120, -120], abs=0.5)


def test_no_split_long_recording_keeps_beat_numbering():
    # 긴 녹음에서 박 번호가 누적 오차로 밀리지 않는지 (초기 버그)
    x = synth([(0.3, 119.5, -205)], 120, beat_error=0.005)
    an = analyze_signal(x, SR, split='없음')
    (sg,) = an.segments
    assert sg.rate == pytest.approx(-205, abs=0.5)
    assert sg.fit.beat_err == pytest.approx(0.005, abs=3e-4)
    assert sg.windows and all(abs(r + 205) < 5 for _, _, r in sg.windows)


def test_accented_ticks_do_not_fool_beat_estimate():
    # 틱 크기가 강약으로 반복되면 여러 박을 한 박으로 잡던 버그 (시간조정3.mp3)
    x = synth([(0.3, 59.5, 8)], 60, accent=4)
    an = analyze_signal(x, SR, split='없음')
    assert an.measured_bph == pytest.approx(18000, rel=1e-3)
    assert an.segments[0].rate == pytest.approx(8, abs=1)


def test_nominal_guess():
    assert guess_nominal_bph(17983.5) == 18000
    assert guess_nominal_bph(28790) == 28800
    assert guess_nominal_bph(4489) is None


def test_default_bph_is_18000():
    x = synth([(0.3, 29.5, -64)], 30)
    an = analyze_signal(x, SR, split='없음')
    assert an.nominal_bph == 18000 and not an.bph_mismatch
    assert an.segments[0].rate == pytest.approx(-64, abs=1)


def test_custom_bph_and_mismatch_warning():
    x = synth([(0.3, 29.5, 20)], 30, beat=0.125)        # 28800 bph 시계
    an = analyze_signal(x, SR, split='없음', bph=28800)
    assert an.segments[0].rate == pytest.approx(20, abs=1) and not an.bph_mismatch
    wrong = analyze_signal(x, SR, split='없음')          # 기본 18000으로 잘못 잼
    assert wrong.bph_mismatch
    auto = analyze_signal(x, SR, split='없음', bph=None)
    assert auto.nominal_bph == 28800


def test_parse_bph():
    assert parse_bph('18000') == 18000 and parse_bph('자동') is None and parse_bph('auto') is None
    for bad in ('빠르게', '100'):
        with pytest.raises(Exception):
            parse_bph(bad)


def test_reference_nominal_requires_standard_bph():
    x = synth([(0.3, 29.5, 0)], 30, beat=0.23)          # 15652 bph: 표준값 아님
    with pytest.raises(AnalysisError):
        analyze_signal(x, SR, split='없음', bph=None, reference='규격')
    an = analyze_signal(x, SR, split='없음', bph=15652, reference='규격')
    assert an.segments[0].rate == pytest.approx(0, abs=2)


def test_invalid_split_value():
    with pytest.raises(ValueError):
        find_cuts('중간', [], 10)


def test_too_short():
    with pytest.raises(AnalysisError):
        analyze_signal(np.zeros(SR), SR)


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='ffmpeg 필요')
def test_cli_batch(tmp_path, capsys):
    paths = []
    for i, rate in enumerate((30, -30)):
        p = tmp_path / f'rec{i}.wav'
        x = synth([(0.3, 29.5, rate)], 30, seed=i)
        wavfile.write(p, SR, (x / np.abs(x).max() * 0.9 * 32767).astype(np.int16))
        paths.append(str(p))
    out = tmp_path / 'out'
    assert main([*paths, '--그래프없음', '--출력', str(out)]) == 0
    text = capsys.readouterr().out
    assert '조정 기록' in text and '반대 방향' in text          # +30 → -30: 직전과 반대로 되돌리라는 안내
    assert (out / 'rec0' / '요약.json').exists()
    log = json.loads((out / '조정기록.json').read_text())
    assert [e['file'] for e in log] == ['rec0', 'rec1']
    assert main([paths[0], '--그래프없음', '--출력', str(out)]) == 0   # 다시 분석해도 기록 순서 유지
    assert [e['file'] for e in json.loads((out / '조정기록.json').read_text())] == ['rec0', 'rec1']


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='ffmpeg 필요')
def test_cli_report_png(tmp_path):
    p = tmp_path / 'rec.wav'
    x = synth([(0.3, 29.5, 12)], 30)
    wavfile.write(p, SR, (x / np.abs(x).max() * 0.9 * 32767).astype(np.int16))
    assert main([str(p), '--출력', str(tmp_path / 'out'), '--진단']) == 0
    for f in ('리포트.png', '진단.png', '요약.txt', '소음제거.wav'):
        assert (tmp_path / 'out' / 'rec' / f).exists()


def test_advice_rules():
    assert fmt_duration(227.1) == '3분 47초' and fmt_duration(6858) == '1시간 54분' and fmt_duration(8.4) == '8.4초'
    assert grade_rate(8).label == '조정 완료' and grade_rate(-25).label == '미세 조정 권장'
    assert grade_rate(45).label == '조정 필요' and grade_rate(-205).label == '크게 어긋남'
    assert '느림' in lever_direction(30) and '빠름' in lever_direction(-30) and '그대로' in lever_direction(5)
    # 실제 조정 기록(시간조정 → 2 → 3)으로 검증한 안내
    assert '직전에 옮긴 방향' in next_step(342.7, .1, 227.1, .1)[1] and '2.0배' in next_step(342.7, .1, 227.1, .1)[1]
    assert '반대 방향' in next_step(227.1, .1, -205.5, .1)[1] and '0.5배' in next_step(227.1, .1, -205.5, .1)[1]
    assert '더 건드리지' in next_step(-205.5, 5, 8.4, .3)[1]
    assert '헛돌' in next_step(-60, 1, -59, 1)[1]


def test_amplitude_from_unlock_to_drop():
    # 진폭 280°, 리프트각 52°, 18000 bph(주기 0.4초) → 언락→드롭 11.84 ms
    dt = 0.4 / np.pi * np.arcsin(np.radians(52) / (2 * np.radians(280)))
    x = synth([(0.3, 59.5, 0)], 60, unlock=dt)
    amp = analyze_signal(x, SR).segments[0].amplitude
    assert amp is not None and amp.reliable
    assert amp.deg == pytest.approx(280, abs=8)
    assert amplitude_of(dt, 0.4, 52) == pytest.approx(280, abs=.01)
    # 리프트각을 바꾸면 거의 비례해서 바뀐다 (같은 시계끼리 비교는 리프트각과 무관)
    amp45 = analyze_signal(x, SR, lift=45).segments[0].amplitude
    assert amp45.deg / amp.deg == pytest.approx(45 / 52, rel=.03)


def test_amplitude_absent_without_unlock_sound():
    amp = analyze_signal(synth([(0.3, 29.5, 0)], 30), SR).segments[0].amplitude
    assert amp is None or not amp.reliable
    assert analyze_signal(synth([(0.3, 29.5, 0)], 30), SR, lift=None).segments[0].amplitude is None


def test_amplitude_with_split_drop_sound():
    # 오버홀 후처럼 드롭 소리가 갈라져 2.5 ms 뒤에 더 큰 봉우리가 와도, 드롭 시작 기준으로 재야 한다
    dt = 0.4 / np.pi * np.arcsin(np.radians(52) / (2 * np.radians(280)))
    x = synth([(0.3, 59.5, 0)], 60, unlock=dt, drop_echo=0.0025)
    amp = analyze_signal(x, SR).segments[0].amplitude
    assert amp is not None
    assert amp.deg == pytest.approx(280, abs=10)


SHEETS = Path(__file__).resolve().parent.parent / 'sheets'
SHEET = str(SHEETS / 'slava_5671.ini')


def test_sheet_loads_slava_5671():
    s = load_sheet(SHEET)
    assert s.bph == 18000 and s.lift is None
    assert s.tol['rate_s_per_day'] == (-60, 60)
    assert s.tol['amplitude_deg'] == (180, 310)
    assert s.tol['power_reserve_h_min'] == (None, 36)
    assert '±1 мин' in s.comments['rate_s_per_day']
    assert load_sheet(str(SHEETS / '_template.ini')).tol == {}


def test_sheet_compare_pass_border_fail(tmp_path):
    dt = 0.4 / np.pi * np.arcsin(np.radians(52) / (2 * np.radians(280)))
    good = analyze_signal(synth([(0.3, 59.5, 12)], 60, unlock=dt), SR)
    res = {c.item: c.status for c in compare(load_sheet(SHEET), good.segments[0], good)}
    assert res['하루 오차'] == PASS and res['진폭'] == PASS and res['비트 에러'] == PASS
    assert res['파워 리저브'] == NA
    fast = analyze_signal(synth([(0.3, 59.5, 90)], 60), SR)          # 하루 +90초: ±60 초과
    res = {c.item: c.status for c in compare(load_sheet(SHEET), fast.segments[0], fast)}
    assert res['하루 오차'] == FAIL and res['조속 레버로 보정 가능'] == PASS
    edge = analyze_signal(synth([(0.3, 29.5, 59)], 30), SR)          # 한계 바로 안쪽: 오차 범위가 걸침
    assert {c.item: c.status for c in compare(load_sheet(SHEET), edge.segments[0], edge)}['하루 오차'] in (PASS, BORDER)
    bad = tmp_path / 'bad.ini'
    bad.write_text('[tolerance]\nrate_s_per_day = a, b\n')
    with pytest.raises(SheetError):
        load_sheet(str(bad))


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='ffmpeg 필요')
def test_cli_sheet_sets_bph_and_writes_json(tmp_path, capsys):
    p = tmp_path / 'rec.wav'
    x = synth([(0.3, 29.5, 5)], 30)
    wavfile.write(p, SR, (x / np.abs(x).max() * 0.9 * 32767).astype(np.int16))
    out = tmp_path / 'out'
    assert main([str(p), '--시트', SHEET, '--그래프없음', '--기록끔', '--출력', str(out)]) == 0
    assert '사양 비교' in capsys.readouterr().out
    data = json.loads((out / 'rec' / '요약.json').read_text())
    assert data['nominal_bph'] == 18000 and data['sheet_check'][0]['name'] == 'Slava 5671 (61М)'
    assert main([str(p), '--시트', str(tmp_path / 'none.ini')]) == 2

"""정답을 아는 합성 틱 소리로 측정 정확도를 검증한다."""
import json
import shutil

import numpy as np
import pytest
import scipy.io.wavfile as wavfile

from clockrate import AnalysisError, analyze_signal
from clockrate.advice import fmt_duration, grade_rate, lever_direction, next_step
from clockrate.analysis import guess_nominal_bph
from clockrate.cli import main, parse_bph
from clockrate.segments import find_cuts

SR = 48000


def synth(parts, duration, beat=0.2, beat_error=0.003, levers=(), accent=None, seed=1):
    """parts: [(시작, 끝, 초/일), ...] 구간마다 해당 일오차로 틱을 만든다.
    accent: 틱 크기 강약 반복 주기 (예: 4면 네 박마다 한 번 크게)."""
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

"""--언어 옵션: 요약이 선택한 언어로 나오고 요약.json은 한국어 값을 유지하는지."""
import json
import shutil

import numpy as np
import pytest
import scipy.io.wavfile as wavfile

from clockrate.cli import main
from clockrate.i18n import set_lang

from test_synthetic import SR, synth


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='ffmpeg 필요')
def test_lang_en_summary(tmp_path, capsys):
    p = tmp_path / 'rec.wav'
    x = synth([(0.3, 29.5, 12)], 30)
    wavfile.write(p, SR, (x / np.abs(x).max() * 0.9 * 32767).astype(np.int16))
    out = tmp_path / 'out'
    try:
        assert main([str(p), '--lang', 'en', '--기록끔', '--출력', str(out)]) == 0
    finally:
        set_lang('ko')                                   # 이후 테스트는 한국어 기본값으로
    text = capsys.readouterr().out
    assert 'Beat error' in text and 'per day' in text and '비트 에러' not in text
    assert (out / 'rec' / '리포트.png').exists()          # DejaVu로도 그래프가 깨지지 않아야 함
    data = json.loads((out / 'rec' / '요약.json').read_text())
    assert data['segments'][0]['grade']['label'] == '미세 조정 권장'   # JSON은 항상 한국어

"""조정 기록: 녹음을 분석할 때마다 결과를 쌓아, 직전 녹음과 비교해 다음 이동량을 안내한다."""
import json
import os
from datetime import datetime

FILENAME = '조정기록.json'


def load(out_dir):
    try:
        with open(os.path.join(out_dir, FILENAME)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def save(out_dir, entries):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, FILENAME), 'w') as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)


def previous(entries, name, bph):
    """name 바로 앞의 같은 규격 기록. 처음 분석하는 파일이면 마지막 기록."""
    names = [e['file'] for e in entries]
    upto = names.index(name) if name in names else len(entries)
    for e in reversed(entries[:upto]):
        if e.get('bph') == bph:
            return e
    return None


def upsert(entries, name, sg, an):
    """같은 파일을 다시 분석하면 제자리에서 갱신한다 (순서 유지)."""
    entry = dict(file=name, bph=an.nominal_bph, rate=round(sg.rate, 2), ci95=round(2 * sg.rate_se, 2),
                 beat_error_ms=round(sg.fit.beat_err * 1000, 2), analyzed=datetime.now().isoformat(timespec='seconds'))
    for i, e in enumerate(entries):
        if e['file'] == name:
            entries[i] = entry
            return entries
    entries.append(entry)
    return entries

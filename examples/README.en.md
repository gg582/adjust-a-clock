[한국어](../README.md) | [English](README.en.md) | [Русский](README.ru.md) | [Deutsch](README.de.md) | [Français](README.fr.md)

The main README lives at [../README.md](../README.md), with translations in [../docs/](../docs/).

# Examples

Real recordings of a Slava 5671 alarm clock made with a phone, and the results of checking those recordings with `clock-rate`.

## Recordings (`recordings/`)

| File | Length | Situation |
|---|---|---|
| `탈진기.mp3` | 15 s | Regulator lever pushed twice during the recording (example of automatic splitting by lever sounds) |
| `시간조정.mp3` | 60 s | After moving the lever once |
| `시간조정2.mp3` | 64 s | After moving the lever further |
| `시간조정3.mp3` | 121 s | After moving it too far toward slow (a recording where the tick loudness alternates strong/weak) |
| `시간조정4.mp3` | 26 s | After moving it back (a short recording with many noise clicks) |
| `직접오버홀.mp3` | 121 s | After a DIY disassembly, cleaning and oiling, with the mainspring fully wound |

## Check results (`results/`)

Each directory contains `리포트.png`, `요약.txt`, and `요약.json`, and the summary includes a comparison against the `sheets/slava_5671.ini` specs.
`직접오버홀/진단.png` shows the sound structure used for noise removal, tick detection, and amplitude calculation.
`조정기록.png`/`조정기록.json` is the adjustment history in the order 시간조정 → 직접오버홀.

## Reproducing

From the repository root:

```bash
E=examples/results
clock-rate examples/recordings/시간조정.mp3 examples/recordings/시간조정2.mp3 \
           examples/recordings/시간조정3.mp3 examples/recordings/시간조정4.mp3 \
           --시트 sheets/slava_5671.ini --출력 $E
clock-rate examples/recordings/직접오버홀.mp3 --시트 sheets/slava_5671.ini --진단 --출력 $E
clock-rate examples/recordings/탈진기.mp3 --분할 자동 --기준 구간1 --이름 가운데,한쪽끝,반대쪽끝 \
           --시트 sheets/slava_5671.ini --기록끔 --출력 $E
```

Passing `--진단` also produces `소음제거.wav`, which was left out of the examples because of its size.

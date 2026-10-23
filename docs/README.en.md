[한국어](../README.md) | [English](README.en.md) | [Русский](README.ru.md) | [Deutsch](README.de.md) | [Français](README.fr.md)

# clockrate — regulate a mechanical clock from recordings

From a phone recording of a clock's ticking, measures **how many seconds per day it runs fast or slow** and its **amplitude**, and tells you **which way and how far to move the regulator lever**.
Each recording is added to a history, and by comparing with the previous recording it computes "how many times the last distance you moved, in which direction" you should move next.

Built while regulating a Slava 5671 (18000 bph) alarm clock, but it works with any mechanical clock that ticks (specify the beat rate with `--bph`).

See [`examples/`](../examples/README.md) for real recordings and their results.

## Installation

Requires [ffmpeg](https://ffmpeg.org/) (`sudo apt install ffmpeg`, `brew install ffmpeg`, etc.).

```bash
pip install -e .            # install the clock-rate command
pip install -e '.[test]'    # including tests
```

You can also run it without installing, via `python3 -m clockrate ...`.

## How to regulate a clock

```bash
clock-rate 녹음1.m4a      # 1. record for at least 1 minute and analyze
                          # 2. move the regulator lever as advised, then record again
clock-rate 녹음2.m4a      # 3. compares with the previous recording and suggests the next move
...                       # 4. repeat until '◎ 조정 완료' (regulation done) appears
```

The terminal and `results/<파일명>/요약.txt` show a summary like this.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 시간조정2.mp3   (녹음 64초 · 18000 bph 기준)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ✖ 크게 어긋남   하루 3분 47초 빠름   (+227.1 ± 4.0 초/일)

 ▶ 할 일
   조속 레버를 느림(-, S) 쪽으로 옮기세요.
   직전 녹음(시간조정) 대비 -115.6 초/일 변화 →
   직전에 옮긴 방향으로, 그때 옮긴 거리의 약 2.0배 더 옮기세요.

 ▶ 이대로 두면
   1일 +3분 47초 · 1주 +26분 29초 · 30일 +1시간 54분

 ▶ 시계 상태
   비트 에러     2.9 ms  ◎ 양호
   진폭          약 298° (288–314°, 틱 308° · 톡 289°)  ◎ 좋음
                 리프트각 52° 가정 — 같은 시계끼리 비교할 때 가장 정확
   속도 안정성   +222 ~ +236 초/일 (10초 단위, 폭 14)  안정

 ▶ 측정 신뢰도  높음
   틱 320/320개 사용 (100%), 놓친 틱 1개 다시 찾음, 잡음 클릭 1개 제외
   틱 시각 흔들림 354 µs · 실측 진동수 18047.3 bph
```

### Judgment criteria

| Symbol | Daily error | Meaning |
|---|---|---|
| ◎ 조정 완료 (done) | within ±10 s (change with `--tolerance`) | don't touch it any further |
| △ 미세 조정 권장 (fine adjustment recommended) | within ±30 s | move only a tiny amount |
| ▲ 조정 필요 (adjustment needed) | within ±60 s | |
| ✖ 크게 어긋남 (far off) | beyond that | |

- **Beat error** is the asymmetry between the tick and tock intervals. 3 ms or less is good; above 5 ms the balance rest position (the beat) should be set.
- **Amplitude** is the angle the balance wheel turns in one swing. Above 330° is too large (watch out for banking), 250–330° is good, 200–250° is fair, below 200° is low (check mainspring winding, lubrication, dirt) — the criteria commonly used for wristwatches. See [Amplitude](#amplitude) below.
- **Rate stability** is the spread of values computed separately over 10–20 second slices of the recording. A wide spread means the mainspring is running down, the clock was moved, or the recording conditions were poor.
- **Measurement confidence** is judged only from the recording conditions (length, tick detection rate, noise clicks). When it is "low", the tool explains why and gives recording tips.
- **Next move** is an estimate assuming the rate changes in proportion to the distance the lever is moved. If there is almost no change from the previous recording, the tool warns that the lever may be slipping or the hairspring may have come out of the regulator pins.

## Output

| File | Contents |
|---|---|
| `results/<파일명>/리포트.png` | Verdict and to-do, target-range gauge, timegrapher plot, and rate-over-time in a single image |
| `results/<파일명>/요약.txt` | The summary above |
| `results/<파일명>/요약.json` | The same data in machine-readable form |
| `results/조정기록.png` | How the daily error and amplitude changed across recordings, in order, plus the next to-do |
| `results/조정기록.json` | Regulation history (re-analyzing the same file updates it in place) |
| `results/<파일명>/다른시계.png` | Only when `--multi-clock` finds another clock: that clock's tick waveform and timegrapher plot |
| `results/<파일명>/진단.png`, `소음제거.wav` | Only with `--diagnostics`: noise removal, tick detection status, and the unlock/drop positions used for the amplitude calculation |

**How to read the timegrapher plot:** each dot shows how far ahead of nominal a tick was (ms).
- **Slope of the line:** dots drifting upward mean fast, downward mean slow.
- **Gray wedge:** the target range (±10 s/day). A line lying inside it is within target.
- **Gap between the two lines:** the distance between the tick (blue) and tock (orange) lines is the beat error.

## Options

| Option | Value | Description |
|---|---|---|
| `--bph` / `--vph` | `18000` (default) | Nominal beat rate. Specify e.g. `28800` for other movements |
| | `auto` | Automatically pick a standard rate (3600–36000) within ±1% of the measured value |
| `--lift-angle` | `52` (default) | Lift angle in degrees for the amplitude calculation. `0` disables amplitude |
| `--sheet` | INI path | Compare measurements against a movement spec sheet (see [Spec sheet](#spec-sheet)). Sheet values are used for bph and lift angle unless given directly |
| `--tolerance` | `10` (default) | Within this (s/day) counts as regulation done |
| `--split` | `none` (default) | Treat the whole recording as one segment |
| | `auto` | If the lever was moved **during** the recording, find the "swish" sound and compare before/after |
| | `3.5,9.2` | Split at the given times (seconds) |
| `--reference` | `auto` (default) | Absolute error against the nominal rate (falls back to segment 1 if no standard rate is found with `--bph auto`) |
| | `nominal` | Absolute error against the nominal rate |
| | `first` | Compare only the change relative to the first segment (for checking the effect of lever positions) |
| `--names` | `center,faster,...` | Segment names |
| `--window` | seconds | Window length for rate-over-time. Defaults to 10 s (segments under 90 s) or 20 s; `0` disables |
| `--out` | folder | Output folder (default `./results`). The regulation history is also kept here |
| `--no-history` | | Do not record to the history and do not compare with the previous recording |
| `--multi-clock` | | After removing the main clock's sound, also find other clocks (e.g., a quartz clock in the background) and measure them (see [Multiple clocks](#multiple-clocks)) |
| `--diagnostics` | | Also save diagnostic graphs and a denoised wav |
| `--no-plots` | | Produce only the summary |
| `--lang` | `ko` (default), `en`, `ru`, `de`, `fr` | Language of the summary and report |

Passing several files at once analyzes them in the given order and adds them to the history: `clock-rate recordings/시간조정*.mp3`

To compare the effect of lever positions in a single recording: `clock-rate 탈진기.mp3 --split auto --reference first --names center,one_end,other_end`

## Amplitude

A single tick sound is made of several smaller sounds layered together. In a Swiss lever escapement (including the Slava 5671), the **unlock** (the faint sound of the escapement releasing) is followed by the **drop** (the louder sound of the tooth landing).
Because the balance turns through the lift angle between these two sounds, the amplitude can be calculated.

```
amplitude = lift_angle / (2·sin(π · unlock→drop time / one period))
```

- **Averaged curve:** the loudness curves of the whole recording are overlaid per tick/tock and reduced to a median; the sharpest peak before the drop, within the physically possible range (the time corresponding to amplitudes of 140–380°), is taken as the unlock.
- **Confidence:** a 95% range is computed by bootstrap resampling of the ticks. If the tick and tock values differ by more than 30°, or the range is wider than 40°, the value is marked "for reference".
- **Lift angle:** a property of the movement. No official value for the Slava 5671 could be found, so the common Swiss lever value of 52° is the default. Absolute values are uncertain by exactly this assumption.
- **Comparing the same clock:** amplitude is nearly proportional to the lift angle, so comparing recordings of the same clock (whether the amplitude has dropped) is accurate regardless of the lift angle. You can see this trend in the history graph.
- **Diagnostic graph:** with `--diagnostics` you can see which sounds were actually picked as the unlock and drop.

## Multiple clocks

With `--multi-clock`, other clocks captured in the recording (e.g., a quartz wall clock in the room) are also found and their daily error measured. Without it, results are exactly the same as before.

```bash
clock-rate recordings/오버홀하루후.mp3 --여러시계
```

```
 ▶ 다른 시계 (--여러시계)
   시계 2   1.000초 간격 · 실측 3599.9 bph · 쿼츠 시계(1초마다 뛰는 초침)로 보임
            오차 범위 안 (사실상 정확)   (-1.3 ± 2.9 초/일)
            틱 177/180개 사용 (98%) · 틱 시각 흔들림 11.2 ms · 800–1500 Hz 대역에서 찾음
            주 시계 − 시계 2: -1.9 ± 4.3 초/일 (녹음 장비 시계 오차와 무관)
```

- **How it finds them:** 200 Hz–12 kHz is split into five bands; a loudness curve is made per band, and the main clock's ticks (a two-beat median shape) are subtracted at every position predicted by the beat model. Repeats of 0.1–2.5 s are looked for in the autocorrelation of the remaining curve; ticks are detected in the clearest band and the daily error is computed with the same beat model as the main clock. Once one clock is found, it is subtracted too and the search repeats (up to 3 clocks).
- **Rejecting false clocks:** a candidate must be clearer than the repeats left over from incomplete subtraction of the main clock (multiples of the main beat interval), must find at least 70% of the expected ticks, and its tick timing jitter must be within 5% of the beat interval to count as a clock.
- **Quartz detection:** a 1-second interval (3600 bph) is taken to be a quartz clock whose second hand steps once per second.
- **Main clock − other clock:** both clocks are measured against the same recording-device clock, so this difference does not include the phone clock error. Using quartz (usually ±0.5 s/day) as the reference gives the main clock's error independent of the phone.
- **Precision:** background clocks are quiet, so their tick timing jitter is large (several to tens of ms), giving a wider confidence interval than the main clock for the same recording length. The interval is the regression error widened by the correlation of neighboring residuals (using per-window spread like the main clock would inflate the error, because each window's slope is inaccurate).
- Other clocks are not added to the regulation history or the spec comparison.

## Spec sheet

Write movement specs as INI under `sheets/` and pass it with `--sheet`; each measurable item is judged against the factory tolerance.

```bash
clock-rate 녹음.m4a --시트 sheets/slava_5671.ini
```

```
 ▶ 사양 비교 — Slava 5671 (61М): 측정 가능한 항목 모두 공차 안 (경계 1개)
   ◎ 합격    하루 오차         -3.2 ± 1.1 초/일       사양 ±60초/일
                          근거: «Суточный ход механизма ±1 мин при температуре +20±5°С»
   △ 경계    진폭            약 301°               사양 180–310°
   · 측정 불가 파워 리저브        —                    사양 36시간 이상
   ...
```

- **Judgment criteria:** **pass** if both the measured value and its 95% range are within tolerance, **borderline** if the value is within but the 95% range straddles the tolerance, **fail** if the value is outside. An amplitude marked "for reference" because tick and tock disagree is left as borderline rather than judged pass/fail.
- **Unmeasurable items:** power reserve, rate differences by mainspring state, amplitude variation, and self-start cannot be measured from a single recording, so they are marked "not measurable" along with how to measure them.
- **Source display:** the `;` comment after a value in the sheet appears in the judgment result as the "basis". Keep the source of each spec there.
- **`sheets/slava_5671.ini`:** transcribes, with original quotations, the Slava 5671 specs and regulation criteria from Л. В. Шамонова, «Ремонт механических будильников» (1987) (daily rate ±1 min, regulator range ±3 min, amplitude 180–310°, power reserve at least 36 h, etc.). Lift angle and beat error tolerance have no figures in the source and are left blank.
- **`sheets/_template.ini`:** an empty template for other movements.

## Recording tips

- In a quiet room, hold the phone microphone right against the back of the clock.
- Record for **at least 1 minute**. Shorter than 20 seconds greatly reduces precision and makes rate stability unavailable.
- Depending on how far the mainspring is wound, the rate can differ by tens of seconds per day. Keep the conditions the same across recordings you compare.

## How it works

1. **Noise removal:** 3.5–16 kHz band-pass followed by spectral gating. The noise reference is taken from the quiet parts between ticks, and a 1-second-window median over time tracks changes in the noise floor (conversation, TV, handling sounds).
2. **Beat interval estimation:** uses the most common interval among peaks of the loudness curve ("envelope" in signal-processing terms). Even if ticks alternate loud/soft, several beats are not mistaken for one.
3. **First-pass tick detection:** takes the time the loudness curve first crosses 30% of the peak height.
4. **Beat numbering and noise removal:** ticks are followed one by one and numbered; noise clicks off the beat are dropped.
5. **Precision refinement:** an average shape (template) is built per tick/tock and cross-correlated with each tick to re-time it at sub-sample precision. Missed ticks are filled in where a sound at the predicted position matches the template well enough (correlation ≥ 0.6). In noisy recordings this reduces tick timing jitter by about 60%.
6. **Beat model:** solves `t = a + n·beat_interval + c·(odd/even)` by least squares. The odd/even term is the beat error.
7. **Amplitude:** computed from the unlock→drop time measured in the original (pre-gating) sound (see [Amplitude](#amplitude)).
8. **Daily error:** `(nominal beat interval / measured beat interval − 1) × 86400`. The confidence interval uses the larger of the regression error and the spread of the per-window values, because the clock's own slow wander would make a regression-only interval too narrow.

## Validation

On the synthetic recordings in `tests/` (including street noise, lever sounds, beat error, loud/soft ticks, and unlock sounds), the daily error matches the ground truth within 0.5 s/day and the amplitude within 8°.
On a synthetic recording mixed with a faint quartz tick (1 kHz) in the background, `--multi-clock` finds the quartz daily error within 1 s/day of the truth, and finds nothing in recordings without another clock (including loud/soft ticks).
On a real recording (Slava 5671), an Android timegrapher app (+7 s/day) and this tool (+8.4 ± 0.6 s/day) agreed.
A real regulation case (2026-10-22~23): a Slava 5671 running 14 min 43 s fast per day was brought to **+0.6 s/day** (measured 18000.1 bph, cross-checked against a background quartz clock at +3.4 ± 28.7 s/day) by adjusting the hairspring effective length and regulator lever as this tool advised. The process is documented in [`docs/slava_5671_regulation_notes.en.md`](slava_5671_regulation_notes.en.md).

```bash
python3 -m pytest
```

## Project layout

```
clockrate/
  audio.py      audio loading (ffmpeg), noise removal, loudness curve
  ticks.py      beat interval estimation, tick detection, beat model, template refinement
  amplitude.py  amplitude from the unlock→drop time
  segments.py   lever-sound detection, split modes
  analysis.py   per-segment daily error, confidence interval, rate-over-time, amplitude (no plots)
  advice.py     judgment grades (error, beat error, amplitude), lever direction, next move, measurement confidence
  history.py    regulation history (조정기록.json)
  report.py     Korean summary, JSON
  plots.py      report, history, and diagnostic graphs
  cli.py        command line (clock-rate)
  sheet.py      spec sheet (INI) loading and tolerance comparison
  multiclock.py --multi-clock: find other clocks in the sound left after removing the main clock
sheets/         movement spec sheets (slava_5671.ini, _template.ini)
examples/       6 real recordings and their results (examples/README.md)
tests/          synthetic-signal tests
recordings/     recordings
photos/         photos (excluded from git)
results/        analysis results (denoised wav files excluded from git)
```

Korean graphs use the first installed font among NanumBarunGothic, NanumGothic, Noto Sans CJK KR, Malgun Gothic, and AppleGothic.

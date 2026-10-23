[한국어](slava_5671_regulation_notes.md) | [English](slava_5671_regulation_notes.en.md) | [Русский](slava_5671_regulation_notes.ru.md) | [Deutsch](slava_5671_regulation_notes.de.md) | [Français](slava_5671_regulation_notes.fr.md)

# Slava 5671 regulation case notes (2026-10-22~23)

A record of actually regulating a Slava 5671 alarm clock with `clock-rate`. The measurements are preserved as-is in `results/조정기록.json`.

## Symptoms

- In the vertical position (the position of actual use), running **+883 s/day (14 min 43 s) fast**. In the horizontal position it was normal at -3 s/day.
- A value beyond the regulator lever's adjustment range (factory rating ±3 min/day), so the lever alone could not fix it.
- Recordings in the vertical position showed a low amplitude of 205–262° (lower than horizontal) and a large beat error of 8–13 ms.

## Course of events

1. Even with the lever turned all the way to -, still more than +9 min/day fast → switched to adjusting the hairspring effective length.
2. Overshot by lengthening the spring too much at once, down to 1 hour slow per day (-3657 s/day) → the rate change per adjustment amount (sensitivity) was measured, making proportional guidance valid from then on.
3. During the hairspring readjustment, the vertical-position amplitude recovered from 240° to 310°, and the beat error dropped to around 2 ms.

## Conclusion: "fast when vertical" was a defect, not an intrinsic positional error

At first it was assumed to be a positional error caused by pivot friction and reduced amplitude in the vertical position, but after the spring was reseated, the horizontal–vertical difference was confirmed to be only **about 5 s/day**. In other words, the cause was the hairspring touching something in the vertical position, and the spring work resolved it as well.

Keeping positional error small from the outset is a task for clocks whose position changes, such as wristwatches and marine chronometers; for a desk clock used in a single position, even the manufacturer does not require it (the factory tolerance for this movement, ±60 s/day, has no positional item). Wristwatch certification standards such as COSC do not apply to desk clocks.

## Final state

- **+0.6 s/day** (measured 18000.1 bph, against the nominal 18000)
- Cross-check against a background quartz clock: main clock − quartz = +3.4 ± 28.7 s/day (an independent confirmation unaffected by the recording device's clock error)
- Horizontal–vertical positional error about 5 s/day
- Amplitude about 248–301°, beat error 1–3 ms

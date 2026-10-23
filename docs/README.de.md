[한국어](../README.md) | [English](README.en.md) | [Русский](README.ru.md) | [Deutsch](README.de.md) | [Français](README.fr.md)

# clockrate — mechanische Uhren per Aufnahme regulieren

Aus einer mit dem Handy aufgenommenen Uhr-Tickgeräusch-Aufnahme misst das Tool, **um wie viele Sekunden pro Tag die Uhr vor- oder nachgeht** und wie groß die **Amplitude** ist, und sagt, **in welche Richtung und um wie viel der Rückerzeiger zu verstellen ist**.
Bei jeder Aufnahme wird das Ergebnis im Regulierungsprotokoll gespeichert und mit der vorherigen Aufnahme verglichen, um zu berechnen, „um das Wievielfache des damals verstellten Wegs und in welche Richtung" weiter verstellt werden muss.

Entstanden beim Regulieren eines Slava-5671-Weckers (18000 bph), funktioniert aber mit jeder mechanischen Uhr, die tickt (Schwingungszahl per `--bph` angeben).

Beispiele echter Aufnahmen und Prüfergebnisse finden sich unter [`examples/`](examples/README.md).

## Installation

[ffmpeg](https://ffmpeg.org/) wird benötigt (`sudo apt install ffmpeg`, `brew install ffmpeg` usw.).

```bash
pip install -e .            # clock-rate 명령 설치
pip install -e '.[test]'    # 테스트까지
```

Ohne Installation geht auch `python3 -m clockrate ...`.

## Ablauf beim Regulieren

```bash
clock-rate 녹음1.m4a      # 1. 1분 이상 녹음해서 분석
                          # 2. 안내대로 조속 레버를 옮기고 다시 녹음
clock-rate 녹음2.m4a      # 3. 직전 녹음과 비교해 다음 이동량 안내
...                       # 4. '◎ 조정 완료'가 나올 때까지 반복
```

Im Terminal und in `results/<파일명>/요약.txt` erscheint eine solche Zusammenfassung.

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

### Bewertungskriterien

| Anzeige | Tagesgangabweichung | Bedeutung |
|---|---|---|
| ◎ Regulierung abgeschlossen | innerhalb ±10 s (änderbar mit `--tolerance`) | Nichts mehr verstellen |
| △ Feinjustierung empfohlen | innerhalb ±30 s | Nur ganz wenig verstellen |
| ▲ Regulierung nötig | innerhalb ±60 s | |
| ✖ deutlich abweichend | darüber | |

- **Schlagfehler** (Beat Error) ist die Asymmetrie zwischen Tick- und Tack-Intervall. Bis 3 ms gut; über 5 ms sollte die Ruhelage der Unruh (der Schlag) korrigiert werden.
- **Amplitude** ist der Winkel, den die Unruh pro Schwingung dreht. Über 330° zu groß (Vorsicht, Anschlagen/Rebanking), 250–330° gut, 200–250° mittel, unter 200° niedrig (Zugfederzustand, Ölung, Verschmutzung prüfen) — übliche Richtwerte für Armbanduhren. Siehe unten [Amplitude](#amplitude).
- **Gangstabilität** ist die Streuung der Werte, die aus in 10–20-Sekunden-Stücke zerschnittenen Teilen der Aufnahme einzeln berechnet wurden. Große Streuung bedeutet: die Zugfeder läuft ab, die Uhr wurde bewegt oder die Aufnahme ist schlecht.
- **Messverlässlichkeit** wird allein aus dem Aufnahmezustand beurteilt (Länge, Tick-Erkennungsrate, Störklicks). Bei „niedrig" werden Grund und Aufnahmetipps angezeigt.
- **Nächster Verstellweg** ist eine Schätzung unter der Annahme, dass sich der Gang proportional zum Verstellweg des Rückers ändert. Wenn der Unterschied zur vorherigen Aufnahme fast null ist, wird darauf hingewiesen, dass der Rücker möglicherweise leer mitdreht oder die Spiralfeder aus den Rückerstiften gerutscht ist.

## Ausgabe

| Datei | Inhalt |
|---|---|
| `results/<파일명>/리포트.png` | Bewertung und Aufgaben, Zielbereichs-Anzeige, Zeitwaagen-Diagramm und Fehlerverlauf auf einer Seite |
| `results/<파일명>/요약.txt` | die obige Zusammenfassung |
| `results/<파일명>/요약.json` | dieselben Daten maschinenlesbar |
| `results/조정기록.png` | Verlauf von Tagesgangabweichung und Amplitude in Aufnahmereihenfolge, mit nächster Aufgabe |
| `results/조정기록.json` | Regulierungsprotokoll (wird bei erneuter Analyse derselben Datei an Ort und Stelle aktualisiert) |
| `results/<파일명>/다른시계.png` | nur wenn `--multi-clock` eine weitere Uhr gefunden hat: deren Tick-Klangform und Zeitwaagen-Diagramm |
| `results/<파일명>/진단.png`, `소음제거.wav` | nur mit `--diagnostics`: Rauschunterdrückung, Tick-Erkennungsstatus, die für die Amplitudenberechnung verwendeten Entriegelungs- und Fall-Positionen |

**Zeitwaagen-Diagramm lesen:** Für jeden Tick wird als Punkt aufgetragen, um wie viele ms er der Sollzeit voraus ist.
- **Steigung der Linie:** steigen die Punkte an, geht die Uhr vor; fallen sie, geht sie nach.
- **Grauer Fächer:** der Zielbereich (±10 s/Tag). Liegt die Linie darin, ist der Zielbereich erreicht.
- **Abstand der beiden Linien:** der Abstand zwischen der Tick-Linie (blau) und der Tack-Linie (orange) ist der Schlagfehler.

## Optionen

| Option | Wert | Beschreibung |
|---|---|---|
| `--bph` | `18000` (Standard) | Soll-Schwingungszahl. Für andere Uhren z. B. `28800` angeben |
| | `자동` | wählt automatisch den Standardwert (3600–36000) innerhalb ±1 % des Messwerts |
| `--lift-angle` | `52` (Standard) | Hubwinkel (Grad) für die Amplitudenberechnung. `0` = keine Amplitudenberechnung |
| `--sheet` | INI-Pfad | vergleicht Messwerte mit einem Werkspezifikationsblatt (siehe [Spezifikationsblatt](#spezifikationsblatt)). Ohne explizite bph-/Hubwinkel-Angabe werden die Werte des Blatts verwendet |
| `--tolerance` | `10` (Standard) | innerhalb dieses Werts (s/Tag) gilt die Regulierung als abgeschlossen |
| `--split` | `없음` (Standard) | ganze Aufnahme als ein Abschnitt |
| | `자동` | wurde der Rücker **während** der Aufnahme verstellt, wird das Streichgeräusch gesucht und davor/danach getrennt verglichen |
| | `3.5,9.2` | an den angegebenen Zeitpunkten (Sekunden) teilen |
| `--reference` | `자동` (Standard) | absoluter Fehler gegenüber der Soll-Schwingungszahl (wird bei `--bph 자동` kein Standardwert gefunden, gilt Abschnitt 1 als Referenz) |
| | `규격` | absoluter Fehler gegenüber der Soll-Schwingungszahl |
| | `구간1` | nur die Änderung gegenüber dem ersten Abschnitt vergleichen (zur Prüfung der Wirkung je Rückerposition) |
| `--names` | `가운데,빠르게,...` | Namen der Abschnitte |
| `--window` | Sekunden | Fensterlänge des Fehlerverlaufs. Ohne Angabe 10 s (Abschnitt unter 90 s) bzw. 20 s, `0` = aus |
| `--out` | Ordner | Ergebnisordner (Standard `./results`). Auch das Regulierungsprotokoll wird hier abgelegt |
| `--no-history` | | nicht im Regulierungsprotokoll speichern und nicht mit der vorherigen Aufnahme vergleichen |
| `--multi-clock` | | sucht im Restklang nach Abzug der Hauptuhr auch andere Uhren (z. B. eine Quarzuhr im Hintergrund) und misst sie (siehe [Mehrere Uhren](#mehrere-uhren)) |
| `--diagnostics` | | zusätzlich Diagnosediagramme und eine rauschbereinigte WAV-Datei speichern |
| `--no-plots` | | nur die Zusammenfassung erzeugen |
| `--lang` | `ko` (Standard), `en`, `ru`, `de`, `fr` | Sprache der Zusammenfassung und des Berichts |

Mehrere Dateien auf einmal werden in der angegebenen Reihenfolge analysiert und ins Protokoll aufgenommen: `clock-rate recordings/시간조정*.mp3`

Um die Wirkung je Rückerposition in einer Aufnahme zu vergleichen: `clock-rate 탈진기.mp3 --split 자동 --reference 구간1 --names 가운데,한쪽끝,반대쪽끝`

## Amplitude

Ein einzelnes Tick-Geräusch besteht aus mehreren überlagerten Einzelgeräuschen. Bei der Schweizer Ankerhemmung (auch in der Slava 5671) folgt auf die **Entriegelung** (leises Geräusch beim Freigeben der Hemmung) der **Fall** (lautes Geräusch des fallenden Zahns).
Während die Unruh um den Hubwinkel weiterdreht, vergeht genau die Zeit zwischen diesen beiden Geräuschen — daraus lässt sich die Amplitude berechnen.

```
진폭 = 리프트각 / (2·sin(π · 언락→드롭 시간 / 한 주기))
```

- **Mittelkurve:** Die Lautstärkekurven der gesamten Aufnahme werden für jeden Tick und Tack überlagert und der Median gebildet; als Entriegelung gilt die markanteste Spitze vor dem Fall im physikalisch möglichen Bereich (Zeit entsprechend einer Amplitude von 140–380°).
- **Verlässlichkeit:** Per Bootstrap (zufälliges Neu-Ziehen der Ticks) wird der 95-%-Bereich bestimmt. Weichen Tick- und Tack-Wert um mehr als 30° ab oder ist der Bereich breiter als 40°, wird „nur als Anhaltspunkt" angezeigt.
- **Hubwinkel:** werksspezifischer Wert. Der offizielle Wert der Slava 5671 konnte nicht gefunden werden, daher ist der für Schweizer Ankerhemmungen übliche Wert 52° voreingestellt. Der absolute Wert ist entsprechend unsicher.
- **Vergleich derselben Uhr:** Da die Amplitude nahezu proportional zum Hubwinkel ist, ist der Vergleich von Aufnahmen derselben Uhr (ob die Amplitude gesunken ist) unabhängig vom Hubwinkel exakt. Dieser Trend ist im Regulierungsprotokoll-Diagramm sichtbar.
- **Diagnosediagramm:** Mit `--diagnostics` ist sichtbar, welche Geräusche tatsächlich als Entriegelung und Fall erkannt wurden.

## Mehrere Uhren

Mit `--multi-clock` werden auch andere Uhren in der Aufnahme gesucht und deren Tagesgangabweichung gemessen (z. B. eine Quarz-Wanduhr im Raum). Ohne diese Option ist das Ergebnis exakt dasselbe wie zuvor.

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

- **Suchmethode:** 200 Hz–12 kHz werden in fünf Bänder geteilt, pro Band eine Lautstärkekurve erstellt und an jeder vom Schlagmodell vorhergesagten Position der Tick der Hauptuhr (Medianform über zwei Schläge) abgezogen. In der Autokorrelation des Rests wird eine Wiederholung zwischen 0,1 und 2,5 s gesucht, im deutlichsten Band werden Ticks erkannt und mit demselben Schlagmodell wie die Hauptuhr die Tagesgangabweichung berechnet. Wird eine Uhr gefunden, wird auch sie abgezogen und weitergesucht (maximal 3).
- **Fehlerkennungen herausfiltern:** Eine Wiederholung muss deutlicher sein als das, was die unvollständig entfernte Hauptuhr hinterlässt (Vielfache ihres Schlagintervalls), mindestens 70 % der erwarteten Ticks müssen gefunden werden und der Tick-Zeitjitter muss ≤ 5 % des Schlagintervalls liegen, damit sie als Uhr anerkannt wird.
- **Quarzerkennung:** Bei 1-Sekunden-Intervall (3600 bph) wird von einer Quarzuhr mit springendem Sekundenzeiger ausgegangen.
- **Hauptuhr − andere Uhr:** Beide Uhren werden mit derselben Aufnahmegerät-Uhr gemessen, daher enthält diese Differenz den Fehler der Handy-Uhr nicht. Mit der Quarzuhr (üblicherweise ±0,5 s/Tag) als Referenz ergibt sich der Fehler der Hauptuhr ohne Umweg über das Handy.
- **Genauigkeit:** Hintergrunduhren klingen leise, ihr Tick-Zeitjitter liegt bei einigen bis einigen zehn ms, sodass das Vertrauensintervall bei gleicher Aufnahmelänge breiter ist als bei der Hauptuhr. Das Intervall wird um die Korrelation benachbarter Residuen erweitert (die fensterweise Streuung wie bei der Hauptuhr würde den Fehler wegen ungenauer Steigung je Fenster zu stark aufblähen).
- Andere Uhren fließen weder ins Regulierungsprotokoll noch in den Spezifikationsvergleich ein.

## Spezifikationsblatt

Werkspezifikationen als INI-Datei in `sheets/` ablegen und mit `--sheet` übergeben — dann wird pro Position geprüft, ob die Messwerte innerhalb der Werktoleranz liegen.

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

- **Bewertung:** Liegen Messwert und 95-%-Bereich innerhalb der Toleranz, gilt **bestanden**; liegt der Messwert innerhalb, der 95-%-Bereich aber teilweise außerhalb, **grenzwertig**; liegt der Messwert außerhalb, **nicht bestanden**. Eine Amplitude, die wegen abweichender Tick-/Tack-Werte nur Anhaltspunkt ist, wird nicht als bestanden/nicht bestanden bewertet, sondern als grenzwertig.
- **Nicht messbare Positionen:** Gangreserve, Gangunterschiede je Zugfederzustand, Amplitudenschwankung und automatischer Anlauf lassen sich aus einer Aufnahme nicht messen — sie werden mit „nicht messbar" und einem Hinweis zur Messmethode aufgeführt.
- **Quellenangabe:** Der `;`-Kommentar hinter einem Wert im Blatt erscheint im Ergebnis als „Quelle". Bitte die Herkunft der Spezifikation dort festhalten.
- **`sheets/slava_5671.ini`:** übernimmt die Slava-5671-Spezifikationen und Regulierungswerte (Tagesgangabweichung ±1 min, Rückerbereich ±3 min, Amplitude 180–310°, Gangreserve mindestens 36 h usw.) aus Л. В. Шамонова, «Ремонт механических будильников» (1987) mit Originalzitaten. Hubwinkel und Schlagfehler-Toleranz haben im Original keine Zahlenwerte und bleiben leer.
- **`sheets/_template.ini`:** leere Vorlage für andere Werke.

## Aufnahmetipps

- In einem ruhigen Raum das Handy-Mikrofon dicht an den Uhrenboden halten.
- **Mindestens 1 Minute** aufnehmen. Unter 20 Sekunden sinkt die Genauigkeit deutlich und die Gangstabilität kann nicht beurteilt werden.
- Je nach Zugfederzustand kann der Gang um mehrere zehn Sekunden pro Tag variieren. Für Vergleiche die Bedingungen angleichen.

## Funktionsweise

1. **Rauschunterdrückung:** Bandpass 3,5–16 kHz, danach Spektral-Gating. Die Rauschreferenz wird aus den stillen Abschnitten zwischen den Ticks genommen; über den zeitlichen Median in 1-s-Fenstern folgt sie auch zeitlichen Schwankungen des Rauschbodens (Gespräche, Fernseher, Handbewegungen).
2. **Schätzung des Schlagintervalls:** der häufigste Abstand zwischen den Spitzen der Lautstärkekurve (signaltechnisch „Hüllkurve", Envelope) wird verwendet. Auch wenn Ticks abwechselnd stark/schwach sind, werden mehrere Schläge nicht mit einem verwechselt.
3. **Erste Tick-Erkennung:** der Zeitpunkt, an dem die Lautstärkekurve erstmals 30 % der Spitzenhöhe überschreitet.
4. **Schlagzählung und Entstörung:** die Ticks werden einzeln verfolgt und mit Schlagnummern versehen; Störklicks außerhalb des Takts werden entfernt.
5. **Feinkorrektur:** Für Tick und Tack wird eine Mittelform (Template) erstellt und per Kreuzkorrelation mit jedem Tick die Zeit mit Subsample-Genauigkeit neu bestimmt. Verpasste Ticks werden an der vorhergesagten Position ergänzt, wenn dort ein dem Template ausreichend ähnliches Geräusch (Korrelation ≥ 0,6) gefunden wird. Bei verrauschten Aufnahmen sinkt der Tick-Zeitjitter um etwa 60 %.
6. **Schlagmodell:** `t = a + n·박간격 + c·(홀짝)` wird per kleinster Quadrate gelöst. Der Gerade/Ungerade-Term ist der Schlagfehler.
7. **Amplitude:** aus der Entriegelung→Fall-Zeit im Originalklang (vor dem Gating) berechnet (siehe oben [Amplitude](#amplitude)).
8. **Tagesgangabweichung:** `(Soll-Schlagintervall / gemessenes Schlagintervall − 1) × 86400`. Für das Vertrauensintervall wird der größere Wert aus Regressionsfehler und Streuung der zeitfensterweisen Werte genommen — wegen langsamer Schwankungen der Uhr selbst wäre das Intervall allein aus dem Regressionsfehler zu eng.

## Verifikation

In den synthetischen Aufnahmen in `tests/` (mit Stadtlärm, Rückergeräusch, Schlagfehler, stark/schwachen Ticks und Entriegelungsgeräusch) liegt die Tagesgangabweichung innerhalb von 0,5 s/Tag und die Amplitude innerhalb von 8° am Sollwert.
In synthetischen Aufnahmen mit leisem Quarz-Tick (1 kHz) im Hintergrund findet `--multi-clock` die Tagesgangabweichung der Quarzuhr innerhalb von 1 s/Tag am Sollwert und findet in Aufnahmen ohne weitere Uhr (auch mit stark/schwachen Ticks) nichts.
Bei einer echten Aufnahme (Slava 5671) stimmte der Wert einer Android-Zeitwaagen-App (+7 s/Tag) mit dem Wert dieses Tools (+8,4 ± 0,6 s/Tag) überein.
Praxisbeispiel einer Regulierung (22.–23.10.2026): Eine Slava 5671, die 14 min 43 s pro Tag vorging, wurde nach Anleitung dieses Tools über die wirksame Spiralfederlänge und den Rückerzeiger auf **+0,6 s/Tag** gebracht (gemessen 18000,1 bph, Gegenprobe mit der Hintergrund-Quarzuhr +3,4 ± 28,7 s/Tag). Der Ablauf steht in [`docs/slava_5671_regulation_notes.de.md`](docs/slava_5671_regulation_notes.de.md).

```bash
python3 -m pytest
```

## Aufbau

```
clockrate/
  audio.py      오디오 읽기(ffmpeg), 소음 제거, 소리 크기 곡선
  ticks.py      박자 간격 추정, 틱 검출, 박자 모델, 템플릿 보정
  amplitude.py  언락→드롭 시간으로 진폭 계산
  segments.py   레버 소리 검출, 분할 모드
  analysis.py   구간별 하루 오차·신뢰구간·시간대별 오차·진폭 (그래프 없음)
  advice.py     판정 등급(오차·비트 에러·진폭), 레버 방향, 다음 이동량, 측정 신뢰도
  history.py    조정 기록 (조정기록.json)
  report.py     한국어 요약, JSON
  plots.py      리포트·조정 기록·진단 그래프
  cli.py        명령줄 (clock-rate)
  sheet.py      사양 시트(INI) 읽기와 공차 비교
  multiclock.py --여러시계: 주 시계를 빼고 남은 소리에서 다른 시계 찾기
sheets/         무브먼트 사양 시트 (slava_5671.ini, _template.ini)
examples/       실제 녹음 6개와 그 점검 결과 (examples/README.md)
tests/          합성 신호 테스트
recordings/     녹음
photos/         사진 (git 제외)
results/        분석 결과 (소음 제거 wav는 git 제외)
```

Für die Grafiken wird die erste installierte Schrift aus NanumBarunGothic, NanumGothic, Noto Sans CJK KR, Malgun Gothic, AppleGothic verwendet.

[한국어](../README.md) | [English](README.en.md) | [Русский](README.ru.md) | [Deutsch](README.de.md) | [Français](README.fr.md)

Die Haupt-README liegt unter [../README.md](../README.md), Übersetzungen in [../docs/](../docs/).

# Beispiele

Echte, mit dem Handy aufgenommene Aufnahmen eines Weckers Slava 5671 und die Ergebnisse ihrer Prüfung mit `clock-rate`.

## Aufnahmen (`recordings/`)

| Datei | Länge | Situation |
|---|---|---|
| `탈진기.mp3` | 15 s | Rücker während der Aufnahme zweimal verschoben (Beispiel für automatische Aufteilung anhand der Rückergeräusche) |
| `시간조정.mp3` | 60 s | Nach einmaligem Verschieben des Rückers |
| `시간조정2.mp3` | 64 s | Nach weiterem Verschieben des Rückers |
| `시간조정3.mp3` | 121 s | Nach zu weitem Verschieben in Richtung Nachgehen (Aufnahme, in der die Ticklautstärke stark/schwach wechselt) |
| `시간조정4.mp3` | 26 s | Nach dem Zurückstellen (kurze Aufnahme mit vielen Störklicks) |
| `직접오버홀.mp3` | 121 s | Nach selbst durchgeführter Zerlegung, Reinigung und Ölung, mit voll aufgezogener Feder |

## Prüfergebnisse (`results/`)

Jedes Verzeichnis enthält `리포트.png`, `요약.txt` und `요약.json`; die Zusammenfassung enthält einen Vergleich mit den Spezifikationen aus `sheets/slava_5671.ini`.
`직접오버홀/진단.png` zeigt die Klangstruktur, die für Rauschentfernung, Tick-Erkennung und Amplitudenberechnung verwendet wurde.
`조정기록.png`/`조정기록.json` ist die Regulierhistorie in der Reihenfolge 시간조정 → 직접오버홀.

## Nachbauen

Aus dem Wurzelverzeichnis des Repositorys:

```bash
E=examples/results
clock-rate examples/recordings/시간조정.mp3 examples/recordings/시간조정2.mp3 \
           examples/recordings/시간조정3.mp3 examples/recordings/시간조정4.mp3 \
           --시트 sheets/slava_5671.ini --출력 $E
clock-rate examples/recordings/직접오버홀.mp3 --시트 sheets/slava_5671.ini --진단 --출력 $E
clock-rate examples/recordings/탈진기.mp3 --분할 자동 --기준 구간1 --이름 가운데,한쪽끝,반대쪽끝 \
           --시트 sheets/slava_5671.ini --기록끔 --출력 $E
```

Mit `--진단` wird zusätzlich `소음제거.wav` erzeugt, das wegen seiner Größe nicht in den Beispielen enthalten ist.

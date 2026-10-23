[한국어](slava_5671_regulation_notes.md) | [English](slava_5671_regulation_notes.en.md) | [Русский](slava_5671_regulation_notes.ru.md) | [Deutsch](slava_5671_regulation_notes.de.md) | [Français](slava_5671_regulation_notes.fr.md)

# Fallstudie zur Regulierung einer Slava 5671 (22.–23.10.2026)

Ein Protokoll der tatsächlichen Regulierung eines Slava-5671-Weckers mit `clock-rate`. Die Messwerte sind unverändert in `results/조정기록.json` hinterlegt.

## Symptome

- In aufrechter Lage (Gebrauchslage) ging die Uhr pro Tag **+883 s/Tag (14 min 43 s) vor**. In liegender Lage war sie mit -3 s/Tag normal.
- Der Wert lag außerhalb des Verstellbereichs des Rückers (Werksangabe ±3 min/Tag) und war mit dem Zeiger allein nicht lösbar.
- Die Aufnahmen in aufrechter Lage zeigten eine Amplitude von 205–262° (niedrig im Vergleich zur liegenden Lage) und einen großen Schlagfehler von 8–13 ms.

## Verlauf

1. Selbst mit dem Zeiger ganz auf - blieb die Uhr bei mehr als +9 min/Tag → Wechsel zur Verstellung der wirksamen Spiralfederlänge.
2. Die Spiralfeder wurde auf einmal zu stark verlängert, was zu einem Überschwingen bis zu 1 Stunde Nachgehen pro Tag (-3657 s/Tag) führte → dadurch wurde die Gangänderung pro Verstellweg (Empfindlichkeit) gemessen, und die proportionale Anleitung wurde danach wirksam.
3. Während der Neupositionierung der Spiralfeder erholte sich die Amplitude in aufrechter Lage von 240° auf 310°, und der Schlagfehler sank auf etwa 2 ms.

## Fazit: „Geht aufrecht vor" war kein inhärenter Lagenunterschied, sondern ein Defekt

Zunächst wurde ein Lagenunterschied durch Zapfenreibung und Amplitudenabfall in aufrechter Lage vermutet. Nach dem Wiedereinsetzen der Spiralfeder zeigte sich jedoch ein Lagenunterschied zwischen liegend und aufrecht von nur **etwa 5 s/Tag**. Die Ursache war also, dass die Spiralfeder in aufrechter Lage irgendwo anstieß — ein Problem, das durch die Arbeit an der Spiralfeder mit behoben wurde.

Lagenunterschiede (Positionsfehler) eng zu halten, ist eine Aufgabe für Uhren, deren Lage sich ändert, wie Armbanduhren oder Schiffschronometer; für Tischuhren, die in einer festen Lage verwendet werden, verlangt auch der Hersteller dies nicht (auch die Werktoleranz dieses Werks von ±60 s/Tag enthält keinen Lagen-Posten). Zertifizierungsstandards für Armbanduhren wie COSC gelten nicht für Tischuhren.

## Endzustand

- **+0,6 s/Tag** (gemessen 18000,1 bph, Sollwert 18000)
- Gegenprobe mit der Hintergrund-Quarzuhr: Hauptuhr − Quarzuhr = +3,4 ± 28,7 s/Tag (unabhängige Bestätigung, frei vom Uhrenfehler des Aufnahmegeräts)
- Lagenunterschied liegend–aufrecht etwa 5 s/Tag
- Amplitude etwa 248–301°, Schlagfehler 1–3 ms

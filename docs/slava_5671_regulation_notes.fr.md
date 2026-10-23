[한국어](slava_5671_regulation_notes.md) | [English](slava_5671_regulation_notes.en.md) | [Русский](slava_5671_regulation_notes.ru.md) | [Deutsch](slava_5671_regulation_notes.de.md) | [Français](slava_5671_regulation_notes.fr.md)

# Notes sur un cas de réglage d'une Slava 5671 (22–23 octobre 2026)

Compte rendu du réglage réel d'un réveil Slava 5671 avec `clock-rate`. Les mesures sont conservées telles quelles dans `results/조정기록.json`.

## Symptômes

- En position verticale (position d'usage réel), la montre **avançait de +883 s/jour (14 min 43 s)**. Couchée, elle était normale à −3 s/jour.
- Un écart au-delà de la plage de réglage de la raquette (±3 min/jour d'après l'usine), impossible à résoudre avec la seule raquette.
- Les enregistrements en position verticale montraient une amplitude de 205–262° (faible par rapport à la position couchée) et une erreur de battement importante de 8–13 ms.

## Déroulement

1. Même avec la raquette au maximum vers le −, l'avance restait supérieure à +9 min/jour → passage au réglage de la longueur active du spiral.
2. En allongeant le spiral trop d'un coup, dépassement jusqu'à 1 heure de retard par jour (−3657 s/jour) → la variation de marche par rapport à la correction (sensibilité) étant mesurée, l'aide proportionnelle est devenue exploitable par la suite.
3. Pendant la remise en place du spiral, l'amplitude en position verticale est remontée de 240° à 310° et l'erreur de battement est descendue autour de 2 ms.

## Conclusion : « avance quand elle est debout » n'était pas un défaut de positions intrinsèque mais un défaut de contact

On a d'abord supposé un écart de positions dû au frottement des pivots et à la baisse d'amplitude en position verticale, mais après la remise en place du spiral, l'écart couché-debout s'est avéré n'être que d'**environ 5 s/jour**. La cause était donc un contact du spiral quelque part en position verticale, et le travail sur le spiral l'a fait disparaître.

Resserrer à l'origine l'écart de positions (positional error) est un enjeu pour les montres dont la position change, comme les montres-bracelets ou les chronomètres de marine ; pour une pendulette utilisée dans une seule position, même le fabricant ne l'exige pas (la tolérance d'usine de ce mouvement, ±60 s/jour, ne comporte aucun critère de positions). Les certifications de montres-bracelets comme le COSC ne s'appliquent pas aux pendulettes.

## État final

- **+0,6 s/jour** (mesuré 18000,1 bph, nominal 18000)
- Validation croisée avec la montre à quartz d'arrière-plan : montre principale − quartz = +3,4 ± 28,7 s/jour (vérification indépendante de l'erreur d'horloge de l'appareil d'enregistrement)
- Écart de positions couché-debout d'environ 5 s/jour
- Amplitude environ 248–301°, erreur de battement 1–3 ms

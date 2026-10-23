[한국어](../README.md) | [English](README.en.md) | [Русский](README.ru.md) | [Deutsch](README.de.md) | [Français](README.fr.md)

Le README principal se trouve dans [../README.md](../README.md), avec les traductions dans [../docs/](../docs/).

# Exemples

Enregistrements réels d'un réveil Slava 5671 faits avec un téléphone, et résultats de leur vérification avec `clock-rate`.

## Enregistrements (`recordings/`)

| Fichier | Durée | Situation |
|---|---|---|
| `탈진기.mp3` | 15 s | Raquette déplacée deux fois pendant l'enregistrement (exemple de découpage automatique d'après les bruits de la raquette) |
| `시간조정.mp3` | 60 s | Après un premier déplacement de la raquette |
| `시간조정2.mp3` | 64 s | Après un déplacement supplémentaire de la raquette |
| `시간조정3.mp3` | 121 s | Après un déplacement trop important vers le retard (enregistrement où l'intensité des tics alterne fort/faible) |
| `시간조정4.mp3` | 26 s | Après retour en arrière (court enregistrement comportant de nombreux clics parasites) |
| `직접오버홀.mp3` | 121 s | Après démontage, nettoyage et huilage faits maison, ressort remonté à fond |

## Résultats de vérification (`results/`)

Chaque répertoire contient `리포트.png`, `요약.txt` et `요약.json`, et le résumé inclut une comparaison avec les spécifications de `sheets/slava_5671.ini`.
`직접오버홀/진단.png` montre la structure sonore utilisée pour la réduction du bruit, la détection des tics et le calcul de l'amplitude.
`조정기록.png`/`조정기록.json` est l'historique de réglage dans l'ordre 시간조정 → 직접오버홀.

## Reproduction

Depuis la racine du dépôt :

```bash
E=examples/results
clock-rate examples/recordings/시간조정.mp3 examples/recordings/시간조정2.mp3 \
           examples/recordings/시간조정3.mp3 examples/recordings/시간조정4.mp3 \
           --시트 sheets/slava_5671.ini --출력 $E
clock-rate examples/recordings/직접오버홀.mp3 --시트 sheets/slava_5671.ini --진단 --출력 $E
clock-rate examples/recordings/탈진기.mp3 --분할 자동 --기준 구간1 --이름 가운데,한쪽끝,반대쪽끝 \
           --시트 sheets/slava_5671.ini --기록끔 --출력 $E
```

Avec `--진단`, un fichier `소음제거.wav` est également généré ; il a été exclu des exemples en raison de sa taille.

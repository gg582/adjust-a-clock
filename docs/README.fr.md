[한국어](../README.md) | [English](README.en.md) | [Русский](README.ru.md) | [Deutsch](README.de.md) | [Français](README.fr.md)

# clockrate — régler une montre mécanique à partir d'un enregistrement

À partir du son d'une montre enregistré avec un téléphone, l'outil mesure **de combien de secondes par jour elle avance ou retarde** ainsi que son **amplitude**, et indique **dans quel sens et de combien déplacer la raquette** (levier de réglage).
À chaque enregistrement, le résultat s'ajoute à l'historique et, par comparaison avec l'enregistrement précédent, l'outil calcule « dans quel sens, et combien de fois la distance précédemment déplacée », il faut déplacer la raquette.

L'outil a été créé en réglant un réveil Slava 5671 (18000 bph), mais il fonctionne avec toute montre mécanique qui fait tic-tac (fréquence indiquée avec `--bph`).

Des exemples d'enregistrements réels et de résultats d'analyse se trouvent dans [`examples/`](../examples/README.md).

## Installation

[ffmpeg](https://ffmpeg.org/) est requis (`sudo apt install ffmpeg`, `brew install ffmpeg`, etc.).

```bash
pip install -e .            # clock-rate 명령 설치
pip install -e '.[test]'    # 테스트까지
```

On peut aussi l'exécuter sans installation avec `python3 -m clockrate ...`.

## Procédure de réglage

```bash
clock-rate 녹음1.m4a      # 1. 1분 이상 녹음해서 분석
                          # 2. 안내대로 조속 레버를 옮기고 다시 녹음
clock-rate 녹음2.m4a      # 3. 직전 녹음과 비교해 다음 이동량 안내
...                       # 4. '◎ 조정 완료'가 나올 때까지 반복
```

Le terminal ainsi que `results/<파일명>/요약.txt` affichent un résumé de ce type.

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

### Critères d'évaluation

| Indication | Écart journalier | Signification |
|---|---|---|
| ◎ 조정 완료 | ±10 s ou moins (modifiable avec `--tolerance`) | N'y touchez plus |
| △ 미세 조정 권장 | ±30 s ou moins | Ne déplacez que très légèrement |
| ▲ 조정 필요 | ±60 s ou moins | |
| ✖ 크게 어긋남 | au-delà | |

- **L'erreur de battement** est l'asymétrie entre les intervalles tic et tac. En dessous de 3 ms elle est bonne ; au-delà de 5 ms, il vaut mieux régler la position d'arrêt du balancier (le battement).
- **L'amplitude** est l'angle parcouru par le balancier en une oscillation. Au-dessus de 330° elle est trop grande (attention au rebond sur la butée), 250–330° bonne, 200–250° moyenne, et en dessous de 200° faible (vérifier le remontage, le graissage, l'encrassement) — critères couramment utilisés pour les montres-bracelets. Voir [Amplitude](#amplitude) ci-dessous.
- **La stabilité de marche** est l'étendue des valeurs calculées séparément sur des tranches de 10–20 s de l'enregistrement. Une grande étendue indique un ressort qui se détend, une montre qui a bougé ou un enregistrement de mauvaise qualité.
- **La fiabilité de la mesure** est jugée uniquement sur la qualité de l'enregistrement (durée, taux de détection des tics, clics parasites). Si elle est « faible », l'outil explique pourquoi et donne des conseils d'enregistrement.
- **Le prochain déplacement** est une estimation fondée sur l'hypothèse que la marche varie proportionnellement à la distance de déplacement de la raquette. Si l'écart avec l'enregistrement précédent est quasi nul, l'outil signale que la raquette a peut-être tourné à vide ou que le spiral est sorti des goupilles de la raquette.

## Fichiers produits

| Fichier | Contenu |
|---|---|
| `results/<파일명>/리포트.png` | Évaluation et action à effectuer, jauge de la plage cible, timegrapher et erreur par plage horaire sur une seule image |
| `results/<파일명>/요약.txt` | le résumé ci-dessus |
| `results/<파일명>/요약.json` | les mêmes données au format machine |
| `results/조정기록.png` | l'évolution de l'écart journalier et de l'amplitude dans l'ordre des enregistrements, et la prochaine action |
| `results/조정기록.json` | l'historique de réglage (réanalyser le même fichier le met à jour en place) |
| `results/<파일명>/다른시계.png` | seulement si `--multi-clock` a trouvé une autre montre : forme du tic et timegrapher de cette montre |
| `results/<파일명>/진단.png`, `소음제거.wav` | seulement avec `--diagnostics` : réduction du bruit, état de la détection des tics, positions unlock/drop utilisées pour le calcul d'amplitude |

**Comment lire le timegrapher :** chaque point indique de combien (ms) un tic est en avance sur la valeur nominale.
- **Pente de la ligne :** des points qui montent = la montre avance ; qui descendent = elle retarde.
- **Secteur gris :** la plage cible (±10 s/jour). Une ligne couchée à l'intérieur est dans la cible.
- **Écart entre les deux lignes :** l'écart entre la ligne des tics (bleu) et celle des tacs (orange) est l'erreur de battement.

## Options

| Option | Valeur | Description |
|---|---|---|
| `--bph` / `--vph` | `18000` (défaut) | fréquence nominale. Indiquer `28800` etc. pour d'autres montres |
| | `자동` | choisit automatiquement une valeur standard (3600–36000) à ±1 % de la valeur mesurée |
| `--lift-angle` | `52` (défaut) | angle de levée (degrés) pour le calcul d'amplitude. `0` désactive le calcul |
| `--sheet` | chemin INI | compare les mesures à une fiche de spécifications du mouvement (voir [Fiche de spécifications](#fiche-de-spécifications)). Si bph et angle de levée ne sont pas indiqués, les valeurs de la fiche sont utilisées |
| `--tolerance` | `10` (défaut) | en dessous de cette valeur (s/jour), le réglage est terminé |
| `--split` | `없음` (défaut) | tout l'enregistrement en un seul segment |
| | `자동` | si la raquette a été déplacée **pendant** l'enregistrement, repère le bruit de glissement et compare l'avant/après |
| | `3.5,9.2` | découpe aux instants indiqués (secondes) |
| `--reference` | `자동` (défaut) | écart absolu par rapport à la valeur nominale (si `--bph 자동` ne trouve pas de valeur nominale, le segment 1 sert de référence) |
| | `규격` | écart absolu par rapport à la valeur nominale |
| | `구간1` | compare seulement les variations par rapport au premier segment (pour mesurer l'effet de la position de la raquette) |
| `--names` | `가운데,빠르게,...` | noms des segments |
| `--window` | secondes | longueur de la fenêtre d'erreur par plage horaire. Par défaut 10 s (segments de moins de 90 s) ou 20 s ; `0` désactive |
| `--out` | dossier | dossier des résultats (défaut `./results`). L'historique de réglage s'y accumule aussi |
| `--no-history` | | ne pas inscrire dans l'historique de réglage ni comparer à l'enregistrement précédent |
| `--multi-clock` | | en soustrayant le son de la montre principale, cherche et mesure aussi d'autres montres dans le son restant (montre à quartz en arrière-plan, etc.) — voir [Plusieurs montres](#plusieurs-montres) |
| `--diagnostics` | | enregistre aussi les graphiques de diagnostic et le wav débruité |
| `--no-plots` | | ne produit que le résumé |
| `--lang` | `ko` (défaut), `en`, `ru`, `de`, `fr` | langue du résumé et du rapport |

Plusieurs fichiers passés en une fois sont analysés dans l'ordre et ajoutés à l'historique : `clock-rate recordings/시간조정*.mp3`

Pour comparer l'effet de chaque position de la raquette en un seul enregistrement : `clock-rate 탈진기.mp3 --split 자동 --reference 구간1 --names 가운데,한쪽끝,반대쪽끝`

## Amplitude

Le son d'un seul tic est une superposition de plusieurs petits bruits. Dans un échappement à ancre suisse (y compris le Slava 5671), le **déverrouillage** (unlock, petit bruit du dégagement de l'échappement) est suivi de la **chute** (drop, bruit plus fort de la dent qui tombe).
Comme le temps entre ces deux bruits correspond à la rotation du balancier sur l'angle de levée, on peut calculer l'amplitude.

```
진폭 = 리프트각 / (2·sin(π · 언락→드롭 시간 / 한 주기))
```

- **Courbe moyenne :** pour chaque tic et tac, on superpose les courbes d'amplitude sonore de tout l'enregistrement et l'on en prend la médiane ; le pic le plus net avant la chute, dans la plage physiquement possible (durée correspondant à une amplitude de 140–380°), est retenu comme unlock.
- **Fiabilité :** une plage à 95 % est obtenue par bootstrap (rééchantillonnage aléatoire des tics). Si les valeurs tic/tac diffèrent de plus de 30° ou si la plage dépasse 40°, le résultat est marqué « à titre indicatif ».
- **Angle de levée :** valeur propre à chaque mouvement. La valeur officielle du Slava 5671 n'ayant pas été trouvée, la valeur par défaut est 52°, courante pour les ancres suisses. La valeur absolue est incertaine à hauteur de cette hypothèse.
- **Comparaison d'une même montre :** l'amplitude étant quasi proportionnelle à l'angle de levée, comparer des enregistrements d'une même montre (l'amplitude a-t-elle diminué ?) est exact indépendamment de l'angle de levée. Cette tendance est visible dans le graphique d'historique de réglage.
- **Graphique de diagnostic :** avec `--diagnostics`, on voit quels bruits ont été retenus comme unlock et drop.

## Plusieurs montres

Avec `--multi-clock`, l'outil repère aussi d'autres montres présentes dans l'enregistrement (par ex. une horloge murale à quartz dans la pièce) et mesure leur écart journalier. Sans cette option, le résultat est identique à celui obtenu avant son introduction.

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

- **Méthode de recherche :** la bande 200 Hz–12 kHz est divisée en cinq bandes ; pour chacune, on construit la courbe d'amplitude sonore et l'on soustrait les tics de la montre principale (forme médiane sur deux temps) aux positions prédites par le modèle de battement. On cherche dans l'autocorrélation du résidu une périodicité comprise entre 0,1 et 2,5 s, on détecte les tics dans la bande la plus nette et l'on calcule l'écart journalier avec le même modèle de battement que pour la montre principale. Une fois une montre trouvée, on la soustrait aussi et l'on recommence (3 au maximum).
- **Rejet des fausses montres :** pour être reconnue, une périodicité doit être plus nette que celle laissée par une soustraction incomplète de la montre principale (multiples de son intervalle de battement), au moins 70 % des tics attendus doivent être trouvés, et la gigue des instants de tic doit être inférieure ou égale à 5 % de l'intervalle.
- **Détection du quartz :** un intervalle de 1 s (3600 bph) est interprété comme une montre à quartz à seconde sautante.
- **Montre principale − autre montre :** les deux montres étant mesurées avec l'horloge du même appareil d'enregistrement, cette différence ne contient pas l'erreur d'horloge du téléphone. En prenant le quartz (généralement ±0,5 s/jour) comme référence, on obtient l'écart de la montre principale sans passer par le téléphone.
- **Précision :** le son d'une montre d'arrière-plan étant faible, la gigue des instants de tic atteint plusieurs ms à quelques dizaines de ms ; à durée d'enregistrement égale, l'intervalle de confiance est donc plus large que pour la montre principale. L'intervalle de confiance est élargi en multipliant l'erreur de régression par la corrélation des résidus voisins (utiliser la dispersion par fenêtre comme pour la montre principale gonflerait excessivement l'erreur, la pente de chaque fenêtre étant imprécise).
- Les autres montres ne sont incluses ni dans l'historique de réglage ni dans la comparaison aux spécifications.

## Fiche de spécifications

En écrivant les spécifications du mouvement en INI dans `sheets/` et en les passant avec `--sheet`, l'outil juge pour chaque poste si la mesure est dans les tolérances d'usine.

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

- **Critères de jugement :** si la mesure et sa plage à 95 % sont toutes deux dans la tolérance → **réussi** ; si la mesure est dedans mais que la plage à 95 % chevauche la tolérance → **limite** ; si la mesure est dehors → **échec**. Une amplitude « à titre indicatif » (valeurs tic/tac différentes) est classée limite sans trancher entre réussi et échec.
- **Postes non mesurables :** réserve de marche, écart selon l'état de remontage, variation d'amplitude, départ automatique — non mesurables sur un seul enregistrement ; l'outil les marque « non mesurable » et indique comment les mesurer.
- **Affichage de la source :** le commentaire placé après `;` derrière une valeur de la fiche apparaît comme « référence » dans le verdict. Conservez l'origine des spécifications.
- **`sheets/slava_5671.ini` :** reprend, avec citations du texte original, les spécifications du Slava 5671 et les critères de réglage de Л. В. Шамонова, «Ремонт механических будильников» (1987) : écart journalier ±1 min, plage de réglage ±3 min, amplitude 180–310°, réserve de marche ≥ 36 h, etc. L'angle de levée et la tolérance d'erreur de battement, dont le texte ne donne pas de valeur, sont laissés vides.
- **`sheets/_template.ini` :** modèle vierge pour d'autres mouvements.

## Conseils d'enregistrement

- Dans une pièce silencieuse, collez le micro du téléphone contre le fond de la montre.
- Enregistrez **au moins 1 minute**. En dessous de 20 s, la précision chute fortement et la stabilité de marche n'est pas visible.
- Selon le degré de remontage, l'écart peut varier de plusieurs dizaines de secondes par jour. Gardez des conditions identiques entre les enregistrements que vous comparez.

## Principe de fonctionnement

1. **Réduction du bruit :** filtre passe-bande 3,5–16 kHz puis spectral gating. La référence de bruit est prise dans les zones silencieuses entre les tics, et la médiane temporelle sur des fenêtres de 1 s permet de suivre l'évolution du plancher de bruit (conversation, télévision, bruits de gestes).
2. **Estimation de l'intervalle de battement :** on retient l'intervalle entre pics le plus fréquent de la courbe d'amplitude sonore (l'« enveloppe » en traitement du signal). Même si les tics alternent fort/faible, plusieurs temps ne sont pas pris pour un seul.
3. **Détection initiale des tics :** instant où la courbe d'amplitude dépasse pour la première fois 30 % de la hauteur du pic.
4. **Numérotation des temps et suppression du bruit :** on suit les tics un par un en leur attribuant un numéro de temps, et l'on retire les clics parasites qui sortent du rythme.
5. **Recalage de précision :** on construit la forme moyenne (modèle) des tics et des tacs et l'on recale chaque tic par corrélation croisée avec une précision infra-échantillon. Les tics manqués sont comblés lorsqu'un son suffisamment proche du modèle (corrélation ≥ 0,6) est trouvé à la position prédite. Sur les enregistrements bruyants, la gigue des instants de tic diminue d'environ 60 %.
6. **Modèle de battement :** `t = a + n·intervalle + c·(parité)` résolu par moindres carrés. Le terme de parité est l'erreur de battement.
7. **Amplitude :** calculée en mesurant le temps unlock→drop sur le son original (avant gating) (voir [Amplitude](#amplitude) ci-dessus).
8. **Écart journalier :** `(intervalle nominal / intervalle mesuré − 1) × 86400`. L'intervalle de confiance retient le plus grand de l'erreur de régression et de la dispersion des valeurs par plage horaire — l'erreur de régression seule donnerait un intervalle trop étroit à cause des lentes dérives propres à la montre.

## Validation

Sur les enregistrements synthétiques de `tests/` (bruit urbain, bruit de raquette, erreur de battement, tics fort/faible et bruit d'unlock inclus), l'écart journalier est exact à 0,5 s/jour près et l'amplitude à 8° près.
Sur un enregistrement synthétique mêlé d'un petit tic de quartz (1 kHz) en arrière-plan, `--multi-clock` retrouve l'écart journalier du quartz à 1 s/jour près, et ne trouve rien sur les enregistrements sans autre montre (tics fort/faible inclus).
Sur un enregistrement réel (Slava 5671), la valeur de l'outil (+8,4 ± 0,6 s/jour) a concordé avec celle d'une application timegrapher Android (+7 s/jour).
Cas de réglage réel (22–23 octobre 2026) : une Slava 5671 qui avançait de 14 min 43 s par jour a été réglée, en suivant les indications de l'outil (longueur active du spiral et raquette), jusqu'à **+0,6 s/jour** (mesure 18000,1 bph, validation croisée avec la montre à quartz d'arrière-plan : +3,4 ± 28,7 s/jour). Le déroulement se trouve dans [`docs/slava_5671_regulation_notes.fr.md`](slava_5671_regulation_notes.fr.md).

```bash
python3 -m pytest
```

## Structure

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

Pour les graphiques en coréen, l'outil utilise la première police installée parmi NanumBarunGothic, NanumGothic, Noto Sans CJK KR, Malgun Gothic et AppleGothic.

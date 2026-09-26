# 예제

Slava 5671 자명종을 휴대폰으로 녹음한 실제 파일과, 그 녹음을 `clock-rate`로 점검한 결과입니다.

## 녹음 (`recordings/`)

| 파일 | 길이 | 상황 |
|---|---|---|
| `탈진기.mp3` | 15초 | 녹음 도중 조속 레버를 두 번 밀었음 (레버 소리 자동 분할 예제) |
| `시간조정.mp3` | 60초 | 레버를 한 번 옮긴 뒤 |
| `시간조정2.mp3` | 64초 | 레버를 더 옮긴 뒤 |
| `시간조정3.mp3` | 121초 | 느림 쪽으로 너무 많이 옮긴 뒤 (틱 크기가 강·약으로 반복되는 녹음) |
| `시간조정4.mp3` | 26초 | 되돌린 뒤 (잡음 클릭이 많은 짧은 녹음) |
| `직접오버홀.mp3` | 121초 | 분해 세척·주유 후, 태엽을 끝까지 감은 상태 |

## 점검 결과 (`results/`)

파일마다 `리포트.png`, `요약.txt`, `요약.json`이 있고, 요약에는 `sheets/slava_5671.ini` 사양 비교가 들어 있습니다.
`직접오버홀/진단.png`는 소음 제거·틱 검출·진폭 계산에 쓴 소리 구조를 보여 줍니다.
`조정기록.png`/`조정기록.json`은 시간조정 → 직접오버홀 순서의 조정 기록입니다.

## 다시 만들기

저장소 최상위에서:

```bash
E=examples/results
clock-rate examples/recordings/시간조정.mp3 examples/recordings/시간조정2.mp3 \
           examples/recordings/시간조정3.mp3 examples/recordings/시간조정4.mp3 \
           --시트 sheets/slava_5671.ini --출력 $E
clock-rate examples/recordings/직접오버홀.mp3 --시트 sheets/slava_5671.ini --진단 --출력 $E
clock-rate examples/recordings/탈진기.mp3 --분할 자동 --기준 구간1 --이름 가운데,한쪽끝,반대쪽끝 \
           --시트 sheets/slava_5671.ini --기록끔 --출력 $E
```

`--진단`을 주면 `소음제거.wav`도 만들어지는데, 용량 때문에 예제에서는 뺐습니다.

---
name: midas-mct-syntax
description: MIDAS CIVIL MCT 파일은 기억으로 쓰지 말고 D드라이브 기존 실물 파일과 대조할 것 — LOADCOMB·단면 치수 순서에서 실제로 틀렸음
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 3608cdcc-51f8-4f29-b15e-59d912b4a76c
  modified: 2026-09-09T06:05:33.662Z
---

MIDAS CIVIL 해석 모델을 만들 때는 화면 클릭 대신 **MCT(Model Command Text) 파일**을 직접 작성해 불러오는 방식을 쓴다. 클릭 방식은 스크린샷 토큰이 절점 수에 비례해 폭증하고 좌표 오류가 조용히 섞인다.

**MCT 문법은 기억으로 쓰면 틀린다. 반드시 기존 실물 파일과 대조할 것.**

검증용 실물 파일 위치:
- `D:\01_과업\2025년 과업\내진성능평가 보고서_용문교 등 4개소\02. 부록\3. 내진성능평가 결과자료\전산DATA\mct파일\` (4개 교량)
- `D:\09_보관\홍형규(출장정산 양식)\2022\...\신형산교.mct`

CP949 인코딩이므로 읽을 때 `iconv -f CP949 -t UTF-8` 필요.

## 2026-09-09 실제로 틀렸던 것

**LOADCOMB** — 파싱 에러로 임포트 전체 실패(N:0, E:0)
```
틀림:  NAME=ALL , GEN , ACTIVE, 0, 0,  , 0, 0          (파라미터 8개)
           LCNAME=SELFWEIGHT, 1.0, LCNAME=POINT, 1.0   (해석타입 없음)
맞음:  NAME=ALL, GEN, ACTIVE, 0, 0, , 0, 0, 0, 1        (10개)
           ST, SELFWEIGHT, 1, ST, POINT, 1             (ST = Static)
```

**DBUSER SB(사각) 단면 치수 순서** — 파싱은 통과하되 결과가 통째로 틀림
```
틀림:  SB , 2, 1, 0.6     → H=1.0, B=0.6 (단면이 누움, Iy 오류)
맞음:  SB , 2, 0.6, 1     → H=0.6, B=1.0
```
`SB` 뒤 공백도 실제 파일 그대로 맞출 것. 임포트 후 A·Iyy를 반드시 눈으로 확인한다.

## 재료

콘크리트 탄성계수는 KDS 기준 `Ec = 8500 × ∛(fck + 4)` [MPa].
fck=24 → Ec = 25,811 MPa. (태봉2교 실물 파일의 C24가 25,791 MPa로 교차검증됨)

기본 단위계는 `KN, M, KCAL, C`. CIVIL NX 화면 단위가 tonf로 되어 있을 수 있으니 값 비교 시 주의(1 tonf ≈ 9.807 kN).

## 절차

해석 결과는 항상 손계산 이론값을 미리 내서 대조한다. 양단고정 기준 집중하중 중앙모멘트 PL/8, 등분포 중앙 wL²/24 · 단부 wL²/12. 값이 크게 벗어나면 모델이 틀린 것.

도면에서 읽은 치수·조건은 확정 전 반드시 대표님께 확인받는다 — 치수 하나 틀리면 해석 결과 전체가 무의미해진다. 관련: [[midas-license-mdesk]]

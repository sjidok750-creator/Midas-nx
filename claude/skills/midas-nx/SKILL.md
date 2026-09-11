---
name: midas-nx
description: 준공도면(DWG)에서 MIDAS CIVIL NX 격자모델·구조해석·허용응력/강도 검토·정밀안전진단 보고서 5장(hwpx)까지 자동으로 만드는 절차. "도면 주고 해석해줘", "안전성 평가 5장 만들어줘", "강박스 격자모델 만들어", "MIDAS로 해석" 요청에 이 스킬을 쓰세요. 순천만IC2교(강박스 5경간)에서 실증한 스크립트를 재사용합니다.
---

# MIDAS CIVIL NX 자동 구조해석 절차

계획서 `D:\Midas\MIDAS_자동화_계획_2026-09-10.md`(「진행 상황」에 실증 기록), 도구 `D:\Midas\tools\`, 실증 프로젝트 `D:\Midas\projects\순천만IC2교\`. 새 교량은 `D:\Midas\projects\<교량명>\`을 만들고 아래 스크립트를 복사해 상수만 바꿉니다.

## 0. 연결 확인 (매 세션)
1. CIVIL NX 실행 후 대표님이 **Apps > API Settings > Connect**를 눌러야 API가 열립니다(관리자 창은 자동 클릭 불가). 안 열려 있으면 "켜 주세요"라고만 요청.
2. `PYTHONUTF8=1 python -c "import sys; sys.path.insert(0, r'D:\Midas\tools'); from midas_api import Civil; print(Civil().version())"` — 키는 레지스트리에서 읽고 **값을 출력하지 않습니다**(채팅에 키를 붙이지 않게 함).
3. 함정: 제목 없는 문서에 `/doc/ANAL`·`/doc/SAVE`를 보내면 "다른 이름으로 저장" 모달로 API가 멈춥니다. 항상 `/doc/SAVEAS` 먼저. 모달 탐지는 `tools\win_probe.ps1`.

## 1. 도면 판독 → 제원서
| 단계 | 스크립트 | 산출 |
|---|---|---|
| DWG→DXF | `tools\dwg2dxf.py --glob` (ODA File Converter) | `dxf\` |
| 문자·좌표 추출 | `tools\dxf_extract.py` | `extract\*.json`, `index.json` |
| 부분 확대 확인 | `tools\dxf_crop.py --find 정규식 --pick N` / `dxf_render.py` | `png\` |
| 제원서 | `tools\spec_build.py` | `제원서.json`, `제원_확인표.md` |

- 치수는 폭발되어 있으므로 문자로 읽습니다. 판두께 행은 길이 행과 y가 다릅니다(x·y 거리 매칭). 받침 좌표표는 2개일 수 있고 A1/P5가 뒤집힐 수 있으니 **종평면도 경간과 교차검증**, 구간 길이 합 = 거더 길이 검산.
- 확인표의 `확인 필요` 항목은 대표님께 한 번에 묻습니다. 현장자료가 없으면 도면값을 씁니다(대표님 규칙).

## 2. 격자모델 → 해석 (`gen_model.py`, `run3.py`)
- 좌표: 한국 평면직각좌표 X=북, Y=동 → 그림은 (E,N). **A1 좌측, P5 우측**(시점 좌측 관례).
- 모델 2개만: 합성전 `A_steel`(강재 자중×할증 + 슬래브), 합성후 `C_comp`(n=8, 2차 고정하중·풍·원심·제동·온도·지점침하·단위단부모멘트·이동하중 DB/DL-24). 기존 구조물 해석이므로 합성후에 이동하중이 들어간 모델만 남깁니다.
- 강재 할증 = 강재재료표 총량 ÷ 모델 강재중량(계산값). 종리브는 단면에 포함, 수평보강재 등은 할증으로.
- 받침: 배치도 SHOE 좌표로 주형별 종류(고정/일방향/양방향) + 절점 국부축 접선(`/db/skew`). 지점 가로보 누락 주의(허용오차 1e-3).
- 재료 USER 강재는 단위중량·질량밀도(78.5, 8.0048)를 명시해야 자중이 생깁니다. 2017년식 `*LINELANE`은 NX 2026에서 조용히 실패 → 이동하중은 JSON(`/db/mvcd`,`llan`,`mvhl`,`mvld`). 이동하중 표 이름은 `DB-24(MV:max)`.
- 5 m 보 손계산 검증(`tools\step1_*.py`)이 통과된 절차입니다. 새 형식이면 먼저 작은 검증 모델로 확인.

## 3. 검토 계산기
- `tables.py` → 부재력 집계(`forces_summary.json`, 키 `"My|S1|G1"`).
- `stress3.py` → 허용응력 case 1~9(2024 양식: 합성전/합성후+활+침하+원심/크리프/건조수축/±온도차/풍), 부모멘트부 철근단면, 압축플랜지 국부좌굴 fca, 전단·비틀림 τ, 내하율 RF, 처짐 L/500, 받침 용량·부반력, 등급(세부지침 표 1.34). 산출 `stress3_gov.json`, `결과_안전성검토_v3.md`.
- `slab.py` → 바닥판 강도설계(캔틸레버 좌·우, 내측 하면·상면), 충돌·풍·원심 포함 조합 ①~④. 충돌 팔길이 등 불확실 값은 상수에 `확인 필요`로 표시.
- `figures.py` → 검토단면·거더 일반도·모델 평면·부재력도 PNG.

## 4. 보고서 5장 조립 (`build_ch5.py`)
- 초안 hwpx(전회 보고서 양식)를 **원본 XML 복제·값 교체**로 채웁니다. 구글드라이브 「한글문서(HWPX) 편집 작업지침」 v2~v3.3을 따르고 `tools\hwpx_edit.py`(set_cell_text·set_cell_lines·set_para_runs·clone_row·add_image·swap_pic·prune_images·verify)를 씁니다. 자세한 함정은 메모리 `hwpx-guideline-pointer`.
- 순서: 기준선(무변경 재저장 동일) → 표 채우기 → 공식 문단 교체(MPa) → 그림 교체(§17) → 미참조 이미지 제거 → `verify()` → `hwp.sh read`로 되읽어 `tonf`·`kgf/㎠`·"case 1 1" 같은 잔존 0 확인 → 전달.
- 단위는 kN·kN·m·MPa, "마모층"은 "포장층".


## 5. 하부구조 (교대·교각)
- `reactions.py` → 받침 절점 반력을 국부축(교축 x·교축직각 y)으로 회전해 지점별 D·L(max/min, 주형별)·W·WL·LF·CF·TP 집계 (`runs
eactions_summary.json`).
- `하부_제원서.json` : 일반도(DXF)에서 EL·기둥높이·기초·말뚝(본수·길이) 추출값. 배근도가 세트에 없으면 "확인 필요"로 두고 소요 철근량만 산정.
- `combos_2010.json` : 도로교설계기준(2010) 강도 I~VII·사용 I~VII 계수표(편집 가능), 지진 A·S·R, 받침마찰 0.05.
- `pier_model.py [P1..]` : 교각별 NX 프레임(기둥 2 + 코핑 3 + 팔 2 요소) MCT 생성 → 임포트·해석 → 13 케이스(RD·RL 4종·W·WL·CF·LF·TP·FR·EQX·EQY) → 파이썬 조합 → 기둥 P–M 소요 As, 말뚝 강체캡 반력, 코핑 기둥면 단면력, `/view/CAPTURE`로 모델·모멘트도 JPG. 정정 구조라 단면력은 강성과 무관.
- `abutment.py` : 교대 단위폭 계산(자중 블록 GEOM, Rankine/Coulomb/M–O 토압, CASE 1~4, 말뚝 2열, 벽체·흉벽 소요 As, 개략도 PNG).
- `build_ch5_v2.py` : v1 hwpx에서 PSC 절 삭제 + 하부구조 절 교체 → `5장_v2.hwpx`.
- 함정: CONLOAD 전부 0인 행 → 임포트 실패(`mct_syntax.conload`가 걸러냄). 캡처는 WIDTH/HEIGHT를 크게(2400×3000) 잡고 `autocrop`으로 잘라야 해상도가 나온다.

### 5-1. 교대 (2026-09-10 개정: 요령 절차 + 한계상태 계수)
- 형상은 **반드시** `tools\abut_geom.py <extract json> <dxf> <out json>`로 좌표 판독(앞굽·벽체·뒷굽·헌치면·받침 x·말뚝 본수). ★플래그가 있으면 사람 확인. 눈으로 짐작해 앞굽/뒷굽을 정하면 2026-09-10처럼 뒤집힌다.
- `abutment2.py`: 절차 = 도로설계요령(1992 2.5.6·3.x / 2020 8-3편 4.): 가상배면 Coulomb δ=φ(지진 ½φ), 앞벽 δ=⅓φ, 재하하중 1 t/㎡, 뒷채움 표준정수 표 2.7(사질토 γ 19, φ 30). 계수·판정 = `combos_kds.json`(도로교설계기준 2016 표 3.4.1/3.4.2, 편심 B/4·0.4B, 저항계수 표 7.5.x, KDS 24 17 11 M–O·R, KDS 24 14 21 재료계수).
- 교각은 `pier_model.py --code kds`(결과 runs\pier_kds), 편재 활하중은 run3의 1차선 케이스(DB/DL-24_L1·L2) 동시 반력.
- 보고서: `build_ch5_v3.py`(v2 → v3): 요령 그림(D:\Midas\references\요령1992_fig\crop) 이식, 참고문헌 KDS. 기준 원문 색인은 `D:\Midas\references\README.md`.

## 대표님 결정(바꾸지 말 것)
A1 좌측·P5 우측 / P3만 고정단 / 받침은 도면 위치(오차 크면 질문) / 2차 고정하중은 계산서 / 유효폭은 도로교 강교편 λ식(근거만 남김) / 조합은 최신 기준, 하중은 가능한 한 모델에 / 현장자료 없으면 도면값.

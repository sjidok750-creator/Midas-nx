---
name: midas-open-api
description: "CIVIL NX 자동화 1순위는 공식 Open API(MIDAS 중계서버 REST + MAPI-Key, 래퍼 D:\\Midas\\tools\\midas_api.py). 2026-09-10 불러오기→해석→결과표까지 실측 통과. 저장 안 하고 ANAL 보내면 모달에 막힘"
metadata: 
  node_type: memory
  type: project
  originSessionId: ac048fbe-9263-4808-af0f-0d086cbaf089
  modified: 2026-09-10T07:09:02.723Z
---

MIDAS CIVIL NX 자동화의 1순위 통로는 화면 클릭이 아니라 **Open API**다. 2026-09-10 이 PC에서 MCT 불러오기 → 저장 → 해석 → 반력·부재력·변위 표 추출까지 **API만으로 완주**했고 손계산과 일치했다.

## 연결 구조 (실측)

- CIVIL NX가 MIDAS 중계 서버 `https://moa-engineers.midasit.com:443/civil`에 붙고, 파이썬은 그 서버에 `MAPI-Key` 헤더로 요청한다. 로컬 포트 10024는 이 PC에서 열리지 않는다(검색 결과의 localhost 예시는 다른 모드).
- CIVIL NX에서 **Apps > API Settings > Connect**를 켜면 키·URI·PORT가 `HKCU\Software\MIDAS\CVLwNX_KR_HYPER_S\CONNECTION`에 기록된다. 공식 라이브러리 `midas-civil`의 기본 경로는 `CVLwNX_KR`이라 이 PC와 다르다. "Connect API on Startup" 체크해 두면 자동 연결.
- 래퍼 `D:\Midas\tools\midas_api.py`(`Civil` 클래스)가 레지스트리에서 키를 읽고 **값은 출력하지 않는다**. 공식 라이브러리는 키 앞 35자를 콘솔에 찍으므로 직접 쓰지 말고 래퍼를 쓴다. 실행 시 `PYTHONUTF8=1` 필요(cp949 콘솔에서 배너 깨짐).
- 파이썬 3.14.3에 `midas-civil 1.7.1`, `requests`, `polars` 설치됨.

## 확인된 엔드포인트

- `POST /doc/IMPORTMXT {"Argument": "D:\\...\\x.mct"}` MCT 불러오기 (경로는 CIVIL NX가 있는 PC 기준)
- `POST /doc/SAVEAS {"Argument": 경로}`, `POST /doc/ANAL {"Assign": {}}` (5m 보 4초)
- `POST /post/table {"Argument": {"TABLE_NAME":"SS_Table","TABLE_TYPE":"REACTIONG|BEAMFORCE|DISPLACEMENTG","UNIT":{"FORCE":"KN","DIST":"M"},"STYLES":{"FORMAT":"Fixed|Scientific","PLACE":n},"NODE_ELEMS":{"KEYS":[...]},"LOAD_CASE_NAMES":["이름(ST)","조합(CB)"],"PARTS":["PartI","PartJ"]}}` → `SS_Table.HEAD/DATA`
- `GET /db/NODE|ELEM|MATL|SECT|CONS|CNLD|STLD` 되읽기 가능. `/db/LCOM`은 404.
- 표 열 순서: REACTIONG [Index,Node,Load,FX,FY,FZ,MX,MY,MZ], BEAMFORCE [Index,Elem,Load,Part,Axial,Shear-y,Shear-z,Torsion,Moment-y,Moment-z], DISPLACEMENTG [Index,Node,Load,DX,DY,DZ,RX,RY,RZ]

## 이동하중(활하중)은 MCT가 아니라 JSON으로 (2026-09-10 실측)

- 2017년식 `*LINELANE` MCT 문법(신형산교 파일)은 NX 2026에서 **조용히 파싱 실패**(절점 0). NX가 내보낸 현재 문법: `NAME=L1, LANE, , 0, 0, BOTH, 0, 3, 1.8, NO, 0` / 요소행 `iELEM, ECC, FACT, bSPAN, ECCVL, CENTF`.
- 확실한 길: MCT는 이동하중 블록 없이 불러온 뒤 `PUT /db/mvcd {"Assign":{"1":{"CODE":"KOREA"}}}` → `PUT /db/llan` (COMMON{LL_NAME, LOAD_DIST:"LANE", MOVING:"BOTH", WHEEL_SPACE, WIDTH…}, LANE_ITEMS[{ELEM, ECC, FACT:0, SPAN_START}]) → `PUT /db/mvhl` ({MVLD_CODE:6, VEHICLE_LOAD_NAME:"DB-24", VEHICLE_LOAD_NUM:1, VEHICLE_TYPE_NAME:"DB-24", STANDARD_CODE:"KS-RB", VEH_DEFAULT:{DYN_LOAD_ALLOWANCE:0, CENT_F:false}}) → `PUT /db/mvld` ({LCNAME, TYPE:0, DEFAULT:{SCALE_FACTORS, COMB_OPTION:"INDEPENDENT", LANE_FACTOR_TYPE:1, _2_LANE_FACTOR_1…, SUB_LOAD_DATAS:[{VEHICLE_TYPE:"VL", VEHICLE_NAME, SCALE_FACTOR, MIN_LOADED_LANE, MAX_LOADED_LANE, LANE_NAMES}]}}). 구현: `D:\Midas\projects\순천만IC2교\build_C.py`.
- 결과 하중명은 `DB-24(max)/(min)/(all)`; 표 요청 시 이름은 `DB-24(MV:max)`. 충격계수·2차선은 자동 포함됨(정적 1차선 재하와 대조해 확인: 이동 max ≈ 정적 × (1+타주형 분담) × 1.136).
- JSON 키는 MIDAS 도움말의 Zendesk API(`support.midasuser.com/api/v2/help_center/articles/search.json?query=…`)로 읽을 수 있다. WebFetch는 403이지만 이 경로는 열린다.

- 절점 국부축(받침 접선방향): `PUT /db/skew {"Assign":{"<node>":{"iMETHOD":1,"ANGLE_X":0,"ANGLE_Y":0,"ANGLE_Z":각도}}}`. MCT `*CONSTRAINT` 코드는 국부축 기준으로 해석됨(일방향 011000, 양방향 001000, 고정 111000). 온도하중 반력 ≈0으로 검증.
- 한국 평면직각좌표는 **X=북, Y=동**. 도면 좌표를 (X,Y)로 그대로 그리면 거울상이 된다(2026-09-10 실수). 그림 좌표는 (E,N)=(Y,X).

## 함정

- **저장 안 된 모델에 `/doc/ANAL`을 보내면 "다른 이름으로 저장" 모달이 떠서 API 전체가 멈춘다**(모든 요청 타임아웃). 반드시 `/doc/SAVEAS`를 먼저 보낸다.
- **제목 없는 문서에 `/doc/SAVE`를 보내도 같은 모달이 뜬다**(2026-09-10 두 번째 사고). 저장은 항상 `/doc/SAVEAS`(경로 지정)로. `/doc/NEW` 전에도 SAVEAS 스크래치로 정리.
- MCT 파싱 실패는 모달 없이 조용히 절점 0으로 끝난다(`GET /db/NODE` 되읽기로 잡을 것). 블록을 하나씩 빼며 재임포트해 원인 분리.
- 모달 여부는 스크린샷 대신 `D:\Midas\tools\win_probe.ps1`(PowerShell `EnumWindows`)로 CVLw PID의 `#32770` 클래스 창을 찾으면 200토큰에 알 수 있다.
- CIVIL NX가 **관리자 권한**으로 떠 있으면 컴퓨터-유즈 입력이 UIPI로 전부 차단된다(9/9 대화상자 못 닫은 원인). 모달은 대표님이 직접 눌러야 한다. 일반 권한 실행을 권장.
- 결과 표 `PLACE 4`는 변위(m)에 부족하다. 변위는 `Scientific`으로 받는다.

## 부호 규약 (실측)

- 하중 −Z → 반력 FZ **+**. 보 Moment-y는 중앙 처짐(sagging) **+**, 고정단 **−**. 반력 MY는 좌측 지점 −, 우측 +.
- 변위 검증 시 **전단변형 포함**(`USE_SHEAR_DEFORM true`가 기본). 5m 보(L/H=8)는 전단 처짐이 약 18%라 휨만 계산하면 안 맞는다. 사각단면 Iyy = B·H³/12, H는 연직 방향(SB 치수 순서 H, B — [[midas-mct-syntax]] 참조).

## 5m 보 검증 결과 (2026-09-10)

중앙 +17.12 / 고정단 −31.24 kN·m, 반력 39.27 kN, 중앙 처짐 5.89e-5 m — 손계산(17.11 / 31.22 / 39.27 / 5.9e-5)과 일치. 산출물 `D:\Midas\runs\5m_beam\` (mcb + 표 JSON). 스크립트 `D:\Midas\tools\step1_*.py`.

**Why:** 9/9 세션은 리스닝 포트가 없다는 이유로 "API 없음"으로 판단해 스크린샷(장당 약 1,600토큰)에 의존했고 모멘트조차 못 읽었다. 실제로는 API 설정을 안 켠 것뿐이었다.

**How to apply:** MIDAS 작업은 `PYTHONUTF8=1 python D:\Midas\tools\midas_api.py`로 연결 확인부터. 실패하면 대표님께 Apps > API Settings > Connect 요청. 모델 만들고 → SAVEAS → ANAL → /post/table 순서. 계획 문서 `D:\Midas\MIDAS_자동화_계획_2026-09-10.md`, 9/9 산출물 `D:\Midas\_이전세션_산출물_20260909\`. 관련: [[midas-mct-syntax]], [[midas-license-mdesk]]

- **화면 캡처 API(2026-09-10 확인):** `POST /view/CAPTURE {"Argument":{"SET_MODE":"pre|post","EXPORT_PATH":"...jpg","WIDTH","HEIGHT","ANGLE":{"HORIZONTAL","VERTICAL"},"DISPLAY":{...,"ZOOM_LEVEL"},"RESULT_GRAPHIC":{"CURRENT_MODE":"beamdiagrams","LOAD_CASE_COMB":{"TYPE":"ST","NAME":..},"COMPONENTS":{"PART":"total","COMP":"My"},...}}}` → 모델·부재력도 JPG 저장. 보고서 삽도는 이걸로 만든다(범례 열 140 px 포함, 배경 자르기는 `pier_model.autocrop`).
- **MCT 함정 추가:** `*CONLOAD` 행의 여섯 성분이 전부 0이면 파일 전체가 절점 0으로 조용히 실패. `*SECTION` 블록 안 빈 줄 금지. 원인 분리는 `tools\import_probe.py`로 블록 이분탐색.
- **변단면·사용자 재료 JSON(2026-09-11 실측, NX 2026 v2.3):** `PUT /db/SECT` TAPERED = `{"SECTTYPE":"TAPERED","SECT_NAME":..,"SECT_BEFORE":{"OFFSET_PT":"CC",…,"SHAPE":"SB","TYPE":2,"SECT_I":{"vSIZE":[H,B1,0…]},"SECT_J":{"vSIZE":[H,B2,0…]},"Y_VAR":1,"Z_VAR":1}}` (TYPE 2 = 사용자 치수, vSIZE 10칸). DBUSER의 `OFFSET_PT":"CT"`로 단면 상면 정렬 가능. 사용자 등방성 재료는 **`PARAM":[{"P_TYPE":2,"ELAST":E,"POISN":..,"THERMAL":..,"DEN":γ,"MASS":0}]` 평면 키**만 통과(도움말의 P_TYPE 1+USER_DEFINED/bELAST 형식은 "STANDARD and DB required"/"탄성계수 잘못" 오류; 이 버전은 P_TYPE 1 = DB 재료). DB 재료 C24(KSCE-LSD15) 밀도는 24.517 kN/m³. 요소 재료·단면 변경은 `GET /db/ELEM` 사본에 MATL/SECT만 바꿔 `PUT`. 구현: `projects/순천만IC2교/pier_model.py nx_sections_materials()`.

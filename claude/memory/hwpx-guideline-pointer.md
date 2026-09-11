---
name: hwpx-guideline-pointer
description: "한글(HWPX) 보고서 편집은 대표님이 정한 구글드라이브 「한글문서(HWPX) 편집 작업지침」(v2 §0~14, v3.1 §15~17, v3.2 §18, v3.3 §19)을 따른다 — 원본 XML 복제·값 교체, 새로 그리기 금지, 검증 필수"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ac048fbe-9263-4808-af0f-0d086cbaf089
  modified: 2026-09-11T05:29:48.689Z
---

대표님은 한글 보고서를 "수도 없이" 만들어 왔고 방법이 정해져 있다. hwp 스킬의 마크다운 변환기가 아니라 **원본 hwpx의 XML을 복제·수정**하는 방식이다.

- 지침 파일(구글드라이브, 소유자 sjidok750): v2 `1STMagrUVA2xl0dI1xyngFGR0067JqS-b` (§0~§14 기본·검증·서식 재작성 금지·쪽나눔·borderFill 재사용), v3.1 `10XHPmvCWfwbDh072TbcZL7NhEjSsv20y` (§15 긴 표·§16 내용 정합성·§17 사진 이식), v3.2 `1N704rct9OgLySP9FZdqqP8cUNOBRZ0YI` (§18 표 선 굵기: 외곽 0.4, 머리행 아래 DOUBLE_SLIM 0.5, 내부 0.12), v3.3 `1EUB5wnUukoQWHIBX-Q5U6qwsbgckAnvcyskivGNlq1s` (§19 캡션: 표 위·그림 아래).
- 핵심 7가지(다른 프로젝트 메모리 hwpx-document-standard와 동일): 대절 쪽바꿈 허용, 소절 이어쓰기, 캡션과 개체 같은 쪽, 긴 표 머리행 반복, 선굵기 0.12/0.4, 표제목 위, 그림제목 아래.
- 구현: `D:\Midas\tools\hwpx_edit.py` (Hwpx 클래스: load/dump/find_table_after/set_cell/clone_row/renumber_objects/save/baseline/verify). 기준선(무변경 재저장 = 항목별 바이트 동일) 확보 후 작업.

- 실전 함정(2026-09-10 5장 조립): ① `<hp:t>` 안의 `<hp:fwSpace/>` 뒤 tail 텍스트를 놓치면 "case 1 1", 단위 잔존 같은 꼬리가 남는다 → para_text는 itertext, set_*는 자식 제거. ② 수식 문단은 `<hp:run>` 안에 `<hp:t>`–`<hp:equation>`–`<hp:t>` 순서라 첫 t만 바꾸면 순서가 깨진다 → `set_para_runs`로 t 목록 순서대로 교체, 수식은 `<hp:script>` 값만 갱신. ③ 병합 헤더 셀은 (row, col) 주소로 못 찾는다 → tr의 tc 순서로 접근하거나 텍스트로 찾기. ④ 문단 삭제·삽입 뒤 고정 인덱스는 어긋나므로 `find_para`로 재탐색. ⑤ 셀 여러 줄은 `set_cell_lines`(첫 문단 복제) — 새 문단을 만들지 말 것. 조립 스크립트 예: `projects\순천만IC2교\build_ch5.py`.

- 그림 교체(§17) 구현: `add_image`(BinData + content.hpf `<opf:item>` 등록, HWPUNIT = px×75) → `swap_pic`(그림틀 유지: orgSz/imgRect/imgClip/imgDim=새 원본 크기, curSz·sz=기존 폭×새 비율, scaMatrix=cur/org, transMatrix 이동 0) → `prune_images`(참조 없는 BinData 삭제, header.xml 참조도 확인). 캡션이 자동번호(autoNum)면 그림 문단+캡션 문단을 deepcopy해 삽입해도 번호가 따라간다.

**Why:** 텍스트만 뽑아 새로 만들면 바탕쪽·머리말·스타일이 전부 사라져 결과물이 무의미하다(§10). 2026-09-10 순천만IC2교 5장 작업에서 확인.

**How to apply:** 5장 같은 보고서 장은 초안 hwpx의 표 구조를 두고 숫자·행·그림만 교체한다. 저장 후 verify() 통과 전에는 파일을 건네지 않는다. 관련: [[midas-open-api]], [[midas-drawing-pipeline]]

- **2026-09-11 추가:** 표·문단 생성은 `D:\Midas\tools\hwpx_table.py`(new_table: 문서 안 표 복제 후 행·열 재구성, new_para, merge_cells, fix_layout). 병합 셀이 있는 표는 (row,col) 인덱스 대신 cellAddr로 접근(build_ch5_v4.setc). 레이아웃 점검은 XML로 표 높이(본문 242 mm 초과=잘림 위험)·pageBreak·빈 문단 연속·연속 쪽나눔을 스캔. 한글 COM(HWPFrame.HwpObject)은 미등록(regsvr32 exit 3)이라 **렌더는 컴퓨터-유즈로 한글을 조작**한다: Start-Process로 hwpx 열기 → 파일 메뉴(22,33) → PDF로 저장하기(62,243) → 파일명 ctrl+a 후 새 이름 입력(덮어쓰기는 한PDF 뷰어(Hpdf.exe)가 잠가 실패) → 저장(598,399) → 30~40 s 뒤 `Stop-Process Hpdf` → PDF를 스크래치로 복사해 fitz로 분석. 문서를 닫을 때 ctrl+F4 → "저장 안 함"(737,425). hwpx를 다시 저장하려면 먼저 한글에서 닫아야 한다(PermissionError).

- **쪽 배치 교훈(2026-09-11, 5장_v4 렌더 9회 반복):** 이 보고서의 표는 모두 treatAsChar="1"(글자처럼)이라 쪽을 넘어 분할되지 않고 통째로 다음 쪽으로 가며, keepWithNext는 표 앞 캡션·제목에 효과가 없다 → `D:\Midas\tools\hwpx_layout.py`의 `stranded_from_pdf(doc, pdf)`가 렌더 PDF에서 "뒤에 표·그림이 오는 제목/표 캡션이 쪽 끝에 홀로 남은" 곳을 찾아 제목 묶음 첫 문단에 pageBreak=1을 걸고(묶음이 이미 쪽 머리면 뒤 문단의 쪽나눔을 푼다) 렌더→수정→렌더를 반복한다(보통 2~3회 수렴). 함정: ① 표지 목차('5.5 …')가 제목으로 잡혀 커서가 끝으로 튐 → 앞 2쪽 건너뜀, ② 같은 제목(①고정하중)이 반복되므로 문서 순서 커서로 찾음, ③ 그림 캡션은 그림 아래라 쪽 끝이 정상(제외), ④ ⑥… 같은 목록 항목은 뒤에 표가 없으면 제외, ⑤ 번호 있는 문단은 렌더 텍스트에서 자동번호(①, 2), 가., 5.2.1, 【표 5.2】)를 벗겨 문단을 찾는다. 그림 캡션 스타일: 문서 표준은 style 16 '그림제목'(paraPr 71 자동번호 【그림 5.x】); v3 템플릿 400은 style 72 '<그림>'로 번호가 없다 → B.fig에서 16/71/charPr 2로 지정. 셀 폭 22 mm(6366 HWPUNIT)에 긴 글을 넣으면 한 글자씩 꺾인다 → 그림 셀을 줄이고 범례 셀을 넓힘(_patch_v4b.py).

# Midas-nx — 도면 → MIDAS CIVIL NX 해석 → 진단 보고서 자동화

준공도면(DWG)을 주면 Claude가 **이 PC의 CIVIL NX를 Open API(REST, 포트 10024)로 직접 조작**해 모델을 만들고 해석하여 결과를 뽑고, 그 결과로 정밀안전진단 보고서 5장(hwpx)을 조립한다. 핵심은 "도면 → NX 모델링 → 결과"가 코드로 매번 같은 방식으로 재현되는 것이다. 보고서 조립은 뒤따라 차츰 손본다.

## 폴더

| 폴더 | 내용 |
|---|---|
| `tools/` | 범용 도구. `midas_api.py`(NX REST 래퍼, MAPI-Key는 레지스트리에서 읽음 — 값은 코드에 없다), `mct_syntax.py`, `dxf_render.py`(DXF→PNG), `abut_geom.py`·`pier_geom.py`(도면 좌표 판독), `spec_build.py`(제원서), `hwpx_edit.py`·`hwpx_table.py`·`hwpx_layout.py`(한글 XML 편집·쪽 배치), `verify.py` |
| `projects/<교량>/` | 교량별 작업. 순천만IC2교: `pier_model.py`(NX 교각 모델·자중 검증), `gen_model.py`·`run_models.py`(상부), `abutment3.py`·`pier_model3.py`·`stress3.py`(편람 단계 검토), `derive.py`(풀이 문장), `appendix_xlsx.py`(부록), `build_ch5_v4.py`+`_patch_v4b.py`(5장 조립·서식), `제원서.json`·`하부_제원서.json`, `extract/`(도면 문자 추출), `png/`(삽도), `runs/`(결과 JSON·PNG·MCT) |
| `references/` | 설계기준 원문(도로교설계기준 2005·2010·LSD 2016, 도로설계요령 2020, 도로설계편람 제5편 2008)과 추출 텍스트, 편람 예제 요약 md. 매번 다시 찾지 않도록 함께 둔다 |
| `claude/` | Claude 운용 규칙 사본: `CLAUDE.md`(전역 지침), `skills/`(midas-nx·hwp·docflow·report-review·codex-verify), `memory/`(세션 간 기억). 새 PC에서는 `~/.claude/` 아래로 복사 |
| `MIDAS_자동화_계획_2026-09-10.md` | 계획서 겸 진행 일지 |

레포에 넣지 않는 것(.gitignore): 준공도면 DWG/DXF 원본, NX 대용량 결과(.blk/.nfxp/.mcb), 납품 보고서(hwpx/pdf/xlsx). 이것들은 과업 폴더와 구글드라이브에 둔다.

## 돌리는 순서 (순천만IC2교 기준)

1. CIVIL NX 실행 → Apps > API Settings > Connect (MAPI-Key가 레지스트리에 기록됨)
2. 도면 판독: `python tools/dxf_render.py`, `abut_geom.py`, `pier_geom.py` → `하부_제원서.json`
3. NX 모델·해석: `python projects/순천만IC2교/pier_model.py` (변단면 코핑·기둥, 자중 1 % 검증), 상부는 `run_models.py`
4. 검토 계산: `abutment3.py`, `pier_model3.py`, `stress3.py` → `runs/*/…_result.json`
5. 보고서: `build_ch5_v4.py` → `_patch_v4b.py` → 한글에서 PDF 렌더 → `hwpx_layout.stranded_from_pdf`로 쪽 배치 확정

## 원칙 (대표님 결정, 2026-09-11)

- 진단은 강도설계·허용응력설계(2010 도로교설계기준) 체계. 한계상태설계법 검토 없음. 다른 제반 규정은 최신.
- 활하중 DB-24/DL-24. 지진하중은 내진성능평가에서 따로 하므로 제외.
- 근거 없는 값은 지어내지 않고 `(확인 필요)`로 남긴다. 수치에는 기준을 붙인다.
- 한글 문서는 원본 XML 복제·값 교체, 저장 후 verify 통과 전에는 건네지 않는다.

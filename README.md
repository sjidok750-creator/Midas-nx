# Midas-nx — 강박스(STB) 교량 정밀안전진단 자동화

준공도면(DWG)을 주면 Claude가 **이 PC의 CIVIL NX를 Open API로 직접 조작**해 상부(강박스 격자)·하부(T형 교각, 역T 교대) 모델을 만들고 해석하여, 편람 단계대로 검토하고 5장(hwpx)을 조립한다. 순천만IC2교(강박스 5경간)에서 실증했다.

공통 도구·설계기준·Claude 운용 규칙은 서브모듈 **`core/`**(= [Midas-core](https://github.com/sjidok750-creator/Midas-core))에 있다. 터널은 별도 레포 [Midas-tunnel](https://github.com/sjidok750-creator/Midas-tunnel).

```bash
git clone --recurse-submodules https://github.com/sjidok750-creator/Midas-nx.git
```

## 폴더

| 폴더 | 내용 |
|---|---|
| `core/` | 서브모듈. `core/tools`(NX API·MCT·DXF·HWPX 도구), `core/references`(설계기준 원문), `core/claude`(CLAUDE.md·skills·memory) |
| `projects/순천만IC2교/` | `pier_model.py`(NX 교각 변단면 모델·자중 검증), `gen_model.py`·`run_models.py`(상부 격자), `abutment3.py`·`pier_model3.py`·`stress3.py`(편람 단계 검토), `derive.py`(풀이 문장), `appendix_xlsx.py`(부록), `build_ch5_v4.py`+`_patch_v4b.py`(5장 조립·서식), `제원서.json`·`하부_제원서.json`, `extract/`(도면 문자 추출), `png/`(삽도), `runs/`(결과 JSON·PNG·MCT) |
| `MIDAS_자동화_계획_2026-09-10.md` | 계획서 겸 진행 일지 |

레포에 넣지 않는 것(.gitignore): 준공도면 DWG/DXF 원본, NX 대용량 결과(.mcb/.nfxp/.blk), 납품 보고서(hwpx/pdf/xlsx). 과업 폴더와 구글드라이브에 둔다.

## 돌리는 순서 (순천만IC2교)

1. CIVIL NX 실행 → Apps > API Settings > Connect ("Connect API on Startup" 체크 권장)
2. 도면 판독: `core/tools/dxf_render.py`, `abut_geom.py`, `pier_geom.py` → `하부_제원서.json`
3. NX 모델·해석: `python projects/순천만IC2교/pier_model3.py P3` (변단면 코핑·기둥, 자중 1 % 검증) — 2026-09-14 재현 확인, 결과 차이 0
4. 검토: `abutment3.py`, `pier_model3.py`, `stress3.py` → `runs/*/…_result.json`
5. 보고서: `build_ch5_v4.py` → `_patch_v4b.py` → 한글 PDF 렌더 → `hwpx_layout.stranded_from_pdf`로 쪽 배치 확정

## 원칙 (대표님 결정, 2026-09-11)

- 진단은 강도설계·허용응력설계(2010 도로교설계기준) 체계. 한계상태설계법 검토 없음. 다른 제반 규정은 최신.
- 활하중 DB-24/DL-24. 지진하중은 내진성능평가에서 따로 하므로 제외.
- 근거 없는 값은 지어내지 않고 `(확인 필요)`로 남긴다. 한글 문서는 원본 XML 복제·값 교체, verify 통과 전에는 건네지 않는다.

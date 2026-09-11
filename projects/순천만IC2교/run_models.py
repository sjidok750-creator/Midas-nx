# -*- coding: utf-8 -*-
"""
MCT 3종을 CIVIL NX API로 차례로: 새 문서 → 불러오기 → 되읽기 검증 → 저장 → 해석 → 주형 BEAMFORCE 표 → JSON
  python run_models.py [A_steel B_comp3n C_compn]
"""
import sys, os, json, time
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\Midas\tools")
from midas_api import Civil

PJ = r"D:\Midas\projects\순천만IC2교"
RUNS = os.path.join(PJ, "runs")
INFO = json.load(open(os.path.join(RUNS, "model_info.json"), encoding="utf-8"))
CASES = {"A_steel": ["DEAD(ST)", "SLAB(ST)", "D1(CB)"], "B_comp3n": ["SDL(ST)", "D2(CB)"], "C_compn": None}

def run(tag):
    c = Civil(timeout=900)
    mct = os.path.join(RUNS, f"{tag}.mct")
    mcb = os.path.join(RUNS, f"{tag}.mcb")
    t = time.time()
    print(f"== {tag}")
    # 제목 없는 문서에 /doc/SAVE 를 보내면 "다른 이름으로 저장" 모달이 떠서 API가 멈춘다 → 항상 SAVEAS(스크래치)로 정리
    c.post("/doc/SAVEAS", {"Argument": os.path.join(RUNS, "_scratch.mcb")})
    print("  NEW   :", c.post("/doc/NEW", {"Argument": {}}).get("message", "?"))
    print("  IMPORT:", c.post("/doc/IMPORTMXT", {"Argument": mct}).get("message", "?"))
    nn, ne = c.node_count(), c.elem_count()
    exp_n, exp_e = INFO["n_nodes"], INFO["n_main"] + INFO["n_xb"]
    print(f"  되읽기: 절점 {nn}/{exp_n}  요소 {ne}/{exp_e}  {'OK' if (nn, ne) == (exp_n, exp_e) else '★불일치'}")
    if (nn, ne) != (exp_n, exp_e):
        return None
    sect = c.get("/db/SECT")["SECT"]
    print(f"  단면 {len(sect)}종, 단위 {c.units()['UNIT']['1']['FORCE']}/{c.units()['UNIT']['1']['DIST']}")
    print("  SAVEAS:", c.post("/doc/SAVEAS", {"Argument": mcb}).get("message", "?"))
    t1 = time.time()
    print("  ANAL  :", c.post("/doc/ANAL", {"Assign": {}}).get("message", "?"), f"({time.time()-t1:.0f}s)")
    elems = [e for e, g, s1, s2, sc in INFO["elems"]]
    arg = {"TABLE_NAME": "SS_Table", "TABLE_TYPE": "BEAMFORCE", "UNIT": {"FORCE": "KN", "DIST": "M"},
           "STYLES": {"FORMAT": "Fixed", "PLACE": 3}, "NODE_ELEMS": {"KEYS": elems}, "PARTS": ["PartI", "PartJ"]}
    if CASES[tag]:
        arg["LOAD_CASE_NAMES"] = CASES[tag]
    r = c.post("/post/table", {"Argument": arg})
    if "SS_Table" not in r:
        print("  결과표 실패:", json.dumps(r, ensure_ascii=False)[:300]); return None
    tb = r["SS_Table"]
    names = sorted({row[2] for row in tb["DATA"]})
    print(f"  BEAMFORCE 행 {len(tb['DATA'])}, 하중명 {names}  ({time.time()-t:.0f}s)")
    json.dump(r, open(os.path.join(RUNS, f"{tag}_beamforce.json"), "w", encoding="utf-8"), ensure_ascii=False)
    # 반력 (Σ 검증용)
    rr = c.post("/post/table", {"Argument": {"TABLE_NAME": "SS_Table", "TABLE_TYPE": "REACTIONG", "UNIT": {"FORCE": "KN", "DIST": "M"},
                                               "STYLES": {"FORMAT": "Fixed", "PLACE": 3}}})
    json.dump(rr, open(os.path.join(RUNS, f"{tag}_reaction.json"), "w", encoding="utf-8"), ensure_ascii=False)
    if "SS_Table" in rr:
        h = rr["SS_Table"]["HEAD"]; iz, il = h.index("FZ"), h.index("Load")
        tot = {}
        for row in rr["SS_Table"]["DATA"]:
            tot[row[il]] = tot.get(row[il], 0) + float(row[iz])
        print("  ΣFZ 반력:", {k: round(v, 1) for k, v in tot.items()})
    return r

if __name__ == "__main__":
    tags = sys.argv[1:] or ["A_steel", "B_comp3n", "C_compn"]
    for tg in tags:
        run(tg)

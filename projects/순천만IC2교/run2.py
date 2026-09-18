# -*- coding: utf-8 -*-
"""
v2 실행: A_steel, C_comp 를 API로 — 새문서 → MCT 불러오기 → 되읽기 검증 → 받침 국부축(JSON) → (C: 이동하중 JSON) → 저장 → 해석 → 표
  python run2.py [A_steel C_comp]
"""
import sys, os, json, time
sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"D:\Midas\core\tools")
from midas_api import Civil
PJ = r"D:\Midas\projects\순천만IC2교"; RUNS = os.path.join(PJ, "runs")
INFO = json.load(open(os.path.join(RUNS, "model_info.json"), encoding="utf-8"))

def moving_loads(c):
    c.put("/db/mvcd", {"Assign": {"1": {"CODE": "KOREA"}}})
    lanes, sup = {"Assign": {}}, INFO["sup_s"]
    s1_of = {e: s1 for e, g, s1, s2, sc in INFO["elems"]}
    for li, g in enumerate(("G1", "G2"), start=1):
        items = [{"ELEM": e, "ECC": 0, "FACT": 0, "SPAN_START": any(abs(s1_of[e] - v) < 1e-3 for v in sup[:-1])} for e in INFO["lane_ids"][g]]
        lanes["Assign"][str(li)] = {"COMMON": {"LL_NAME": f"L{li}", "LOAD_DIST": "LANE", "GROUP_NAME": "", "SKEW_START": 0, "SKEW_END": 0,
                                               "MOVING": "BOTH", "WHEEL_SPACE": 1.8, "WIDTH": 3, "OPT_AUTO_LANE": False, "ALLOW_WIDTH": 0},
                                    "LANE_ITEMS": items}
    c.put("/db/llan", lanes)
    veh = {"Assign": {str(i): {"MVLD_CODE": 6, "VEHICLE_LOAD_NAME": nm, "VEHICLE_LOAD_NUM": 1, "VEHICLE_TYPE_NAME": nm, "STANDARD_CODE": "KS-RB",
                               "VEH_DEFAULT": {"DYN_LOAD_ALLOWANCE": 0, "CENT_F": False}} for i, nm in enumerate(("DB-24", "DL-24"), start=1)}}
    c.put("/db/mvhl", veh)
    def case(nm):
        return {"LCNAME": nm, "DESC": "", "TYPE": 0, "DEFAULT": {"SCALE_FACTORS": [1, 1, 0.9, 0.75, 0.75, 0.75], "COMB_OPTION": "INDEPENDENT",
                "LANE_FACTOR_TYPE": 1, "_2_LANE_FACTOR_1": 1, "_2_LANE_FACTOR_2": 1, "_3_LANE_FACTOR_1": 1, "_3_LANE_FACTOR_2": 0.5, "_3_LANE_FACTOR_3": 0.5, "_3_LANE_FACTOR_4": 0.25,
                "SUB_LOAD_DATAS": [{"VEHICLE_TYPE": "VL", "VEHICLE_NAME": nm, "SCALE_FACTOR": 1, "MIN_LOADED_LANE": 1, "MAX_LOADED_LANE": 2, "LANE_NAMES": ["L1", "L2"]}]}}
    c.put("/db/mvld", {"Assign": {"1": case("DB-24"), "2": case("DL-24")}})
    print("  이동하중: 차선", len(c.get("/db/llan")["LLAN"]), "차량", len(c.get("/db/mvhl")["MVHL"]), "케이스", len(c.get("/db/mvld")["MVLD"]))

def run(tag):
    c = Civil(timeout=1800); t0 = time.time(); print(f"== {tag}")
    c.post("/doc/SAVEAS", {"Argument": r"D:\Midas\runs\_scratch.mcb"}); c.post("/doc/NEW", {"Argument": {}})
    c.post("/doc/IMPORTMXT", {"Argument": os.path.join(RUNS, f"{tag}.mct")})
    nn, ne = c.node_count(), c.elem_count(); exp = (INFO["n_nodes"], INFO["n_main"] + INFO["n_xb"])
    print(f"  되읽기: 절점 {nn}/{exp[0]} 요소 {ne}/{exp[1]} {'OK' if (nn, ne) == exp else '★불일치'}")
    if (nn, ne) != exp: return
    # 받침 국부축: x' = 접선 방향
    skew = {"Assign": {str(b["node"]): {"iMETHOD": 1, "ANGLE_X": 0, "ANGLE_Y": 0, "ANGLE_Z": round(b["angle_deg"], 4)} for b in INFO["bearings"]}}
    r = c.put("/db/skew", skew); print("  국부축:", len(c.get("/db/skew").get("SKEW", {})), "절점 | 구속:", len(c.get("/db/CONS").get("CONS", {})), "절점")
    if tag == "C_comp": moving_loads(c)
    c.post("/doc/SAVEAS", {"Argument": os.path.join(RUNS, f"{tag}.mcb")})
    t = time.time(); print("  ANAL:", c.post("/doc/ANAL", {"Assign": {}}).get("message"), f"({time.time()-t:.0f}s)")
    elems = [e for e, g, s1, s2, sc in INFO["elems"]]
    r = c.post("/post/table", {"Argument": {"TABLE_NAME": "SS_Table", "TABLE_TYPE": "BEAMFORCE", "UNIT": {"FORCE": "KN", "DIST": "M"},
                                            "STYLES": {"FORMAT": "Fixed", "PLACE": 3}, "NODE_ELEMS": {"KEYS": elems}, "PARTS": ["PartI", "PartJ"]}})
    if "SS_Table" not in r: print("  결과표 실패", json.dumps(r, ensure_ascii=False)[:200]); return
    print("  BEAMFORCE 행", len(r["SS_Table"]["DATA"]), "하중명", sorted({row[2] for row in r["SS_Table"]["DATA"]}))
    json.dump(r, open(os.path.join(RUNS, f"{tag}_beamforce.json"), "w", encoding="utf-8"), ensure_ascii=False)
    rr = c.post("/post/table", {"Argument": {"TABLE_NAME": "SS_Table", "TABLE_TYPE": "REACTIONG", "UNIT": {"FORCE": "KN", "DIST": "M"}, "STYLES": {"FORMAT": "Fixed", "PLACE": 2}}})
    json.dump(rr, open(os.path.join(RUNS, f"{tag}_reaction.json"), "w", encoding="utf-8"), ensure_ascii=False)
    if "SS_Table" in rr:
        h = rr["SS_Table"]["HEAD"]; tot = {}
        for row in rr["SS_Table"]["DATA"]:
            for comp in ("FX", "FY", "FZ"):
                tot.setdefault(row[h.index("Load")], {}).setdefault(comp, 0); tot[row[h.index("Load")]][comp] += float(row[h.index(comp)])
        print("  Σ반력:", {k: {kk: round(vv, 1) for kk, vv in v.items()} for k, v in tot.items() if not k.endswith("(all)")})
    print(f"  ({time.time()-t0:.0f}s)")

if __name__ == "__main__":
    for tg in (sys.argv[1:] or ["A_steel", "C_comp"]): run(tg)

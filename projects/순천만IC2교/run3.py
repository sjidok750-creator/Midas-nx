# -*- coding: utf-8 -*-
"""
v3 실행: A_steel, C_comp — 새문서 → MCT → 되읽기 → 받침 국부축 → JSON 추가하중(비틀림·지점침하·이동하중) → 저장 → 해석 → 표
  python run3.py [A_steel C_comp]
결과: runs/<tag>_beamforce.json, _reaction.json, _disp.json (C: 이동하중 변위)
"""
import sys, os, json, time
sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"D:\Midas\core\tools")
from midas_api import Civil
PJ = r"D:\Midas\projects\순천만IC2교"; RUNS = os.path.join(PJ, "runs")
INFO = json.load(open(os.path.join(RUNS, "model_info.json"), encoding="utf-8"))

def bmld_item(idn, lc, typ, direction, p):
    return {"ID": idn, "LCNAME": lc, "GROUP_NAME": "", "CMD": "BEAM", "TYPE": typ, "DIRECTION": direction, "USE_PROJECTION": False,
            "USE_ECCEN": False, "D": [0, 1, 0, 0], "P": [p, p, 0, 0], "USE_ADDITIONAL": False, "ADDITIONAL_I_END": 0, "ADDITIONAL_J_END": 0, "USE_ADDITIONAL_J_END": False}

def add_torsion(c, lc, mx_by_girder):
    """주형 요소에 분포 비틀림모멘트(UNIMOMENT, 요소 x축) 추가 — 기존 BMLD ITEMS 뒤에 붙인다"""
    cur = c.get("/db/BMLD").get("BMLD", {})
    body = {"Assign": {}}
    for e, g, s1, s2, sc in INFO["elems"]:
        items = list(cur.get(str(e), {}).get("ITEMS", []))
        items.append(bmld_item(max([it["ID"] for it in items] + [0]) + 1, lc, "UNIMOMENT", "LX", mx_by_girder[g]))
        body["Assign"][str(e)] = {"ITEMS": items}
    r = c.put("/db/BMLD", body)
    n = sum(1 for v in c.get("/db/BMLD")["BMLD"].values() for it in v["ITEMS"] if it["TYPE"] == "UNIMOMENT" and it["LCNAME"] == lc)
    print(f"  비틀림 {lc}: UNIMOMENT {n}개 {'OK' if n == len(INFO['elems']) else '★부족'}")

def add_settlements(c):
    """지점침하 SD_<지점>: 해당 지점의 두 주형 받침 절점에 DZ = −δ"""
    body = {"Assign": {}}
    for pier in ("A1", "P1", "P2", "P3", "P4", "P5"):
        for b in INFO["bearings"]:
            if b["pier"] != pier: continue
            vals = [{"OPT_FLAG": i == 2, "DISPLACEMENT": (-INFO["settle"] if i == 2 else 0.0)} for i in range(6)]
            body["Assign"].setdefault(str(b["node"]), {"ITEMS": []})["ITEMS"].append({"ID": len(body["Assign"][str(b["node"])]["ITEMS"]) + 1, "LCNAME": f"SD_{pier}", "GROUP_NAME": "", "VALUES": vals})
    r = c.put("/db/sdsp", body)
    g = c.get("/db/sdsp").get("SDSP", {})
    print(f"  지점침하: 절점 {len(g)}개 {'OK' if len(g) == 12 else '★확인'} ({json.dumps(r, ensure_ascii=False)[:80]})")

def moving_loads(c):
    c.put("/db/mvcd", {"Assign": {"1": {"CODE": "KOREA"}}})
    lanes, sup = {"Assign": {}}, INFO["sup_s"]; s1_of = {e: s1 for e, g, s1, s2, sc in INFO["elems"]}
    for li, g in enumerate(("G1", "G2"), start=1):
        items = [{"ELEM": e, "ECC": 0, "FACT": 0, "SPAN_START": any(abs(s1_of[e] - v) < 1e-3 for v in sup[:-1])} for e in INFO["lane_ids"][g]]
        lanes["Assign"][str(li)] = {"COMMON": {"LL_NAME": f"L{li}", "LOAD_DIST": "LANE", "GROUP_NAME": "", "SKEW_START": 0, "SKEW_END": 0, "MOVING": "BOTH",
                                               "WHEEL_SPACE": 1.8, "WIDTH": 3, "OPT_AUTO_LANE": False, "ALLOW_WIDTH": 0}, "LANE_ITEMS": items}
    c.put("/db/llan", lanes)
    c.put("/db/mvhl", {"Assign": {str(i): {"MVLD_CODE": 6, "VEHICLE_LOAD_NAME": nm, "VEHICLE_LOAD_NUM": 1, "VEHICLE_TYPE_NAME": nm, "STANDARD_CODE": "KS-RB",
                                            "VEH_DEFAULT": {"DYN_LOAD_ALLOWANCE": 0, "CENT_F": False}} for i, nm in enumerate(("DB-24", "DL-24"), start=1)}})
    def case(nm):
        return {"LCNAME": nm, "DESC": "", "TYPE": 0, "DEFAULT": {"SCALE_FACTORS": [1, 1, 0.9, 0.75, 0.75, 0.75], "COMB_OPTION": "INDEPENDENT", "LANE_FACTOR_TYPE": 1,
                "_2_LANE_FACTOR_1": 1, "_2_LANE_FACTOR_2": 1, "_3_LANE_FACTOR_1": 1, "_3_LANE_FACTOR_2": 0.5, "_3_LANE_FACTOR_3": 0.5, "_3_LANE_FACTOR_4": 0.25,
                "SUB_LOAD_DATAS": [{"VEHICLE_TYPE": "VL", "VEHICLE_NAME": nm, "SCALE_FACTOR": 1, "MIN_LOADED_LANE": 1, "MAX_LOADED_LANE": 2, "LANE_NAMES": ["L1", "L2"]}]}}
    def case1(nm, lane):
        """편재(1차선) 케이스: 지정 차선만 재하 — 교각 편심모멘트·교대 편측 반력용"""
        d = case(nm); d["LCNAME"] = f"{nm}_{lane}"; d["DEFAULT"]["SUB_LOAD_DATAS"][0].update({"MIN_LOADED_LANE": 1, "MAX_LOADED_LANE": 1, "LANE_NAMES": [lane]}); return d
    c.put("/db/mvld", {"Assign": {"1": case("DB-24"), "2": case("DL-24"), "3": case1("DB-24", "L1"), "4": case1("DB-24", "L2"), "5": case1("DL-24", "L1"), "6": case1("DL-24", "L2")}})
    print("  이동하중: 차선", len(c.get("/db/llan")["LLAN"]), "차량", len(c.get("/db/mvhl")["MVHL"]), "케이스", len(c.get("/db/mvld")["MVLD"]))

def table(c, ttype, keys, cases=None, parts=None, place=3, fmt="Fixed"):
    arg = {"TABLE_NAME": "SS_Table", "TABLE_TYPE": ttype, "UNIT": {"FORCE": "KN", "DIST": "M"}, "STYLES": {"FORMAT": fmt, "PLACE": place}}
    if keys: arg["NODE_ELEMS"] = {"KEYS": keys}
    if cases: arg["LOAD_CASE_NAMES"] = cases
    if parts: arg["PARTS"] = parts
    return c.post("/post/table", {"Argument": arg})

def run(tag):
    c = Civil(timeout=1800); t0 = time.time(); print(f"== {tag}")
    c.post("/doc/SAVEAS", {"Argument": r"D:\Midas\runs\_scratch.mcb"}); c.post("/doc/NEW", {"Argument": {}})
    c.post("/doc/IMPORTMXT", {"Argument": os.path.join(RUNS, f"{tag}.mct")})
    nn, ne = c.node_count(), c.elem_count(); exp = (INFO["n_nodes"], INFO["n_main"] + INFO["n_xb"])
    print(f"  되읽기: 절점 {nn}/{exp[0]} 요소 {ne}/{exp[1]} {'OK' if (nn, ne) == exp else '★불일치'}")
    if (nn, ne) != exp: return
    c.put("/db/skew", {"Assign": {str(b["node"]): {"iMETHOD": 1, "ANGLE_X": 0, "ANGLE_Y": 0, "ANGLE_Z": round(b["angle_deg"], 4)} for b in INFO["bearings"]}})
    print("  국부축", len(c.get("/db/skew").get("SKEW", {})), "| 구속", len(c.get("/db/CONS").get("CONS", {})))
    if tag == "A_steel":
        add_torsion(c, "SLAB", INFO["mx_slab"])
    else:
        add_torsion(c, "SDL", INFO["mx_sdl"]); add_settlements(c); moving_loads(c)
    c.post("/doc/SAVEAS", {"Argument": os.path.join(RUNS, f"{tag}.mcb")})
    t = time.time(); print("  ANAL:", c.post("/doc/ANAL", {"Assign": {}}).get("message"), f"({time.time()-t:.0f}s)")
    elems = [e for e, g, s1, s2, sc in INFO["elems"]]
    r = table(c, "BEAMFORCE", elems, parts=["PartI", "PartJ"])
    if "SS_Table" not in r: print("  결과표 실패", json.dumps(r, ensure_ascii=False)[:200]); return
    names = sorted({row[2] for row in r["SS_Table"]["DATA"]}); print("  BEAMFORCE 행", len(r["SS_Table"]["DATA"]), "하중명", names)
    json.dump(r, open(os.path.join(RUNS, f"{tag}_beamforce.json"), "w", encoding="utf-8"), ensure_ascii=False)
    rr = table(c, "REACTIONG", None, place=2); json.dump(rr, open(os.path.join(RUNS, f"{tag}_reaction.json"), "w", encoding="utf-8"), ensure_ascii=False)
    if "SS_Table" in rr:
        h = rr["SS_Table"]["HEAD"]; tot = {}
        for row in rr["SS_Table"]["DATA"]:
            if row[h.index("Load")].endswith("(all)"): continue
            tot.setdefault(row[h.index("Load")], 0.0); tot[row[h.index("Load")]] += float(row[h.index("FZ")])
        print("  ΣFZ:", {k: round(v, 1) for k, v in tot.items()})
    nodes = [n for g in ("G1", "G2") for n, s in INFO["nodes_G"][g]]
    mv = [n.replace("(max)", "(MV:max)").replace("(min)", "(MV:min)") for n in names if "(max)" in n or "(min)" in n]   # 표 요청 시 이동하중 이름은 (MV:max)
    rd = table(c, "DISPLACEMENTG", nodes, cases=mv or None, place=6)
    json.dump(rd, open(os.path.join(RUNS, f"{tag}_disp.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"  변위표 행 {len(rd.get('SS_Table', {}).get('DATA', []))}  ({time.time()-t0:.0f}s)")

if __name__ == "__main__":
    for tg in (sys.argv[1:] or ["A_steel", "C_comp"]): run(tg)

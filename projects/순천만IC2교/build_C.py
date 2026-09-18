# -*- coding: utf-8 -*-
"""모델 C(합성후 단기): MCT(v4, 이동하중 제외) 불러온 뒤 이동하중은 API JSON으로 정의 → 해석 → BEAMFORCE"""
import sys, os, json, time; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"D:\Midas\core\tools")
from midas_api import Civil
R = r"D:\Midas\projects\순천만IC2교\runs"
INFO = json.load(open(os.path.join(R, "model_info.json"), encoding="utf-8"))
c = Civil(timeout=1800)
def show(tag, r): print(f"  {tag}: {json.dumps(r, ensure_ascii=False)[:160]}")
t0 = time.time()
c.post("/doc/SAVEAS", {"Argument": r"D:\Midas\runs\_scratch.mcb"}); c.post("/doc/NEW", {"Argument": {}})
c.post("/doc/IMPORTMXT", {"Argument": os.path.join(R, "C_v4_noMV.mct")})
nn, ne = c.node_count(), c.elem_count(); print("절점", nn, "요소", ne)
assert (nn, ne) == (INFO["n_nodes"], INFO["n_main"] + INFO["n_xb"])
show("MVCD", c.put("/db/mvcd", {"Assign": {"1": {"CODE": "KOREA"}}}))
lanes = {"Assign": {}}
for li, g in enumerate(("G1", "G2"), start=1):
    ids = [(e, s1) for e, gg, s1, s2, sc in INFO["elems"] if gg == g]
    sup = INFO["sup_s"]
    # 경간 시작(SPAN_START)을 각 지점 직후 요소에 표시 → 충격계수 i=15/(40+L)를 경간별로 자동 산정 (KOREA 코드)
    items = [{"ELEM": e, "ECC": 0, "FACT": 0, "SPAN_START": any(abs(s1 - v) < 1e-3 for v in sup[:-1])} for e, s1 in ids]
    print(f"  {g}: 요소 {len(items)}, 경간시작 표시 {sum(1 for it in items if it['SPAN_START'])}개")
    lanes["Assign"][str(li)] = {"COMMON": {"LL_NAME": f"L{li}", "LOAD_DIST": "LANE", "GROUP_NAME": "", "SKEW_START": 0, "SKEW_END": 0,
                                           "MOVING": "BOTH", "WHEEL_SPACE": 1.8, "WIDTH": 3, "OPT_AUTO_LANE": False, "ALLOW_WIDTH": 0},
                                "LANE_ITEMS": items}
c.put("/db/llan", lanes); print("  차선:", len(c.get("/db/llan")["LLAN"]))
veh = {"Assign": {}}
for i, nm in enumerate(("DB-24", "DL-24"), start=1):
    veh["Assign"][str(i)] = {"MVLD_CODE": 6, "VEHICLE_LOAD_NAME": nm, "VEHICLE_LOAD_NUM": 1, "VEHICLE_TYPE_NAME": nm,
                             "STANDARD_CODE": "KS-RB", "VEH_DEFAULT": {"DYN_LOAD_ALLOWANCE": 0, "CENT_F": False}}
show("MVHL", c.put("/db/mvhl", veh)); print("  차량:", list(v["VEHICLE_LOAD_NAME"] for v in c.get("/db/mvhl").get("MVHL", {}).values()))
def case(cid, nm):
    d = {"LCNAME": nm, "DESC": "", "TYPE": 0, "DEFAULT": {"SCALE_FACTORS": [1, 1, 0.9, 0.75, 0.75, 0.75], "COMB_OPTION": "INDEPENDENT",
         "LANE_FACTOR_TYPE": 1, "_2_LANE_FACTOR_1": 1, "_2_LANE_FACTOR_2": 1, "_3_LANE_FACTOR_1": 1, "_3_LANE_FACTOR_2": 0.5, "_3_LANE_FACTOR_3": 0.5, "_3_LANE_FACTOR_4": 0.25,
         "SUB_LOAD_DATAS": [{"VEHICLE_TYPE": "VL", "VEHICLE_NAME": nm, "SCALE_FACTOR": 1, "MIN_LOADED_LANE": 1, "MAX_LOADED_LANE": 2, "LANE_NAMES": ["L1", "L2"]}]}}
    return {str(cid): d}
r = c.put("/db/mvld", {"Assign": {**case(1, "DB-24"), **case(2, "DL-24")}}); show("MVLD", r)
if "error" in r:   # 차선계수 키 없이 재시도
    for k in list(r):
        pass
    body = {"Assign": {**case(1, "DB-24"), **case(2, "DL-24")}}
    for v in body["Assign"].values():
        for key in [k for k in v["DEFAULT"] if k.startswith("_")]: v["DEFAULT"].pop(key)
    show("MVLD(재시도)", c.put("/db/mvld", body))
print("  이동하중 케이스:", [v["LCNAME"] for v in c.get("/db/mvld").get("MVLD", {}).values()])
show("SAVEAS", c.post("/doc/SAVEAS", {"Argument": os.path.join(R, "C_compn.mcb")}))
t = time.time(); show("ANAL", c.post("/doc/ANAL", {"Assign": {}})); print(f"  해석 {time.time()-t:.0f}s")
elems = [e for e, g, s1, s2, sc in INFO["elems"]]
r = c.post("/post/table", {"Argument": {"TABLE_NAME": "SS_Table", "TABLE_TYPE": "BEAMFORCE", "UNIT": {"FORCE": "KN", "DIST": "M"},
                                        "STYLES": {"FORMAT": "Fixed", "PLACE": 3}, "NODE_ELEMS": {"KEYS": elems}, "PARTS": ["PartI", "PartJ"]}})
if "SS_Table" in r:
    names = sorted({row[2] for row in r["SS_Table"]["DATA"]}); print("  BEAMFORCE 행", len(r["SS_Table"]["DATA"]), "하중명", names)
    json.dump(r, open(os.path.join(R, "C_compn_beamforce.json"), "w", encoding="utf-8"), ensure_ascii=False)
else:
    print("  결과표:", json.dumps(r, ensure_ascii=False)[:300])
c.post("/doc/EXPORTMXT", {"Argument": os.path.join(R, "C_compn_export.mct")})
print(f"총 {time.time()-t0:.0f}s")

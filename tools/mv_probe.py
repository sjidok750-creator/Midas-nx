# -*- coding: utf-8 -*-
"""이동하중을 JSON으로 정의해 보고, CIVIL NX가 내보낸 MCT에서 NX 문법을 얻는다"""
import sys, os, json; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"D:\Midas\tools")
from midas_api import Civil
R = r"D:\Midas\projects\순천만IC2교\runs"
INFO = json.load(open(os.path.join(R, "model_info.json"), encoding="utf-8"))
c = Civil(timeout=300)
def show(tag, r): print(f"  {tag}: {json.dumps(r, ensure_ascii=False)[:400]}")
c.post("/doc/SAVEAS", {"Argument": r"D:\Midas\runs\_scratch.mcb"}); c.post("/doc/NEW", {"Argument": {}})
c.post("/doc/IMPORTMXT", {"Argument": os.path.join(R, "C_v4_noMV.mct")})
print("절점", c.node_count(), "요소", c.elem_count())
show("MVCD", c.put("/db/mvcd", {"Assign": {"1": {"CODE": "KOREA"}}}))
lanes = {"Assign": {}}
for li, g in enumerate(("G1", "G2"), start=1):
    ids = [e for e, gg, s1, s2, sc in INFO["elems"] if gg == g]
    lanes["Assign"][str(li)] = {"COMMON": {"LL_NAME": f"L{li}", "LOAD_DIST": "LANE", "GROUP_NAME": "", "SKEW_START": 0, "SKEW_END": 0,
                                           "MOVING": "BOTH", "WHEEL_SPACE": 1.8, "WIDTH": 3, "OPT_AUTO_LANE": False, "ALLOW_WIDTH": 0},
                                "LANE_ITEMS": [{"ELEM": e, "ECC": 0, "FACT": 0, "SPAN_START": (k == 0)} for k, e in enumerate(ids)]}
show("LLAN PUT", c.put("/db/llan", lanes))
g = c.get("/db/llan"); print("  LLAN GET 차선 수:", len(g.get("LLAN", {})), "| 키:", list(g.get("LLAN", {}).get("1", {}).keys()))
# 차량: 키 추정 시도
tries = {
 "v1": {"VEHICLE_LOAD_NAME": "DB-24", "VEHICLE_LOAD_NUM": 1, "STANDARD_CODE": "KS-RB", "VEHICLE_TYPE_NAME": "DB-24"},
 "v2": {"MVLD_CODE": 2, "VEHICLE_LOAD_NAME": "DB-24", "VEHICLE_LOAD_NUM": 1, "STANDARD_CODE": "KS-RB", "VEHICLE_TYPE_NAME": "DB-24"},
 "v3": {"MVLD_CODE": 1, "VEHICLE_LOAD_NAME": "DB-24", "VEHICLE_LOAD_NUM": 1, "STANDARD_CODE": "KS-RB", "VEHICLE_TYPE_NAME": "DB-24"},
}
for k, body in tries.items():
    try: show(f"MVHL {k}", c.put("/db/mvhl", {"Assign": {"1": body}}))
    except Exception as e: print(f"  MVHL {k}: 오류 {str(e)[:300]}")
    g = c.get("/db/mvhl"); print("     GET MVHL:", json.dumps(g, ensure_ascii=False)[:300])
    if g.get("MVHL"): break
out = os.path.join(R, "C_probe_export.mct")
show("EXPORT", c.post("/doc/EXPORTMXT", {"Argument": out}))
print("exported:", os.path.exists(out), os.path.getsize(out) if os.path.exists(out) else 0)

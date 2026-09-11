# -*- coding: utf-8 -*-
"""5m 보: 저장 → 해석 → 반력/부재력/변위 표 추출"""
import sys, json, time, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\Midas\tools")
from midas_api import Civil

c = Civil(timeout=300)
OUT = r"D:\Midas\runs\5m_beam"
os.makedirs(OUT, exist_ok=True)
MCB = os.path.join(OUT, "RC_Beam_5m.mcb")
LC = ["SELFWEIGHT(ST)", "POINT(ST)", "ALL(CB)"]

t = time.time()
print("SAVEAS:", json.dumps(c.post("/doc/SAVEAS", {"Argument": MCB}), ensure_ascii=False)[:200])
print("ANAL:", json.dumps(c.post("/doc/ANAL", {"Assign": {}}), ensure_ascii=False)[:300], f"({time.time()-t:.1f}s)")

def table(ttype, extra=None, name=None):
    arg = {"TABLE_NAME": "SS_Table", "TABLE_TYPE": ttype,
           "UNIT": {"FORCE": "KN", "DIST": "M"},
           "STYLES": {"FORMAT": "Fixed", "PLACE": 4},
           "LOAD_CASE_NAMES": LC}
    if extra:
        arg.update(extra)
    r = c.post("/post/table", {"Argument": arg})
    with open(os.path.join(OUT, (name or ttype) + ".json"), "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
    return r

def show(r, n=60):
    if "SS_Table" not in r:
        print("  응답:", json.dumps(r, ensure_ascii=False)[:400]); return
    tb = r["SS_Table"]
    print("  HEAD:", tb.get("HEAD"))
    for row in tb.get("DATA", [])[:n]:
        print("  ", row)

print("== 반력 REACTIONG (절점 2, 50)")
show(table("REACTIONG", {"NODE_ELEMS": {"KEYS": [2, 50]}}))
print("== 부재력 BEAMFORCE (요소 2, 25, 26, 49)")
show(table("BEAMFORCE", {"NODE_ELEMS": {"KEYS": [2, 25, 26, 49]}, "PARTS": ["PartI", "PartJ"]}))
print("== 변위 DISPLACEMENTG (절점 26)")
show(table("DISPLACEMENTG", {"NODE_ELEMS": {"KEYS": [26]}}))

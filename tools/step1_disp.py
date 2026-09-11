# -*- coding: utf-8 -*-
import sys, json; sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\Midas\tools")
from midas_api import Civil
c = Civil(timeout=120)
r = c.post("/post/table", {"Argument": {"TABLE_NAME": "SS_Table", "TABLE_TYPE": "DISPLACEMENTG",
     "UNIT": {"FORCE": "KN", "DIST": "M"}, "STYLES": {"FORMAT": "Scientific", "PLACE": 5},
     "NODE_ELEMS": {"KEYS": [26]}, "LOAD_CASE_NAMES": ["SELFWEIGHT(ST)", "POINT(ST)", "ALL(CB)"]}})
for row in r["SS_Table"]["DATA"]: print("  MIDAS", row[2], "DZ =", row[5])
E=25.811e6; I=0.6*1.0**3/12; L=4.8; P=5.0; w=14.71
dP = P*L**3/(192*E*I); dw = w*L**4/(384*E*I)
print(f"  손계산  POINT DZ = -{dP:.5e} | SELFWEIGHT DZ = -{dw:.5e} | ALL = -{dP+dw:.5e}   (EI={E*I:.0f} kN·m², I={I:.3f} m⁴)")

# -*- coding: utf-8 -*-
import sys, json; sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\Midas\tools")
from midas_api import Civil
c = Civil()
mct = r"D:\Midas\_이전세션_산출물_20260909\RC_Beam_5m.mct"
print("IMPORT:", json.dumps(c.post("/doc/IMPORTMXT", {"Argument": mct}), ensure_ascii=False)[:300])
print("단위:", json.dumps(c.units(), ensure_ascii=False))
print("절점:", c.node_count(), "| 요소:", c.elem_count())
for ep in ("/db/MATL", "/db/SECT", "/db/CONS", "/db/CNLD", "/db/STLD", "/db/LCOM"):
    try:
        d = c.get(ep); print(ep, "=>", json.dumps(d, ensure_ascii=False)[:600])
    except Exception as e:
        print(ep, "실패:", str(e)[:200])

# -*- coding: utf-8 -*-
import sys, json; sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\Midas\tools")
from midas_api import Civil
c = Civil(timeout=20)
for ep in ("/config/ver", "/ope/PROJECTSTATUS"):
    try: print(ep, "=>", json.dumps(c.get(ep), ensure_ascii=False)[:300])
    except Exception as e: print(ep, "실패:", str(e)[:160])
try:
    r = c.post("/post/table", {"Argument": {"TABLE_NAME": "SS_Table", "TABLE_TYPE": "REACTIONG",
        "UNIT": {"FORCE": "KN", "DIST": "M"}, "NODE_ELEMS": {"KEYS": [2, 50]}, "LOAD_CASE_NAMES": ["SELFWEIGHT(ST)", "POINT(ST)"]}})
    print("REACTIONG =>", json.dumps(r, ensure_ascii=False)[:700])
except Exception as e: print("REACTIONG 실패:", str(e)[:200])

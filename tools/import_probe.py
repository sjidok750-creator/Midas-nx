# -*- coding: utf-8 -*-
"""MCT 여러 개를 차례로 새 문서에 불러와 절점/요소 수만 확인 (파싱 실패 원인 분리용)"""
import sys, os; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"D:\Midas\tools")
from midas_api import Civil
c = Civil(timeout=300)
scratch = r"D:\Midas\runs\_scratch.mcb"; os.makedirs(os.path.dirname(scratch), exist_ok=True)
for f in sys.argv[1:]:
    c.post("/doc/SAVEAS", {"Argument": scratch}); c.post("/doc/NEW", {"Argument": {}})
    c.post("/doc/IMPORTMXT", {"Argument": f})
    print(f"{os.path.basename(f):28s} 절점 {c.node_count():4d} 요소 {c.elem_count():4d}")

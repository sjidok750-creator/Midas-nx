# -*- coding: utf-8 -*-
"""격자모델 평면도 PNG: python plot_plan.py <runs폴더> <mct파일명> <출력png>"""
import json, os, sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["Malgun Gothic"]; plt.rcParams["axes.unicode_minus"] = False
R, mct, out = sys.argv[1], sys.argv[2], sys.argv[3]
INFO = json.load(open(os.path.join(R, "model_info.json"), encoding="utf-8"))
nodes, elems, grab = {}, [], None
for line in open(os.path.join(R, mct), encoding="utf-8"):
    if line.startswith("*NODE"): grab = "N"; continue
    if line.startswith("*ELEMENT"): grab = "E"; continue
    if line.startswith("*"): grab = None
    if grab and line.strip() and not line.startswith(";"):
        p = [x.strip() for x in line.split(",")]
        if grab == "N": nodes[int(p[0])] = (float(p[1]), float(p[2]))
        else: elems.append((int(p[0]), int(p[4]), int(p[5])))
fig, ax = plt.subplots(figsize=(16, 5))
main = set(e for e, g, s1, s2, sc in INFO["elems"])
for e, n1, n2 in elems:
    a, b = nodes[n1], nodes[n2]
    ax.plot([a[0], b[0]], [a[1], b[1]], color=("tab:blue" if e in main else "gray"), lw=(1.8 if e in main else 0.8))
for lb, s in zip(["A1", "P1", "P2", "P3", "P4", "P5"], INFO["sup_s"]):
    j = min(range(len(INFO["nodes_G"]["G1"])), key=lambda k: abs(INFO["nodes_G"]["G1"][k][1] - s))
    a, b = nodes[INFO["nodes_G"]["G1"][j][0]], nodes[INFO["nodes_G"]["G2"][j][0]]
    ax.plot([a[0], b[0]], [a[1], b[1]], "k^", ms=9); ax.annotate(lb, ((a[0]+b[0])/2, max(a[1], b[1]) + 1.5), ha="center", fontsize=12, weight="bold")
g1, g2 = nodes[INFO["nodes_G"]["G1"][0][0]], nodes[INFO["nodes_G"]["G2"][0][0]]
ax.annotate("G1", (g1[0]-3, g1[1]), ha="right", color="tab:blue", fontsize=11); ax.annotate("G2", (g2[0]-3, g2[1]), ha="right", color="tab:blue", fontsize=11)
ax.set_aspect("equal"); ax.grid(alpha=.3); ax.set_xlabel("X (m) → 종점 방향"); ax.set_ylabel("Y (m)")
ax.set_title(f"평면 — {mct} (삼각형: 지점, 회색: 가로보 {len(elems)-len(main)}개)")
fig.savefig(out, dpi=110, bbox_inches="tight"); print("saved", out, "| 가로보", len(elems) - len(main))

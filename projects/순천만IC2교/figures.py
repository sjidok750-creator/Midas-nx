# -*- coding: utf-8 -*-
"""
5장 그림 생성 (matplotlib → PNG, runs/fig/)
  fig_section.png     검토단면(횡단면 개략도)          ← 제원서(폭원·박스 폭·H·바닥판)
  fig_girder_top.png  거더 일반도(경간·상판 두께·검토단면) ← gen_model.plate_segments/geometry
  fig_girder_bot.png  거더 일반도(하판 두께)
  fig_model_plan.png  격자 모델 평면도                   ← runs/C_comp.mct, model_info.json
  fig_diagrams.png    G1 휨모멘트도·전단력도(합성전 사하중, 합성후 사하중, 활하중 포락) ← runs/*_beamforce.json
동일 형식(강박스 격자)의 다음 교량에서도 gen_model·runs 산출물만 있으면 그대로 사용.
"""
import sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
PJ = r"D:\Midas\projects\순천만IC2교"; RUNS = os.path.join(PJ, "runs"); FIG = os.path.join(RUNS, "fig")
sys.path.insert(0, r"D:\Midas\tools"); sys.path.insert(0, PJ)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["Malgun Gothic"]; plt.rcParams["axes.unicode_minus"] = False
import gen_model as G
INFO = json.load(open(os.path.join(RUNS, "model_info.json"), encoding="utf-8"))
os.makedirs(FIG, exist_ok=True)
SUP = ["A1", "P1", "P2", "P3", "P4", "P5"]

def fig_section():
    """횡단면 개략도: 폭원 8.670 = 1.200 + 2.000 + 2.270 + 2.000 + 1.200, H 2.300, 바닥판 0.24 + 헌치 0.06"""
    W = 8.670; wall = 1.200; bw = 2.000; gap = 2.270; H = 2.300; tc = 0.24; th = 0.06
    fig, ax = plt.subplots(figsize=(10, 6.2)); ax.set_aspect("equal"); ax.axis("off")
    x0 = 0.0; y0 = 0.0                                       # 바닥판 상면 = y0
    # 바닥판 (캔틸레버 단부 0.30 → 주형 위 0.30, 내측 0.24)
    xs = [x0, x0 + W, x0 + W, x0 + wall + bw + gap, x0 + wall + bw + gap - 0.0, x0 + wall + bw, x0 + wall + bw, x0 + wall, x0 + wall - 0.0, x0]
    ax.plot([x0, x0 + W], [y0, y0], "k", lw=1.5)
    ax.plot([x0, x0 + wall + bw + gap + bw + wall], [y0 - tc - th, y0 - tc - th], "k", lw=1.5)
    for xb in (x0 + wall, x0 + wall + bw + gap):             # 박스 2련
        ax.add_patch(plt.Rectangle((xb, y0 - tc - th - H), bw, H, fill=False, lw=1.8))
        for k in range(1, 6): ax.plot([xb + bw * k / 6] * 2, [y0 - tc - th - 0.02, y0 - tc - th - 0.17], "k", lw=1)   # 상부 종리브 5
        for k in range(1, 3): ax.plot([xb + bw * k / 3] * 2, [y0 - tc - th - H + 0.02, y0 - tc - th - H + 0.17], "k", lw=1)  # 하부 종리브 2
    for xw, sgn in ((x0, 1), (x0 + W, -1)):                  # 방호벽
        ax.add_patch(plt.Polygon([(xw, y0), (xw + sgn * 0.45, y0), (xw + sgn * 0.30, y0 + 0.35), (xw + sgn * 0.23, y0 + 1.32), (xw, y0 + 1.32)], fill=False, lw=1.5))
    ax.plot([x0, x0 + W], [y0 - tc - th - H - 0.35, y0 - tc - th - H - 0.35], "k", lw=0.6)
    def dim(x1, x2, y, txt, off=0.12):
        ax.annotate("", (x1, y), (x2, y), arrowprops=dict(arrowstyle="<->", lw=0.8)); ax.text((x1 + x2) / 2, y + off, txt, ha="center", va="bottom", fontsize=10)
    yd = y0 - tc - th - H - 0.9
    dim(x0, x0 + wall, yd, "1.200"); dim(x0 + wall, x0 + wall + bw, yd, "2.000"); dim(x0 + wall + bw, x0 + wall + bw + gap, yd, "2.270")
    dim(x0 + wall + bw + gap, x0 + wall + 2 * bw + gap, yd, "2.000"); dim(x0 + wall + 2 * bw + gap, x0 + W, yd, "1.200"); dim(x0, x0 + W, yd - 0.7, "8.670")
    dim(x0, x0 + 1.95, y0 + 1.9, "1.950"); dim(x0 + 1.95, x0 + W, y0 + 1.9, "6.720"); ax.text(x0 + 1.95, y0 + 2.5, "C of ROAD", ha="center", fontsize=10)
    ax.plot([x0 + 1.95] * 2, [y0 - tc - th - H - 0.3, y0 + 2.4], "k-.", lw=0.7)
    ax.annotate("", (x0 + W + 0.5, y0 - tc - th), (x0 + W + 0.5, y0 - tc - th - H), arrowprops=dict(arrowstyle="<->", lw=0.8)); ax.text(x0 + W + 0.62, y0 - tc - th - H / 2, "2.300", rotation=90, va="center", fontsize=10)
    ax.annotate("", (x0 + W + 0.5, y0), (x0 + W + 0.5, y0 - tc - th), arrowprops=dict(arrowstyle="<->", lw=0.8)); ax.text(x0 + W + 0.62, y0 - (tc + th) / 2, "0.300", va="center", fontsize=9)
    ax.text(x0 + wall + bw / 2, y0 - tc - th - H / 2, "G1", ha="center", va="center", fontsize=13, weight="bold"); ax.text(x0 + wall + bw + gap + bw / 2, y0 - tc - th - H / 2, "G2", ha="center", va="center", fontsize=13, weight="bold")
    ax.text(x0 + W / 2, y0 + 3.1, "검토단면 (S3 경간 중앙, 정모멘트부 : 상부 종리브 5 · 하부 종리브 2)", ha="center", fontsize=10)
    ax.set_xlim(x0 - 0.5, x0 + W + 1.3); ax.set_ylim(yd - 1.2, y0 + 3.5)
    fig.savefig(os.path.join(FIG, "fig_section.png"), dpi=150, bbox_inches="tight"); plt.close(fig)

def fig_girder(which):
    """거더 일반도 스트립: 상단 경간·지점, 중단 판두께 구간(mm), 하단 검토단면 SP 위치"""
    segs = G.plate_segments(which); L = INFO["total"]; sup = INFO["sup_s"]
    fig, ax = plt.subplots(figsize=(16, 2.6)); ax.axis("off")
    ax.plot([0, L], [0, 0], "k", lw=2.5)
    for lb, s in zip(SUP, sup): ax.plot(s, -0.08, "k^", ms=10); ax.text(s, -0.32, lb, ha="center", fontsize=10, weight="bold")
    for i in range(5): ax.text((sup[i] + sup[i + 1]) / 2, 0.12, f"{(sup[i+1]-sup[i])*1000:,.0f}", ha="center", fontsize=9)
    ax.annotate("", (0, 0.5), (L, 0.5), arrowprops=dict(arrowstyle="<->", lw=0.7)); ax.text(L / 2, 0.55, f"거더 길이 {L*1000:,.0f}", ha="center", fontsize=9)
    y = 0.95
    for a, b, t in segs:
        ax.plot([a, b], [y, y], "k", lw=1); ax.plot([a, a], [y - 0.06, y + 0.06], "k", lw=0.8); ax.plot([b, b], [y - 0.06, y + 0.06], "k", lw=0.8)
        if b - a < 9.0: ax.text((a + b) / 2, y + 0.08, f"{(b-a)*1000:.0f} ({t*1000:.0f})", ha="center", va="bottom", fontsize=6.5, rotation=90)
        else: ax.text((a + b) / 2, y + 0.08, f"{(b-a)*1000:.0f}", ha="center", fontsize=7); ax.text((a + b) / 2, y - 0.2, f"({t*1000:.0f}mm)", ha="center", fontsize=7)
    ax.text(-2, y, "상판" if which == "top" else "하판", ha="right", va="center", fontsize=10)
    ax.text(-2, 0, "경간", ha="right", va="center", fontsize=10)
    ax.text(L + 2, y, "(mm)", fontsize=7, va="center"); ax.set_xlim(-8, L + 3); ax.set_ylim(-0.5, 1.75)
    fig.savefig(os.path.join(FIG, f"fig_girder_{which}.png"), dpi=150, bbox_inches="tight"); plt.close(fig)

def fig_model_plan():
    nodes, elems, grab = {}, [], None
    for line in open(INFO["models"]["C_comp"], encoding="utf-8"):
        if line.startswith("*NODE"): grab = "N"; continue
        if line.startswith("*ELEMENT"): grab = "E"; continue
        if line.startswith("*"): grab = None
        if grab and line.strip() and not line.startswith(";"):
            p = [x.strip() for x in line.split(",")]
            if grab == "N": nodes[int(p[0])] = (float(p[1]), float(p[2]))
            else: elems.append((int(p[0]), int(p[4]), int(p[5])))
    fig, ax = plt.subplots(figsize=(16, 4)); ax.set_aspect("equal"); ax.axis("off")
    main = {e for e, g, s1, s2, sc in INFO["elems"]}
    for e, n1, n2 in elems:
        a, b = nodes[n1], nodes[n2]; ax.plot([a[0], b[0]], [a[1], b[1]], color=("k" if e in main else "0.55"), lw=(1.6 if e in main else 0.7))
    for lb, s in zip(SUP, INFO["sup_s"]):
        j = min(range(len(INFO["nodes_G"]["G1"])), key=lambda k: abs(INFO["nodes_G"]["G1"][k][1] - s))
        a, b = nodes[INFO["nodes_G"]["G1"][j][0]], nodes[INFO["nodes_G"]["G2"][j][0]]
        ax.plot([a[0], b[0]], [a[1], b[1]], "k^", ms=9); ax.annotate(lb, ((a[0] + b[0]) / 2, max(a[1], b[1]) + 2.0), ha="center", fontsize=12, weight="bold")
    a = nodes[INFO["nodes_G"]["G1"][0][0]]; b = nodes[INFO["nodes_G"]["G2"][0][0]]
    ax.text(a[0] - 3, a[1], "G1", ha="right", va="center", fontsize=11, weight="bold"); ax.text(b[0] - 3, b[1], "G2", ha="right", va="center", fontsize=11, weight="bold")
    ax.text(nodes[INFO["nodes_G"]["G1"][-1][0]][0] / 2, min(v[1] for v in nodes.values()) - 6,
            f"절점 {INFO['n_nodes']}개, 주형 요소 {INFO['n_main']}개(단면 {INFO['n_sections']}종), 가로보 {INFO['n_xb']}개 (5 m 간격 + 지점), 받침 12개 (P3 고정)", ha="center", fontsize=10)
    ys = [v[1] for v in nodes.values()]; ax.set_ylim(min(ys) - 9, max(ys) + 5)
    fig.savefig(os.path.join(FIG, "fig_model_plan.png"), dpi=150, bbox_inches="tight"); plt.close(fig)

def fig_diagrams(g="G1"):
    """휨모멘트도·전단력도 (요소 I/J 값을 s 좌표에 배치)"""
    A = json.load(open(os.path.join(RUNS, "A_steel_beamforce.json"), encoding="utf-8"))["SS_Table"]["DATA"]
    C = json.load(open(os.path.join(RUNS, "C_comp_beamforce.json"), encoding="utf-8"))["SS_Table"]["DATA"]
    es = {e: (s1, s2) for e, gg, s1, s2, sc in INFO["elems"] if gg == g}
    def series(rows, loads, col):
        out = {}
        for r in rows:
            e = int(r[1])
            if e not in es or r[2] not in loads: continue
            s = es[e][0] if r[3].startswith("I") else es[e][1]
            out.setdefault(s, 0.0); out[s] += float(r[col])
        xs = sorted(out); return xs, [out[x] for x in xs]
    def env(rows, names, col, fn):
        out = {}
        for r in rows:
            e = int(r[1])
            if e not in es or r[2] not in names: continue
            s = es[e][0] if r[3].startswith("I") else es[e][1]; v = float(r[col])
            out[s] = fn(out.get(s, v), v)
        xs = sorted(out); return xs, [out[x] for x in xs]
    fig, axs = plt.subplots(2, 1, figsize=(16, 7), sharex=True)
    for ax, col, ttl, unit in ((axs[0], 8, "휨모멘트도", "kN·m"), (axs[1], 6, "전단력도", "kN")):
        x1, y1 = series(A, {"DEAD", "SLAB"}, col); ax.plot(x1, y1, "k-", lw=1.2, label="합성전 사하중 (강재+슬래브)")
        x2, y2 = series(C, {"SDL"}, col); ax.plot(x2, y2, "b-", lw=1.0, label="합성후 사하중")
        xm, ym = env(C, {"DB-24(max)", "DL-24(max)"}, col, max); xn, yn = env(C, {"DB-24(min)", "DL-24(min)"}, col, min)
        ax.fill_between(xm, ym, [0] * len(ym), color="tab:red", alpha=0.25, label="활하중 max (DB/DL-24 포락)"); ax.fill_between(xn, yn, [0] * len(yn), color="tab:green", alpha=0.25, label="활하중 min")
        ax.axhline(0, color="k", lw=0.6)
        for lb, s in zip(SUP, INFO["sup_s"]): ax.axvline(s, color="0.6", lw=0.6, ls="--"); ax.text(s, 1.01, lb, ha="center", fontsize=9, weight="bold", transform=ax.get_xaxis_transform())
        if col == 8: ax.invert_yaxis()
        ax.set_ylabel(f"{ttl} ({unit})"); ax.grid(alpha=0.3); ax.legend(loc="lower right" if col == 8 else "upper right", fontsize=8, ncol=2)
    axs[1].set_xlabel("거더 축 거리 s (m)  A1 → P5"); axs[0].set_title(f"{g} 부재력도 (부호: MIDAS Moment-y, 정모멘트 아래쪽)", fontsize=11, pad=18)
    fig.savefig(os.path.join(FIG, "fig_diagrams.png"), dpi=150, bbox_inches="tight"); plt.close(fig)

if __name__ == "__main__":
    fig_section(); fig_girder("top"); fig_girder("bot"); fig_model_plan(); fig_diagrams()
    print("저장:", FIG, os.listdir(FIG))

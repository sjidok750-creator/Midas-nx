# -*- coding: utf-8 -*-
"""하부구조 보고서 삽도: P–M 상관도, 말뚝 배치·반력, 교각 하중 재하도 (runs/pier3/<P>_result.json, runs/abutment/A1_v3_result.json → png/report/*.png)"""
import sys, os, json, math
sys.stdout.reconfigure(encoding="utf-8")
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["Malgun Gothic"]; plt.rcParams["axes.unicode_minus"] = False
PJ = r"D:\Midas\projects\순천만IC2교"; RUNS = os.path.join(PJ, "runs"); OUT = os.path.join(PJ, "png", "report"); os.makedirs(OUT, exist_ok=True)

def pm_diagram(name="P3"):
    r = json.load(open(os.path.join(RUNS, "pier3", f"{name}_result.json"), encoding="utf-8")); col = r["column"]
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.6))
    for ax, dirn, lab in zip(axs, ("x", "y"), ("교축 방향 휨 (My, 깊이 2.5 m)", "교축직각 방향 휨 (Mx, 깊이 3.0 m)")):
        pts = sorted(col[f"cap_{dirn}"], key=lambda t: t[1]); Ps = [p for p, m in col[f"cap_{dirn}"]]; Ms = [m for p, m in col[f"cap_{dirn}"]]
        ax.plot(Ms, Ps, "b-", lw=1.5, label="φPn–φMn (φ=0.70)")
        cs = [c for c in col["cases"] if c["dirn"] == dirn]
        ax.scatter([c["Mmag"] for c in cs], [c["P"] for c in cs], s=14, c="r", label="계수하중 조합 (δs·Mu, Pu)")
        w = max(cs, key=lambda c: c["ratio"]); ax.annotate(f"최대 {w['ratio']:.2f}\n{w['key']}", (w["Mmag"], w["P"]), textcoords="offset points", xytext=(8, -18), fontsize=7)
        ax.set_xlabel("M (kN·m)"); ax.set_ylabel("P (kN)"); ax.set_title(f"{name} 기둥 {lab}", fontsize=10); ax.grid(alpha=0.3); ax.legend(fontsize=8); ax.set_xlim(left=0); ax.set_ylim(bottom=0)
    fig.suptitle(f"주철근 {r['rebar'].get('기둥_주철근', '')} (As = {col['As']:,.0f} mm², ρ = {col['rho']*100:.2f} %)", fontsize=9)
    fig.tight_layout(); p = os.path.join(OUT, f"{name}_PM.png"); fig.savefig(p, dpi=150); plt.close(fig); return p

def pile_layout(name="P3"):
    r = json.load(open(os.path.join(RUNS, "pier3", f"{name}_result.json"), encoding="utf-8")); pl = r["piles"]; g = r["geom"]; f = r["footing"]
    L, B, tf = g["foot"]; fig, ax = plt.subplots(figsize=(6.5, 6.5)); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(plt.Rectangle((-L / 2, -B / 2), L, B, fill=False, lw=1.8)); ax.add_patch(plt.Rectangle((-g["bx"] / 2, -g["by"] / 2), g["bx"], g["by"], fill=False, lw=1.2, ls="--"))
    key = f["pile_max_key"]; c = next(x for x in r["combos"] if x["key"] == key); n = pl["n"]
    vals = []
    for x in pl["xs"]:
        for y in pl["ys"]:
            R = c["Pf"] / n + c["Myf"] * x / pl["Sx2"] + c["Mxf"] * y / pl["Sy2"]; vals.append(R)
            ax.add_patch(plt.Circle((x, y), 0.254, fill=True, facecolor="#dde", edgecolor="k", lw=0.8)); ax.text(x, y, f"{R:.0f}", ha="center", va="center", fontsize=6)
    ax.text(0, B / 2 + 0.35, f"{name} 말뚝 배치 ({n}본, Ø508) — 반력 kN/본, 조합: {key}", ha="center", fontsize=8)
    ax.text(0, -B / 2 - 0.4, f"X 교축 →, 기초 {L}×{B}×{tf} m, 최대 {max(vals):.0f} / 최소 {min(vals):.0f} kN (허용 {f['Ra']:.0f})", ha="center", fontsize=8)
    ax.set_xlim(-L / 2 - 0.6, L / 2 + 0.6); ax.set_ylim(-B / 2 - 0.8, B / 2 + 0.8)
    p = os.path.join(OUT, f"{name}_piles.png"); fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); return p

def load_diagram(name="P3"):
    """편람 [단계 5-1] 형식: 코핑 위 받침 위치에 하중 화살표·수치 (고정/활하중 만재/편재 G1/편재 G2)"""
    r = json.load(open(os.path.join(RUNS, "pier3", f"{name}_result.json"), encoding="utf-8")); g = r["geom"]
    RX = json.load(open(os.path.join(RUNS, "reactions_summary.json"), encoding="utf-8"))["support"][name]; hb = g["s_brg"] / 2
    sets = [("고정하중 (kN)", (RX["D_g"]["G1"], RX["D_g"]["G2"])), ("활하중 만재 (kN)", (RX["L_g"]["G1"][0], RX["L_g"]["G2"][0])),
            ("활하중 편재 L1 (kN)", (RX["L_one"]["L1"]["G1"], RX["L_one"]["L1"]["G2"])), ("활하중 편재 L2 (kN)", (RX["L_one"]["L2"]["G1"], RX["L_one"]["L2"]["G2"]))]
    fig, axs = plt.subplots(1, 4, figsize=(12, 3.6))
    for ax, (title, (v1, v2)) in zip(axs, sets):
        ax.axis("off"); ax.set_aspect("equal"); ax.plot([-g["cop_top"] / 2, g["cop_top"] / 2], [0, 0], "k-", lw=2); ax.plot([0, 0], [0, -4], "k-", lw=2)
        for x, v in ((hb, v1), (-hb, v2)):
            ax.annotate("", (x, 0.05), (x, 1.6), arrowprops=dict(arrowstyle="->", lw=1.4)); ax.text(x, 1.75, f"{v:,.1f}", ha="center", fontsize=8)
        ax.text(hb, -0.45, "G1", ha="center", fontsize=8); ax.text(-hb, -0.45, "G2", ha="center", fontsize=8); ax.set_title(title, fontsize=9); ax.set_xlim(-4, 4); ax.set_ylim(-4.3, 2.4)
    p = os.path.join(OUT, f"{name}_loads.png"); fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); return p

if __name__ == "__main__":
    for n in (sys.argv[1:] or ["P3"]): print(pm_diagram(n), pile_layout(n), load_diagram(n))

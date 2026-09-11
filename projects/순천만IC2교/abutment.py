# -*- coding: utf-8 -*-
"""
교대 안전성 계산 툴 (역T형·말뚝기초) — 도로교설계기준(2010) 하중조합, 도로설계요령(2002) 교대 설계 절차
  입력 : 하부_제원서.json(A1), runs/reactions_summary.json(상부반력), combos_2010.json
  방법 : 단위폭(1 m) 안정검토(Rankine 토압) + 벽체·흉벽 단면력(Coulomb 토압) + 말뚝 반력(강체 캡, 열 배치) + 지진시(Mononobe–Okabe)
  하중 CASE (2021 양식) : 1 시공시(자중+토압+상재), 2 고정하중 재하, 3 활하중 재하, 4 지진시
  출력 : runs/abutment/A1_result.json, runs/결과_교대.md, runs/abutment/A1_section.png(개략도)
  주의 : 뒷채움 토질정수·말뚝 지반지지력·배근은 자료 없음 → 표준값/확인 필요 표시. 형상 블록은 GEOM 에서 편집
"""
import sys, os, json, math
sys.stdout.reconfigure(encoding="utf-8")
PJ = r"D:\Midas\projects\순천만IC2교"; RUNS = os.path.join(PJ, "runs"); OUT = os.path.join(RUNS, "abutment"); os.makedirs(OUT, exist_ok=True)
SUB = json.load(open(os.path.join(PJ, "하부_제원서.json"), encoding="utf-8")); A = SUB["교대"]["A1"]
RX = json.load(open(os.path.join(RUNS, "reactions_summary.json"), encoding="utf-8"))["support"]["A1"]
CB = json.load(open(os.path.join(PJ, "combos_2010.json"), encoding="utf-8"))
GC = SUB["재료"]["gamma_c"]; FCK, FY = SUB["재료"]["fck_구체"], SUB["재료"]["fy"]
# ── 형상 (m). x: 기초 앞단(toe) 0 → 뒷채움 쪽 +, z: 기초 저면 0 → 상향. 준공도면 교대 일반도(1) 단면 A-A ──
Bf, tf = A["기초폭"], A["기초두께"]                     # 5.6, 1.2
x_stem = A["기초_앞굽"]; t_stem = A["벽체두께"]           # 3.1, 1.2
z_seat = A["받침면_EL"] - A["기초저면_EL"]               # 5.049
z_top = A["노면_EL"] - A["기초저면_EL"]                  # 8.0
t_par = A["흉벽두께"]; h_haunch = 1.739                   # 흉벽 0.5, 전면 헌치 1:1 (도면 1.739)
LW = A["폭"]                                            # 교대 길이 8.67 (단위폭 환산)
x_brg = x_stem + t_stem / 2                             # 받침 중심 (확인 필요: 단면 A-A 'C of SHOE')
# 블록: (이름, 면적, 도심 x, 도심 z, 재료) — 콘크리트 ①~④, 흙 ⓐ~ⓑ
GEOM = [("① 기초", Bf * tf, Bf / 2, tf / 2, "c"),
        ("② 벽체", t_stem * (z_seat - tf), x_stem + t_stem / 2, tf + (z_seat - tf) / 2, "c"),
        ("③ 전면 헌치(1:1)", h_haunch * h_haunch / 2, x_stem - h_haunch / 3, tf + h_haunch / 3, "c"),
        ("④ 흉벽", t_par * (z_top - z_seat), x_stem + t_stem - t_par / 2, z_seat + (z_top - z_seat) / 2, "c"),
        ("ⓐ 뒷굽 위 흙", (Bf - x_stem - t_stem) * (z_top - tf), (x_stem + t_stem + Bf) / 2, tf + (z_top - tf) / 2, "s"),
        ("ⓑ 앞굽 위 흙(무시)", 0.0, x_stem / 2, tf, "s")]
# ── 지반·하중 조건 (자료 없음 → 도로설계요령 표준값, 확인 필요) ──
_tp = CB["토압"]
SOIL = dict(phi=_tp["phi"], gamma=_tp["gamma"], delta_wall=_tp["phi"] * _tp["delta_ratio"], q=_tp["q"], _="뒷채움 φ·γ 표준값(지반조사 없음, 확인 필요), 벽면마찰각 δ=φ/3, 상재하중 q=10 kN/m² (2016 국도건설공사 설계실무요령 4-02 토압, 도로교설계기준 2.1.8/5.5.9)")
MU = CB["받침마찰계수"]; KH = CB["지진"]["교대_kh"]        # 도로교설계기준 6.6.3.2 (3): 교축방향 변위 허용 독립식 교대 kh = 0.5A
PILE = dict(n=A["말뚝"]["본수"], rows=[0.8, Bf - 0.8], per_row=6, D=SUB["말뚝"]["직경"], t=SUB["말뚝"]["두께_교대"], L=A["말뚝"]["길이"], _="2열(앞·뒤 0.8 m) × 6본 (확인 필요), 허용지지력 확인 필요")
REBAR = dict(stem="확인 필요", parapet="확인 필요", As_stem=0.0, As_par=0.0, d_stem=t_stem - 0.1, d_par=t_par - 0.07)

def rankine_ka(phi): return math.tan(math.radians(45 - phi / 2)) ** 2
def coulomb_ka(phi, delta, theta=0.0, alpha=0.0):
    p, d, t, a = map(math.radians, (phi, delta, theta, alpha))
    k3 = math.sin(p + d) * math.sin(p - a) / (math.cos(t + d) * math.cos(t - a))
    return math.cos(p - t) ** 2 / (math.cos(t) ** 2 * math.cos(t + d) * (1 + math.sqrt(k3)) ** 2)
def mo_kae(phi, delta, kh, kv=0.0, theta=0.0, alpha=0.0):
    """Mononobe–Okabe 지진시 주동토압계수"""
    p, d, t, a = map(math.radians, (phi, delta, theta, alpha)); psi = math.atan(kh / (1 - kv))
    if p - a - psi <= 0: return None
    num = math.cos(p - psi - t) ** 2
    den = math.cos(psi) * math.cos(t) ** 2 * math.cos(d + t + psi) * (1 + math.sqrt(math.sin(p + d) * math.sin(p - a - psi) / (math.cos(d + t + psi) * math.cos(t - a)))) ** 2
    return num / den

def self_weight():
    rows = []
    for nm, area, x, z, mat in GEOM:
        w = area * (GC if mat == "c" else SOIL["gamma"]); rows.append(dict(name=nm, area=area, w=w, x=x, z=z, m=w * x))
    return rows

def cases():
    """단위폭 하중표. 모멘트는 기초 앞단(toe) 기준 (저항 +: 연직력×x, 전도 −: 수평력×z)"""
    H = z_top; Ka = rankine_ka(SOIL["phi"]); g = SOIL["gamma"]; q = SOIL["q"]
    sw = self_weight(); Vsw = sum(r["w"] for r in sw); Msw = sum(r["m"] for r in sw)
    Pa = 0.5 * Ka * g * H ** 2; Pq = Ka * q * H
    D = RX["D"] / LW; L = max(RX["Lmax"], 0.0) / LW; Ff = MU * RX["D"] / LW    # kN/m
    qs = q * (Bf - x_stem - t_stem)                                                 # 뒷굽 위 상재하중(연직)
    Kae = mo_kae(SOIL["phi"], SOIL["delta_wall"], KH); Pae = 0.5 * (Kae or Ka) * g * H ** 2 * (1 - 0.0); dPae = Pae - Pa
    out = {}
    def mk(name, items):
        V = sum(i[1] for i in items); Hh = sum(i[2] for i in items); M = sum(i[3] for i in items)
        x = M / V if V else 0.0; e = Bf / 2 - x
        out[name] = dict(items=[dict(name=a, V=b, H=c, M=d) for a, b, c, d in items], V=V, H=Hh, M=M, x=x, e=e, e_lim=Bf / 6)
    base = [("자중(콘크리트+흙)", Vsw, 0.0, Msw), ("배면토압 (Rankine)", 0.0, Pa, -Pa * H / 3)]
    mk("1 시공시", base)                                                                     # 2021 양식: 자중 + 토압
    mk("2 고정하중 재하", base + [("고정하중 반력", D, 0.0, D * x_brg), ("고정하중 마찰력", 0.0, Ff, -Ff * z_seat)])
    mk("3 활하중 재하", [base[0], ("배면토압+상재 토압", 0.0, Pa + Pq, -Pa * H / 3 - Pq * H / 2), ("고정하중 반력", D, 0.0, D * x_brg), ("활하중 반력", L, 0.0, L * x_brg), ("지표 활하중(뒷굽 상재)", qs, 0.0, qs * (x_stem + t_stem + Bf) / 2), ("고정하중 마찰력", 0.0, Ff, -Ff * z_seat)])
    # 지진시 (6.6.3.2): M–O 전토압 Pae가 배면에 균등분포, 합력 H/2. 관성력 kh·W(구체·흙), 상부는 가동받침(변위 허용) → 상부 관성력 미전달(마찰력만)
    mk("4 지진시", [base[0], ("지진시 토압 Pae (M–O, 균등분포 H/2)", 0.0, Pae, -Pae * H / 2), ("고정하중 반력", D, 0.0, D * x_brg), ("고정하중 마찰력", 0.0, Ff, -Ff * z_seat),
                  ("구체·흙 관성력 kh·W", 0.0, KH * Vsw, -KH * sum(r["w"] * r["z"] for r in sw))])
    return out, dict(Ka=Ka, Pa=Pa, Pq=Pq, Kae=Kae, Pae=Pae, dPae=dPae, D=D, L=L, Ff=Ff, sw=sw, Vsw=Vsw, Msw=Msw)

def piles(cs):
    """열 배치 강체 캡: P_i = V/n ± M_c·x_i/Σx² (단위폭 → 전폭 환산 후 본당)"""
    n = PILE["n"]; xs = [r - Bf / 2 for r in PILE["rows"]]; per = PILE["per_row"]; Sx2 = per * sum(x * x for x in xs)
    out = {}
    for name, c in cs.items():
        V = c["V"] * LW; Mc = (c["M"] - c["V"] * Bf / 2) * LW      # 기초 중심 기준 모멘트
        pr = {f"x={r:.1f}": V / n + Mc * (r - Bf / 2) / Sx2 for r in PILE["rows"]}
        out[name] = dict(V=V, Mc=Mc, P=pr, Pmax=max(pr.values()), Pmin=min(pr.values()), Hp=c["H"] * LW / n)
    D, t = PILE["D"], PILE["t"] - 0.002; Ap = math.pi / 4 * (D ** 2 - (D - 2 * t) ** 2)
    return out, dict(Ra_struct=Ap * 140 * 1000, Ap=Ap, Sx2=Sx2, n=n)

def wall_forces(info):
    """벽체 기부(기초 상면)·흉벽 기부 단면력 (단위폭). Coulomb 토압(단면설계, 구체 배면), 강도 ①: 1.3D + 2.15(L+i) + 1.7H — 토압 H(상재 q 포함, Pa = Ka(q+γh)) 1.7, 마찰력(D) 1.3"""
    Kc = coulomb_ka(SOIL["phi"], SOIL["delta_wall"]); g, q = SOIL["gamma"], SOIL["q"]; f = CB["강도"]["①"]
    Hw = z_top - tf; Pa = 0.5 * Kc * g * Hw ** 2 * math.cos(math.radians(SOIL["delta_wall"])); Pq = Kc * q * Hw * math.cos(math.radians(SOIL["delta_wall"]))
    Me = Pa * Hw / 3; Mq = Pq * Hw / 2; Mf = info["Ff"] * (z_seat - tf)
    Mu = f["H"] * (Me + Mq) + f["D"] * Mf; Vu = f["H"] * (Pa + Pq) + f["D"] * info["Ff"]
    Hp = z_top - z_seat; Pap = 0.5 * Kc * g * Hp ** 2; Pqp = Kc * q * Hp
    Mup = f["H"] * (Pap * Hp / 3 + Pqp * Hp / 2); Vup = f["H"] * (Pap + Pqp)                       # 흉벽: 토압 + 상재(윤하중 등가) — 2020 도로설계요령 4.6
    def as_req(Mu, d, b=1.0):
        """단철근 소요 As (m²/m): Mu = φ·As·fy·(d − a/2)"""
        phi = 0.85; lo, hi = 0.0, 0.05
        for _ in range(40):
            mid = (lo + hi) / 2; a = mid * FY / (0.85 * FCK * b); Mn = phi * mid * FY * (d - a / 2) * 1000
            if Mn >= Mu: hi = mid
            else: lo = mid
        return hi
    return dict(Kc=Kc, stem=dict(Pa=Pa, Pq=Pq, Me=Me, Mq=Mq, Mf=Mf, Mu=Mu, Vu=Vu, d=REBAR["d_stem"], As_req=as_req(Mu, REBAR["d_stem"])),
                parapet=dict(Pa=Pap, Pq=Pqp, Mu=Mup, Vu=Vup, d=REBAR["d_par"], As_req=as_req(Mup, REBAR["d_par"])))

def figure(path):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = ["Malgun Gothic"]; plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(8, 7)); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), Bf, tf, fill=False, lw=1.8)); ax.add_patch(plt.Rectangle((x_stem, tf), t_stem, z_seat - tf, fill=False, lw=1.8))
    ax.add_patch(plt.Polygon([(x_stem, tf), (x_stem, tf + h_haunch), (x_stem - h_haunch, tf)], fill=False, lw=1.5))
    ax.add_patch(plt.Rectangle((x_stem + t_stem - t_par, z_seat), t_par, z_top - z_seat, fill=False, lw=1.8))
    ax.plot([x_stem + t_stem, Bf + 2.0], [z_top, z_top], "k--", lw=0.8); ax.text(Bf + 0.5, z_top + 0.15, "뒷채움 (γ, φ)", fontsize=9)
    for r in PILE["rows"]: ax.add_patch(plt.Rectangle((r - PILE["D"] / 2, -3.0), PILE["D"], 3.0, fill=False, lw=1)); ax.text(r, -3.4, f"말뚝 x={r:.1f}", ha="center", fontsize=8)
    for nm, area, x, z, mat in GEOM:
        if area > 0: ax.text(x, z, nm.split()[0], ha="center", va="center", fontsize=11, weight="bold")
    def dim(x1, x2, y, t): ax.annotate("", (x1, y), (x2, y), arrowprops=dict(arrowstyle="<->", lw=0.7)); ax.text((x1 + x2) / 2, y - 0.35, t, ha="center", fontsize=8)
    dim(0, x_stem, -0.5, f"{x_stem:.3f}"); dim(x_stem, x_stem + t_stem, -0.5, f"{t_stem:.3f}"); dim(x_stem + t_stem, Bf, -0.5, f"{Bf - x_stem - t_stem:.3f}"); dim(0, Bf, -1.1, f"B = {Bf:.3f}")
    ax.annotate("", (Bf + 1.2, 0), (Bf + 1.2, z_top), arrowprops=dict(arrowstyle="<->", lw=0.7)); ax.text(Bf + 1.3, z_top / 2, f"H = {z_top:.3f}", rotation=90, va="center", fontsize=8)
    ax.annotate("", (-0.8, 0), (-0.8, z_seat), arrowprops=dict(arrowstyle="<->", lw=0.7)); ax.text(-1.0, z_seat / 2, f"받침면 {z_seat:.3f}", rotation=90, va="center", fontsize=8)
    ax.plot([x_brg], [z_seat], "kv", ms=8); ax.text(x_brg, z_seat + 0.25, "받침", ha="center", fontsize=8)
    ax.set_xlim(-1.6, Bf + 3.0); ax.set_ylim(-4.0, z_top + 1.0); ax.set_title("교대 A1 단면 개략도 (단위폭 검토, 준공도면 교대 일반도(1) 단면 A-A)", fontsize=10)
    fig.savefig(path, dpi=150, bbox_inches="tight"); plt.close(fig)

def main():
    cs, info = cases(); pl, pinfo = piles(cs); wf = wall_forces(info)
    res = dict(geom=dict(Bf=Bf, tf=tf, x_stem=x_stem, t_stem=t_stem, z_seat=z_seat, z_top=z_top, t_par=t_par, LW=LW, x_brg=x_brg, blocks=GEOM), soil=SOIL, kh=KH, pile=PILE, cases=cs, info={k: v for k, v in info.items() if k != "sw"}, sw=info["sw"], piles=pl, pile_info=pinfo, wall=wf, rebar=REBAR)
    json.dump(res, open(os.path.join(OUT, "A1_result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1); figure(os.path.join(OUT, "A1_section.png"))
    rep = ["# 교대 A1 안전성 검토 (역T형·강관말뚝 기초)", "", f"단위폭 1 m 기준 (교대 길이 {LW} m). 뒷채움 φ={SOIL['phi']}°, γ={SOIL['gamma']} kN/m³, δ={SOIL['delta_wall']}°, q={SOIL['q']} kN/m² (표준값, 확인 필요). 받침마찰 μ={MU}. 지진 kh={KH} (확인 필요).", "",
           "## 자중 (단위폭)", "", "| 구분 | 면적 (m²) | 하중 (kN/m) | x (m) | 모멘트 (kN·m/m) |", "| :-- | --: | --: | --: | --: |"]
    for r in info["sw"]: rep.append(f"| {r['name']} | {r['area']:.3f} | {r['w']:.2f} | {r['x']:.3f} | {r['m']:.2f} |")
    rep += [f"| 합계 | | {info['Vsw']:.2f} | | {info['Msw']:.2f} |", "", f"## 토압 : Rankine Ka = {info['Ka']:.3f} (안정), Coulomb Ka = {wf['Kc']:.3f} (벽체), M–O Kae = {info['Kae']:.3f} → ΔPae = {info['dPae']:.2f} kN/m", "",
            f"Pa = ½·Ka·γ·H² = {info['Pa']:.2f} kN/m, 상재 Pq = {info['Pq']:.2f} kN/m, 상부 D = {info['D']:.2f}, L = {info['L']:.2f} kN/m, 마찰 = {info['Ff']:.2f} kN/m", ""]
    for name, c in cs.items():
        rep += [f"### 하중 CASE {name}", "", "| 하중 | 연직 V | 수평 H | toe 모멘트 M |", "| :-- | --: | --: | --: |"]
        for i in c["items"]: rep.append(f"| {i['name']} | {i['V']:.2f} | {i['H']:.2f} | {i['M']:.2f} |")
        rep += [f"| 합계 | {c['V']:.2f} | {c['H']:.2f} | {c['M']:.2f} |", "", f"합력 위치 x = {c['x']:.3f} m, 편심 e = {c['e']:.3f} m (B/6 = {c['e_lim']:.3f}) → {'B/6 이내' if abs(c['e']) <= c['e_lim'] else 'B/6 초과 (말뚝기초: 말뚝 반력으로 판정)'}", ""]
    rep += ["## 말뚝 반력 (전폭, 강체 캡 2열)", "", "| CASE | ΣV (kN) | Mc (kN·m) | 앞열 | 뒷열 | 수평/본 | 구조적 허용 |", "| :-- | --: | --: | --: | --: | --: | --: |"]
    for name, p in pl.items():
        vals = list(p["P"].values()); rep.append(f"| {name} | {p['V']:.0f} | {p['Mc']:.0f} | {vals[0]:.0f} | {vals[1]:.0f} | {p['Hp']:.1f} | {pinfo['Ra_struct']:.0f}{' (지진 ×1.5)' if name.startswith('4') else ''} |")
    st, pa = wf["stem"], wf["parapet"]
    rep += ["", "지반 허용지지력·수평지지력: 확인 필요(구조계산서/지반조사).", "", "## 벽체·흉벽 단면력 (단위폭, 강도 ① : 1.7H + 1.3D)", "", "| 부재 | 토압 Pa | 상재 Pq | Mu (kN·m/m) | Vu (kN/m) | d (m) | 소요 As (cm²/m) | 배근 |", "| :-- | --: | --: | --: | --: | --: | --: | :-- |",
            f"| 벽체 기부 | {st['Pa']:.2f} | {st['Pq']:.2f} | {st['Mu']:.2f} | {st['Vu']:.2f} | {st['d']:.2f} | {st['As_req']*1e4:.2f} | {REBAR['stem']} |",
            f"| 흉벽 기부 | {pa['Pa']:.2f} | {pa['Pq']:.2f} | {pa['Mu']:.2f} | {pa['Vu']:.2f} | {pa['d']:.2f} | {pa['As_req']*1e4:.2f} | {REBAR['parapet']} |", "",
            "확인 필요: 뒷채움 토질정수, 말뚝 배치(열 위치)·허용지지력, 벽체·흉벽 배근, 받침 위치, 지진 수평진도."]
    open(os.path.join(RUNS, "결과_교대.md"), "w", encoding="utf-8").write("\n".join(rep)); print("저장 결과_교대.md, A1_result.json, A1_section.png")
    for name, c in cs.items(): print(f"{name}: V {c['V']:.1f} H {c['H']:.1f} e {c['e']:.3f} | 말뚝 {pl[name]['Pmax']:.0f}/{pl[name]['Pmin']:.0f}")
    print("벽체 Mu", round(st["Mu"], 1), "As_req cm²", round(st["As_req"] * 1e4, 1), "| 흉벽 Mu", round(pa["Mu"], 1))

if __name__ == "__main__":
    main()

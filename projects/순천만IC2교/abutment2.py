# -*- coding: utf-8 -*-
"""
교대 안전성 계산기 v2 — 절차: 도로설계요령(한국도로공사, 제3권 8-3편 교대 설계), 계수·판정: 한계상태설계법(도로교설계기준 2016 = KDS 24 12 11/14 51, KDS 24 17 11)
  형상  : tools/abut_geom.py 판독 결과(runs/abutment/geom_001.json, 앞굽·뒷굽·벽체·헌치·말뚝 자동 판정) + 하부_제원서 EL
  하중  : DC(구체 ①~④) EV(뒷굽 위 흙 ⓐ) EH(가상배면 Coulomb, δ=φ 상시·½φ 지진시 [요령 표 2.8]) LS(재하하중 10 kN/m² [요령 2.5.6(2)])
          상부반력 DC+DW / LL(격자해석 DB-24 반력, 확인 필요: KDS 활하중 KL-510 미적용) FR(받침 마찰 μ·R) EQ(M–O 균등분포 H/2, kh = 0.5·S [KDS 24 17 11 4.4.3.2, 2010 6.6.3.2])
  조합  : combos_kds.json — 극한 I(지지력·전도·앞벽), 극단 I(지진), 사용 I(말뚝 배열·변위). 영구하중 γp 최대/최소 중 불리한 값
  판정  : 전도 e ≤ B/4 (극한) / 0.4B (극단) [7.9.3.3, 7.6.3.1(5)], 말뚝 축력 ≤ φc·Pn(구조, 부식 2 mm) [지반 저항 확인 필요], 앞벽·흉벽 소요 As [KDS 24 14 21 재료계수]
  출력  : runs/abutment/A1_v2_result.json, runs/결과_교대_v2.md, runs/abutment/A1_v2_section.png
"""
import sys, os, json, math
sys.stdout.reconfigure(encoding="utf-8")
PJ = r"D:\Midas\projects\순천만IC2교"; RUNS = os.path.join(PJ, "runs"); OUT = os.path.join(RUNS, "abutment"); os.makedirs(OUT, exist_ok=True)
SUB = json.load(open(os.path.join(PJ, "하부_제원서.json"), encoding="utf-8")); A = SUB["교대"]["A1"]
RX = json.load(open(os.path.join(RUNS, "reactions_summary.json"), encoding="utf-8"))["support"]["A1"]
CB = json.load(open(os.path.join(PJ, "combos_kds.json"), encoding="utf-8"))
GEO = json.load(open(os.path.join(OUT, "geom_001.json"), encoding="utf-8"))["section"]
GC = SUB["재료"]["gamma_c"]; FCK, FY = SUB["재료"]["fck_구체"], SUB["재료"]["fy"]
# ── 형상 (도면 판독 자동값) : x = 앞굽 연단(교량 쪽) 0 → 뒷채움 쪽 +, z = 기초 저면 0 ──
toe, ts, heel, Bf = GEO["toe"], GEO["stem"], GEO["heel"], GEO["B"]
tf = A["기초두께"]; z_seat = A["받침면_EL"] - A["기초저면_EL"]; z_top = A["노면_EL"] - A["기초저면_EL"]
t_par = A["흉벽두께"]; hh = A.get("헌치높이", 1.739)                         # 배면 1:1 헌치 (도면 1.739, abut_geom heights_found)
x_stem0 = toe; x_stem1 = toe + ts; LW = A["폭"]
x_brg = GEO["x_shoe_from_toe"] if GEO.get("x_shoe_from_toe") else toe + ts / 2      # 받침 중심(앞굽 연단 기준, 도면 'C of SHOE' 판독)
assert GEO["haunch_on"] == "back" and GEO["front_side"], "도면 판독 방향 확인 필요"
H = z_top
# 블록: (이름, 면적, 도심x, 도심z, 종류)
GEOM = [("① 기초", Bf * tf, Bf / 2, tf / 2, "DC"),
        ("② 벽체", ts * (z_seat - tf), x_stem0 + ts / 2, tf + (z_seat - tf) / 2, "DC"),
        ("③ 배면 헌치 1:1", hh * hh / 2, x_stem1 + hh / 3, tf + hh / 3, "DC"),
        ("④ 흉벽", t_par * (z_top - z_seat), x_stem1 - t_par / 2, z_seat + (z_top - z_seat) / 2, "DC"),
        ("ⓐ 뒷굽 위 흙", heel * (z_top - tf) - hh * hh / 2, None, None, "EV")]
# 흙 도심 (직사각형 − 헌치 삼각형)
_ar = heel * (z_top - tf); _cx = x_stem1 + heel / 2; _cz = tf + (z_top - tf) / 2; _at = hh * hh / 2; _tx = x_stem1 + hh / 3; _tz = tf + hh / 3
GEOM[4] = ("ⓐ 뒷굽 위 흙", _ar - _at, (_ar * _cx - _at * _tx) / (_ar - _at), (_ar * _cz - _at * _tz) / (_ar - _at), "EV")
# ── 지반·하중 정수 ──
TP = CB["토압_교대"]; PHI, GAM, Q = TP["phi"], TP["gamma"], TP["q_LS"]
MU = 0.05; S_EQ = CB["검토기준"]["지진"]["S_유효수평지반가속도"]; KH = CB["검토기준"]["지진"]["교대_kh_비"] * S_EQ
PILE = dict(n=A["말뚝"]["본수"], rows_from_toe=A["말뚝"].get("열위치_앞굽기준", [0.7, 3.4, 4.9]), per_row=6, D=SUB["말뚝"]["직경"], t=SUB["말뚝"]["두께_교대"], fy=235.0, L=A["말뚝"]["길이"])
MAT = CB["재료계수_KDS241421"]

def coulomb_ka(phi, delta, theta=0.0, alpha=0.0):
    p, d, t, a = map(math.radians, (phi, delta, theta, alpha))
    k3 = math.sin(p + d) * math.sin(p - a) / (math.cos(t + d) * math.cos(t - a))
    return math.cos(p - t) ** 2 / (math.cos(t) ** 2 * math.cos(t + d) * (1 + math.sqrt(k3)) ** 2)
def mo_kae(phi, delta, kh, kv=0.0, theta=0.0, alpha=0.0):
    p, d, t, a = map(math.radians, (phi, delta, theta, alpha)); psi = math.atan(kh / (1 - kv))
    num = math.cos(p - psi - t) ** 2
    den = math.cos(psi) * math.cos(t) ** 2 * math.cos(d + t + psi) * (1 + math.sqrt(math.sin(p + d) * math.sin(p - a - psi) / (math.cos(d + t + psi) * math.cos(t - a)))) ** 2
    return num / den

def loads():
    """단위폭 하중 성분 (kN/m, kN·m/m; 모멘트는 앞굽 연단 기준, 저항 +)"""
    L = {}
    for nm, ar, x, z, kind in GEOM:
        w = ar * (GC if kind == "DC" else GAM); L[nm] = dict(kind=kind, V=w, H=0.0, M=w * x, x=x, z=z, area=ar)
    # 가상배면(x = B) 토압: Coulomb δ=φ(상시) — 경사 δ의 합력 → 수평·연직 성분(연직은 저항)
    d_st = PHI; Ka = coulomb_ka(PHI, d_st); Pa = 0.5 * Ka * GAM * H ** 2
    L["EH 배면토압(가상배면, δ=φ)"] = dict(kind="EH", V=Pa * math.sin(math.radians(d_st)), H=Pa * math.cos(math.radians(d_st)), M=Pa * math.sin(math.radians(d_st)) * Bf - Pa * math.cos(math.radians(d_st)) * H / 3, z=H / 3, x=Bf, Ka=Ka)
    Pq = Ka * Q * H
    L["LS 재하하중 토압(q=10)"] = dict(kind="LS", V=Pq * math.sin(math.radians(d_st)), H=Pq * math.cos(math.radians(d_st)), M=Pq * math.sin(math.radians(d_st)) * Bf - Pq * math.cos(math.radians(d_st)) * H / 2, z=H / 2, x=Bf)
    L["LS 재하하중 연직(뒷굽 위)"] = dict(kind="LSV", V=Q * heel, H=0.0, M=Q * heel * (x_stem1 + heel / 2), x=x_stem1 + heel / 2, z=z_top)
    D = RX["D"] / LW; LL = max(RX["Lmax"], 0.0) / LW
    L["상부 고정하중 반력 DC+DW"] = dict(kind="DCs", V=D, H=0.0, M=D * x_brg, x=x_brg, z=z_seat)
    L["상부 활하중 반력 LL"] = dict(kind="LL", V=LL, H=0.0, M=LL * x_brg, x=x_brg, z=z_seat)
    FR = MU * D; L["받침 마찰력 FR (μ=0.05)"] = dict(kind="FR", V=0.0, H=FR, M=-FR * z_seat, x=x_brg, z=z_seat)
    # 지진: M–O 전토압(δ=½φ, 균등분포 → 합력 H/2) + 구체·흙 관성력
    d_eq = PHI / 2; Kae = mo_kae(PHI, d_eq, KH); Pae = 0.5 * Kae * GAM * H ** 2
    L["EQ 지진시 토압 Pae (M–O, δ=½φ, H/2)"] = dict(kind="EQ", V=Pae * math.sin(math.radians(d_eq)), H=Pae * math.cos(math.radians(d_eq)), M=Pae * math.sin(math.radians(d_eq)) * Bf - Pae * math.cos(math.radians(d_eq)) * H / 2, z=H / 2, x=Bf, Kae=Kae)
    Wst = sum(v["V"] for k, v in L.items() if v["kind"] in ("DC", "EV")); Mz = sum(v["V"] * v["z"] for k, v in L.items() if v["kind"] in ("DC", "EV"))
    L["EQ 구체·흙 관성력 kh·W"] = dict(kind="EQ", V=0.0, H=KH * Wst, M=-KH * Mz, z=Mz / Wst, x=None)
    return L, dict(Ka=Ka, Kae=Kae, Pa=Pa, Pq=Pq, Pae=Pae, D=D, LL=LL, FR=FR, kh=KH, delta_st=d_st, delta_eq=d_eq)

def combine(L, case):
    """case: '극한 I'|'극단 I'|'사용 I'; 반환 {mode: dict(V,H,M,e)} — mode 'max'(지지력: 영구 최대) / 'min'(전도: 저항 영구 최소, 전도 토압 최대)"""
    f = CB["조합"][case]; gp = CB["gamma_p"]; out = {}
    for mode in ("max", "min"):
        i = 0 if mode == "max" else 1
        gDC = gp["DC"][i] if "DC_override" not in f else f["DC_override"]; gEV = gp["EV_abutment"][i]; gEH = gp["EH_active"][0]   # 토압은 항상 최대(불리)
        if f.get("gamma_p_override"): gDC = gEV = gEH = f["gamma_p_override"]
        if case == "극단 I": gEH = 1.0                                      # 극단상황: 정적 토압 γ=1.0(잠정), 지진토압 EQ 1.0
        V = Hh = M = 0.0; rows = []
        for nm, v in L.items():
            k = v["kind"]
            g = {"DC": gDC, "EV": gEV, "EH": gEH, "LS": f["LS"], "LSV": (f["LS"] if mode == "max" else 0.0), "DCs": gDC, "LL": f["LL"], "FR": f["FR"], "EQ": f["EQ"]}[k]
            if g == 0: continue
            V += g * v["V"]; Hh += g * v["H"]; M += g * v["M"]; rows.append(dict(name=nm, gamma=g, V=g * v["V"], H=g * v["H"], M=g * v["M"]))
        x = M / V if V else 0.0; out[mode] = dict(V=V, H=Hh, M=M, x=x, e=Bf / 2 - x, rows=rows)
    return out

def piles(comb):
    n = PILE["n"]; rows = PILE["rows_from_toe"]; per = PILE["per_row"]; xs = [r - Bf / 2 for r in rows]; Sx2 = per * sum(x * x for x in xs)
    V = comb["V"] * LW; Mc = (comb["M"] - comb["V"] * Bf / 2) * LW
    P = {f"열 x={r:.1f}": V / n + Mc * (r - Bf / 2) / Sx2 for r in rows}
    return dict(V=V, Mc=Mc, P=P, Pmax=max(P.values()), Pmin=min(P.values()), Hp=comb["H"] * LW / n)

def pile_capacity():
    D, t = PILE["D"], PILE["t"] - CB["검토기준"]["말뚝_구조"]["부식두께_mm"] / 1000; Ap = math.pi / 4 * (D ** 2 - (D - 2 * t) ** 2)
    Pn = Ap * PILE["fy"] * 1000; return dict(Ap=Ap, Pn=Pn, phiPn=CB["검토기준"]["말뚝_구조"]["phi_c"] * Pn)

def wall_design(info):
    """앞벽 기부(기초 상면)·흉벽 기부: 구체 배면 Coulomb δ=⅓φ [요령 표 2.8], 극한 I: EH 1.5, LS 1.8, FR 1.0. KDS 24 14 21 재료계수로 소요 As"""
    f = CB["조합"]["극한 I"]; gEH = CB["gamma_p"]["EH_active"][0]
    d = PHI / 3; Kc = coulomb_ka(PHI, d); Hw = z_top - tf
    Pa = 0.5 * Kc * GAM * Hw ** 2 * math.cos(math.radians(d)); Pq = Kc * Q * Hw * math.cos(math.radians(d))
    Mu = gEH * Pa * Hw / 3 + f["LS"] * Pq * Hw / 2 + f["FR"] * info["FR"] * (z_seat - tf); Vu = gEH * Pa + f["LS"] * Pq + f["FR"] * info["FR"]
    Hp = z_top - z_seat; Pap = 0.5 * Kc * GAM * Hp ** 2 * math.cos(math.radians(d)); Pqp = Kc * Q * Hp * math.cos(math.radians(d))
    Mup = gEH * Pap * Hp / 3 + f["LS"] * Pqp * Hp / 2; Vup = gEH * Pap + f["LS"] * Pqp
    fcd = MAT["phi_c"] * 0.85 * FCK; fyd = MAT["phi_s"] * FY
    def as_req(M, dd, b=1.0):
        lo, hi = 0.0, 0.06
        for _ in range(50):
            mid = (lo + hi) / 2; a = mid * fyd / (fcd * b); Mr = mid * fyd * (dd - a / 2) * 1000
            if Mr >= M: hi = mid
            else: lo = mid
        return hi
    return dict(Kc=Kc, delta=d, stem=dict(Pa=Pa, Pq=Pq, Mu=Mu, Vu=Vu, d=ts - 0.10, As_req=as_req(Mu, ts - 0.10)), parapet=dict(Pa=Pap, Pq=Pqp, Mu=Mup, Vu=Vup, d=t_par - 0.07, As_req=as_req(Mup, t_par - 0.07)), fcd=fcd, fyd=fyd)

def figure(path, info):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = ["Malgun Gothic"]; plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(9, 7)); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), Bf, tf, fill=False, lw=1.8)); ax.add_patch(plt.Rectangle((x_stem0, tf), ts, z_seat - tf, fill=False, lw=1.8))
    ax.add_patch(plt.Polygon([(x_stem1, tf), (x_stem1 + hh, tf), (x_stem1, tf + hh)], fill=False, lw=1.5))
    ax.add_patch(plt.Rectangle((x_stem1 - t_par, z_seat), t_par, z_top - z_seat, fill=False, lw=1.8))
    ax.add_patch(plt.Polygon([(x_stem1, tf + hh), (x_stem1 + hh, tf), (Bf, tf), (Bf, z_top), (x_stem1, z_top)], closed=True, fill=True, facecolor="#f2e6c9", edgecolor="#a08040", lw=0.8, hatch="..."))
    ax.plot([Bf, Bf], [0, z_top], "r--", lw=1.2); ax.text(Bf + 0.1, z_top * 0.55, "가상배면\n(안정계산, δ=φ)", color="r", fontsize=9)
    ax.plot([Bf, Bf + 2.5], [z_top, z_top], "k--", lw=0.8); ax.text(Bf + 0.6, z_top + 0.15, f"뒷채움 γ={GAM} kN/m³, φ={PHI}°, q={Q} kN/m²", fontsize=8)
    # 토압 분포 (삼각형) 개략
    pk = info["Pa"] * 2 / H / 12
    ax.add_patch(plt.Polygon([(Bf, 0), (Bf + pk, 0), (Bf, z_top)], fill=True, facecolor="#ffcccc", edgecolor="r", lw=0.8, alpha=0.6))
    for r in PILE["rows_from_toe"]: ax.add_patch(plt.Rectangle((r - PILE["D"] / 2, -2.5), PILE["D"], 2.5, fill=False, lw=1)); ax.text(r, -2.9, f"{r:.1f}", ha="center", fontsize=8)
    for nm, ar, x, z, kind in GEOM: ax.text(x, z, nm.split()[0], ha="center", va="center", fontsize=11, weight="bold")
    def dim(x1, x2, y, t): ax.annotate("", (x1, y), (x2, y), arrowprops=dict(arrowstyle="<->", lw=0.7)); ax.text((x1 + x2) / 2, y - 0.32, t, ha="center", fontsize=8)
    dim(0, toe, -0.5, f"앞굽 {toe:.3f}"); dim(toe, x_stem1, -0.5, f"{ts:.3f}"); dim(x_stem1, Bf, -0.5, f"뒷굽 {heel:.3f}"); dim(0, Bf, -1.1, f"B = {Bf:.3f}")
    ax.annotate("", (-0.7, 0), (-0.7, z_seat), arrowprops=dict(arrowstyle="<->", lw=0.7)); ax.text(-0.95, z_seat / 2, f"받침면 {z_seat:.3f}", rotation=90, va="center", ha="center", fontsize=8)
    ax.annotate("", (-1.3, 0), (-1.3, z_top), arrowprops=dict(arrowstyle="<->", lw=0.7)); ax.text(-1.55, z_top / 2, f"H = {z_top:.3f}", rotation=90, va="center", ha="center", fontsize=8)
    ax.plot([x_brg], [z_seat], "kv", ms=8); ax.text(x_brg, z_seat + 0.3, f"받침 x={x_brg:.2f}", ha="center", fontsize=8)
    ax.text(toe / 2, z_seat + 1.0, "교량 쪽\n(앞굽)", ha="center", fontsize=9); ax.set_xlim(-1.9, Bf + 3.2); ax.set_ylim(-3.3, z_top + 0.9)
    fig.savefig(path, dpi=150, bbox_inches="tight"); plt.close(fig)

def main():
    L, info = loads(); cap = pile_capacity(); res = dict(geom=dict(toe=toe, stem=ts, heel=heel, B=Bf, tf=tf, z_seat=z_seat, z_top=z_top, t_par=t_par, hh=hh, x_brg=x_brg, LW=LW, source=GEO), soil=dict(phi=PHI, gamma=GAM, q=Q, kh=KH), loads=L, info=info, cases={}, piles={}, pile_cap=cap)
    lim = {"극한 I": Bf / 4, "극단 I": 0.4 * Bf, "사용 I": Bf / 6}
    for case in ("극한 I", "극단 I", "사용 I"):
        c = combine(L, case); res["cases"][case] = c
        for mode in ("max", "min"): res["piles"][f"{case}|{mode}"] = piles(c[mode])
    w = wall_design(info); res["wall"] = w
    json.dump(res, open(os.path.join(OUT, "A1_v2_result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1); figure(os.path.join(OUT, "A1_v2_section.png"), info)
    rep = ["# 교대 A1 안전성 검토 v2 (도로설계요령 절차 + 한계상태설계법 계수)", "",
           f"형상(도면 자동판독): 앞굽 {toe} m(교량 쪽), 벽체 {ts} m, 뒷굽 {heel} m(배면 1:1 헌치 {hh} m), B = {Bf} m, 기초 {tf} m, 받침면 {z_seat:.3f} m, H = {z_top:.3f} m, 받침 x = {x_brg:.2f} m. 말뚝 {PILE['n']}본 = {len(PILE['rows_from_toe'])}열 × {PILE['per_row']}본, 열 위치(앞굽 기준) {PILE['rows_from_toe']} m (열 순서 확인 필요).",
           f"뒷채움 γ = {GAM} kN/m³, φ = {PHI}° (도로설계요령 표 2.7 '잘 다져진 모래 및 사질토', 지반조사 없음), 재하하중 q = {Q} kN/m² (요령 2.5.6(2)). δ: 가상배면 φ / 지진시 ½φ, 앞벽 ⅓φ (요령 표 2.8). Ka = {info['Ka']:.3f}, Kae = {info['Kae']:.3f} (kh = {KH:.3f} = 0.5·S), 받침 마찰 μ = {MU}.", "",
           "## 단위폭 하중 (kN/m, kN·m/m, 앞굽 연단 기준 모멘트)", "", "| 하중 | 종류 | V | H | M | 작용점 x / z |", "| :-- | :-- | --: | --: | --: | :-- |"]
    for nm, v in L.items(): rep.append(f"| {nm} | {v['kind']} | {v['V']:.2f} | {v['H']:.2f} | {v['M']:.2f} | {('%.3f' % v['x']) if v.get('x') is not None else '-'} / {('%.3f' % v['z']) if v.get('z') is not None else '-'} |")
    rep += ["", "## 하중조합별 안정 (전도: 합력 위치·편심)", "", "| 조합 | 영구하중 | ΣV | ΣH | ΣM | x | e | 허용 e | 판정 |", "| :-- | :-- | --: | --: | --: | --: | --: | --: | :-- |"]
    for case, c in res["cases"].items():
        for mode in ("max", "min"):
            m = c[mode]; ok = abs(m["e"]) <= lim[case]; rep.append(f"| {case} | {'최대' if mode == 'max' else '최소(전도 검토)'} | {m['V']:.1f} | {m['H']:.1f} | {m['M']:.1f} | {m['x']:.3f} | {m['e']:.3f} | {lim[case]:.3f} | {'O.K' if ok else 'N.G'} |")
    rep += ["", f"## 말뚝 반력 (전폭 {LW} m, 강체 캡 {len(PILE['rows_from_toe'])}열) — 구조 저항 φc·Pn = {cap['phiPn']:,.0f} kN (Ø{PILE['D']*1000:.0f}×{PILE['t']*1000:.0f}, 부식 2 mm, fy {PILE['fy']:.0f}), 지반 저항 확인 필요", "", "| 조합 | ΣV (kN) | Mc (kN·m) | " + " | ".join(f"x={r:.1f}" for r in PILE["rows_from_toe"]) + " | 최대/φPn | 수평/본 |", "|" + " :-- |" * (5 + len(PILE["rows_from_toe"]))]
    for k, p in res["piles"].items():
        rep.append(f"| {k} | {p['V']:.0f} | {p['Mc']:.0f} | " + " | ".join(f"{v:.0f}" for v in p["P"].values()) + f" | {p['Pmax']/cap['phiPn']:.2f} | {p['Hp']:.1f} |")
    st, pa = w["stem"], w["parapet"]
    rep += ["", "## 앞벽·흉벽 (구체 배면 Coulomb δ=⅓φ, 극한 I: EH 1.5·LS 1.8·FR 1.0; KDS 24 14 21 재료계수 φc 0.65·φs 0.90)", "", "| 부재 | Pa | Pq | Mu (kN·m/m) | Vu (kN/m) | d (m) | 소요 As (cm²/m) | 배근 |", "| :-- | --: | --: | --: | --: | --: | --: | :-- |",
            f"| 앞벽 기부 | {st['Pa']:.2f} | {st['Pq']:.2f} | {st['Mu']:.2f} | {st['Vu']:.2f} | {st['d']:.2f} | {st['As_req']*1e4:.2f} | 확인 필요 |", f"| 흉벽 기부 | {pa['Pa']:.2f} | {pa['Pq']:.2f} | {pa['Mu']:.2f} | {pa['Vu']:.2f} | {pa['d']:.2f} | {pa['As_req']*1e4:.2f} | 확인 필요 |",
            "", "확인 필요: 말뚝 열 순서(앞굽 기준), 지반 지지력(말뚝 저항계수 표 7.5.2), 배근, 활하중 KL-510 환산, 극단 I 활하중계수 γEQ, 교대 kh."]
    open(os.path.join(RUNS, "결과_교대_v2.md"), "w", encoding="utf-8").write("\n".join(rep))
    for case, c in res["cases"].items(): print(f"{case}: max V {c['max']['V']:.1f} e {c['max']['e']:.3f} | min V {c['min']['V']:.1f} e {c['min']['e']:.3f} (허용 {lim[case]:.2f}) | 말뚝 max {res['piles'][case+'|max']['Pmax']:.0f}")
    print("앞벽 Mu", round(st["Mu"], 1), "As", round(st["As_req"] * 1e4, 1), "| 흉벽 Mu", round(pa["Mu"], 1)); print("저장 결과_교대_v2.md")

if __name__ == "__main__":
    main()

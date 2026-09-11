# -*- coding: utf-8 -*-
"""
교대 안전성 계산기 v3 — 도로설계편람 제5편(2008) 509.1 역T형 교대 설계 예의 [단계] 흐름을 진단용으로 옮긴 것
  체계  : 안정검토 = 허용응력법(사용하중, 말뚝기초 → 말뚝 반력 검토로 대체 [편람 509.2.5 7-2]), 단면검토 = 강도설계법(도로교설계기준 2010 식 ①: 1.3D + 2.15(L+i) + 1.7H)
          지진하중 제외(내진성능평가 별도), 한계상태설계법 미사용 (대표님 2026-09-11 결정)
  단계  : [1] 검토조건·제원(도면 자동판독 geom_001.json + 하부_제원서) [2] 지진변위 검토 — 제외 [3] 받침 용량 검토 [4] 설계조건(재료·뒷채움·마찰·토압계수·상부반력 단위폭·상재하중)
          [5] 설계력 산정(자중표·상부반력·토압·하중집계표) [6] 안정검토(말뚝 반력·수평력·본체 응력) [7] 단면검토(벽체·수평철근·흉벽(토압+윤하중)·앞굽·뒷굽, 도면 배근 → 강도비)
          [8] 접속슬래브·[9] 날개벽 — 제외
  토압  : 안정검토 = 가상배면(뒷굽 연단 연직면) Rankine(δ=0) [편람 4-7, 2016 실무요령]; 단면검토 = 구체 배면 Coulomb δ=φ/3 [편람 4-7, 2020 도로설계요령 4.6]; 상재하중 q = 10 kN/m²
  받침  : 탄성받침(고무) 겉보기 정지마찰계수 0.15 [편람 509.1 단계 4-1] → 수평력 = 0.15 × 고정하중 반력
  흉벽  : 토압 + 윤하중(DB-24 후륜 96 kN, 접지 0.2×0.5 m, 차량점유폭 1/2 = 1.5 m 분포, 지표 1 m 범위 [2020 요령 4.6 식 4.16~4.18, 편람 7-3])
  출력  : runs/abutment/A1_v3_result.json, runs/결과_교대_v3.md, runs/abutment/A1_v3_*.png
"""
import sys, os, json, math
sys.stdout.reconfigure(encoding="utf-8")
PJ = r"D:\Midas\projects\순천만IC2교"; RUNS = os.path.join(PJ, "runs"); OUT = os.path.join(RUNS, "abutment"); os.makedirs(OUT, exist_ok=True)
SUB = json.load(open(os.path.join(PJ, "하부_제원서.json"), encoding="utf-8")); A = SUB["교대"]["A1"]
RX = json.load(open(os.path.join(RUNS, "reactions_summary.json"), encoding="utf-8"))["support"]["A1"]
CB = json.load(open(os.path.join(PJ, "combos_2010.json"), encoding="utf-8"))
GEO = json.load(open(os.path.join(OUT, "geom_001.json"), encoding="utf-8"))["section"]
GC = SUB["재료"]["gamma_c"]; FCK, FY = SUB["재료"]["fck_구체"], SUB["재료"]["fy"]
# ── [단계 1] 형상 (도면 자동판독) : x = 앞굽 연단(교량 쪽) 0 → 뒷채움 쪽 +, z = 기초 저면 0 ──
toe, ts, heel, Bf = GEO["toe"], GEO["stem"], GEO["heel"], GEO["B"]
tf = A["기초두께"]; z_seat = A["받침면_EL"] - A["기초저면_EL"]; z_top = A["노면_EL"] - A["기초저면_EL"]
t_par = A["흉벽두께"]; hh = A.get("헌치높이", 1.739); x_stem0 = toe; x_stem1 = toe + ts; LW = A["폭"]
x_brg = GEO["x_shoe_from_toe"] if GEO.get("x_shoe_from_toe") else toe + ts / 2
assert GEO["haunch_on"] == "back" and GEO["front_side"], "도면 판독 방향 확인 필요"
H = z_top; Hw = z_top - tf; Hp = z_top - z_seat                      # 안정 토압 높이, 벽체 계산높이(기초상면~노면), 흉벽 높이
GEOM = [("① 기초", Bf * tf, Bf / 2, tf / 2, "DC"), ("② 벽체", ts * (z_seat - tf), x_stem0 + ts / 2, tf + (z_seat - tf) / 2, "DC"),
        ("③ 배면 헌치 1:1", hh * hh / 2, x_stem1 + hh / 3, tf + hh / 3, "DC"), ("④ 흉벽", t_par * Hp, x_stem1 - t_par / 2, z_seat + Hp / 2, "DC")]
_ar = heel * (z_top - tf); _cx = x_stem1 + heel / 2; _cz = tf + (z_top - tf) / 2; _at = hh * hh / 2; _tx = x_stem1 + hh / 3; _tz = tf + hh / 3
GEOM.append(("⑤ 뒷굽 위 흙", _ar - _at, (_ar * _cx - _at * _tx) / (_ar - _at), (_ar * _cz - _at * _tz) / (_ar - _at), "EV"))
# ── [단계 4] 설계조건 ──
TP = CB["토압"]; PHI, GAM, Q = TP["phi"], TP["gamma"], TP["q"]
MU_RUB = 0.15                                                        # 탄성받침 겉보기 정지마찰계수 [편람 4-1]
BRG = dict(n=2, cap_kN=250 * 9.80665, name="250톤 탄성받침(고무) ×2")  # 도면 교대 일반도
PILE = dict(n=A["말뚝"]["본수"], rows_from_toe=A["말뚝"].get("열위치_앞굽기준", [0.7, 3.4, 4.9]), per_row=6, D=SUB["말뚝"]["직경"], t=SUB["말뚝"]["두께_교대"], L=A["말뚝"]["길이"],
            fa=140.0, fa_v=80.0, corr=0.002, grade="SPS400")           # 장기 허용압축응력 140 MPa, 허용전단 80 MPa [편람 6-4·7-6, 도로교설계기준 2010 5.8]
REBAR = A.get("배근", {})                                              # 하부_제원서.json 교대 배근(도면 C0051105-005/006 판독)
F = CB["강도"]["①"]                                                     # 1.3D + 2.15(L+i) + 1.7H
PHI_F, PHI_V = 0.85, 0.80                                            # 도로교설계기준 2010 2.2.3.3 강도감소계수(휨 0.85, 전단 0.80)

def coulomb_ka(phi, delta, theta=0.0, alpha=0.0):
    p, d, t, a = map(math.radians, (phi, delta, theta, alpha))
    k3 = math.sin(p + d) * math.sin(p - a) / (math.cos(t + d) * math.cos(t - a))
    return math.cos(p - t) ** 2 / (math.cos(t) ** 2 * math.cos(t + d) * (1 + math.sqrt(k3)) ** 2)
def rankine_ka(phi): return math.tan(math.radians(45 - phi / 2)) ** 2
def bar_area(d): return {13: 126.7, 16: 198.6, 19: 286.5, 22: 387.1, 25: 506.7, 29: 642.4, 32: 794.2}[d]
def as_per_m(mark):
    """'D25@125' → mm²/m"""
    d, s = mark.upper().replace("D", "").split("@"); return bar_area(int(d)) * 1000 / float(s)
def phi_mn(As, d, b=1000.0, fck=FCK, fy=FY):
    """단철근 직사각형 φMn (kN·m), As mm², d mm"""
    a = As * fy / (0.85 * fck * b); return PHI_F * As * fy * (d - a / 2) / 1e6, a
def phi_vc(d, b=1000.0, fck=FCK): return PHI_V * math.sqrt(fck) / 6 * b * d / 1e3

def step4():
    Ka_r = rankine_ka(PHI); d_w = PHI / 3; Ka_c = coulomb_ka(PHI, d_w)
    return dict(Ka_stab=Ka_r, Ka_wall=Ka_c, delta_wall=d_w, D=RX["D"] / LW, LL=max(RX["Lmax"], 0.0) / LW, q=Q, mu=MU_RUB,
                table=[("φ (deg)", PHI, PHI), ("α, β (deg)", 0, 0), ("δ (deg)", 0.0, round(d_w, 3)), ("토압계수 K", round(Ka_r, 3), round(Ka_c, 3))])

def step5(c):
    """단위폭(1 m) 설계력. 모멘트는 앞굽 연단 기준(저항 +, 전도 −). 반환 rows(구분, V, H, x, y, Mr, Mo)"""
    rows = []
    for nm, ar, x, z, kind in GEOM:
        w = ar * (GC if kind == "DC" else GAM); rows.append(dict(name=nm, kind=kind, V=w, H=0.0, x=x, y=z, Mr=w * x, Mo=0.0, area=ar))
    D, LL = c["D"], c["LL"]; FR = MU_RUB * D
    rows.append(dict(name="상부 고정하중 반력", kind="DCs", V=D, H=FR, x=x_brg, y=z_seat, Mr=D * x_brg, Mo=FR * z_seat))
    Pa = 0.5 * c["Ka_stab"] * GAM * H ** 2; Pq = c["Ka_stab"] * Q * H
    rows.append(dict(name="배면 토압 (가상배면, Rankine)", kind="EH", V=0.0, H=Pa, x=Bf, y=H / 3, Mr=0.0, Mo=Pa * H / 3))
    rows.append(dict(name="배면 상재하중 토압 (q=10)", kind="LSH", V=0.0, H=Pq, x=Bf, y=H / 2, Mr=0.0, Mo=Pq * H / 2))
    rows.append(dict(name="뒷굽 위 상재하중", kind="LSV", V=Q * heel, H=0.0, x=x_stem1 + heel / 2, y=z_top, Mr=Q * heel * (x_stem1 + heel / 2), Mo=0.0))
    rows.append(dict(name="상부 활하중 반력", kind="LL", V=LL, H=0.0, x=x_brg, y=z_seat, Mr=LL * x_brg, Mo=0.0))
    def tot(kinds): return dict(V=sum(r["V"] for r in rows if r["kind"] in kinds), H=sum(r["H"] for r in rows if r["kind"] in kinds), Mr=sum(r["Mr"] for r in rows if r["kind"] in kinds), Mo=sum(r["Mo"] for r in rows if r["kind"] in kinds))
    cases = {"D+H (활하중 비재하)": tot(("DC", "EV", "DCs", "EH")), "D+L+H (활하중 재하)": tot(("DC", "EV", "DCs", "EH", "LSH", "LSV", "LL"))}
    for k, v in cases.items(): v["xi"] = (v["Mr"] - v["Mo"]) / v["V"]; v["e"] = Bf / 2 - v["xi"]
    return rows, cases, dict(Pa=Pa, Pq=Pq, FR=FR)

def step6(cases):
    """말뚝 반력(강체 캡, 관용법 [2020 요령 6.1.2 식 6.1]) — 전폭 환산. 수평력은 균등 분담. 본체 응력 f = R/Ae (휨은 지반 자료 없어 미산정)"""
    D, t = PILE["D"], PILE["t"] - PILE["corr"]; Ap = math.pi / 4 * (D ** 2 - (D - 2 * t) ** 2)
    Ra = Ap * PILE["fa"] * 1e3; n = PILE["n"]; xs = [r - Bf / 2 for r in PILE["rows_from_toe"]]; Sx2 = PILE["per_row"] * sum(x * x for x in xs)
    out = {}
    for k, v in cases.items():
        V = v["V"] * LW; Hh = v["H"] * LW; M = V * v["e"]                 # 말뚝군 도심 기준 모멘트 (편심 e, 교량 쪽 +)
        R = {f"R{i+1} (x={r:.1f})": V / n + M * (-(r - Bf / 2)) / Sx2 for i, r in enumerate(PILE["rows_from_toe"])}   # 앞굽(x 작음) 쪽이 압축 증가
        Rmax, Rmin = max(R.values()), min(R.values()); Hp = Hh / n
        out[k] = dict(V=V, H=Hh, M=M, e=v["e"], R=R, Rmax=Rmax, Rmin=Rmin, Hp=Hp, f=Rmax / Ap / 1e3, v=2.0 * Hp / Ap / 1e3, ok_R=Rmax <= Ra, ok_v=2.0 * Hp / Ap / 1e3 <= PILE["fa_v"], ok_t=Rmin >= 0)
    return dict(Ap=Ap, Ra=Ra, Sx2=Sx2, n=n, cases=out)

def wheel_on_parapet(Ka, T=96.0, a=0.2, b=0.5, wdist=1.5, depth=1.0, n=2000):
    """흉벽 윤하중 [2020 요령 4.6 식 4.16]: P(x) = Ka·T/((a+x)(b+x)), 지표 1 m 범위 합력·작용점, 차량점유폭 1/2 = 1.5 m 분포 → 단위폭"""
    dx = depth / n; Fs = 0.0; Ms = 0.0
    for i in range(n):
        x = (i + 0.5) * dx; p = Ka * T / ((a + x) * (b + x)); Fs += p * dx; Ms += p * dx * x
    return Fs / wdist, Ms / Fs                                            # kN/m, 지표에서 작용점 깊이(m)

def step7(c, cases, pl):
    d_w = c["delta_wall"]; Kc = c["Ka_wall"]; cosd = math.cos(math.radians(d_w)); out = {}
    # 7-1 벽체 기부 (기초 상면): 상부 고정하중 마찰력(D, 1.3), 토압(H, 1.7), 노면하중 토압(H, 1.7) — 활하중 반력은 축력이라 모멘트 없음
    Pa = 0.5 * Kc * GAM * Hw ** 2 * cosd; Pq = Kc * Q * Hw * cosd; FR = MU_RUB * c["D"]
    rows = [dict(name="상부하중 마찰력", formula="0.15 × 고정하중 반력", V=FR, arm=z_seat - tf, M=FR * (z_seat - tf), f=F["D"]),
            dict(name="토압", formula="½·Ka·γ·H²·cosδ", V=Pa, arm=Hw / 3, M=Pa * Hw / 3, f=F["H"]),
            dict(name="노면하중 토압", formula="Ka·q·H·cosδ", V=Pq, arm=Hw / 2, M=Pq * Hw / 2, f=F["H"])]
    Vu = sum(r["V"] * r["f"] for r in rows); Mu = sum(r["M"] * r["f"] for r in rows); Vs = sum(r["V"] for r in rows); Ms = sum(r["M"] for r in rows)
    wb = REBAR.get("벽체_배면_주철근", "D25@125"); As = as_per_m(wb); dd = ts * 1000 - REBAR.get("벽체_피복_mm", 100); Mn, a = phi_mn(As, dd); Vc = phi_vc(dd)
    out["stem"] = dict(rows=rows, Vu=Vu, Mu=Mu, Vs=Vs, Ms=Ms, bar=wb, As=As, d=dd, phiMn=Mn, phiVc=Vc, ratio_M=Mu / Mn, ratio_V=Vu / Vc, rho=As / (1000 * dd), rho_min=max(1.4 / FY, 0.25 * math.sqrt(FCK) / FY))
    # 7-2 수평철근: 0.0015·b·h (두께 1.2 m 상한) [도로교 2010 4.3.9]
    hb = REBAR.get("벽체_수평철근", "D19@150"); req = 0.0015 * 1000 * min(ts, 1.2) * 1000
    out["horiz"] = dict(bar=hb, As=2 * as_per_m(hb), req=req, ok=2 * as_per_m(hb) >= req)
    # 7-3 흉벽: 토압 + 윤하중
    Pap = 0.5 * Kc * GAM * Hp ** 2 * cosd; Pqp = Kc * Q * Hp * cosd; Fw, zw = wheel_on_parapet(Kc); Mw = Fw * (Hp - zw)
    prow = [dict(name="토압", formula="½·Ka·γ·h²·cosδ", V=Pap, arm=Hp / 3, M=Pap * Hp / 3, f=F["H"]),
            dict(name="상재하중 토압 (q=10)", formula="Ka·q·h·cosδ", V=Pqp, arm=Hp / 2, M=Pqp * Hp / 2, f=F["H"]),
            dict(name="윤하중 (DB-24 후륜 96 kN)", formula="Ka·T/((a+x)(b+x)) 적분, 1 m 범위", V=Fw, arm=Hp - zw, M=Mw, f=F["H"])]
    pb = REBAR.get("흉벽_주철근", "D16@150"); Asp = as_per_m(pb); dp = t_par * 1000 - REBAR.get("흉벽_피복_mm", 70); Mnp, _ = phi_mn(Asp, dp); Vcp = phi_vc(dp)
    # 경우 A: 토압 + 상재하중(준공 당시 설계 방식) / 경우 B: 토압 + 윤하중(2020 도로설계요령 4.6)
    VuA = F["H"] * (Pap + Pqp); MuA = F["H"] * (Pap * Hp / 3 + Pqp * Hp / 2); VuB = F["H"] * (Pap + Fw); MuB = F["H"] * (Pap * Hp / 3 + Mw)
    out["parapet"] = dict(rows=prow, Vu=VuB, Mu=MuB, VuA=VuA, MuA=MuA, bar=pb, As=Asp, d=dp, phiMn=Mnp, phiVc=Vcp, ratio_M=MuB / Mnp, ratio_V=VuB / Vcp, ratio_MA=MuA / Mnp, ratio_VA=VuA / Vcp, wheel=dict(F=Fw, z=zw))
    # 7-4 기초: 계수하중 말뚝 반력 (1.3D + 2.15L + 1.7H) → 앞굽·뒷굽 단면력 (편람 7-4~7-6)
    rows5, _, _ = step5(c); V = Hh = Mr = Mo = 0.0
    for r in rows5:
        f = {"DC": F["D"], "EV": F["D"], "DCs": F["D"], "EH": F["H"], "LSH": F["H"], "LSV": F["L"], "LL": F["L"]}[r["kind"]]
        V += f * r["V"]; Hh += f * r["H"]; Mr += f * r["Mr"]; Mo += f * r["Mo"]
    e = Bf / 2 - (Mr - Mo) / V; Vt = V * LW; Mt = Vt * e
    xs = [r - Bf / 2 for r in PILE["rows_from_toe"]]; Ru = [Vt / PILE["n"] + Mt * (-x) / pl["Sx2"] for x in xs]      # 본당
    Rm = [Ru[i] * PILE["per_row"] / LW for i in range(len(Ru))]                                                    # 단위폭당 열 반력
    # 앞굽: 벽체 전면(x=toe)에서 앞굽 연단 쪽 말뚝열 반력 − 앞굽 자중(1.3)
    toe_rows = [(Rm[i], toe - r) for i, r in enumerate(PILE["rows_from_toe"]) if r < toe]
    M_toe = sum(R * arm for R, arm in toe_rows) - F["D"] * toe * tf * GC * toe / 2
    dfoot = (tf * 1000 - REBAR.get("기초_피복_mm", 150)) / 1000; Dp = PILE["D"]
    def pile_share(dist_from_section):
        """전단 위험단면(벽면에서 d) 바깥쪽 말뚝 반력 포함률: 말뚝 중심이 단면에서 D/2 이상 바깥 1.0, D/2 이상 안쪽 0, 그 사이 직선 보간"""
        return min(1.0, max(0.0, (dist_from_section + Dp / 2) / Dp))
    V_toe = sum(R * pile_share((toe - dfoot) - r) for R, r in ((Rm[i], r) for i, r in enumerate(PILE["rows_from_toe"]) if r < toe)) - F["D"] * max(toe - dfoot, 0) * tf * GC
    out["shear_note"] = f"전단 위험단면 = 벽면에서 d = {dfoot:.3f} m (앞굽 x = {toe - dfoot:.3f}, 뒷굽 x = {x_stem1 + dfoot:.3f}); 말뚝 중심이 단면 안쪽으로 D/2 이상이면 미포함"
    # 뒷굽: 벽체 배면(x=x_stem1)에서 흙(1.3)+상재(2.15)+자중(1.3) − 뒷굽 쪽 말뚝열 반력
    soil = GEOM[4]; Ms_ = F["D"] * soil[1] * GAM * (soil[2] - x_stem1) + F["L"] * Q * heel * heel / 2 + F["D"] * heel * tf * GC * heel / 2
    heel_rows = [(Rm[i], r - x_stem1) for i, r in enumerate(PILE["rows_from_toe"]) if r > x_stem1]
    M_heel = Ms_ - sum(R * arm for R, arm in heel_rows)
    lh = max(heel - dfoot, 0)                                   # 뒷굽 전단 단면(벽 배면에서 d) 바깥 길이
    V_heel = (F["D"] * soil[1] * GAM + F["L"] * Q * heel + F["D"] * heel * tf * GC) * (lh / heel) - sum(R * pile_share(r - (x_stem1 + dfoot)) for R, r in ((Rm[i], r) for i, r in enumerate(PILE["rows_from_toe"]) if r > x_stem1))
    fb = REBAR.get("기초_주철근", "D22@150"); Asf = as_per_m(fb); df = tf * 1000 - REBAR.get("기초_피복_mm", 150); Mnf, _ = phi_mn(Asf, df); Vcf = phi_vc(df)
    out["footing"] = dict(Ru=Ru, Rm=Rm, e=e, V=Vt, M=Mt, toe=dict(Mu=M_toe, Vu=V_toe, ratio_M=abs(M_toe) / Mnf, ratio_V=abs(V_toe) / Vcf), heel=dict(Mu=M_heel, Vu=V_heel, ratio_M=abs(M_heel) / Mnf, ratio_V=abs(V_heel) / Vcf), bar=fb, As=Asf, d=df, phiMn=Mnf, phiVc=Vcf)
    return out

def figures(c, info):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = ["Malgun Gothic"]; plt.rcParams["axes.unicode_minus"] = False
    # (1) 검토단면·하중 블록·가상배면·토압
    fig, ax = plt.subplots(figsize=(9, 7)); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), Bf, tf, fill=False, lw=1.8)); ax.add_patch(plt.Rectangle((x_stem0, tf), ts, z_seat - tf, fill=False, lw=1.8))
    ax.add_patch(plt.Polygon([(x_stem1, tf), (x_stem1 + hh, tf), (x_stem1, tf + hh)], fill=False, lw=1.5)); ax.add_patch(plt.Rectangle((x_stem1 - t_par, z_seat), t_par, Hp, fill=False, lw=1.8))
    ax.add_patch(plt.Polygon([(x_stem1, tf + hh), (x_stem1 + hh, tf), (Bf, tf), (Bf, z_top), (x_stem1, z_top)], closed=True, fill=True, facecolor="#f2e6c9", edgecolor="#a08040", lw=0.8, hatch="..."))
    ax.plot([Bf, Bf], [0, z_top], "r--", lw=1.2); ax.text(Bf + 0.1, z_top * 0.55, "가상배면\n(안정검토, Rankine)", color="r", fontsize=9)
    ax.plot([x_stem1, x_stem1], [tf, z_top], "b--", lw=1.0); ax.text(x_stem1 + 0.05, tf + 0.3, "구체배면\n(단면검토, δ=φ/3)", color="b", fontsize=8)
    ax.plot([Bf, Bf + 2.5], [z_top, z_top], "k--", lw=0.8); ax.text(Bf + 0.6, z_top + 0.15, f"뒷채움 γ={GAM} kN/m³, φ={PHI}°, q={Q} kN/m²", fontsize=8)
    pk = info["Pa"] * 2 / H / 12; ax.add_patch(plt.Polygon([(Bf, 0), (Bf + pk, 0), (Bf, z_top)], fill=True, facecolor="#ffcccc", edgecolor="r", lw=0.8, alpha=0.6))
    ax.annotate("", (Bf + 0.05, H / 3), (Bf + pk * 0.8, H / 3), arrowprops=dict(arrowstyle="->", color="r")); ax.text(Bf + pk * 0.8 + 0.05, H / 3, "Pa (H/3)", color="r", fontsize=8, va="center")
    for r in PILE["rows_from_toe"]: ax.add_patch(plt.Rectangle((r - PILE["D"] / 2, -2.5), PILE["D"], 2.5, fill=False, lw=1)); ax.text(r, -2.9, f"{r:.1f}", ha="center", fontsize=8)
    for nm, ar, x, z, kind in GEOM: ax.text(x, z, nm.split()[0], ha="center", va="center", fontsize=11, weight="bold")
    def dim(x1, x2, y, t): ax.annotate("", (x1, y), (x2, y), arrowprops=dict(arrowstyle="<->", lw=0.7)); ax.text((x1 + x2) / 2, y - 0.32, t, ha="center", fontsize=8)
    dim(0, toe, -0.5, f"앞굽 {toe:.3f}"); dim(toe, x_stem1, -0.5, f"{ts:.3f}"); dim(x_stem1, Bf, -0.5, f"뒷굽 {heel:.3f}"); dim(0, Bf, -1.1, f"B = {Bf:.3f}")
    ax.annotate("", (-0.7, 0), (-0.7, z_seat), arrowprops=dict(arrowstyle="<->", lw=0.7)); ax.text(-0.95, z_seat / 2, f"받침면 {z_seat:.3f}", rotation=90, va="center", ha="center", fontsize=8)
    ax.annotate("", (-1.3, 0), (-1.3, z_top), arrowprops=dict(arrowstyle="<->", lw=0.7)); ax.text(-1.55, z_top / 2, f"H = {z_top:.3f}", rotation=90, va="center", ha="center", fontsize=8)
    ax.plot([x_brg], [z_seat], "kv", ms=8); ax.text(x_brg, z_seat + 0.3, f"받침 x={x_brg:.2f}\nR_D, R_L, 0.15R_D →", ha="center", fontsize=8)
    ax.text(toe / 2, z_seat + 1.0, "교량 쪽\n(앞굽)", ha="center", fontsize=9); ax.set_xlim(-1.9, Bf + 3.2); ax.set_ylim(-3.3, z_top + 0.9)
    fig.savefig(os.path.join(OUT, "A1_v3_section.png"), dpi=150, bbox_inches="tight"); plt.close(fig)
    # (2) 벽체·흉벽 하중도
    fig, axs = plt.subplots(1, 2, figsize=(9, 4.2))
    for ax, (hgt, thk, title, Ka, extra) in zip(axs, ((Hw, ts, f"벽체 (H = {Hw:.3f} m, 구체배면 Coulomb δ=φ/3)", c["Ka_wall"], "FR = 0.15·R_D"), (Hp, t_par, f"흉벽 (h = {Hp:.3f} m) — 토압 + 윤하중", c["Ka_wall"], "T = 96 kN, 1.5 m 분포"))):
        ax.set_aspect("equal"); ax.axis("off"); ax.add_patch(plt.Rectangle((0, 0), thk, hgt, fill=False, lw=1.8))
        pk = Ka * GAM * hgt / 10; ax.add_patch(plt.Polygon([(thk, 0), (thk + pk, 0), (thk, hgt)], facecolor="#ffcccc", edgecolor="r", lw=0.8))
        ax.text(thk + pk + 0.1, hgt / 3, "토압 (h/3)", color="r", fontsize=8, va="center"); ax.text(thk / 2, -0.4, extra, ha="center", fontsize=8)
        ax.set_title(title, fontsize=9); ax.set_xlim(-0.5, thk + pk + 2.0); ax.set_ylim(-0.8, hgt + 0.3)
    fig.savefig(os.path.join(OUT, "A1_v3_wall_loads.png"), dpi=150, bbox_inches="tight"); plt.close(fig)

def main():
    c = step4(); rows, cases, info = step5(c); pl = step6(cases); w = step7(c, cases, pl)
    brg = dict(name=BRG["name"], cap=BRG["cap_kN"], R=(RX["D"] + RX["Lmax"]) / BRG["n"], H=MU_RUB * RX["D"] / BRG["n"])
    brg["ratio"] = brg["R"] / brg["cap"]
    res = dict(geom=dict(toe=toe, stem=ts, heel=heel, B=Bf, tf=tf, z_seat=z_seat, z_top=z_top, t_par=t_par, hh=hh, x_brg=x_brg, LW=LW, Hw=Hw, Hp=Hp), soil=dict(phi=PHI, gamma=GAM, q=Q),
               cond=c, bearing=brg, loads=rows, cases=cases, info=info, piles=pl, section=w, rebar=REBAR, pile_spec=PILE)
    json.dump(res, open(os.path.join(OUT, "A1_v3_result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1); figures(c, info)
    rep = ["# 교대 A1 안전성 검토 v3 (도로설계편람 509.1 단계, 도로교설계기준 2010 강도설계 ①, 지진 제외)", "",
           f"[단계 1] 형상: 앞굽 {toe} m, 벽체 {ts} m, 뒷굽 {heel} m(배면 헌치 {hh} m), B = {Bf} m, 기초 {tf} m, 받침면 {z_seat:.3f} m, H = {z_top:.3f} m, 받침 x = {x_brg:.2f} m, 폭 {LW} m. 말뚝 {PILE['n']}본 ({len(PILE['rows_from_toe'])}열 × {PILE['per_row']}), 열 위치 {PILE['rows_from_toe']} m.",
           f"[단계 3] 받침: {brg['name']}, 반력 (D+L)/2 = {brg['R']:,.0f} kN ≤ 용량 {brg['cap']:,.0f} kN → 비 {brg['ratio']:.2f}",
           f"[단계 4] 뒷채움 γ = {GAM}, φ = {PHI}°, q = {Q}; 안정 Ka(Rankine) = {c['Ka_stab']:.3f}, 벽체 Ka(Coulomb δ=φ/3) = {c['Ka_wall']:.3f}; 상부반력 단위폭 D = {c['D']:.2f}, L = {c['LL']:.2f} kN/m; 받침 마찰 0.15 → FR = {info['FR']:.2f} kN/m", "",
           "## [단계 5] 하중집계 (단위폭, kN, m, kN·m; 앞굽 연단 기준)", "", "| 구분 | 수직력 | 수평력 | x | y | M저항 | M전도 |", "| :-- | --: | --: | --: | --: | --: | --: |"]
    for r in rows: rep.append(f"| {r['name']} | {r['V']:.2f} | {r['H']:.2f} | {r['x']:.3f} | {r['y']:.3f} | {r['Mr']:.2f} | {r['Mo']:.2f} |")
    for k, v in cases.items(): rep.append(f"| **{k}** | {v['V']:.2f} | {v['H']:.2f} | ξ={v['xi']:.3f} | e={v['e']:.3f} | {v['Mr']:.2f} | {v['Mo']:.2f} |")
    rep += ["", f"## [단계 6] 말뚝 반력 (강체 캡, 전폭 {LW} m; Ae = {pl['Ap']*1e4:.1f} cm² (부식 2 mm), Ra = {pl['Ra']:,.0f} kN, 허용전단 {PILE['fa_v']} MPa)", "", "| 조합 | ΣV | ΣH | e | " + " | ".join(pl["cases"][next(iter(pl["cases"]))]["R"].keys()) + " | 수평/본 | f (MPa) | v (MPa) | 판정 |", "|" + " :-- |" * (9 + len(PILE["rows_from_toe"]))]
    for k, v in pl["cases"].items(): rep.append(f"| {k} | {v['V']:.0f} | {v['H']:.0f} | {v['e']:.3f} | " + " | ".join(f"{x:.0f}" for x in v["R"].values()) + f" | {v['Hp']:.1f} | {v['f']:.1f} | {v['v']:.1f} | {'O.K' if v['ok_R'] and v['ok_v'] and v['ok_t'] else 'N.G'} |")
    st, hz, pa, ft = w["stem"], w["horiz"], w["parapet"], w["footing"]
    rep += ["", "## [단계 7] 단면검토 (강도설계 ①: 1.3D + 2.15(L+i) + 1.7H, φ 휨 0.85·전단 0.80)", "", "| 부재 | 배근 | As (mm²/m) | d (mm) | Mu (kN·m/m) | φMn | Mu/φMn | Vu (kN/m) | φVc | Vu/φVc |", "| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: |",
            f"| 벽체 기부 | {st['bar']} | {st['As']:.0f} | {st['d']:.0f} | {st['Mu']:.1f} | {st['phiMn']:.1f} | {st['ratio_M']:.3f} | {st['Vu']:.1f} | {st['phiVc']:.1f} | {st['ratio_V']:.3f} |",
            f"| 흉벽 기부 | {pa['bar']} | {pa['As']:.0f} | {pa['d']:.0f} | {pa['Mu']:.1f} | {pa['phiMn']:.1f} | {pa['ratio_M']:.3f} | {pa['Vu']:.1f} | {pa['phiVc']:.1f} | {pa['ratio_V']:.3f} |",
            f"| 앞굽판 | {ft['bar']} | {ft['As']:.0f} | {ft['d']:.0f} | {ft['toe']['Mu']:.1f} | {ft['phiMn']:.1f} | {ft['toe']['ratio_M']:.3f} | {ft['toe']['Vu']:.1f} | {ft['phiVc']:.1f} | {ft['toe']['ratio_V']:.3f} |",
            f"| 뒷굽판 | {ft['bar']} | {ft['As']:.0f} | {ft['d']:.0f} | {ft['heel']['Mu']:.1f} | {ft['phiMn']:.1f} | {ft['heel']['ratio_M']:.3f} | {ft['heel']['Vu']:.1f} | {ft['phiVc']:.1f} | {ft['heel']['ratio_V']:.3f} |",
            "", f"수평철근: {hz['bar']} 양면 As = {hz['As']:.0f} mm²/m ≥ 0.0015·b·h = {hz['req']:.0f} → {'O.K' if hz['ok'] else 'N.G'}. 흉벽 윤하중 합력 {pa['wheel']['F']:.2f} kN/m, 작용점 지표 아래 {pa['wheel']['z']:.3f} m.",
            f"기초 계수하중 말뚝반력(본당) {['%.0f' % x for x in ft['Ru']]} kN, e = {ft['e']:.3f} m.", "",
            "제외: [단계 2] 지진변위 검토·지진시 하중(내진성능평가 별도), [단계 8] 접속슬래브, [단계 9] 날개벽. 말뚝 지반 지지력·침하·수평변위는 지반조사·시공기록 없음 → 미산정."]
    open(os.path.join(RUNS, "결과_교대_v3.md"), "w", encoding="utf-8").write("\n".join(rep))
    for k, v in cases.items(): print(f"{k}: V {v['V']:.1f} H {v['H']:.1f} e {v['e']:.3f} | 말뚝 Rmax {pl['cases'][k]['Rmax']:.0f} Rmin {pl['cases'][k]['Rmin']:.0f} f {pl['cases'][k]['f']:.1f} MPa")
    print(f"벽체 Mu {st['Mu']:.1f} / φMn {st['phiMn']:.1f} = {st['ratio_M']:.3f} | 흉벽 {pa['ratio_M']:.3f} | 앞굽 {ft['toe']['ratio_M']:.3f} | 뒷굽 {ft['heel']['ratio_M']:.3f} | 받침 {brg['ratio']:.2f}"); print("저장 결과_교대_v3.md")

if __name__ == "__main__":
    main()

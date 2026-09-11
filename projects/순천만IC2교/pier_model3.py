# -*- coding: utf-8 -*-
"""
교각 안전성 검토 v3 — 도로설계편람 제5편(2008) 509.2 T형 교각 설계 예의 [단계] 흐름(진단용), 지진하중 제외, 도로교설계기준 2010 강도설계 ①~⑥·⑧·⑨ + 사용조합
  [1] 검토조건  [2] 단면제원·제상수(변단면 코핑 포함)  [3] 하중(상부반력 만재/편재, 풍, 제동, 온도·마찰)  [4] 하중조합(2010 식, 지진 ⑦ 제외)
  [5] NX 프레임 해석(pier_model.run_nx 재사용: 변단면 코핑·밀도 보정) → 하중별·조합별 기둥 상·하단 단면력
  [6] 부재검토: 코핑(브래킷/깊은보 판정·주철근·전단), 기둥(세장비·모멘트확대·P–M 강도비·전단), [7] 기초(강체판정·말뚝 반력(사용하중)·기초 단면), [8] 받침 용량
  배근: 하부_제원서.json 교각 배근(도면 판독). 사용: python pier_model3.py [P1..P5] [--norun]
  출력: runs/pier3/<P>_result.json, runs/결과_교각_v3.md, 캡처 runs/pier3/<P>_*.jpg
"""
import sys, os, json, math
sys.stdout.reconfigure(encoding="utf-8")
PJ = r"D:\Midas\projects\순천만IC2교"; sys.path.insert(0, PJ); sys.path.insert(0, r"D:\Midas\tools")
import pier_model as PM
from pier_model import SUB, RX, CB, GC, EC, FCK, FY, MU, P_WIND, H_W, H_WL, pier_geom, taper_area, build_mct, pier_weights, parse, rc_column_capacity, pm_ratio, autocrop
RUNS = PM.RUNS; OUT = os.path.join(RUNS, "pier3"); os.makedirs(OUT, exist_ok=True); PM.OUT = OUT
PHI_F, PHI_V, PHI_C = 0.85, 0.80, 0.70          # 2010 2.2.3.3: 휨 0.85, 전단 0.80, 띠철근 기둥 0.70
BAR = {13: 126.7, 16: 198.6, 19: 286.5, 22: 387.1, 25: 506.7, 29: 642.4, 32: 794.2}
BRG_CAP = {"P1": 600, "P2": 700, "P3": 700, "P4": 600, "P5": 600}   # 톤 (도면 받침 표기; P5 STB측 확인 필요)

def make_loads(g, rx):
    """지진 제외 하중 케이스 (pier_model.make_loads에서 EQ 제거)"""
    L = PM.make_loads(g, rx)
    for k in ("EQX", "EQY"): L["con"].pop(k, None); L["beam"].pop(k, None)
    L["cases"] = [k for k in L["cases"] if not k.startswith("EQ")]; L["info"].pop("seismic", None)
    return L

def combine(R):
    """2010 강도 ①~⑥·⑧·⑨(⑦ 지진 제외) + 사용 1~5·0. 활하중은 만재/최소/편재(G1·G2) 4가지. 반환 {key: dict(kind, cid, fD, L, base[6])}"""
    grp = {"D": ["DEAD", "RD"], "CF": ["CF"], "W": ["W"], "WL": ["WL"], "BK": ["LF"], "G": ["TP", "FR"]}
    def vec(c): return R.get(c, [0.0] * 6)
    res = {}
    for kind in ("강도", "사용"):
        for cid, f in CB[kind].items():
            if f.get("E"): continue
            for Lc in ((["RLmax"], ["RLmin"], ["RL_G1"], ["RL_G2"]) if f["L"] else (["RLmax"],)):
                v = [0.0] * 6
                for gk, fac in (("D", f["D"]), ("CF", f["CF"]), ("W", f["W"]), ("WL", f["WL"]), ("BK", f["BK"]), ("G", f["G"])):
                    for c in grp[gk]:
                        for i in range(6): v[i] += fac * vec(c)[i]
                for c in Lc:
                    for i in range(6): v[i] += f["L"] * vec(c)[i]
                res[f"{kind} {cid} | L={Lc[0]}"] = dict(kind=kind, cid=cid, fD=f["D"], L=Lc[0], base=v)
                if kind == "강도" and f.get("D_min", 1.0) != f["D"]:            # 표 2.2.6 최소 축하중·최대 편심 (고정하중계수 1.0/0.95/0.9)
                    vm = [v[i] - (f["D"] - f["D_min"]) * sum(vec(c)[i] for c in grp["D"]) for i in range(6)]
                    res[f"강도 {cid}(편심) | L={Lc[0]}"] = dict(kind="강도", cid=cid, fD=f["D_min"], L=Lc[0], base=vm)
    return res

def section_props(g):
    """[단계 2] 단면 제상수: 기둥(사각), 코핑 줄기(변단면 3.0→6.5 선형 근사) 위치별 A·I"""
    rows = [dict(name="기둥", b=g["by"], h=g["bx"], A=g["bx"] * g["by"], Iy=g["by"] * g["bx"] ** 3 / 12, Ix=g["bx"] * g["by"] ** 3 / 12)]
    for z, w in ((0.0, g["by"]), (2.5, (g["by"] + g["cop_top"]) / 2), (5.0, g["cop_top"]), (g["Hcop"], g["cop_top"])):
        rows.append(dict(name=f"코핑 z={z:.1f}", b=w, h=g["cop_t"], A=w * g["cop_t"], Iy=w * g["cop_t"] ** 3 / 12, Ix=g["cop_t"] * w ** 3 / 12))
    rows.append(dict(name="코핑 실제(Y형)", b=None, h=g["cop_t"], A=g["cop_area"] * g["cop_t"], Iy=None, Ix=None, note=f"정면적 {g['cop_area']:.3f} m² × {g['cop_t']} m = {g['cop_area']*g['cop_t']:.2f} m³"))
    return rows

def coping_check(g, rx, rb):
    """[단계 6-1~6-3] 코핑 팔: 위험단면 기둥면, 브래킷(av/d ≤ 1) 또는 깊은보(ln/d < 5) 판정 [편람 6-2·6-3, 도로교 2010 4.4.6.8·콘크리트 7.7]. 하중: 강도 ① 받침 1개 최대 반력"""
    hb = g["s_brg"] / 2; av = hb - g["by"] / 2; h = g["Hcop"]; d = h - rb.get("코핑_피복_mm", 150) / 1000; b = g["cop_t"]
    Vu = max(CB["강도"]["①"]["D"] * rx["D_g"][gd] + CB["강도"]["①"]["L"] * max(rx["L_g"][gd][0], 0) for gd in ("G1", "G2"))
    Nuc = 0.2 * Vu; Mu = Vu * av + Nuc * (h - d)
    mode = "브래킷" if av / d <= 1.0 else ("깊은보" if 2 * av / d < 5 else "보")
    Vn_max = min(0.2 * FCK * 1000 * b * d, 5.6 * 1000 * b * d); phiVn = PHI_V * Vn_max
    mu = 1.4; Avf = Vu * 1e3 / (PHI_V * FY * mu)                                    # mm²
    # Af: Mu/φ = Af·fy·(d − a/2), a = Af·fy/(0.85·fck·b) → 이차식
    A_ = FY ** 2 / (2 * 0.85 * FCK * b * 1000); B_ = -FY * d * 1000; C_ = Mu * 1e6 / PHI_F
    Af = (-B_ - math.sqrt(B_ ** 2 - 4 * A_ * C_)) / (2 * A_); An = Nuc * 1e3 / (PHI_F * FY)
    As_req = max(Af + An, 2 * Af / 3 + An); As_min = 0.04 * FCK / FY * b * 1000 * d * 1000
    n29 = rb.get("코핑_주철근_본수", 48); As_use = n29 * BAR[29]
    Ah_req = 0.5 * (As_req - An); s_h = rb.get("코핑_띠철근_간격_mm", 250); Ah_use = 2 * BAR[25] * (2 * d * 1000 / 3) / s_h
    # 깊은보 전단 (수직 C3 D25@250, 수평 CS D22 무시)
    ln = 2 * av; Vc = math.sqrt(FCK) / 6 * b * d * 1000; Av = 2 * BAR[25]; Vs = (Av / s_h * (1 + ln / d) / 12) * FY * d * 1000 / 1000
    return dict(av=av, d=d, h=h, b=b, Vu=Vu, Nuc=Nuc, Mu=Mu, mode=mode, av_d=av / d, phiVn_max=phiVn, ok_Vn=Vu <= phiVn, Avf=Avf, Af=Af, An=An, As_req=As_req, As_min=As_min, As_use=As_use,
                ratio_As=As_req / As_use, ratio_Asmin=As_min / As_use, Ah_req=Ah_req, Ah_use=Ah_use, ratio_Ah=Ah_req / Ah_use, ln=ln, ln_d=ln / d, phiVc=PHI_V * Vc, phiVn_deep=PHI_V * (Vc + Vs), ratio_V=Vu / (PHI_V * (Vc + Vs)))

def column_check(g, rows, rb):
    """[단계 6-7~6-11] 기둥: 세장비(k=2.1 캔틸레버), 모멘트확대 δs = 1/(1 − Pu/0.75Pc) [콘크리트구조설계기준 6.5], P–M 강도비(φ=0.70), 전단"""
    As = rb.get("기둥_As_mm2", 0.0) / 1e6; Lu = g["Hc"]; k = 2.1
    out = dict(As=As * 1e6, rho=As / (g["bx"] * g["by"]), Lu=Lu, k=k, cases=[])
    for dirn, (b, h) in (("x", (g["by"], g["bx"])), ("y", (g["bx"], g["by"]))):      # x: 교축 휨 My (깊이 bx), y: 교축직각 휨 Mx (깊이 by)
        r = h / math.sqrt(12); lam = k * Lu / r; Ig = b * h ** 3 / 12
        cap = rc_column_capacity(b, h, As, phi=PHI_C); out[f"lambda_{dirn}"] = lam; out[f"slender_{dirn}"] = lam >= 22
        for c in rows:
            if c["kind"] != "강도": continue
            P = c["P"]; M = abs(c["My"] if dirn == "x" else c["Mx"]); PD = c["fD"] * c["PD"]
            bd = min(PD / P, 1.0) if P > 0 else 0.0; EI = 0.4 * EC * Ig / (1 + bd); Pc = math.pi ** 2 * EI / (k * Lu) ** 2
            ds = 1.0 / (1 - P / (0.75 * Pc)) if P < 0.75 * Pc else 99.0; ds = max(ds, 1.0); Mm = ds * M
            out["cases"].append(dict(key=c["key"], dirn=dirn, P=P, M=M, bd=bd, Pc=Pc, ds=ds, Mmag=Mm, ratio=pm_ratio(cap, P, Mm)))
        out[f"cap_{dirn}"] = cap
    out["worst"] = max(out["cases"], key=lambda c: c["ratio"]) if out["cases"] else None
    # 전단: 계수 조합 최대 수평력 vs φVc (d ≈ 0.8h 보수적), 띠철근 D16@300 2가닥
    Vmax = max((math.hypot(c["Vx"], c["Vy"]), c["key"]) for c in rows if c["kind"] == "강도"); d = 0.8 * g["bx"]
    Vc = math.sqrt(FCK) / 6 * g["by"] * d * 1000; Av = 2 * BAR[16]; s = 300.0; Vs = Av * FY * d * 1000 / s / 1000
    out["shear"] = dict(Vu=Vmax[0], key=Vmax[1], phiVc=PHI_V * Vc, phiVn=PHI_V * (Vc + Vs), ratio=Vmax[0] / (PHI_V * (Vc + Vs)), Av_min=0.35 * g["by"] * 1000 * s / FY, Av_use=Av)
    return out

def footing_check(g, rows, piles, rb, Wf):
    """[단계 7] 기초: 강체판정 βλ ≤ 1 [도로교 2010 5.4.5.2], 말뚝 반력(사용조합), 기초 단면(기둥면, 강도 조합 말뚝반력 − 자중, F D25@125)"""
    ft = g["foot"]; L_, B_, tf = ft; D = SUB["말뚝"]["직경"]; t = SUB["말뚝"]["두께_교각"] - 0.002; Ap = math.pi / 4 * (D ** 2 - (D - 2 * t) ** 2)
    Lp = g["piles"]["길이"]; a = 0.014 * (Lp / D) + 0.78; Kv = a * Ap * 2.1e8 / Lp; n = g["piles"]["본수"]
    kp = Kv * n / (L_ * B_); beta = (3 * kp / (EC * tf ** 3)) ** 0.25; lam = max((L_ - g["bx"]) / 2, (B_ - g["by"]) / 2); rigid = beta * lam <= 1.0
    # 말뚝 반력: 사용 조합 최대/최소, 계수 조합은 기초 단면용
    use = [c for c in rows if c["kind"] == "사용"]; fac = [c for c in rows if c["kind"] == "강도"]
    pmax_u = max(use, key=lambda c: c["pile_max"]); pmin_u = min(use, key=lambda c: c["pile_min"]); hp_u = max(c["pile_h"] for c in use)
    Ra = Ap * 140 * 1e3
    # 기초 단면: 기둥면 바깥 말뚝열 반력 × 팔 − 자중 (교축 방향, 계수 조합 최대)
    xs, ys = piles["xs"], piles["ys"]; Sx2, Sy2 = piles["Sx2"], piles["Sy2"]; best = None
    for c in fac:
        Pf = c["Pf"]; Mxf, Myf = c["Mxf"], c["Myf"]
        for dirn, coords, other_n, half, S2, M in (("x", xs, len(ys), g["bx"] / 2, Sx2, abs(Myf)), ("y", ys, len(xs), g["by"] / 2, Sy2, abs(Mxf))):
            outer = [(Pf / n + M * x / S2) * other_n for x in coords if x > half + 1e-6]; arms = [x - half for x in coords if x > half + 1e-6]
            lc = (L_ if dirn == "x" else B_) / 2 - half; wsw = c["fD"] * GC * tf * (B_ if dirn == "x" else L_)
            Mu = sum(R * ar for R, ar in zip(outer, arms)) - wsw * lc ** 2 / 2; Vu = sum(outer) - wsw * lc
            if best is None or Mu > best["Mu"]: best = dict(key=c["key"], dirn=dirn, Mu=Mu, Vu=Vu, lc=lc, R=outer)
    bar = rb.get("기초_주철근_규격", "D25@125"); dd_, ss_ = bar.replace("D", "").split("@"); As_m = BAR[int(dd_)] * 1000 / float(ss_)
    width = (B_ if best["dirn"] == "x" else L_); As = As_m * width; d = tf * 1000 - rb.get("기초_피복_mm", 150)
    a_ = As * FY / (0.85 * FCK * width * 1000); phiMn = PHI_F * As * FY * (d - a_ / 2) / 1e6; phiVc = PHI_V * math.sqrt(FCK) / 6 * width * 1000 * d / 1e3
    return dict(Ap=Ap, a=a, Kv=Kv, kp=kp, beta=beta, lam=lam, beta_lam=beta * lam, rigid=rigid, Ra=Ra, pile_max=pmax_u["pile_max"], pile_max_key=pmax_u["key"], pile_min=pmin_u["pile_min"], pile_min_key=pmin_u["key"], pile_h=hp_u,
                ratio_pile=pmax_u["pile_max"] / Ra, f_pile=pmax_u["pile_max"] / Ap / 1e3, section=dict(**best, bar=bar, As=As, d=d, phiMn=phiMn, phiVc=phiVc, ratio_M=best["Mu"] / phiMn, ratio_V=best["Vu"] / phiVc), Wf=Wf)

def analyse(name, do_run=True):
    g = pier_geom(name); rx = RX[name]; rb = SUB["교각"].get(name, {}).get("배근") or SUB["교각"]["P3"].get("배근", {}); loads = make_loads(g, rx)
    mct, N, E = build_mct(g, loads); mp = os.path.join(OUT, f"{name}.mct"); open(mp, "w", encoding="utf-8").write(mct); fj = os.path.join(OUT, f"{name}_tables.json")
    if do_run:
        bf, rc = PM.run_nx(name, mp, loads["cases"], g); json.dump(dict(bf=bf, rc=rc), open(fj, "w", encoding="utf-8"), ensure_ascii=False)
    else:
        d = json.load(open(fj, encoding="utf-8")); bf, rc = d["bf"], d["rc"]
    F, R = parse(bf, rc, loads["cases"]); combos = combine(R)
    nP = g["piles"]["본수"]; ft = g["foot"]; nx = int(round(math.sqrt(nP))); ny = nP // nx; sx = (ft[0] - 1.4) / max(nx - 1, 1); sy = (ft[1] - 1.4) / max(ny - 1, 1)
    xs = [(-(nx - 1) / 2 + i) * sx for i in range(nx)]; ys = [(-(ny - 1) / 2 + j) * sy for j in range(ny)]; Sx2 = sum(x * x for x in xs) * ny; Sy2 = sum(y * y for y in ys) * nx
    Wf = loads["info"]["weights"]["foot"]; tf = ft[2]; PD = R["DEAD"][2] + R["RD"][2]
    rows = []
    for key, c in combos.items():
        FX, FY_, FZ, MX, MY, MZ = c["base"]; Pf = FZ + c["fD"] * Wf; Mxf = MX - FY_ * tf; Myf = MY + FX * tf
        pmax = Pf / nP + abs(Myf) * max(xs) / Sx2 + abs(Mxf) * max(ys) / Sy2; pmin = Pf / nP - abs(Myf) * max(xs) / Sx2 - abs(Mxf) * max(ys) / Sy2
        rows.append(dict(key=key, kind=c["kind"], cid=c["cid"], fD=c["fD"], L=c["L"], P=FZ, Vx=FX, Vy=FY_, Mx=MX, My=MY, PD=PD, Pf=Pf, Mxf=Mxf, Myf=Myf, pile_max=pmax, pile_min=pmin, pile_h=math.hypot(FX, FY_) / nP))
    piles = dict(n=nP, xs=xs, ys=ys, Sx2=Sx2, Sy2=Sy2)
    cop = coping_check(g, rx, rb); col = column_check(g, rows, rb); fnd = footing_check(g, rows, piles, rb, Wf)
    cap = BRG_CAP.get(name, 600) * 9.80665; Rb = max(rx["D_g"][gd] + max(rx["L_g"][gd][0], 0) for gd in ("G1", "G2")); brg = dict(cap=cap, R=Rb, ratio=Rb / cap, ton=BRG_CAP.get(name, 600))
    # 하중별 기둥 상·하단 단면력 표 (요소 2 J단 = 기둥 상단, 절점 1 반력 = 하단)
    per_load = {}
    for c in ["DEAD"] + loads["cases"]:
        top = F.get(c, {}).get((2, "J"), [0] * 6); base = R.get(c, [0] * 6)
        per_load[c] = dict(top=dict(P=-top[0], My=top[4], Mx=top[5], Vx=top[2], Vy=top[1]), base=dict(P=base[2], Vx=base[0], Vy=base[1], Mx=base[3], My=base[4]))
    rep_keys = {"축력최대": max(rows, key=lambda r: r["P"] if r["kind"] == "강도" else -1)["key"], "교축직각 모멘트최대": max(rows, key=lambda r: abs(r["Mx"]) if r["kind"] == "강도" else -1)["key"],
                "교축 모멘트최대": max(rows, key=lambda r: abs(r["My"]) if r["kind"] == "강도" else -1)["key"], "편심최대(최소축력)": min(rows, key=lambda r: r["P"] if r["kind"] == "강도" else 1e12)["key"]}
    out = dict(name=name, geom=g, rebar=rb, loads_info=loads["info"], per_load=per_load, combos=rows, rep=rep_keys, props=section_props(g), coping=cop, column=col, footing=fnd, bearing=brg, piles=piles)
    for tag in ("model", "My_RD"): autocrop(os.path.join(OUT, f"{name}_{tag}.jpg"))
    json.dump(out, open(os.path.join(OUT, f"{name}_result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    return out

def report(results):
    rep = ["# 교각 안전성 검토 v3 (도로설계편람 509.2 단계, 도로교설계기준 2010 강도 ①~⑥·⑧·⑨ + 사용조합, 지진 제외)", "",
           f"단위 kN, kN·m. 기둥 3.0(교축직각)×2.5(교축). φ: 휨 0.85, 전단 0.80, 기둥 0.70. 받침마찰 {MU}, 하부 풍하중 {P_WIND} kN/m². 말뚝 허용 140 MPa(SPS400 장기), 배근은 도면 판독값(제원서).", "",
           "## [단계 3·5] 하중별 기둥 하단 단면력 (P3 대표 형식, 전 교각 JSON 참조)", ""]
    for r in results:
        rep += [f"### {r['name']} — 받침 {r['bearing']['ton']}톤: (D+L)max/받침 = {r['bearing']['R']:,.0f} kN, 용량 {r['bearing']['cap']:,.0f} kN, 비 {r['bearing']['ratio']:.2f}", "", "| 하중 | P | Vx | Vy | Mx | My |", "| :-- | --: | --: | --: | --: | --: |"]
        for c, v in r["per_load"].items(): b = v["base"]; rep.append(f"| {c} | {b['P']:.0f} | {b['Vx']:.0f} | {b['Vy']:.0f} | {b['Mx']:.0f} | {b['My']:.0f} |")
        rep += ["", "| 대표 조합 | 조합 | P | Mx | My | Vx | Vy |", "| :-- | :-- | --: | --: | --: | --: | --: |"]
        for nm, key in r["rep"].items():
            c = next(x for x in r["combos"] if x["key"] == key); rep.append(f"| {nm} | {key} | {c['P']:.0f} | {c['Mx']:.0f} | {c['My']:.0f} | {c['Vx']:.0f} | {c['Vy']:.0f} |")
        rep.append("")
    rep += ["## [단계 6] 코핑 (기둥면 위험단면)", "", "| 교각 | av | d | av/d | 판정 | Vu | Mu | φVn,max | As 소요(강도)/사용 | 비 | As,min(0.04fck/fy·bd)/사용 | Ah 소요/사용 | 비 | 깊은보 Vu/φ(Vc+Vs) |", "| :-- | --: | --: | --: | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |"]
    for r in results:
        c = r["coping"]; rep.append(f"| {r['name']} | {c['av']:.3f} | {c['d']:.3f} | {c['av_d']:.3f} | {c['mode']} | {c['Vu']:.0f} | {c['Mu']:.0f} | {c['phiVn_max']:.0f} | {c['As_req']:.0f}/{c['As_use']:.0f} | {c['ratio_As']:.3f} | {c['As_min']:.0f} ({c['ratio_Asmin']:.2f}) | {c['Ah_req']:.0f}/{c['Ah_use']:.0f} | {c['ratio_Ah']:.3f} | {c['ratio_V']:.3f} |")
    rep += ["", "## [단계 6] 기둥 (세장비·모멘트확대·P–M, 전단)", "", "| 교각 | As (ρ) | λx/λy | 최불리 조합 | 방향 | Pu | Mu | δs | δs·Mu | Mu/φMn | 전단 Vu/φVn |", "| :-- | --: | --: | :-- | :-- | --: | --: | --: | --: | --: | --: |"]
    for r in results:
        c = r["column"]; w = c["worst"]; rep.append(f"| {r['name']} | {c['As']:.0f} ({c['rho']*100:.2f} %) | {c['lambda_x']:.1f}/{c['lambda_y']:.1f} | {w['key']} | {w['dirn']} | {w['P']:.0f} | {w['M']:.0f} | {w['ds']:.3f} | {w['Mmag']:.0f} | {w['ratio']:.3f} | {c['shear']['ratio']:.3f} |")
    rep += ["", "## [단계 7] 기초·말뚝", "", "| 교각 | Kv (kN/m) | βλ | 강체 | 말뚝 max (사용) | 조합 | 말뚝 min | 수평/본 | R/Ra | 기초 단면 Mu | φMn | 비 | Vu/φVc |", "| :-- | --: | --: | :-- | --: | :-- | --: | --: | --: | --: | --: | --: | --: |"]
    for r in results:
        f = r["footing"]; s = f["section"]; rep.append(f"| {r['name']} | {f['Kv']:,.0f} | {f['beta_lam']:.3f} | {'O.K' if f['rigid'] else 'N.G'} | {f['pile_max']:.0f} | {f['pile_max_key']} | {f['pile_min']:.0f} | {f['pile_h']:.0f} | {f['ratio_pile']:.3f} | {s['Mu']:.0f} ({s['dirn']}) | {s['phiMn']:.0f} | {s['ratio_M']:.3f} | {s['ratio_V']:.3f} |")
    rep += ["", "제외: 지진하중·응답수정계수·심부구속철근(내진성능평가), 받침 연단거리·최소 받침지지길이(내진), 말뚝 지반 지지력·침하·수평변위(지반자료 없음). P4·P5 말뚝 배치, P5 코핑(상폭 8.0)·PSC측 반력은 확인 필요."]
    open(os.path.join(RUNS, "결과_교각_v3.md"), "w", encoding="utf-8").write("\n".join(rep)); print("저장 결과_교각_v3.md")

if __name__ == "__main__":
    argv = sys.argv[1:]; do_run = "--norun" not in argv; names = [n for n in argv if n.startswith("P")] or ["P1", "P2", "P3", "P4", "P5"]
    results = []
    for n in names:
        print("==", n); r = analyse(n, do_run); results.append(r)
        print(f"  코핑 {r['coping']['mode']} As비 {r['coping']['ratio_As']:.3f}(최소철근비 {r['coping']['ratio_Asmin']:.2f}) | 기둥 {r['column']['worst']['ratio']:.3f} ({r['column']['worst']['key']}) | 말뚝 {r['footing']['ratio_pile']:.3f} | 기초 {r['footing']['section']['ratio_M']:.3f} | 받침 {r['bearing']['ratio']:.2f}")
    report(results)

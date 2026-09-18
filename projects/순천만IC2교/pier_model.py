# -*- coding: utf-8 -*-
"""
교각 해석 도구 (NX 모델 생성 → 해석 → 하중조합 → 코핑·기둥·말뚝 검토)
  입력 : 하부_제원서.json(교각 제원), runs/reactions_summary.json(상부반력, reactions.py), combos_2010.json(하중조합)
  모델 : X=교축(종점 방향 +), Y=교축직각(G1 측 +), Z=상향, 원점=기초 상면·기둥 중심. 기둥(사각)+코핑 줄기+코핑 팔(받침 좌석 절점) 프레임, 기초상면 고정
        정정 구조이므로 단면력은 강성과 무관(단면은 자중·지진주기 산정용). 말뚝은 기초 저면 강체 캡 가정으로 파이썬 계산
  하중 : 각 하중을 별도 ST 케이스로 재하 → 요소력·반력 추출 → 파이썬에서 조합(도로교설계기준 2010 강도 I~VII, 사용 I~VII)
  검토 : 기둥 P–M 상관(변형률 적합, 사각단면), 코핑 휨·전단, 말뚝 축력·수평력. 배근은 REBAR 매개변수(배근도 확보 전 '확인 필요')
  사용 : python pier_model.py [P1 P2 ...]   (인수 없으면 P1~P5)
  산출 : runs/pier/<P>.mct/.mcb, runs/pier/<P>_forces.json, runs/pier/<P>_*.jpg(캡처), runs/결과_교각.md
"""
import sys, os, json, math, time
sys.stdout.reconfigure(encoding="utf-8")
PJ = r"D:\Midas\projects\순천만IC2교"; RUNS = os.path.join(PJ, "runs"); OUT = os.path.join(RUNS, "pier"); os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, r"D:\Midas\core\tools"); sys.path.insert(0, PJ)
import mct_syntax as M
SUB = json.load(open(os.path.join(PJ, "하부_제원서.json"), encoding="utf-8"))
RX = json.load(open(os.path.join(RUNS, "reactions_summary.json"), encoding="utf-8"))["support"]
CB = json.load(open(os.path.join(PJ, "combos_2010.json"), encoding="utf-8"))
G = 9.80665
FCK, FY = SUB["재료"]["fck_구체"], SUB["재료"]["fy"]; GC = SUB["재료"]["gamma_c"]; EC = SUB["재료"]["Ec"] * 1000.0   # kN/m²
MU = CB["받침마찰계수"]; P_WIND = CB["풍하중"]["p_pier"]
CODE = "kds" if "--code" in sys.argv and sys.argv[sys.argv.index("--code") + 1] == "kds" else "2010"   # 조합 체계: 2010(강도 ①~⑨) | kds(한계상태 combos_kds.json)
if CODE == "kds": OUT = os.path.join(RUNS, "pier_kds"); os.makedirs(OUT, exist_ok=True)
GOV_COP = "극한 I" if CODE == "kds" else "강도 ①"
H_DECK = 2.30 + 0.30          # 받침 상면 ~ 노면 (거더 2.3 + 바닥판·포장 0.3)
H_WL = H_DECK + 1.8           # 활하중 풍하중·원심·제동 작용높이 (노면 위 1.8 m)
H_W = (H_DECK + 1.32) / 2     # 상부 풍하중 작용높이 (수압면 중심: 거더+바닥판+방호벽 1.32)
# 배근(배근도 없음 → 확인 필요). 기둥 3.0×2.5: 주철근 As_total, 코핑: 상면 인장 As
REBAR = {"col_As": 0.0, "col_bars": "확인 필요", "cop_As": 0.0, "cop_bars": "확인 필요", "cop_d": 5.9, "cop_bw": 2.5, "cover": 0.1}

def pier_geom(name):
    p = SUB["교각"][name]; c = SUB["교각"]["_공통"]
    Hc = p["기둥높이"]; Hcop = c["코핑_높이"]; Hs = Hc + Hcop
    return dict(name=name, Hc=Hc, Hcop=Hcop, Hs=Hs, bx=c["기둥_교축"], by=c["기둥_교축직각"], cop_top=p.get("코핑_상폭", c["코핑_상폭"]), cop_t=c["코핑_두께(교축)"], cop_v=c["코핑_상단수직부"],
                cop_area=p.get("코핑_정면단면적", c.get("코핑_정면단면적")), cop_zc=c.get("코핑_도심높이_기둥상단기준"),   # Y형 정면 단면적(m², tools/pier_geom.py DXF 적분)
                s_brg=c["받침간격"], foot=p["기초"], piles=p["말뚝"], EL_seat=p["받침_EL"], EL_foot=p["기초상면_EL"], brg=p["받침"])

def taper_area(g):
    """NX 변단면 모델(줄기 3.0→6.5 선형 + 머리 6.5×상단수직부)의 정면 면적 — 실제 Y형 면적과의 비로 코핑 재료 밀도를 보정"""
    return (g["by"] + g["cop_top"]) / 2 * (g["Hcop"] - g["cop_v"]) + g["cop_top"] * g["cop_v"]

def nx_sections_materials(c, g):
    """MCT 임포트 후 API로 실제 형상 반영: 코핑 줄기 변단면(3.0→4.75→6.5), 머리 6.5, 팔은 무게 0·상면 정렬(CT) 부재.
    재료: 기둥 C24(γ=GC), 코핑 C24_COP(γ=GC×실제면적/변단면면적 → NX 자중 = 도면 Y형 자중), 팔 ARM_W0(γ=0)."""
    def sb(name, b, offset="CC"):
        return {"SECTTYPE": "DBUSER", "SECT_NAME": name, "SECT_BEFORE": {"OFFSET_PT": offset, "OFFSET_CENTER": 0, "USER_OFFSET_REF": 0, "HORZ_OFFSET_OPT": 0, "USERDEF_OFFSET_YI": 0, "VERT_OFFSET_OPT": 0, "USERDEF_OFFSET_ZI": 0,
                                                                          "USE_SHEAR_DEFORM": True, "USE_WARPING_EFFECT": False, "SHAPE": "SB", "DATATYPE": 2, "SECT_I": {"vSIZE": [g["cop_t"], b, 0, 0, 0, 0, 0, 0, 0, 0]}}}
    def tap(name, b1, b2):
        return {"SECTTYPE": "TAPERED", "SECT_NAME": name, "SECT_BEFORE": {"OFFSET_PT": "CC", "OFFSET_CENTER": 0, "USER_OFFSET_REF": 0, "HORZ_OFFSET_OPT": 0, "USERDEF_OFFSET_YI": 0, "USERDEF_OFFSET_YJ": 0, "VERT_OFFSET_OPT": 0,
                                                                          "USERDEF_OFFSET_ZI": 0, "USERDEF_OFFSET_ZJ": 0, "USE_SHEAR_DEFORM": True, "USE_WARPING_EFFECT": False, "SHAPE": "SB", "TYPE": 2,
                                                                          "SECT_I": {"vSIZE": [g["cop_t"], b1, 0, 0, 0, 0, 0, 0, 0, 0]}, "SECT_J": {"vSIZE": [g["cop_t"], b2, 0, 0, 0, 0, 0, 0, 0, 0]}, "Y_VAR": 1, "Z_VAR": 1}}
    bm = (g["by"] + g["cop_top"]) / 2
    c.put("/db/SECT", {"Assign": {"2": tap("COP_STEM_L", g["by"], bm), "5": tap("COP_STEM_U", bm, g["cop_top"]), "3": sb("COP_HEAD", g["cop_top"]), "4": sb("COP_ARM", 1.6, "CT")}})
    ratio = g["cop_area"] / taper_area(g)
    def usr(name, den, E=EC):
        # NX 2026 실측: 사용자 등방성 재료는 P_TYPE 2 + 평면 키(ELAST/POISN/THERMAL/DEN/MASS). 도움말의 P_TYPE 1+USER_DEFINED 형식은 거부됨
        return {"TYPE": "CONC", "NAME": name, "HE_SPEC": 0, "HE_COND": 0, "bMASS_DENS": False, "DAMP_RAT": 0.05, "PARAM": [{"P_TYPE": 2, "ELAST": E, "POISN": 0.2, "THERMAL": 1e-5, "DEN": den, "MASS": 0}]}
    r = c.put("/db/MATL", {"Assign": {"1": usr("C24", GC), "2": usr("C24_COP", GC * ratio), "3": usr("ARM_W0", 0.0, 10 * EC)}})
    if "error" in json.dumps(r): raise RuntimeError("MATL PUT 실패: " + json.dumps(r, ensure_ascii=False)[:200])
    E = c.get("/db/ELEM")["ELEM"]; upd = {}
    for e, (m, s) in {"3": (2, 2), "4": (2, 5), "5": (2, 3), "6": (3, 4), "7": (3, 4)}.items():
        d = dict(E[e]); d["MATL"] = m; d["SECT"] = s; upd[e] = d
    c.put("/db/ELEM", {"Assign": upd})
    S = c.get("/db/SECT")["SECT"]; Mt = c.get("/db/MATL")["MATL"]; Eb = c.get("/db/ELEM")["ELEM"]
    ok = S["2"]["SECTTYPE"] == "TAPERED" and S["5"]["SECTTYPE"] == "TAPERED" and S["4"]["SECT_BEFORE"]["OFFSET_PT"] == "CT" and len(Mt) == 3 and all(Eb[e]["MATL"] == m and Eb[e]["SECT"] == s for e, (m, s) in {"3": (2, 2), "4": (2, 5), "5": (2, 3), "6": (3, 4), "7": (3, 4)}.items())
    print(f"  단면·재료 되읽기 {'OK' if ok else '★불일치'}: 코핑 밀도비 {ratio:.4f} (Y형 {g['cop_area']:.3f} / 변단면 {taper_area(g):.3f} m²)")
    if not ok: raise RuntimeError("단면·재료 배정 불일치")

def build_mct(g, loads):
    """loads: {case: [(node, fx, fy, fz, mx, my, mz)]}, beam: {case: [(elem, dir, w)]}"""
    Hc, Hs, hb = g["Hc"], g["Hs"], g["s_brg"] / 2
    N = {1: (0, 0, 0), 2: (0, 0, Hc / 2), 3: (0, 0, Hc), 4: (0, 0, Hc + 2.5), 5: (0, 0, Hc + 5.0), 6: (0, 0, Hs), 7: (0, hb, Hs), 8: (0, -hb, Hs)}
    E = [(1, 1, 1, 1, 2), (2, 1, 1, 2, 3), (3, 1, 2, 3, 4), (4, 1, 2, 4, 5), (5, 1, 3, 5, 6), (6, 1, 4, 6, 7), (7, 1, 4, 6, 8)]
    s = M.header(f"교각 {g['name']} 프레임 모델 (순천만IC2교)", ["X 교축, Y 교축직각(G1 +), Z 상향, 원점 기초상면", "정정 구조: 단면력은 강성 무관"]) + M.version() + M.unit() + M.structype()
    s += M.nodes(N) + M.elements(E)
    s += M.material_conc(1, "C24", EC)
    s += "\n*SECTION    ; Section\n"
    for sid, nm, H, B in ((1, "COL_3.0x2.5", g["bx"], g["by"]), (2, "COP_STEM", g["cop_t"], 4.2), (3, "COP_HEAD", g["cop_t"], g["cop_top"]), (4, "COP_ARM", g["cop_t"], 1.6)):
        s += M.section_rect(sid, nm, H, B).strip().split("\n")[-1] + "\n"          # 한 블록에 4행 (빈 줄 금지)
    cases = [("DEAD", "D")] + [(k, "D" if k.startswith("R") or k == "FR" else ("L" if k.startswith("L") else ("W" if k.startswith("W") else ("L" if k.startswith("EQ") else ("T" if k in ("TP", "TM") else ("CF" if k == "CF" else "L")))))) for k in loads["cases"]]
    s += M.stldcase(cases); s += M.selfweight("DEAD")
    for k in loads["cases"]:
        if loads["con"].get(k): s += M.conload(k, loads["con"][k])
        if loads["beam"].get(k):
            s += f"\n*USE-STLD, {k}\n*BEAMLOAD    ; Element Beam Loads\n"
            for e, d, w in loads["beam"][k]: s += f"  {e}, BEAM   , UNILOAD, {d}, NO , NO, aDir[1], , , , 0, {w:.4f}, 1, {w:.4f}, 0, 0, 0, 0, , NO, 0, 0, NO, \n"
    s += M.constraint([("1", "111111")]) + M.enddata()
    return s, N, E

def pier_weights(g):
    """코핑·기둥·기초 자중(kN) — 코핑은 도면 Y형 실제 단면적 (사다리꼴 근사 아님)"""
    cop = g["cop_area"] * g["cop_t"] * GC          # Y형 정면 단면적(도면 DXF 적분) × 두께 × γc — NX 자중(밀도 보정)과 동일
    col = g["bx"] * g["by"] * g["Hc"] * GC
    ft = g["foot"][0] * g["foot"][1] * g["foot"][2] * GC
    return cop, col, ft

def seismic_coeff(g, W_super):
    """단일모드 정적등가: T = 2π√(m/k), k = 3EI/H³(받침 높이), Cs = 1.2·A·S/T^(2/3) ≤ 2.5A (도로교설계기준 2010 6.5)"""
    A, S = CB["지진"]["A"], CB["지진"]["S"]; cop, col, ft = pier_weights(g)
    W = W_super + cop + 0.5 * col; m = W / G
    out = {}
    for d, I in (("X", g["by"] * g["bx"] ** 3 / 12), ("Y", g["bx"] * g["by"] ** 3 / 12)):
        k = 3 * EC * I / g["Hs"] ** 3; T = 2 * math.pi * math.sqrt(m / k)
        Cs = min(1.2 * A * S / T ** (2 / 3), CB["지진"]["Cs_max_factor"] * A)
        out[d] = dict(I=I, k=k, T=T, Cs=Cs, W=W)
    return out

def make_loads(g, rx):
    """하중 케이스 정의. 반환 dict(cases, con, beam, info)"""
    hb = g["s_brg"] / 2; con = {}; beam = {}; info = {}
    D1, D2 = rx["D_g"]["G1"], rx["D_g"]["G2"]; con["RD"] = [(7, 0, 0, -D1, 0, 0, 0), (8, 0, 0, -D2, 0, 0, 0)]
    L1, L2 = rx["L_g"]["G1"], rx["L_g"]["G2"]
    con["RLmax"] = [(7, 0, 0, -L1[0], 0, 0, 0), (8, 0, 0, -L2[0], 0, 0, 0)]          # 만재(양 주형 max)
    con["RLmin"] = [(7, 0, 0, -L1[1], 0, 0, 0), (8, 0, 0, -L2[1], 0, 0, 0)]
    one = rx.get("L_one")
    if one and (one["L1"]["G1"] or one["L2"]["G2"]):      # 편재: 1차선 재하 케이스(run3 case1)의 주형별 동시 반력
        con["RL_G1"] = [(7, 0, 0, -one["L1"]["G1"], 0, 0, 0), (8, 0, 0, -one["L1"]["G2"], 0, 0, 0)]
        con["RL_G2"] = [(7, 0, 0, -one["L2"]["G1"], 0, 0, 0), (8, 0, 0, -one["L2"]["G2"], 0, 0, 0)]
    else:                                                 # 1차선 결과가 없으면 상한값(G1 max, G2 min≥0) — 편심 상한
        con["RL_G1"] = [(7, 0, 0, -L1[0], 0, 0, 0), (8, 0, 0, -max(L2[1], 0.0), 0, 0, 0)]
        con["RL_G2"] = [(7, 0, 0, -max(L1[1], 0.0), 0, 0, 0), (8, 0, 0, -L2[0], 0, 0, 0)]
    H = rx["H"]
    # 풍하중: 상부(격자 반력, 수압중심 높이 보정 모멘트) + 교각 자체(3.0 kN/m² × 폭)
    wy = H["W"][1]; con["W"] = [(7, 0, wy / 2, 0, wy / 2 * H_W, 0, 0), (8, 0, wy / 2, 0, wy / 2 * H_W, 0, 0)]
    beam["W"] = [(e, "GY", -P_WIND * g["bx"]) for e in (1, 2)] + [(e, "GY", -P_WIND * g["cop_t"]) for e in (3, 4, 5)]   # 교축직각 풍 (Y−)
    wl = H["WL"][1]; con["WL"] = [(7, 0, wl / 2, 0, wl / 2 * H_WL, 0, 0), (8, 0, wl / 2, 0, wl / 2 * H_WL, 0, 0)]
    cf = H["CF"][1]; con["CF"] = [(7, 0, cf / 2, 0, cf / 2 * H_WL, 0, 0), (8, 0, cf / 2, 0, cf / 2 * H_WL, 0, 0)]
    fixed = "고정" in g["brg"]
    lf = H["LF"][0] if fixed else 0.0; con["LF"] = [(7, lf / 2, 0, 0, 0, -lf / 2 * H_WL, 0), (8, lf / 2, 0, 0, 0, -lf / 2 * H_WL, 0)]
    tp = H["TP"][0] if fixed else 0.0; con["TP"] = [(7, tp / 2, 0, 0, 0, 0, 0), (8, tp / 2, 0, 0, 0, 0, 0)]
    fr = 0.0 if fixed else MU * rx["D"]; con["FR"] = [(7, fr / 2, 0, 0, 0, 0, 0), (8, fr / 2, 0, 0, 0, 0, 0)]        # 가동받침 마찰(온도 이동)
    sc = seismic_coeff(g, rx["D"]); info["seismic"] = sc; cop, col, ft = pier_weights(g); info["weights"] = dict(cop=cop, col=col, foot=ft)
    for d, (ix, iy) in (("X", (1, 0)), ("Y", (0, 1))):
        Cs = sc[d]["Cs"]; F = Cs * rx["D"]
        con[f"EQ{d}"] = [(7, ix * F / 2, iy * F / 2, 0, 0, 0, 0), (8, ix * F / 2, iy * F / 2, 0, 0, 0, 0)]
        wcol = Cs * g["bx"] * g["by"] * GC; wcop = Cs * cop / g["Hcop"]
        beam[f"EQ{d}"] = [(e, "GX" if d == "X" else "GY", wcol) for e in (1, 2)] + [(e, "GX" if d == "X" else "GY", wcop) for e in (3, 4, 5)]
    cases = ["RD", "RLmax", "RLmin", "RL_G1", "RL_G2", "W", "WL", "CF", "LF", "TP", "FR", "EQX", "EQY"]
    info["fixed"] = fixed; info["fr"] = fr; info["lf"] = lf; info["tp"] = tp
    return dict(cases=cases, con=con, beam=beam, info=info)

def run_nx(name, mct_path, cases, g):
    from midas_api import Civil
    import run3
    c = Civil(timeout=900)
    c.post("/doc/SAVEAS", {"Argument": r"D:\Midas\runs\_scratch.mcb"}); c.post("/doc/NEW", {"Argument": {}})
    c.post("/doc/IMPORTMXT", {"Argument": mct_path}); nn, ne = c.node_count(), c.elem_count(); print(f"  되읽기 절점 {nn}/8 요소 {ne}/7")
    if (nn, ne) != (8, 7): raise RuntimeError("MCT 임포트 불일치")
    nx_sections_materials(c, g)                      # 변단면 코핑·밀도 보정·무게 0 팔
    c.post("/doc/SAVEAS", {"Argument": mct_path.replace(".mct", ".mcb")})
    t = time.time(); print("  ANAL:", c.post("/doc/ANAL", {"Assign": {}}).get("message"), f"({time.time()-t:.0f}s)")
    allc = ["DEAD"] + cases
    bf = run3.table(c, "BEAMFORCE", [1, 2, 3, 4, 5, 6, 7], cases=[f"{k}(ST)" for k in allc], parts=["PartI", "PartJ"])
    rc = run3.table(c, "REACTIONG", [1], cases=[f"{k}(ST)" for k in allc])
    H = rc["SS_Table"]["HEAD"]; dead = [float(dict(zip(H, r))["FZ"]) for r in rc["SS_Table"]["DATA"] if dict(zip(H, r))["Load"].startswith("DEAD")][0]
    cop, col, ft = pier_weights(g); exp = cop + col
    print(f"  자중 검증: NX DEAD {dead:.1f} kN vs 도면 기준 코핑 {cop:.0f} + 기둥 {col:.0f} = {exp:.1f} kN ({(dead / exp - 1) * 100:+.2f} %)")
    if abs(dead / exp - 1) > 0.01: raise RuntimeError("NX 자중이 도면 기준과 1 % 이상 다름")
    # 캡처: 모델(정면 Y-Z), 모멘트도(RD)
    for tag, arg in (("model", {"SET_MODE": "pre", "ANGLE": {"HORIZONTAL": 90, "VERTICAL": 0}, "DISPLAY": {"NODE": {"NODE": True, "NODE_NUMBER": True}, "ELEMENT": {"ELEMENT_NUMBER": True}, "PERSPECTIVE": False, "ZOOM_LEVEL": 260}}),
                     ("My_RD", {"SET_MODE": "post", "ANGLE": {"HORIZONTAL": 90, "VERTICAL": 0}, "DISPLAY": {"PERSPECTIVE": False, "ZOOM_LEVEL": 260},
                                "RESULT_GRAPHIC": {"CURRENT_MODE": "beamdiagrams", "LOAD_CASE_COMB": {"TYPE": "ST", "NAME": "RD"}, "COMPONENTS": {"PART": "total", "COMP": "My"},
                                                   "DISPLAY_OPTIONS": {"FIDELITY": "Exact", "FILL": "line fill", "SCALE": 1.0}, "TYPE_OF_DISPLAY": {"CONTOUR": {"OPT_CHECK": True}, "LEGEND": {"OPT_CHECK": True}, "VALUES": {"OPT_CHECK": True, "DECIMAL_PT": 0, "VALUE_EXP": False}}}})):
        a = dict(arg); a.update({"SET_HIDDEN": False, "EXPORT_PATH": os.path.join(OUT, f"{name}_{tag}.jpg"), "WIDTH": 2400, "HEIGHT": 3000})
        try: c.post("/view/CAPTURE", {"Argument": a})
        except Exception as e: print("  캡처 실패:", str(e)[:120])
    return bf, rc

def parse(bf, rc, cases):
    """요소력: {case: {(elem, part): [Fx, Fy, Fz, Mx, My, Mz]}}, 반력 {case: [FX..MZ]}"""
    F = {}; H = bf["SS_Table"]["HEAD"]
    for r in bf["SS_Table"]["DATA"]:
        d = dict(zip(H, r)); k = d["Load"].split("(")[0]; F.setdefault(k, {})[(int(d["Elem"]), d["Part"][0])] = [float(d[x]) for x in ("Axial", "Shear-y", "Shear-z", "Torsion", "Moment-y", "Moment-z")]
    R = {}; H = rc["SS_Table"]["HEAD"]
    for r in rc["SS_Table"]["DATA"]:
        d = dict(zip(H, r)); R[d["Load"].split("(")[0]] = [float(d[x]) for x in ("FX", "FY", "FZ", "MX", "MY", "MZ")]
    return F, R

def combine(R, F, info):
    """조합별 기둥 기저(절점 1 반력 = 기초상면 작용력)와 코핑 근원(요소 5 J단 / 요소 6·7 I단) 단면력.
    하중군: D = DEAD+RD, L = 활(만재/편재 4가지 중 최불리), CF, W(+WL), LF, T = TP 또는 FR, EQ = ±EQX ± 0.3EQY / ±0.3EQX ± EQY"""
    # 도로교설계기준(2010) 2.2.3.2 식 ①~⑨ / 표 2.2.3 : D=DEAD+RD, L=RL*, CF, W, WL, BK=LF, G=TP+FR(온도 이동·마찰), E=EQ, H·Q·CO=0(교각)
    grp = {"D": ["DEAD", "RD"], "CF": ["CF"], "W": ["W"], "WL": ["WL"], "BK": ["LF"], "G": ["TP", "FR"]}
    def vec(case, src): return src.get(case, [0.0] * 6)
    def gsum(keys, src): return [sum(vec(k, src)[i] for k in keys) for i in range(6)]
    res = {}; Rcol = CB["지진"]["R_기둥"]; Rfnd = Rcol / 2.0          # 6.4.7.2 기초 설계지진력 = 탄성지진력 / (R/2)
    for kind in ("강도", "사용"):
        for cid, f in CB[kind].items():
            for Lc in ((["RLmax"], ["RLmin"], ["RL_G1"], ["RL_G2"]) if f["L"] else (["RLmax"],)):
                for eq in ([], ["EQX+", "EQY+"], ["EQX+", "EQY-"], ["EQY+", "EQX+"], ["EQY+", "EQX-"]) if f["E"] else ([],):
                    if f["E"] and not eq: continue
                    src = R; v = [0.0] * 6; ve = [0.0] * 6
                    def add(keys, fac, s=src):
                        for i in range(6): v[i] += fac * gsum(keys, s)[i]
                    add(grp["D"], f["D"]); add(Lc, f["L"]); add(grp["CF"], f["CF"]); add(grp["W"], f["W"]); add(grp["WL"], f["WL"]); add(grp["BK"], f["BK"]); add(grp["G"], f["G"])
                    for j, e in enumerate(eq):
                        k, sg = e[:-1], (1 if e[-1] == "+" else -1); fac = (1.0 if j == 0 else 0.3) * sg * f["E"]
                        for i in range(6): ve[i] += fac * vec(k, src)[i]
                    key = f"{kind} {cid} | L={Lc[0]}" + (f" | EQ={'/'.join(eq)}" if eq else "")
                    # 6.3.4: 하부구조 축방향력·전단력은 R 미적용, 모멘트만 /R. 기초는 /(R/2)
                    col = [v[i] + (ve[i] / Rcol if i >= 3 else ve[i]) for i in range(6)]
                    fnd = [v[i] + (ve[i] / Rfnd if i >= 3 else ve[i]) for i in range(6)]
                    res[key] = {"base": fnd, "base_col": col, "elastic": [a + b for a, b in zip(v, ve)]}
    return res

def combine_kds(R, F, info):
    """한계상태설계법 조합 (combos_kds.json = 도로교설계기준 2016 표 3.4.1·3.4.2 / KDS 24 12 11).
    DC = DEAD+RD (γp 1.25/0.90 두 경우), LL = RL*(변형 4종), CF, WS = W, WL, BR = LF, FR = FR(마찰), TU = TP(0.5/1.2 중 불리), EQ.
    지진: 기둥 모멘트 /R(단일기둥 3, KDS 24 17 11 표 4.1-4), 축력·전단 R 미적용; 기초는 R 미적용 탄성력(4.2.7.2, 소성힌지력 미산정)"""
    K = json.load(open(os.path.join(PJ, "combos_kds.json"), encoding="utf-8")); gp = K["gamma_p"]; Rcol = K["검토기준"]["지진"]["R_기둥"]
    def vec(c): return R.get(c, [0.0] * 6)
    def add(v, keys, fac):
        for k in keys:
            for i in range(6): v[i] += fac * vec(k)[i]
    res = {}
    for cid, f in K["조합"].items():
        gDCs = [f["DC_override"]] if "DC_override" in f else ([1.0] if f.get("gamma_p_override") else gp["DC"])
        for gDC in gDCs:
            for Lc in ((["RLmax"], ["RLmin"], ["RL_G1"], ["RL_G2"]) if f["LL"] else (["RLmax"],)):
                for eq in ([], ["EQX+", "EQY+"], ["EQX+", "EQY-"], ["EQY+", "EQX+"], ["EQY+", "EQX-"]) if f["EQ"] else ([],):
                    if f["EQ"] and not eq: continue
                    v = [0.0] * 6; ve = [0.0] * 6
                    add(v, ["DEAD", "RD"], gDC); add(v, Lc, f["LL"]); add(v, ["CF"], f["CF"]); add(v, ["W"], f["WS"]); add(v, ["WL"], f["WL"]); add(v, ["LF"], f["BR"]); add(v, ["FR"], f["FR"])
                    tu = f["TU"]; gTU = max(tu) if isinstance(tu, list) else tu; add(v, ["TP"], gTU)
                    for j, e in enumerate(eq):
                        k, sg = e[:-1], (1 if e[-1] == "+" else -1); fac = (1.0 if j == 0 else 0.3) * sg * f["EQ"]
                        for i in range(6): ve[i] += fac * vec(k)[i]
                    key = f"{cid} | DC {gDC:g} | L={Lc[0]}" + (f" | EQ={'/'.join(eq)}" if eq else "")
                    col = [v[i] + (ve[i] / Rcol if i >= 3 else ve[i]) for i in range(6)]
                    res[key] = {"base": [a + b for a, b in zip(v, ve)], "base_col": col, "elastic": [a + b for a, b in zip(v, ve)]}
    return res

def rc_column_capacity(b, h, As_tot, n_layers=4, fck=FCK, fy=FY, phi=0.65):
    """사각 기둥 P–M 상관 (변형률 적합, 등가응력블록). 철근은 둘레 균등(4변 배치 근사: 상·하 각 3/8, 중간 1/4 2층)
    반환: [(phiPn, phiMn)] 곡선 (kN, kN·m). As_tot=0이면 무근(콘크리트만)"""
    Es = 200000.0; ecu = 0.003; b1 = 0.85 if fck <= 28 else max(0.65, 0.85 - 0.007 * (fck - 28))
    d1 = 0.10; layers = [(d1, 3 / 8), (h / 3, 1 / 8), (2 * h / 3, 1 / 8), (h - d1, 3 / 8)]
    pts = []
    for c in [x * h for x in (0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5, 2.0, 4.0)]:
        a = min(b1 * c, h); Cc = 0.85 * fck * 1000 * a * b; Pn = Cc; Mn = Cc * (h / 2 - a / 2)
        for y, frac in layers:
            As = As_tot * frac; es = ecu * (c - y) / c; fs = max(-fy, min(fy, Es * es)); fs_eff = fs - (0.85 * fck if (y < a and fs > 0) else 0)
            Fs = As * fs_eff * 1000; Pn += Fs; Mn += Fs * (h / 2 - y)
        pts.append((phi * Pn, phi * Mn))
    P0 = 0.85 * fck * 1000 * (b * h - As_tot) + fy * 1000 * As_tot; pts.append((phi * 0.8 * P0, 0.0))
    return pts

def pm_ratio(pts, P, Mres):
    """주어진 P(압축 +)에서 φMn 보간 → M/φMn"""
    pts = sorted(pts, key=lambda t: t[0]); Pmax = pts[-1][0]
    if P >= Pmax: return 99.0
    for (p1, m1), (p2, m2) in zip(pts, pts[1:]):
        if p1 <= P <= p2:
            m = m1 + (m2 - m1) * (P - p1) / (p2 - p1 + 1e-9); return Mres / m if m > 0 else 99.0
    return Mres / pts[0][1] if pts[0][1] > 0 else 99.0

def analyse_pier(name, do_run=True):
    g = pier_geom(name); rx = RX[name]; loads = make_loads(g, rx)
    mct, N, E = build_mct(g, loads); mp = os.path.join(OUT, f"{name}.mct"); open(mp, "w", encoding="utf-8").write(mct)
    fj = os.path.join(OUT, f"{name}_tables.json")
    if do_run:
        bf, rc = run_nx(name, mp, loads["cases"], g); json.dump(dict(bf=bf, rc=rc), open(fj, "w", encoding="utf-8"), ensure_ascii=False)
    else:
        d = json.load(open(fj, encoding="utf-8")); bf, rc = d["bf"], d["rc"]
    F, R = parse(bf, rc, loads["cases"])
    # 기둥 기저: 절점 1 반력(구조물이 받는 힘) → 기둥 하단 단면력: P = FZ, Vx = FX, Vy = FY, Mx = MX(교축직각 하중), My = MY(교축 하중)
    res = combine_kds(R, F, loads["info"]) if CODE == "kds" else combine(R, F, loads["info"])
    # 검토: 기둥 P–M (교축·교축직각 각각), 말뚝
    b, h = g["by"], g["bx"]                     # 교축직각 폭 3.0, 교축 두께 2.5
    cap_x = rc_column_capacity(g["by"], g["bx"], REBAR["col_As"])   # 교축 방향 휨(My) : 압축연 폭 = by, 깊이 = bx
    cap_y = rc_column_capacity(g["bx"], g["by"], REBAR["col_As"])   # 교축직각 휨(Mx)
    nP = g["piles"]["본수"]; ft = g["foot"]
    # 말뚝 좌표(격자 근사: 정사각/직사각 균등)
    nx = int(round(math.sqrt(nP))); ny = nP // nx; sx = (ft[0] - 2 * 0.7) / max(nx - 1, 1); sy = (ft[1] - 2 * 0.7) / max(ny - 1, 1)
    xs = [(-(nx - 1) / 2 + i) * sx for i in range(nx)]; ys = [(-(ny - 1) / 2 + j) * sy for j in range(ny)]
    Sx2 = sum(x * x for x in xs) * ny; Sy2 = sum(y * y for y in ys) * nx
    Wf = loads["info"]["weights"]["foot"]; tf = ft[2]
    rows = []; worst = {"col_x": (0, None), "col_y": (0, None), "pile_max": (-1e9, None), "pile_min": (1e9, None), "Pmax": (0, None), "Pmin": (1e9, None)}
    for key, v in res.items():
        FX, FY, FZ, MX, MY, MZ = v["base"]; kind = key.split()[0]
        fD = float(key.split("| DC ")[1].split(" |")[0]) if CODE == "kds" else CB[kind][key.split()[1]]["D"]
        P, Mx, My = v["base_col"][2], v["base_col"][3], v["base_col"][4]      # 기둥 하단 (기초 상면), 지진 모멘트/R 적용
        # 기초 저면: 기초 자중 추가, 수평력에 의한 모멘트 증가 (두께 tf). 말뚝 배열 판정은 사용하중(계수 없음) 조합 기준 (2.2.3.2 (6))
        Pf = FZ + fD * Wf; Mxf = MX - FY * tf; Myf = MY + FX * tf
        pmax = Pf / nP + abs(Myf) * max(xs) / Sx2 + abs(Mxf) * max(ys) / Sy2; pmin = Pf / nP - abs(Myf) * max(xs) / Sx2 - abs(Mxf) * max(ys) / Sy2
        hp = math.hypot(FX, FY) / nP
        r = dict(key=key, P=P, Vx=FX, Vy=FY, Mx=Mx, My=My, Pf=Pf, Mxf=Mxf, Myf=Myf, pile_max=pmax, pile_min=pmin, pile_h=hp)
        if REBAR["col_As"] > 0:
            r["ratio_x"] = pm_ratio(cap_x, P, abs(My)); r["ratio_y"] = pm_ratio(cap_y, P, abs(Mx))
        rows.append(r)
        for kk, val in (("col_x", abs(My)), ("col_y", abs(Mx)), ("pile_max", pmax), ("Pmax", P)):
            if val > worst[kk][0]: worst[kk] = (val, key)
        for kk, val in (("pile_min", pmin), ("Pmin", P)):
            if val < worst[kk][0]: worst[kk] = (val, key)
    # 소요 주철근량(기둥): 조합별 (P, M)이 P–M 곡선 안에 들도록 하는 최소 As_tot (이축은 각 방향 별도, 근사)
    def req_As(dirn):
        lo, hi = 0.0, 0.08 * g["bx"] * g["by"]
        def ok(As):
            cap = rc_column_capacity(g["by"], g["bx"], As) if dirn == "x" else rc_column_capacity(g["bx"], g["by"], As)
            return all(pm_ratio(cap, r["P"], abs(r["My"] if dirn == "x" else r["Mx"])) <= 1.0 for r in rows)
        if ok(lo): return 0.0
        if not ok(hi): return hi
        for _ in range(30):
            mid = (lo + hi) / 2
            if ok(mid): hi = mid
            else: lo = mid
        return hi
    As_req = dict(x=req_As("x"), y=req_As("y"))
    # 말뚝 구조적 허용축력 (강관 Ø508, 부식 2 mm 공제, σa = 140 MPa; 지진시 1.5배). 지반 허용지지력은 확인 필요
    dp, tp_ = SUB["말뚝"]["직경"], SUB["말뚝"]["두께_교각"] - 0.002; Ap = math.pi / 4 * (dp ** 2 - (dp - 2 * tp_) ** 2); pile_Ra = Ap * 140 * 1000
    # 코핑 근원 (요소 6 I단 = 절점 6, G1 팔): 사용/강도 조합별 팔 근원 모멘트·전단 (RD, RL 만 지배적) — 별도 직접 계산 (정정): M = R × hb, V = R
    hb = g["s_brg"] / 2; cop = {}
    Rd = max(rx["D_g"]["G1"], rx["D_g"]["G2"]); Rl = max(rx["L_g"]["G1"][0], rx["L_g"]["G2"][0])
    if CODE == "kds":
        K = json.load(open(os.path.join(PJ, "combos_kds.json"), encoding="utf-8"))
        for cid, f in K["조합"].items():
            gD = f.get("DC_override", 1.0 if f.get("gamma_p_override") else K["gamma_p"]["DC"][0]); V = gD * Rd + f["LL"] * Rl
            cop[cid] = dict(V=V, M=V * hb, M_face=V * (hb - g["by"] / 2))
    else:
        for kind in ("강도", "사용"):
            for cid, f in CB[kind].items():
                V = f["D"] * Rd + f["L"] * Rl; cop[f"{kind} {cid}"] = dict(V=V, M=V * hb, M_face=V * (hb - g["by"] / 2))   # 근원: 기둥면(팔길이 hb − 기둥 반폭 1.5)
    out = dict(name=name, geom=g, loads_info=loads["info"], reactions=R, forces_by_case={k: {f"{e}{p}": v for (e, p), v in d.items()} for k, d in F.items()},
               combos=rows, worst={k: dict(value=v[0], combo=v[1]) for k, v in worst.items()}, coping=cop, piles=dict(n=nP, xs=xs, ys=ys, Sx2=Sx2, Sy2=Sy2),
               col_capacity_noRebar=dict(x=cap_x[:3], y=cap_y[:3]), As_req=As_req, pile_Ra=pile_Ra, pile_Ap=Ap)
    for tag in ("model", "My_RD"): autocrop(os.path.join(OUT, f"{name}_{tag}.jpg"))
    json.dump(out, open(os.path.join(OUT, f"{name}_result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return out

def autocrop(path, pad=30, keep_left=140):
    """NX 캡처의 빈 배경을 잘라냄 (범례 열은 유지)"""
    try:
        from PIL import Image, ImageChops
        im = Image.open(path).convert("RGB"); w, h = im.size
        body = im.crop((keep_left, 0, w, h)); bg = Image.new("RGB", body.size, body.getpixel((body.size[0] - 2, body.size[1] - 2)))
        bbox = ImageChops.difference(body, bg).convert("L").point(lambda p: 255 if p > 25 else 0).getbbox()
        if not bbox: return
        x0, y0, x1, y1 = bbox; crop = body.crop((max(0, x0 - pad), max(0, y0 - pad), min(body.size[0], x1 + pad), min(body.size[1], y1 + pad)))
        legend = im.crop((0, 0, keep_left, h)); lb = ImageChops.difference(legend, Image.new("RGB", legend.size, bg.getpixel((0, 0)))).convert("L").point(lambda p: 255 if p > 25 else 0).getbbox()
        if not lb:                                            # 범례 없음(모델 뷰): 본체만
            crop.save(path, quality=92); return
        top = legend.crop((0, 0, keep_left, min(h, 330)))    # 값 범례(상단)만 유지, 하단 정보는 캡션으로 대체
        H = max(crop.size[1], top.size[1]); new = Image.new("RGB", (keep_left + crop.size[0], H), bg.getpixel((0, 0)))
        new.paste(top, (0, 0)); new.paste(crop, (keep_left, (H - crop.size[1]) // 2)); new.save(path, quality=92)
    except Exception as e: print("  autocrop 실패:", e)

def report(results):
    rep = ["# 교각 안전성 검토 (도로교설계기준 2010 2.2.3.2 강도 조합 ①~⑨ · 표 2.2.3 사용 조합, NX 프레임 모델)", "", f"단위 kN, kN·m. 기둥 3.0(교축직각)×2.5(교축). 받침마찰계수 {MU}. 지진: A={CB['지진']['A']}, S={CB['지진']['S']}(확인 필요), 정적등가(단일모드), 기둥 모멘트/R={CB['지진']['R_기둥']:.0f}·기초 /(R/2) (6.3.4, 6.4.7.2). 배근: {REBAR['col_bars']} → 단면 강도 검토는 배근 확보 후.", ""]
    rep += ["## 하중 요약 (상부반력·자중·지진계수)", "", "| 교각 | 받침 | 상부 D | 활 max | 자중 코핑/기둥/기초 | LF | TP | 마찰 FR | EQ Cs(X/Y) | T(X/Y) s |", "| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: |"]
    for r in results:
        i = r["loads_info"]; w = i["weights"]; s = i["seismic"]; rx = RX[r["name"]]
        rep.append(f"| {r['name']} | {r['geom']['brg']} | {rx['D']:.0f} | {rx['Lmax']:.0f} | {w['cop']:.0f}/{w['col']:.0f}/{w['foot']:.0f} | {i['lf']:.0f} | {i['tp']:.0f} | {i['fr']:.0f} | {s['X']['Cs']:.3f}/{s['Y']['Cs']:.3f} | {s['X']['T']:.2f}/{s['Y']['T']:.2f} |")
    rep += ["", "## 기둥 하단(기초 상면) 최대 단면력 (조합 포락)", "", "| 교각 | Pmax (조합) | Pmin (조합) | My max 교축 (조합) | Mx max 교축직각 (조합) |", "| :-- | --: | --: | --: | --: |"]
    for r in results:
        w = r["worst"]; rep.append(f"| {r['name']} | {w['Pmax']['value']:.0f} ({w['Pmax']['combo']}) | {w['Pmin']['value']:.0f} ({w['Pmin']['combo']}) | {w['col_x']['value']:.0f} ({w['col_x']['combo']}) | {w['col_y']['value']:.0f} ({w['col_y']['combo']}) |")
    rep += ["", "## 말뚝 반력 (강체 캡, 기초 저면)", "", "| 교각 | 본수 | 최대 축력 (조합) | 최소 축력 (조합) | 최대 수평력/본 | 구조적 허용(상시/지진) | 지반 허용 |", "| :-- | --: | --: | --: | --: | --: | --: |"]
    for r in results:
        w = r["worst"]; hp = max(c["pile_h"] for c in r["combos"]); rep.append(f"| {r['name']} | {r['piles']['n']} | {w['pile_max']['value']:.0f} ({w['pile_max']['combo']}) | {w['pile_min']['value']:.0f} ({w['pile_min']['combo']}) | {hp:.0f} | {r['pile_Ra']:.0f}/{1.5*r['pile_Ra']:.0f} | 확인 필요 |")
    rep += ["", "## 기둥 소요 주철근량 (P–M 상관, φ=0.65, 지진력/R=3 적용, 배근도 확인 전 참고값)", "", "| 교각 | 교축 휨(My) 소요 As (cm²) | 교축직각 휨(Mx) 소요 As (cm²) | 철근비(큰 값) |", "| :-- | --: | --: | --: |"]
    for r in results:
        a = r["As_req"]; rep.append(f"| {r['name']} | {a['x']*1e4:.0f} | {a['y']*1e4:.0f} | {max(a['x'], a['y'])/(r['geom']['bx']*r['geom']['by'])*100:.2f} % |")
    rep += ["", "## 코핑 팔 근원(기둥면) — 강도 ① (1.3D + 2.15(L+i)) 기준", "", "| 교각 | Vu | Mu(기둥면) |", "| :-- | --: | --: |"]
    for r in results:
        c = r["coping"][GOV_COP]; rep.append(f"| {r['name']} | {c['V']:.0f} | {c['M_face']:.0f} |")
    rep += ["", "확인 필요: 기둥·코핑 배근, 말뚝 허용지지력(지반), 지반계수 S, P4·P5 말뚝 배치."]
    fn = "결과_교각_kds.md" if CODE == "kds" else "결과_교각.md"
    if CODE == "kds": rep[0] = "# 교각 안전성 검토 (한계상태설계법: 도로교설계기준 2016 표 3.4.1/KDS 24 12 11 조합, KDS 24 17 11 R, NX 프레임 모델)"
    open(os.path.join(RUNS, fn), "w", encoding="utf-8").write("\n".join(rep)); print("저장", fn)

if __name__ == "__main__":
    argv = sys.argv[1:]; do_run = "--norun" not in argv
    names = [n for n in argv if n.startswith("P")] or ["P1", "P2", "P3", "P4", "P5"]
    results = []
    for n in names:
        print("==", n); results.append(analyse_pier(n, do_run))
        w = results[-1]["worst"]; print(f"  Pmax {w['Pmax']['value']:.0f}  My {w['col_x']['value']:.0f} ({w['col_x']['combo']})  Mx {w['col_y']['value']:.0f}  말뚝 max {w['pile_max']['value']:.0f} min {w['pile_min']['value']:.0f}")
    report(results)

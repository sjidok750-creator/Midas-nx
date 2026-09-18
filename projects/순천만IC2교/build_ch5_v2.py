# -*- coding: utf-8 -*-
"""
제5장 v2 — STB 구간만 남기고(PSC 절 삭제) 하부구조(교대 A1·교각 P1~P5) 절을 금회 해석값으로 교체
  입력: report/5장_STB_v1.hwpx (build_ch5.py 산출), runs/abutment/A1_result.json, runs/pier/P*_result.json, runs/reactions_summary.json
  출력: report/5장_v2.hwpx
  문단 인덱스는 5장_STB_v1.hwpx 기준(하부구조 절 858~1099, 요약 1147~1184). 하부구조 편집 → 그림 → PSC 범위 삭제(뒤에서 앞으로) 순서
"""
import sys, os, json, copy, math
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\Midas\core\tools"); PJ = r"D:\Midas\projects\순천만IC2교"; sys.path.insert(0, PJ)
from hwpx_edit import Hwpx, para_text, P
from build_ch5 import cell, setc, table_of, caption_units, load_fig, RUNS, REP
A = json.load(open(os.path.join(RUNS, "abutment", "A1_result.json"), encoding="utf-8"))
PR = {n: json.load(open(os.path.join(RUNS, "pier", f"{n}_result.json"), encoding="utf-8")) for n in ("P1", "P2", "P3", "P4", "P5")}
RX = json.load(open(os.path.join(RUNS, "reactions_summary.json"), encoding="utf-8"))["support"]
CB = json.load(open(os.path.join(PJ, "combos_2010.json"), encoding="utf-8"))
SUB = json.load(open(os.path.join(PJ, "하부_제원서.json"), encoding="utf-8"))
GOV = "P3"; p3 = PR[GOV]; g3 = p3["geom"]

def tcs(tbl, r): return tbl.findall(P + "tr")[r].findall(P + "tc")
def set_row(doc, tbl, r, vals, tail=True):
    """행 r의 뒤에서부터 len(vals)개 셀에 값 (앞쪽 병합 셀 건너뜀)"""
    cs = tcs(tbl, r); cs = cs[-len(vals):] if tail else cs[:len(vals)]
    for tc, v in zip(cs, vals): doc.set_cell_text(tc, v)
def set_para(doc, ps, i, text): doc.set_para_text(ps[i], text)
def blank(doc, ps, i0, i1):
    for i in range(i0, i1): doc.set_para_text(ps[i], "")
def f0(x): return f"{x:,.0f}"
def f1(x): return f"{x:,.1f}"
def f2(x): return f"{x:.2f}"
def f3(x): return f"{x:.3f}"

def abutment_section(doc, ps):
    a = A; g = a["geom"]; s = a["soil"]; info = a["info"]; cs = a["cases"]; pl = a["piles"]; w = a["wall"]
    set_para(doc, ps, 859, "교대(A1) 설계조건")
    set_para(doc, ps, 862, "상부구조 형식     : 강박스거더교 (STB 구간, 5경간 연속)"); set_para(doc, ps, 866, "사각              : 90°")
    set_para(doc, ps, 870, "SHOE의 가동형식  : 가동 (일방향·양방향)"); set_para(doc, ps, 871, "SHOE의 종류      : 250톤 탄성받침 (교량받침 배치도)")
    set_para(doc, ps, 875, f"뒷채움 내부마찰각 : Φ  = {s['phi']:.0f}°  (지반조사 자료 없음 → 도로설계요령 표준값, 확인 필요)")
    set_para(doc, ps, 878, f"뒷채움 단위중량   : γ = {s['gamma']:.1f} kN/㎥")
    set_para(doc, ps, 887, f"고정하중 반력 : {f1(RX['A1']['D'])} kN (격자해석, 합성전+합성후)"); set_para(doc, ps, 888, f"활하중 반력 : {f1(RX['A1']['Lmax'])} kN (DB/DL-24 max, 충격 포함)"); set_para(doc, ps, 889, f"과재하중 : {s['q']:.0f} kN/㎡")
    set_para(doc, ps, 893, f"단위중량 : γc = {SUB['재료']['gamma_c']:.1f} kN/㎥"); set_para(doc, ps, 894, f"설계강도 : fck = {SUB['재료']['fck_구체']:.0f} MPa"); set_para(doc, ps, 895, f"철    근 : fy = {SUB['재료']['fy']:.0f} MPa (SD300)")
    set_para(doc, ps, 898, "도로교 설계기준(2010)"); set_para(doc, ps, 899, "콘크리트구조기준(2012)")
    set_para(doc, ps, 905, "본 교량의 교대 안전성 평가는 STB 구간 시점측 교대 A1을 대상으로 실시하였다(종점측 P5는 교각). 검토는 단위폭 1 m에 대해 수행하고 말뚝 반력은 전폭(8.670 m)으로 환산하였다.")
    set_para(doc, ps, 907, "교대 A1 단면 개략도 및 하중 블록")
    set_para(doc, ps, 911, f"∙고정하중 반력 : {f1(RX['A1']['D'])} kN ( / 8.670 m = {f2(info['D'])} kN/m)"); set_para(doc, ps, 912, f"∙활하중 반력 : {f1(RX['A1']['Lmax'])} kN ( / 8.670 m = {f2(info['L'])} kN/m)")
    set_para(doc, ps, 913, "자중 – 단위폭 (콘크리트 ①~④, 흙 ⓐ)")
    t = table_of(doc, 915); sw = a["sw"]; conc = [r for r in sw if r["name"][0] in "①②③④"]; soil = [r for r in sw if r["name"][0] in "ⓐⓑ"]
    doc.set_cell_lines(cell(t, 0, 1), [f"∙ 콘크리트 ① ~ ④ (γc = {SUB['재료']['gamma_c']} kN/㎥)", f"  - 총 하중    : {f2(sum(r['w'] for r in conc))} kN/m", f"  - 발생 모멘트 : {f2(sum(r['m'] for r in conc))} kN·m/m (toe 기준)",
                                        f"∙ 흙 ⓐ (γ = {s['gamma']} kN/㎥)", f"  - 총 하중    : {f2(sum(r['w'] for r in soil))} kN/m", f"  - 발생 모멘트 : {f2(sum(r['m'] for r in soil))} kN·m/m",
                                        f"∙ 합계 : V = {f2(info['Vsw'])} kN/m, M = {f2(info['Msw'])} kN·m/m"] + [f"   {r['name']} : A = {r['area']:.3f} ㎡, w = {r['w']:.2f} kN/m, x = {r['x']:.3f} m" for r in sw if r["area"] > 0])
    phi, d = s["phi"], s["delta_wall"]; K1 = math.cos(math.radians(phi)) ** 2; K2 = math.cos(math.radians(d)); K3 = math.sin(math.radians(phi + d)) * math.sin(math.radians(phi)) / math.cos(math.radians(d)); K4 = (1 + math.sqrt(K3)) ** 2
    set_para(doc, ps, 919, f"Ka1 = tan²(45° − Φ/2) = {info['Ka']:.3f}"); set_para(doc, ps, 921, f"Ka2 = K1 / (K2×K4) = {w['Kc']:.3f}  [ δ = Φ/3 = {d:.2f}° ]")
    set_para(doc, ps, 922, f"- K1 = cos²(Φ−θ) = {K1:.3f}"); set_para(doc, ps, 923, f"- K2 = cos²θ × cos(θ+δ) = {K2:.3f}"); set_para(doc, ps, 924, f"- K3 = sin(Φ+δ) × sin(Φ−α) ÷ [cos(θ+δ)×cos(θ−α)] = {K3:.3f}"); set_para(doc, ps, 925, f"- K4 = (1 + √K3)² = {K4:.3f}")
    set_para(doc, ps, 927, "α : 지표면과 수평면이 이루는 각 0°"); set_para(doc, ps, 928, "θ : 벽배면과 연직면이 이루는 각 0°"); set_para(doc, ps, 929, f"δ : 벽배면과 흙 사이의 벽면 마찰각 {d:.2f}°")
    H = g["z_top"]; t = table_of(doc, 931); caption_units(doc, 930)
    set_row(doc, t, 0, ["구 분", "산 식", "하중(kN/m)", "거리(m)", "모멘트(kN·m/m)"])
    set_row(doc, t, 1, ["배면토", f"{info['Ka']:.3f}×{s['gamma']}×{H:.2f}²×0.5", f2(info["Pa"]), f3(H / 3), f2(info["Pa"] * H / 3)])
    set_row(doc, t, 2, ["상재활하중", f"{info['Ka']:.3f}×{s['q']:.0f}×{H:.2f}", f2(info["Pq"]), f3(H / 2), f2(info["Pq"] * H / 2)])
    set_row(doc, t, 3, ["합  계", "", f2(info["Pa"] + info["Pq"]), "", f2(info["Pa"] * H / 3 + info["Pq"] * H / 2)])
    t = table_of(doc, 934); xb = g["x_brg"]; zs = g["z_seat"]; qs = s["q"] * (g["Bf"] - g["x_stem"] - g["t_stem"])
    set_row(doc, t, 0, ["구 분", "산 식", "하중(kN/m)", "거리(m)", "모멘트(kN·m/m)"])
    set_row(doc, t, 1, ["고정하중", f"{f1(RX['A1']['D'])} / 8.670", f2(info["D"]), f3(xb), f2(info["D"] * xb)])
    set_row(doc, t, 2, ["활하중", f"{f1(RX['A1']['Lmax'])} / 8.670", f2(info["L"]), f3(xb), f2(info["L"] * xb)])
    set_row(doc, t, 3, ["합  계", "-", f2(info["D"] + info["L"]), "-", f2((info["D"] + info["L"]) * xb)])
    set_row(doc, t, 4, ["고정하중 수평력(마찰)", f"{CB['받침마찰계수']} × {f2(info['D'])}", f2(info["Ff"]), f3(zs), f2(info["Ff"] * zs)])
    set_row(doc, t, 5, ["지표 활하중(뒷굽)", f"{s['q']:.0f} × {g['Bf'] - g['x_stem'] - g['t_stem']:.2f}", f2(qs), f3((g["x_stem"] + g["t_stem"] + g["Bf"]) / 2), f2(qs * (g["x_stem"] + g["t_stem"] + g["Bf"]) / 2)])
    set_para(doc, ps, 935, f"∙벽체 검토시 받침 마찰력에 의한 모멘트 = {f2(info['Ff'])} × {zs - g['tf']:.3f} = {f2(w['stem']['Mf'])} kN·m/m")
    t = table_of(doc, 938); set_row(doc, t, 1, ["하중 CASE", "하중", "연직력 (kN/m)", "수평력 (kN/m)", "“0”점 모멘트 (kN·m/m)", "e = M/V"])
    r = 2
    for k, (name, c) in enumerate(cs.items()):
        if name.startswith("4"): break
        for it in c["items"]:
            vals = [it["name"], f2(it["V"]) if it["V"] else "-", f2(it["H"]) if it["H"] else "-", f2(it["M"]), ""]; set_row(doc, t, r, vals); r += 1
        set_row(doc, t, r, ["합계", f2(c["V"]), f2(c["H"]), f2(c["M"]), f3(c["x"])]); r += 1
    for tc in tcs(t, 2)[:1] + tcs(t, 5)[:1] + tcs(t, 10)[:1]: pass
    caption_units(doc, 940); t = table_of(doc, 941); st, pa = w["stem"], w["parapet"]
    set_row(doc, t, 0, ["구분", "부재높이(㎜)", "유효깊이(d)(㎜)", "As, use", "Mu(kN·m/m)", "ΦMn(kN·m/m)", "안전율", "비고"])
    set_row(doc, t, 1, ["벽체", f"{g['t_stem']*1000:,.0f}", f"{st['d']*1000:,.0f}", "확인 필요(배근도)", f2(st["Mu"]), "-", "-", f"소요 As {st['As_req']*1e4:.1f} ㎠/m"])
    set_row(doc, t, 2, ["흉벽", f"{g['t_par']*1000:,.0f}", f"{pa['d']*1000:,.0f}", "확인 필요(배근도)", f2(pa["Mu"]), "-", "-", f"소요 As {pa['As_req']*1e4:.1f} ㎠/m"])
    Ra = a["pile_info"]["Ra_struct"]; c3, c4 = pl["3 활하중 재하"], pl["4 지진시"]
    for idx in (944,):
        caption_units(doc, idx - 1); t = table_of(doc, idx)
        set_row(doc, t, 0, ["구 분", "말뚝지지력(kN)", "허용값(kN)", "안전율", "비 고"])
        set_row(doc, t, 1, ["상시", f1(c3["Pmax"]), f"{f0(Ra)} (구조) / 지반 확인 필요", f2(Ra / c3["Pmax"]), "구조적 안전율"])
        set_row(doc, t, 2, ["지진시", f1(c4["Pmax"]), f"{f0(1.5 * Ra)} (구조×1.5)", f2(1.5 * Ra / c4["Pmax"]), "구조적 안전율"])
        set_row(doc, t, 3, ["상시", f1(c3["Hp"]), "확인 필요", "-", "지반 수평지지력"]); set_row(doc, t, 4, ["지진시", f1(c4["Hp"]), "확인 필요", "-", ""]); set_row(doc, t, 5, ["-", "15.000", "-", "지반정수 필요"])

def pier_section(doc, ps):
    p = p3; rx = RX[GOV]; g = g3; li = p["loads_info"]; wts = li["weights"]; sc = li["seismic"]
    set_para(doc, ps, 948, "교량형식 : 강박스거더교 (STB 구간, 5경간 연속)"); set_para(doc, ps, 949, "교량연장 : 49.840 + 50.000 + 70.000 + 49.996 + 49.876 = 269.711 m")
    set_para(doc, ps, 952, "교각형식 : Y형 코핑 + 사각기둥 (3.0×2.5 m)"); set_para(doc, ps, 956, "기초지반 : 확인 필요 (지반조사 자료 없음, 강관말뚝 Ø508)")
    t = table_of(doc, 961); set_row(doc, t, 1, [f"γc = {SUB['재료']['gamma_c']} kN/㎥", f"fy = {SUB['재료']['fy']:.0f} MPa"]); set_row(doc, t, 2, [f"fck = {SUB['재료']['fck_구체']:.0f} MPa", "-"])
    set_para(doc, ps, 972, "도로교 설계기준(2010)"); set_para(doc, ps, 973, "콘크리트구조기준(2012)")
    set_para(doc, ps, 980, f"본 교량의 교각 안전성 평가는 기둥 높이가 가장 크고 고정단 받침으로 제동·온도 수평력을 받는 P3를 대표로 상세 수록하였으며, P1~P5 전체를 동일한 절차(NX 프레임 모델, 도로교설계기준(2010) 2.2.3.2 강도설계법 하중조합 ①~⑨ 및 표 2.2.3 허용응력 하중조합 1~6)로 검토하여 요약표에 수록하였다.")
    set_para(doc, ps, 982, "교각 P3 해석 모델 (MIDAS CIVIL NX 프레임: 기둥·코핑 8절점 7요소, 기초상면 고정)")
    caption_units(doc, 985); t = table_of(doc, 986); D1 = RX[GOV]["D_g"]; L = RX[GOV]["L_g"]
    set_row(doc, t, 0, ["G1", "G2", "계"])
    set_row(doc, t, 1, [f1(D1["G1"]), f1(D1["G2"]), f1(D1["G1"] + D1["G2"])]); set_row(doc, t, 3, [f1(D1["G1"]), f1(D1["G2"]), f1(D1["G1"] + D1["G2"])])
    one = (L["G1"][0], max(L["G2"][1], 0.0)); full = (L["G1"][0], L["G2"][0])
    set_row(doc, t, 4, [f1(one[0]), f1(one[1]), f1(sum(one))]); set_row(doc, t, 5, [f1(full[0]), f1(full[1]), f1(sum(full))])
    set_row(doc, t, 6, [f1(D1["G1"] + one[0]), f1(D1["G2"] + one[1]), f1(D1["G1"] + D1["G2"] + sum(one))]); set_row(doc, t, 7, [f1(D1["G1"] + full[0]), f1(D1["G2"] + full[1]), f1(D1["G1"] + D1["G2"] + sum(full))])
    for tc in tcs(t, 1)[:1]: doc.set_cell_text(tc, "고정하중 (kN)")
    for tc in tcs(t, 4)[:1]: doc.set_cell_text(tc, "활하중 (kN)")
    for tc in tcs(t, 6)[:1]: doc.set_cell_text(tc, "계 (kN)")
    gc = SUB["재료"]["gamma_c"]
    lines = ["2.2 하부자중 (γc = %.1f kN/㎥)" % gc, "(1) COPING (Y형: 상단 수직부 + 사다리꼴 근사)",
             f"( {g['cop_top']:.3f} × {g['cop_v']:.3f} + ({g['cop_top']:.3f} + 3.000)/2 × {g['Hcop'] - g['cop_v']:.3f} ) × {g['cop_t']:.2f} × {gc} = {f1(wts['cop'])} kN",
             "(2) COLUMN", f"( {g['by']:.3f} × {g['bx']:.3f} ) × {g['Hc']:.2f} × {gc} = {f1(wts['col'])} kN", "(3) FOOTING", f"{g['foot'][0]:.2f} × {g['foot'][1]:.2f} × {g['foot'][2]:.3f} × {gc} = {f1(wts['foot'])} kN"]
    for k, ln in enumerate(lines): set_para(doc, ps, 987 + k, ln)
    blank(doc, ps, 987 + len(lines), 1005)
    W = rx["H"]["W"]; WL = rx["H"]["WL"]
    lines = ["2.3 풍하중", "(1) 상부구조 풍하중 : 격자모델에 재하한 풍하중(3.0 kN/㎡ × 수압면 3.6 m)의 받침 반력 사용",
             f"·교축직각방향 W = {f1(abs(W[1]))} kN (작용높이 = 받침 상면 + {(2.6 + 1.32) / 2:.2f} m), 활하중 재하시 WL = {f1(abs(WL[1]))} kN (노면 위 1.8 m)",
             f"(2) 교각 자체 풍하중 : {CB['풍하중']['p_pier']} kN/㎡ × 기둥 폭 {g['bx']:.1f} m = {CB['풍하중']['p_pier'] * g['bx']:.2f} kN/m, 코핑 {g['cop_t']:.1f} m = {CB['풍하중']['p_pier'] * g['cop_t']:.2f} kN/m (등분포, 요소 재하)"]
    for k, ln in enumerate(lines): set_para(doc, ps, 1006 + k, ln)
    blank(doc, ps, 1006 + len(lines), 1033)
    lines = ["2.4 종방향 수평력 (LONGITUDINAL FORCE)", f"(1) 제동하중 LF : 격자해석 고정단 반력 = {f1(abs(li['lf']))} kN (노면 위 1.8 m 작용)", f"(2) 온도변화 : 고정단 수평 반력 TP = {f1(abs(li['tp']))} kN (격자해석, 받침 국부축)",
             f"(3) 교좌장치 마찰 : {'고정단(P3) → 마찰력 없음' if li['fixed'] else f'μ·R = {CB[chr(48)] if False else CB['받침마찰계수']} × {f1(rx['D'])} = {f1(li['fr'])} kN'}",
             "(4) 지진하중 (정적등가, 단일모드 스펙트럼: Cs = 1.2·A·S / T^(2/3) ≤ 2.5A, A = %.3f, S = %.1f)" % (CB["지진"]["A"], CB["지진"]["S"]),
             f"(가) 교축방향 : I = {sc['X']['I']:.3f} m⁴, k = 3EI/H³ = {f0(sc['X']['k'])} kN/m, W = {f0(sc['X']['W'])} kN, T = {sc['X']['T']:.3f} s, Cs = {sc['X']['Cs']:.3f} → F = Cs·D = {f1(sc['X']['Cs'] * rx['D'])} kN (+ 교각 관성력)",
             f"(나) 교축직각방향 : I = {sc['Y']['I']:.3f} m⁴, k = {f0(sc['Y']['k'])} kN/m, T = {sc['Y']['T']:.3f} s, Cs = {sc['Y']['Cs']:.3f} → F = {f1(sc['Y']['Cs'] * rx['D'])} kN",
             f"·응답수정계수 : 기둥 R = {CB['지진']['R_기둥']:.0f}, 기초 R = {CB['지진']['R_기초']:.0f}, 직교방향 조합 100 % + 30 %"]
    for k, ln in enumerate(lines): set_para(doc, ps, 1034 + k, ln)
    blank(doc, ps, 1034 + len(lines), 1064)
    set_para(doc, ps, 1065, "2.5 상부반력 비대칭에 따른 모멘트 (코핑 단부 기준 거리, 받침 간격 4.270 m)")
    t = table_of(doc, 1067); x1, x2 = 1.115, 1.115 + 4.27; mid = 3.25
    rows = [("고정하중", D1["G1"], D1["G2"], ""), ("활하중", full[0], full[1], "만재시"), ("활하중", one[0], one[1], "편재시")]
    r = 1; tot = [0, 0]
    for nm, a1, a2, note in rows:
        set_row(doc, t, r, [f3(x1), f1(a1), f1(a1 * x1), note] if r == 1 else [f3(x1), f1(a1), f1(a1 * x1), note]); r += 1
        set_row(doc, t, r, [f3(x2), f1(a2), f1(a2 * x2)]); r += 1
        set_row(doc, t, r, [f1(a1 + a2), f1(a1 * x1 + a2 * x2)]); r += 1
    tot = (D1["G1"] + full[0] + D1["G2"] + full[1], (D1["G1"] + full[0]) * x1 + (D1["G2"] + full[1]) * x2); set_row(doc, t, 10, [f1(tot[0]), f1(tot[1]), ""])
    ed = (D1["G1"] * x1 + D1["G2"] * x2) / (D1["G1"] + D1["G2"]) - mid; el = (full[0] * x1 + full[1] * x2) / sum(full) - mid; eo = (one[0] * x1 + one[1] * x2) / sum(one) - mid
    set_para(doc, ps, 1069, f"고정하중에 의한 편심거리 ed = {ed:.3f} m, Md = {f1((D1['G1'] + D1['G2']) * ed)} kN·m"); set_para(doc, ps, 1070, f"활하중에 의한 편심거리(만재) el = {el:.3f} m, Ml = {f1(sum(full) * el)} kN·m"); set_para(doc, ps, 1071, f"활하중에 의한 편심거리(편재) eT = {eo:.3f} m, Ml = {f1(sum(one) * eo)} kN·m")
    set_para(doc, ps, 1073, "2.6 유수압 하중 (교축직각방향) - 하천이 없는 구간"); set_para(doc, ps, 1076, "충돌력 Pft = 0.00 kN (하천·도로 횡단 없음)"); set_para(doc, ps, 1078, "충돌모멘트 = 0.00 kN·m")
    set_para(doc, ps, 1080, "교각의 안전성 검토 결과")
    wst = p["worst"]; cop = p["coping"]["강도 ①"]; As = p["As_req"]
    for idx, extra in ((1082, False), (1096, True)):
        t = table_of(doc, idx)
        set_row(doc, t, 0, ["휨강도(kN·m)", "전단강도(kN)", "축력(kN)"] + (["비 고"] if extra else []), tail=False) if False else None
        hdr = tcs(t, 0); doc.set_cell_text(hdr[1], "휨강도(kN·m)"); doc.set_cell_text(hdr[2], "전단강도(kN)"); doc.set_cell_text(hdr[3], "축력(kN)")
        set_row(doc, t, 2, ["코핑", f1(cop["M_face"]), "확인 필요", "-", f1(cop["V"]), "확인 필요", "-", "-", "-", "-"] + (["배근 확인 후"] if extra else []))
        set_row(doc, t, 3, ["기둥", f1(max(wst["col_x"]["value"], wst["col_y"]["value"])), "확인 필요", "-", "-", "-", "-", f1(wst["Pmax"]["value"]), "확인 필요", "-"] + ([f"소요 As {max(As['x'], As['y'])*1e4:.0f} ㎠"] if extra else []))
    for idx in (1085, 1099):
        t = table_of(doc, idx); Ra = p["pile_Ra"]; pm = wst["pile_max"]["value"]; hp = max(c["pile_h"] for c in p["combos"]); Ap = p["pile_Ap"]
        set_row(doc, t, 1, ["수직력", f1(pm), f"{f0(Ra)} (구조, 지진시 ×1.5)", f2(1.5 * Ra / pm), "지반 허용 확인 필요"])
        set_row(doc, t, 2, ["수평력", f1(hp), "확인 필요", "-", "지반 수평지지력"])
        set_row(doc, t, 3, [f"{pm / Ap / 1000:.1f}", "140 (×1.5 지진시)", f2(210 / (pm / Ap / 1000)), "O.K"])
        set_row(doc, t, 4, ["-", "15.00", "-", "지반정수 필요"])
        for tc in tcs(t, 3)[:1]: doc.set_cell_text(tc, "말뚝응력(MPa)")
        for tc in tcs(t, 1)[:1]: doc.set_cell_text(tc, "말뚝지지력 검토(kN)")
    set_para(doc, ps, 1084, "말뚝 평가 (P3, 강도 ⑦ 지진시 최대, 강체 캡 49본)")
    set_para(doc, ps, 1095, "교각(P3) 단면력 평가 (P1~P5 요약은 아래 표)"); set_para(doc, ps, 1098, "교각(P3) 말뚝 평가")
    set_para(doc, ps, 1088, "교대(A1) 휨강도 평가"); set_para(doc, ps, 1091, "교대(A1) 말뚝 평가")
    t = table_of(doc, 1089); s = A["wall"]; g = A["geom"]
    set_row(doc, t, 0, ["구분", "부재높이(㎜)", "유효깊이(d)(㎜)", "As, use", "Mu(kN·m/m)", "ΦMn(kN·m/m)", "안전율", "비고"])
    set_row(doc, t, 1, ["벽체", f"{g['t_stem']*1000:,.0f}", f"{s['stem']['d']*1000:,.0f}", "확인 필요", f2(s["stem"]["Mu"]), "-", "-", f"소요 As {s['stem']['As_req']*1e4:.1f} ㎠/m"])
    set_row(doc, t, 2, ["흉벽", f"{g['t_par']*1000:,.0f}", f"{s['parapet']['d']*1000:,.0f}", "확인 필요", f2(s["parapet"]["Mu"]), "-", "-", f"소요 As {s['parapet']['As_req']*1e4:.1f} ㎠/m"])
    t = table_of(doc, 1092); pl = A["piles"]; Ra = A["pile_info"]["Ra_struct"]; c3, c4 = pl["3 활하중 재하"], pl["4 지진시"]
    set_row(doc, t, 0, ["구 분", "말뚝지지력(kN)", "허용값(kN)", "안전율", "비 고"])
    set_row(doc, t, 1, ["상시", f1(c3["Pmax"]), f"{f0(Ra)} (구조)", f2(Ra / c3["Pmax"]), "지반 허용 확인 필요"]); set_row(doc, t, 2, ["지진시", f1(c4["Pmax"]), f"{f0(1.5 * Ra)}", f2(1.5 * Ra / c4["Pmax"]), ""])
    set_row(doc, t, 3, ["상시", f1(c3["Hp"]), "확인 필요", "-", ""]); set_row(doc, t, 4, ["지진시", f1(c4["Hp"]), "확인 필요", "-", ""]); set_row(doc, t, 5, ["-", "15.000", "-", ""])

def pier_summary_table(doc, ps):
    """교각 P1~P5 요약표: 1096 표 뒤에 표(1099 말뚝표 복제)를 추가하지 않고, 1096 표에 행을 늘려 P1~P5 기둥/코핑 단면력 수록"""
    t = table_of(doc, 1096); doc.clone_row(t, 3, count=8)                      # 행 3(기둥) 뒤에 8행 → P1~P5 코핑/기둥 (10행) 중 P3 2행은 기존
    r = 2
    for n in ("P1", "P2", "P3", "P4", "P5"):
        p = PR[n]; w = p["worst"]; c = p["coping"]["강도 ①"]; As = p["As_req"]
        set_row(doc, t, r, [f"{n} 코핑", f1(c["M_face"]), "확인 필요", "-", f1(c["V"]), "확인 필요", "-", "-", "-", "-", "배근 확인 후"]); r += 1
        set_row(doc, t, r, [f"{n} 기둥", f1(max(w["col_x"]["value"], w["col_y"]["value"])), "확인 필요", "-", "-", "-", "-", f1(w["Pmax"]["value"]), "확인 필요", "-", f"소요 As {max(As['x'], As['y'])*1e4:.0f} ㎠"]); r += 1
    doc.mark_header(t, 2)
    set_para(doc, ps, 1095, "교각(P1~P5) 단면력 평가 (기둥: 지진력/R=3 적용 최대 휨모멘트·최대 축력, 코핑: 강도 ① 기둥면)")

def summary_conclusion(doc, ps):
    t = table_of(doc, 1170); s = A["wall"]; p = p3; w = p["worst"]; c = p["coping"]["강도 ①"]
    hdr = tcs(t, 0); doc.set_cell_text(hdr[1], "휨강도 검토(kN·m)"); doc.set_cell_text(hdr[2], "축력·전단 검토(kN)")
    set_row(doc, t, 2, ["벽체", "확인 필요", f2(s["stem"]["Mu"]), "-", "-", "-", "-", "배근 확인 후 판정"])
    set_row(doc, t, 3, ["흉벽", "확인 필요", f2(s["parapet"]["Mu"]), "-", "-", "-", "-"])
    set_row(doc, t, 4, ["코핑(P3)", "확인 필요", f1(c["M_face"]), "-", "확인 필요", f1(c["V"]), "-"])
    set_row(doc, t, 5, ["기둥(P3)", "확인 필요", f1(max(w["col_x"]["value"], w["col_y"]["value"])), "-", "확인 필요", f1(w["Pmax"]["value"]), "-"])
    Ra = A["pile_info"]["Ra_struct"]; c3 = A["piles"]["3 활하중 재하"]; pm = p["worst"]["pile_max"]["value"]
    set_para(doc, ps, 1179, f"교대(A1)에 대한 안전성 검토 결과, 벽체 기부 소요 휨모멘트 {s['stem']['Mu']:.1f} kN·m/m(소요 철근량 {s['stem']['As_req']*1e4:.1f} ㎠/m), 흉벽 {s['parapet']['Mu']:.1f} kN·m/m가 산정되었으며, 말뚝 최대 축력 {c3['Pmax']:.0f} kN은 강관말뚝(Ø508×12) 구조적 허용값 {Ra:,.0f} kN 이내(안전율 {Ra / c3['Pmax']:.2f})이다. 단면 강도에 대한 안전율은 배근도(또는 구조계산서) 확보 후 확정한다.")
    set_para(doc, ps, 1180, f"교각(P1~P5)에 대한 안전성 검토 결과, 대표 교각 P3의 기둥 최대 축력 {w['Pmax']['value']:,.0f} kN, 최대 휨모멘트 {max(w['col_x']['value'], w['col_y']['value']):,.0f} kN·m(지진시, R=3), 코핑 기둥면 휨모멘트 {c['M_face']:,.0f} kN·m가 산정되었으며, 말뚝 최대 축력 {pm:,.0f} kN(지진시)은 구조적 허용값 {1.5 * p['pile_Ra']:,.0f} kN 이내이다. 기둥 소요 주철근비는 최대 {max(max(PR[n]['As_req']['x'], PR[n]['As_req']['y']) for n in PR) / (g3['bx'] * g3['by']) * 100:.2f} %로 최소 철근비(1 %) 이내이며, 단면 안전율은 배근 확인 후 확정한다.")

def intro_tables(doc, ps):
    t = table_of(doc, 12)
    doc.set_cell_lines(tcs(t, 1)[0], ["5경간 연속 강박스거더 (STB 구간)"]); doc.set_cell_lines(tcs(t, 1)[1], ["∙ 폭 8.67 m", "∙ 연장 2@50+70+2@50 = 269.7 m (A1~P5)"])
    doc.set_cell_lines(tcs(t, 2)[1], ["∙ 최대 정모멘트부(S3 중앙)·최대 부모멘트부(P3)의 허용응력 검토 및 내하력 평가, 바닥판 강도설계법 검토"])
    t = table_of(doc, 14)
    doc.set_cell_lines(tcs(t, 1)[1], ["P3"]); doc.set_cell_lines(tcs(t, 1)[2], ["∙ 교각형식 : Y형 코핑 + 사각기둥, 기초형식 : 강관말뚝(Ø508×9, 49본)", "∙ 기둥 높이 최대(15.0 m)·고정단 받침으로 수평력이 가장 큼 (P1~P5 전체 검토, P3 상세 수록)"])
    doc.set_cell_lines(tcs(t, 2)[1], ["A1"]); doc.set_cell_lines(tcs(t, 2)[2], ["∙ 교대형식 : 역T형, 기초형식 : 강관말뚝(Ø508×12, 12본)", "∙ STB 구간 시점측 교대"])
    doc.set_cell_lines(tcs(t, 3)[-1], ["∙ 교대는 역T형, 교각은 Y형 코핑 사각기둥이며 기초는 강관말뚝으로 시공되어 있으므로, 상부 격자해석 반력을 받아 교각은 NX 프레임 모델, 교대는 단위폭 계산으로 도로교설계기준(2010) 하중조합에 대해 검토하였다."])

def figures(doc, ps):
    def swap_in(para, name, k=0):
        pic = list(para.iter(P + "pic"))[k]; data, ext, w, h = load_fig_path(name); ref = doc.add_image(data, ext); doc.swap_pic(pic, ref, w, h, max_width_hu=42000)
    def load_fig_path(path):
        import io
        from PIL import Image
        im = Image.open(path); w, h = im.size; data = open(path, "rb").read(); ext = path.rsplit(".", 1)[-1].lower().replace("jpeg", "jpg")
        if len(data) > 300 * 1024: buf = io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=92); data = buf.getvalue(); ext = "jpg"
        return data, ext, w, h
    swap_in(ps[906], os.path.join(RUNS, "abutment", "A1_section.png")); swap_in(ps[915], os.path.join(RUNS, "abutment", "A1_section.png"))
    swap_in(ps[981], os.path.join(RUNS, "pier", "P3_model.jpg"))
    # 모멘트도: 981(표+그림)·982(캡션) 복제해 982 뒤에 삽입
    tp, cp = copy.deepcopy(ps[981]), copy.deepcopy(ps[982]); parent = ps[982].getparent(); pos = parent.index(ps[982]) + 1
    parent.insert(pos, tp); parent.insert(pos + 1, cp); swap_in(tp, os.path.join(RUNS, "pier", "P3_My_RD.jpg")); doc.set_para_text(cp, "교각 P3 휨모멘트도 (고정하중 반력 RD, NX 캡처)")
    for q in (tp, cp):
        for la in q.findall(P + "linesegarray"): q.remove(la)
    return 2   # 삽입 문단 수

DELETE_RANGES = [(1176, 1177), (1161, 1168), (1153, 1157), (1138, 1144), (851, 858), (421, 840), (185, 221), (101, 144), (46, 48)]

def main():
    src = os.path.join(REP, "5장_STB_v1.hwpx"); out = os.path.join(REP, "5장_v2.hwpx")
    doc = Hwpx(src).load(); ps = doc.paragraphs(); assert len(ps) == 1185, len(ps)
    intro_tables(doc, ps); abutment_section(doc, ps); pier_section(doc, ps); pier_summary_table(doc, ps); summary_conclusion(doc, ps)
    # 잔여 PSC·구단위 정리: 5.1 조건비교표 설계강도, 교각 사용재료 Ec, 5.5 바닥판 요약표 PSCI 행 삭제
    i = doc.find_para("구조검토 조건비교")[0]; t = table_of(doc, i + 1); doc.set_cell_lines(tcs(t, 12)[-1], ["∙준공도면", "-바닥판 : 27.0 ㎫", "-교대, 교각 : 24.0 ㎫"])
    t = table_of(doc, 961); set_row(doc, t, 3, [f"Ec = {SUB['재료']['Ec']:,.0f} MPa", "-"])
    i = doc.find_para("바닥판 안전성 평가결과")[0]; t = table_of(doc, i + 1); doc.delete_rows(t, [4, 5, 6]); tcs(t, 1)[0].find(P + "cellSpan").set("rowSpan", "3")
    ins = figures(doc, ps)                       # 982 뒤 2문단 삽입 → 983 이후 인덱스 +2
    for i0, i1 in DELETE_RANGES:                 # 뒤에서 앞으로
        d = ins if i0 > 982 else 0; doc.delete_paragraphs(i0 + d, i1 + d)
    # 관련도면 헤딩 뒤 빈 표(교대·교각 일반도 자리)는 유지. 결론 PSC 문장 삭제됨.
    print("미참조 이미지 제거:", doc.prune_images()); doc.renumber_objects(); doc.save(out)
    rep = doc.verify(out); print(json.dumps(rep, ensure_ascii=False)[:600]); print("저장:", out, "문단", len(doc.paragraphs()))

if __name__ == "__main__":
    main()

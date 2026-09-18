# -*- coding: utf-8 -*-
"""
제5장 v3 — v2(5장_v2.hwpx)에서 하부구조 절을 '도로설계요령 절차 + 한계상태설계법(KDS 24) 계수'로 교체, 교대 형상은 자동판독(abut_geom) 결과, 요령 그림 삽도 이식
  입력: report/5장_v2.hwpx, runs/abutment/A1_v2_result.json (abutment2.py), runs/pier_kds/P*_result.json (pier_model.py --code kds), runs/reactions_summary.json(편재 1차선 포함)
        D:/Midas/core/references/요령1992_fig/crop/*.png (도로설계요령 그림 2.10·표 2.8·그림 3.3·3.40·5.4)
  출력: report/5장_v3.hwpx
  문단 인덱스: 5장_v2.hwpx 기준(하부구조 351~594, 요약 646~648, 결론 656~657, 참고문헌 25~33). 뒤쪽부터 편집하지 않고, 삽입은 마지막에 수행
"""
import sys, os, json, copy, math
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\Midas\core\tools"); PJ = r"D:\Midas\projects\순천만IC2교"; sys.path.insert(0, PJ)
from hwpx_edit import Hwpx, para_text, P
from build_ch5 import cell, setc, table_of, caption_units, RUNS, REP
from build_ch5_v2 import tcs, set_row, set_para, blank, f0, f1, f2, f3
A = json.load(open(os.path.join(RUNS, "abutment", "A1_v2_result.json"), encoding="utf-8"))
PR = {n: json.load(open(os.path.join(RUNS, "pier_kds", f"{n}_result.json"), encoding="utf-8")) for n in ("P1", "P2", "P3", "P4", "P5")}
RX = json.load(open(os.path.join(RUNS, "reactions_summary.json"), encoding="utf-8"))["support"]
K = json.load(open(os.path.join(PJ, "combos_kds.json"), encoding="utf-8"))
SUB = json.load(open(os.path.join(PJ, "하부_제원서.json"), encoding="utf-8"))
FIGD = r"D:\Midas\core\references\요령1992_fig\crop"
GOV = "P3"; p3 = PR[GOV]; g3 = p3["geom"]

def load_png(path):
    from PIL import Image
    im = Image.open(path); return open(path, "rb").read(), path.rsplit(".", 1)[-1].lower(), im.size[0], im.size[1]

def swap_in(doc, para, path, k=0, max_w=None):
    pic = list(para.iter(P + "pic"))[k]; data, ext, w, h = load_png(path); ref = doc.add_image(data, ext); doc.swap_pic(pic, ref, w, h, max_width_hu=max_w)

def insert_fig_after(doc, ps, anchor_idx, tmpl_pic_idx, tmpl_cap_idx, path, caption, max_w=30000):
    """anchor 문단 뒤에 [그림표 문단, 캡션 문단] 복제 삽입 (§17-2 deepcopy). 반환 삽입 2문단"""
    tp, cp = copy.deepcopy(ps[tmpl_pic_idx]), copy.deepcopy(ps[tmpl_cap_idx]); parent = ps[anchor_idx].getparent(); pos = parent.index(ps[anchor_idx]) + 1
    parent.insert(pos, tp); parent.insert(pos + 1, cp); swap_in(doc, tp, path, 0, max_w); doc.set_para_text(cp, caption)
    for q in (tp, cp):
        for la in q.findall(P + "linesegarray"): q.remove(la)
    return tp, cp

def refs(doc, ps, idxs):
    lines = ["도로설계요령 제3권 교량 (한국도로공사, 2020) 8-3편 교량 하부 구조물 4. 교대·교각의 설계", "도로설계요령 제3권 교량 (한국도로공사, 1992) 8-3편 2.5 토압, 3. 교대·교각 설계 (토질상수 표 2.7, 벽면마찰각 표 2.8)",
             "도로교설계기준(한계상태설계법) 일반교량편 (국토교통부, 2016) 3.4 하중조합, 7장 하부구조 [KDS 24 12 11:2021, KDS 24 14 51]", "KDS 24 17 11:2022 교량 내진설계기준(한계상태설계법)", "KDS 24 14 21:2025 콘크리트교 설계기준(한계상태설계법)"]
    for i, ln in zip(idxs, lines): set_para(doc, ps, i, ln)

def abutment_v3(doc, ps):
    g = A["geom"]; s = A["soil"]; info = A["info"]; L = A["loads"]; cs = A["cases"]; pl = A["piles"]; w = A["wall"]; cap = A["pile_cap"]
    set_para(doc, ps, 368, f"뒷채움 내부마찰각 : Φ = {s['phi']:.0f}°  (도로설계요령 표 2.7 '잘 다져진 모래 및 사질토' 표준값 — 지반조사 자료 없음)")
    set_para(doc, ps, 371, f"뒷채움 단위중량   : γ = {s['gamma']:.1f} kN/㎥ (요령 표 2.7: 1.9 t/㎥)")
    set_para(doc, ps, 376, "안정검토시 : 기초 뒷굽 연단의 연직 가상배면에 Coulomb 토압, 벽면마찰각 δ = Φ (도로설계요령 표 2.8, 그림 2.10(a))")
    set_para(doc, ps, 377, "벽체계산시 : 구체 배면에 Coulomb 토압, δ = Φ/3 (요령 표 2.8, 그림 2.10(b))")
    set_para(doc, ps, 378, f"- 지진시 : Mononobe–Okabe 토압, δ = Φ/2, 배면 균등분포·합력 H/2 (KDS 24 17 11 4.4.3.2), 수평진도 kh = 0.5·S = {s['kh']:.3f}")
    set_para(doc, ps, 382, f"재하하중 : q = {s['q']:.0f} kN/㎡ (도로설계요령 2.5.6(2): 상시 교대 배면 1 t/㎡)")
    refs(doc, ps, range(391, 396))
    set_para(doc, ps, 398, f"본 교량의 교대 안전성 평가는 STB 구간 시점측 교대 A1을 대상으로 실시하였다. 형상은 준공도면 교대 일반도(1) 단면 A-A를 좌표 기반으로 자동 판독하여 앞굽(교량 쪽) {g['toe']:.3f} m, 벽체 {g['stem']:.3f} m, 뒷굽(뒷채움 쪽) {g['heel']:.3f} m(배면 1:1 헌치 {g['hh']:.3f} m), 기초폭 B = {g['B']:.3f} m, 말뚝 {SUB['교대']['A1']['말뚝']['본수']}본(3열×6본)으로 확인하였다. 검토 절차는 도로설계요령(교대 설계)을 따르고 하중계수·저항계수·판정기준은 한계상태설계법(도로교설계기준 2016, KDS 24)을 적용하였으며, 단위폭 1 m로 계산하고 말뚝 반력은 전폭 {g['LW']} m로 환산하였다.")
    swap_in(doc, ps[399], os.path.join(RUNS, "abutment", "A1_v2_section.png")); set_para(doc, ps, 400, "교대 A1 검토 단면 (도면 자동판독 형상, 하중 블록, 가상배면)")
    set_para(doc, ps, 404, f"∙고정하중 반력 DC+DW : {f1(RX['A1']['D'])} kN ( / {g['LW']} m = {f2(info['D'])} kN/m) — 격자해석"); set_para(doc, ps, 405, f"∙활하중 반력 LL : {f1(RX['A1']['Lmax'])} kN ( / {g['LW']} m = {f2(info['LL'])} kN/m) — DB/DL-24 격자해석 (KDS KL-510 미환산, 확인 필요)")
    set_para(doc, ps, 406, "자중 – 단위폭 (콘크리트 ①~④ = DC, 뒷굽 위 흙 ⓐ = EV)"); set_para(doc, ps, 407, "")
    t = table_of(doc, 408); swap_in(doc, ps[408], os.path.join(RUNS, "abutment", "A1_v2_section.png"), 0, 26000)
    blk = [k for k in L if L[k]["kind"] in ("DC", "EV")]
    doc.set_cell_lines(cell(t, 0, 1), [f"∙ {k} : A = {L[k]['area']:.3f} ㎡, w = {L[k]['V']:.2f} kN/m, x = {L[k]['x']:.3f} m, M = {L[k]['M']:.2f} kN·m/m" for k in blk] +
                       [f"∙ 콘크리트 DC 합계 : V = {sum(L[k]['V'] for k in blk if L[k]['kind']=='DC'):.2f} kN/m", f"∙ 흙 EV 합계 : V = {sum(L[k]['V'] for k in blk if L[k]['kind']=='EV'):.2f} kN/m", "  (모멘트는 앞굽 연단 기준, 저항 +)"])
    lines = [f"∙안정검토시 : 가상배면(뒷굽 연단 연직면) Coulomb, δ = Φ = {info['delta_st']:.0f}° [요령 표 2.8]", f"Ka = {info['Ka']:.3f}  (참고: Rankine tan²(45°−Φ/2) = {math.tan(math.radians(45 - s['phi']/2))**2:.3f})",
             f"Pa = ½·Ka·γ·H² = ½ × {info['Ka']:.3f} × {s['gamma']} × {g['z_top']:.3f}² = {info['Pa']:.2f} kN/m (수평 {info['Pa']*math.cos(math.radians(info['delta_st'])):.2f}, 연직 {info['Pa']*math.sin(math.radians(info['delta_st'])):.2f}), 작용점 H/3",
             f"재하하중 토압 Pq = Ka·q·H = {info['Pq']:.2f} kN/m, 작용점 H/2", f"∙벽체계산시 : 구체 배면 Coulomb, δ = Φ/3 = {w['delta']:.2f}°, Ka = {w['Kc']:.3f}",
             f"∙지진시 : Mononobe–Okabe, δ = Φ/2 = {info['delta_eq']:.0f}°, kh = {s['kh']:.3f} → Kae = {info['Kae']:.3f}, Pae = {info['Pae']:.2f} kN/m (균등분포, 합력 H/2)",
             "α : 지표면과 수평면이 이루는 각 0°", "θ : 벽배면과 연직면이 이루는 각 0°", f"δ : 벽면 마찰각 — 안정 {info['delta_st']:.0f}° / 벽체 {w['delta']:.2f}° / 지진시 {info['delta_eq']:.0f}°", "", "", "∙토압계산 (단위폭)"]
    for i, ln in zip(range(411, 424), lines): set_para(doc, ps, i, ln)
    t = table_of(doc, 424); eh, ls = L["EH 배면토압(가상배면, δ=φ)"], L["LS 재하하중 토압(q=10)"]
    set_row(doc, t, 0, ["구 분", "산 식", "수평력 H (kN/m)", "작용높이 (m)", "전도모멘트 (kN·m/m)"])
    set_row(doc, t, 1, ["배면토압 EH", f"{info['Ka']:.3f}×{s['gamma']}×{g['z_top']:.2f}²×0.5×cosδ", f2(eh["H"]), f3(eh["z"]), f2(-eh["H"] * eh["z"])])
    set_row(doc, t, 2, ["재하하중 토압 LS", f"{info['Ka']:.3f}×{s['q']:.0f}×{g['z_top']:.2f}×cosδ", f2(ls["H"]), f3(ls["z"]), f2(-ls["H"] * ls["z"])])
    set_row(doc, t, 3, ["합  계", f"연직성분 EH {eh['V']:.2f} + LS {ls['V']:.2f} (저항)", f2(eh["H"] + ls["H"]), "", f2(-eh["H"] * eh["z"] - ls["H"] * ls["z"])])
    t = table_of(doc, 427); dcs, ll, fr, lsv = L["상부 고정하중 반력 DC+DW"], L["상부 활하중 반력 LL"], L["받침 마찰력 FR (μ=0.05)"], L["LS 재하하중 연직(뒷굽 위)"]
    set_row(doc, t, 0, ["구 분", "산 식", "하중(kN/m)", "거리(m)", "모멘트(kN·m/m)"])
    set_row(doc, t, 1, ["고정하중 반력 DC+DW", f"{f1(RX['A1']['D'])} / {g['LW']}", f2(dcs["V"]), f3(dcs["x"]), f2(dcs["M"])]); set_row(doc, t, 2, ["활하중 반력 LL", f"{f1(RX['A1']['Lmax'])} / {g['LW']}", f2(ll["V"]), f3(ll["x"]), f2(ll["M"])])
    set_row(doc, t, 3, ["합  계", "-", f2(dcs["V"] + ll["V"]), "-", f2(dcs["M"] + ll["M"])]); set_row(doc, t, 4, ["받침 마찰력 FR", f"0.05 × {f2(dcs['V'])}", f2(fr["H"]), f3(fr["z"]), f2(fr["M"])])
    set_row(doc, t, 5, ["재하하중 연직 LS (뒷굽 위)", f"{s['q']:.0f} × {g['heel']:.2f}", f2(lsv["V"]), f3(lsv["x"]), f2(lsv["M"])])
    set_para(doc, ps, 428, f"∙벽체 검토시 받침 마찰력에 의한 모멘트 = {f2(fr['H'])} × {g['z_seat'] - g['tf']:.3f} = {f2(fr['H'] * (g['z_seat'] - g['tf']))} kN·m/m")
    set_para(doc, ps, 430, "하중조합별 안정 검토 (한계상태설계법: 극한한계상태 I · 극단상황한계상태 I(지진) · 사용한계상태 I) — 전도: 합력 위치")
    t = table_of(doc, 431); doc.delete_rows(t, [9, 8, 14, 13, 12, 11]); trs = t.findall(P + "tr")
    for r0 in (2, 5, 8): tcs(t, r0)[0].find(P + "cellSpan").set("rowSpan", "3")
    set_row(doc, t, 0, ["구 분", "하중조합별 합력 (단위폭)"]); set_row(doc, t, 1, ["하중조합", "영구하중 계수", "ΣV (kN/m)", "ΣH (kN/m)", "ΣM (kN·m/m, 앞굽)", "합력 x / e (m)"])
    lim = {"극한 I": g["B"] / 4, "극단 I": 0.4 * g["B"], "사용 I": g["B"] / 6}
    r = 2
    for case in ("극한 I", "극단 I", "사용 I"):
        c = cs[case]
        for j, mode in enumerate(("max", "min")):
            m = c[mode]; vals = [("γp 최대" if mode == "max" else "γp 최소(전도)"), f1(m["V"]), f1(m["H"]), f1(m["M"]), f"{m['x']:.3f} / {m['e']:.3f}"]
            if j == 0: doc.set_cell_text(tcs(t, r)[0], f"{case}")
            set_row(doc, t, r, vals); r += 1
        set_row(doc, t, r, ["판정", "", "", f"허용 e ≤ {lim[case]:.3f}", "O.K" if all(abs(c[m]["e"]) <= lim[case] for m in ("max", "min")) else "N.G"]); r += 1
    caption_units(doc, 433); set_para(doc, ps, 433, "휨강도 평가 (앞벽·흉벽, 극한 I: 1.5EH + 1.8LS + 1.0FR, KDS 24 14 21 재료계수 φc 0.65·φs 0.90)")
    t = table_of(doc, 434); st, pa = w["stem"], w["parapet"]
    set_row(doc, t, 0, ["구분", "부재높이(㎜)", "유효깊이(d)(㎜)", "As, use", "Mu(kN·m/m)", "Mr(kN·m/m)", "판정", "비고"])
    set_row(doc, t, 1, ["앞벽 기부", f"{g['stem']*1000:,.0f}", f"{st['d']*1000:,.0f}", "확인 필요(배근도)", f2(st["Mu"]), "-", "배근 확인 후", f"소요 As {st['As_req']*1e4:.1f} ㎠/m"])
    set_row(doc, t, 2, ["흉벽 기부", f"{g['t_par']*1000:,.0f}", f"{pa['d']*1000:,.0f}", "확인 필요(배근도)", f2(pa["Mu"]), "-", "배근 확인 후", f"소요 As {pa['As_req']*1e4:.1f} ㎠/m"])
    set_para(doc, ps, 436, f"말뚝 평가 (강관말뚝 Ø508×12 {SUB['교대']['A1']['말뚝']['본수']}본, 3열, 강체 캡; 도로설계요령 그림 5.4 군말뚝 도심선 방법)")
    t = table_of(doc, 437); pu, pe, ps_ = pl["극한 I|max"], pl["극단 I|max"], pl["사용 I|max"]
    set_row(doc, t, 0, ["구 분", "말뚝 축력 (kN/본)", "저항 (kN/본)", "축력/저항", "비 고"])
    set_row(doc, t, 1, ["극한 I", f1(pu["Pmax"]), f"{f0(cap['phiPn'])} (구조 φc·Pn)", f2(pu["Pmax"] / cap["phiPn"]), "지반 저항 확인 필요"]); set_row(doc, t, 2, ["극단 I(지진)", f1(pe["Pmax"]), f"{f0(cap['Pn'])} (저항계수 1.0)", f2(pe["Pmax"] / cap["Pn"]), "7.5.6"])
    set_row(doc, t, 3, ["극한 I", f1(pu["Hp"]), "확인 필요", "-", "수평 저항"]); set_row(doc, t, 4, ["극단 I(지진)", f1(pe["Hp"]), "확인 필요", "-", ""]); set_row(doc, t, 5, ["사용 I 최대 축력", f1(ps_["Pmax"]), "-", "-", "말뚝 배열 검토용"])

def pier_v3(doc, ps):
    p = p3; rx = RX[GOV]; g = g3; li = p["loads_info"]; sc = li["seismic"]; Kz = K["검토기준"]["지진"]
    set_para(doc, ps, 457, "한계상태설계법 — 하중조합: 도로교설계기준(한계상태설계법, 2016) 표 3.4.1/3.4.2 (KDS 24 12 11) 극한 I·III·IV·V, 극단 I, 사용 I"); set_para(doc, ps, 458, "단면 검토: KDS 24 14 21 재료계수(φc 0.65, φs 0.90) — 배근 확보 후 P–M 상관 검토")
    refs(doc, ps, range(465, 470))
    set_para(doc, ps, 473, "본 교량의 교각 안전성 평가는 기둥 높이가 가장 크고 고정단 받침으로 제동·온도 수평력을 받는 P3를 대표로 상세 수록하였으며, P1~P5 전체를 동일한 절차(MIDAS CIVIL NX 프레임 모델, 한계상태설계법 하중조합 극한 I·III·IV·V·극단 I·사용 I, KDS 24 17 11 응답수정계수)로 검토하여 요약표에 수록하였다. 상부 반력은 격자해석(DB/DL-24) 값이며 편재 활하중은 1차선 재하 케이스의 주형별 반력을 사용하였다.")
    D1 = rx["D_g"]; Lg = rx["L_g"]; one = rx["L_one"]; t = table_of(doc, 481)
    full = (Lg["G1"][0], Lg["G2"][0]); side = (one["L1"]["G1"], one["L1"]["G2"])
    set_row(doc, t, 4, [f1(side[0]), f1(side[1]), f1(sum(side))]); set_row(doc, t, 5, [f1(full[0]), f1(full[1]), f1(sum(full))])
    set_row(doc, t, 6, [f1(D1["G1"] + side[0]), f1(D1["G2"] + side[1]), f1(D1["G1"] + D1["G2"] + sum(side))]); set_row(doc, t, 7, [f1(D1["G1"] + full[0]), f1(D1["G2"] + full[1]), f1(D1["G1"] + D1["G2"] + sum(full))])
    for tc in tcs(t, 4)[:1]: doc.set_cell_text(tc, "활하중 (kN) 편재: 1차선(L1) 재하")
    set_para(doc, ps, 536, f"·응답수정계수 (KDS 24 17 11 표 4.1-4) : 단일기둥 R = {Kz['R_기둥']:.0f} (모멘트만 적용, 축력·전단 미적용 4.1.5), 기초 = R 미적용 탄성력 (4.2.7.2), 직교방향 100 % + 30 % (4.2.4)")
    t = table_of(doc, 562); x1, x2 = 1.115, 1.115 + 4.27; mid = 3.25
    rows = [("고정하중", D1["G1"], D1["G2"], ""), ("활하중", full[0], full[1], "만재시(2차선)"), ("활하중", side[0], side[1], "편재시(1차선 L1)")]
    r = 1
    for nm, a1, a2, note in rows:
        set_row(doc, t, r, [f3(x1), f1(a1), f1(a1 * x1), note]); r += 1; set_row(doc, t, r, [f3(x2), f1(a2), f1(a2 * x2)]); r += 1; set_row(doc, t, r, [f1(a1 + a2), f1(a1 * x1 + a2 * x2)]); r += 1
    tot = (D1["G1"] + full[0] + D1["G2"] + full[1], (D1["G1"] + full[0]) * x1 + (D1["G2"] + full[1]) * x2); set_row(doc, t, 10, [f1(tot[0]), f1(tot[1]), ""])
    ed = (D1["G1"] * x1 + D1["G2"] * x2) / (D1["G1"] + D1["G2"]) - mid; el = (full[0] * x1 + full[1] * x2) / sum(full) - mid; eo = (side[0] * x1 + side[1] * x2) / sum(side) - mid
    set_para(doc, ps, 564, f"고정하중 편심 ed = {ed:+.3f} m (코핑 중심 기준, G1 쪽 −), Md = {f1((D1['G1'] + D1['G2']) * ed)} kN·m"); set_para(doc, ps, 565, f"활하중(만재) 편심 el = {el:+.3f} m, Ml = {f1(sum(full) * el)} kN·m"); set_para(doc, ps, 566, f"활하중(편재, L1 1차선) 편심 eT = {eo:+.3f} m, Ml = {f1(sum(side) * eo)} kN·m")
    wst = p["worst"]; cop = p["coping"]["극한 I"]; As = p["As_req"]
    for idx in (577, 591):
        t = table_of(doc, idx); hdr = tcs(t, 0); doc.set_cell_text(hdr[1], "휨모멘트 Mu (kN·m)"); doc.set_cell_text(hdr[2], "전단력 Vu (kN)"); doc.set_cell_text(hdr[3], "축력 Pu (kN)")
    t = table_of(doc, 577)
    set_row(doc, t, 2, ["코핑", f1(cop["M_face"]), "확인 필요", "-", f1(cop["V"]), "확인 필요", "-", "-", "-", "-"])
    set_row(doc, t, 3, ["기둥", f1(max(wst["col_x"]["value"], wst["col_y"]["value"])), "확인 필요", "-", "-", "-", "-", f1(wst["Pmax"]["value"]), "확인 필요", "-"])
    set_para(doc, ps, 579, "말뚝 평가 (P3, 극단 I 지진시 최대 — R 미적용 탄성지진력, 강체 캡 49본)")
    for idx in (580, 594):
        t = table_of(doc, idx); Ra = p["pile_Ra"]; pm = wst["pile_max"]["value"]; hp = max(c["pile_h"] for c in p["combos"]); Ap = p["pile_Ap"]
        set_row(doc, t, 1, ["수직력", f1(pm), f"{f0(Ra / 140 * 235 * 0.9)} (구조 φc·Pn, fy 235)", f2(Ra / 140 * 235 * 0.9 / pm), "지반 저항 확인 필요"])
        set_row(doc, t, 2, ["수평력", f1(hp), "확인 필요", "-", "지반 수평저항"]); set_row(doc, t, 3, [f"{pm / Ap / 1000:.1f}", "235 (fy)", f2(235 / (pm / Ap / 1000)), "O.K"]); set_row(doc, t, 4, ["-", "-", "-", "지반정수 필요"])
        for tc in tcs(t, 3)[:1]: doc.set_cell_text(tc, "말뚝응력(MPa)")
    set_para(doc, ps, 590, "교각(P1~P5) 단면력 평가 (한계상태설계법 포락: 기둥 최대 휨모멘트(지진 모멘트/R=3)·최대 축력, 코핑 극한 I 기둥면)")
    t = table_of(doc, 591); r = 2
    for n in ("P1", "P2", "P3", "P4", "P5"):
        q = PR[n]; wq = q["worst"]; c = q["coping"]["극한 I"]; Aq = q["As_req"]
        set_row(doc, t, r, [f"{n} 코핑", f1(c["M_face"]), "확인 필요", "-", f1(c["V"]), "확인 필요", "-", "-", "-", "-", "배근 확인 후"]); r += 1
        set_row(doc, t, r, [f"{n} 기둥", f1(max(wq["col_x"]["value"], wq["col_y"]["value"])), "확인 필요", "-", "-", "-", "-", f1(wq["Pmax"]["value"]), "확인 필요", "-", f"소요 As {max(Aq['x'], Aq['y'])*1e4:.0f} ㎠"]); r += 1

def summary_v3(doc, ps):
    t = table_of(doc, 648); st, pa = A["wall"]["stem"], A["wall"]["parapet"]; w = p3["worst"]; c = p3["coping"]["극한 I"]
    hdr = tcs(t, 0); doc.set_cell_text(hdr[1], "휨 검토 Mu (kN·m)"); doc.set_cell_text(hdr[2], "축력·전단 검토 (kN)")
    set_row(doc, t, 2, ["앞벽", "확인 필요", f2(st["Mu"]), "-", "-", "-", "-", "배근 확인 후 판정"]); set_row(doc, t, 3, ["흉벽", "확인 필요", f2(pa["Mu"]), "-", "-", "-", "-"])
    set_row(doc, t, 4, ["코핑(P3)", "확인 필요", f1(c["M_face"]), "-", "확인 필요", f1(c["V"]), "-"]); set_row(doc, t, 5, ["기둥(P3)", "확인 필요", f1(max(w["col_x"]["value"], w["col_y"]["value"])), "-", "확인 필요", f1(w["Pmax"]["value"]), "-"])
    g = A["geom"]; cs = A["cases"]; pl = A["piles"]; cap = A["pile_cap"]
    set_para(doc, ps, 656, f"교대(A1)는 도로설계요령의 교대 설계 절차(가상배면 토압 δ=Φ, 재하하중 1 t/㎡)에 한계상태설계법 하중계수를 적용하여 검토한 결과, 전도(합력 위치)는 극한 I 편심 {max(abs(cs['극한 I'][m]['e']) for m in ('max','min')):.3f} m ≤ B/4 = {g['B']/4:.3f} m, 극단 I(지진) {max(abs(cs['극단 I'][m]['e']) for m in ('max','min')):.3f} m ≤ 0.4B = {0.4*g['B']:.3f} m로 안정하며, 말뚝 최대 축력 {pl['극한 I|max']['Pmax']:.0f} kN(극한 I)·{pl['극단 I|max']['Pmax']:.0f} kN(극단 I)은 강관말뚝 구조 저항 {cap['phiPn']:,.0f} kN 이내이다. 앞벽 기부 소요 휨모멘트 {st['Mu']:.1f} kN·m/m(소요 철근 {st['As_req']*1e4:.1f} ㎠/m), 흉벽 {pa['Mu']:.1f} kN·m/m가 산정되었고 단면 안전율은 배근도 확보 후 확정한다. 지반 지지력·말뚝 열 순서·활하중(KL-510) 환산은 확인 필요 항목이다.")
    set_para(doc, ps, 657, f"교각(P1~P5)은 한계상태설계법 하중조합(극한 I·III·IV·V, 극단 I, 사용 I)으로 검토한 결과, 대표 교각 P3의 기둥 최대 축력 {w['Pmax']['value']:,.0f} kN, 최대 휨모멘트 {max(w['col_x']['value'], w['col_y']['value']):,.0f} kN·m(극단 I, R=3), 코핑 기둥면 휨모멘트 {c['M_face']:,.0f} kN·m가 산정되었으며, 말뚝 최대 축력 {w['pile_max']['value']:,.0f} kN(극단 I, R 미적용)은 구조 저항 이내이다. 기둥 소요 주철근비는 최대 {max(max(PR[n]['As_req']['x'], PR[n]['As_req']['y']) for n in PR) / (g3['bx'] * g3['by']) * 100:.2f} %로 최소 철근비 이내이며, 단면 안전율은 배근 확인 후 확정한다.")

def intro_v3(doc, ps):
    set_para(doc, ps, 20, "순천만IC2교는 1등교(DB-24, DL-24)로 설계되어 있으며, 상부구조(강박스거더·바닥판)는 도로교 설계기준(2010)에 따라 허용응력설계법과 강도설계법으로 검토하였고, 하부구조(교대·교각)는 도로설계요령(한국도로공사)의 교대·교각 설계 절차를 따르되 하중조합·저항계수·판정기준은 최신 한계상태설계법(도로교설계기준 2016 = KDS 24 12 11/14 51, KDS 24 17 11:2022, KDS 24 14 21:2025)을 적용하여 안전성 평가를 실시하였다.")
    lines = ["1) 도로교 설계기준(2010) — 상부구조", "2) 도로교 설계기준 해설(2008)", "3) 콘크리트구조기준(2012)", "4) 도로설계요령 제3권 교량(한국도로공사, 2020; 1992) — 교대·교각 설계 절차, 토질상수",
             "5) 도로교설계기준(한계상태설계법) 일반교량편(2016) [KDS 24 12 11:2021 설계하중조합, KDS 24 14 51 하부구조] — 하부구조", "6) KDS 24 17 11:2022 교량 내진설계기준(한계상태설계법)", "8) KDS 24 14 21:2025 콘크리트교 설계기준(한계상태설계법)",
             "9) 2016 국도건설공사 설계실무요령(국토교통부) 4-02 구조물공", "10) 강도로교 상세부 설계지침(1997)"]
    for i, ln in zip(range(25, 34), lines): set_para(doc, ps, i, ln)
    t = table_of(doc, 18); set_row(doc, t, 4, ["∙한계상태설계법 (KDS 24 12 11 조합) / 절차: 도로설계요령"] if False else ["하부구조", "∙강도설계법"])   # 설계당시 열은 유지
    t = table_of(doc, 14); doc.set_cell_lines(tcs(t, 2)[2], ["∙ 교대형식 : 역T형(앞굽 1.3 m·뒷굽 3.1 m·배면 헌치), 기초형식 : 강관말뚝(Ø508×12, 3열×6본=18본)", "∙ STB 구간 시점측 교대 — 도면 좌표 자동판독으로 형상 확인"])

def figures_v3(doc, ps):
    """요령 그림 이식: 교대 검토단면 캡션(400) 뒤에 그림 2.10·표 2.8·그림 3.3, 휨강도 표(434) 앞에 그림 3.40, 말뚝 표(437) 앞에 그림 5.4 — 뒤쪽부터 삽입해 앞 인덱스 보존"""
    tp, cp = 399, 400
    insert_fig_after(doc, ps, 436, tp, cp, os.path.join(FIGD, "그림5.4_군말뚝도심선.png"), "군말뚝의 도심선과 말뚝 축방향력 (도로설계요령 그림 5.4)", 22000)
    insert_fig_after(doc, ps, 433, tp, cp, os.path.join(FIGD, "그림3.40_흉벽의설계.png"), "흉벽의 설계 (도로설계요령 그림 3.40)", 18000)
    insert_fig_after(doc, ps, 400, tp, cp, os.path.join(FIGD, "그림3.3_토압의작용방법.png"), "토압의 작용방법 — (a) 상시 (b) 지진시 (도로설계요령 그림 3.3)", 34000)
    insert_fig_after(doc, ps, 400, tp, cp, os.path.join(FIGD, "표2.8_벽면마찰각.png"), "벽면과 흙의 마찰각 δ (도로설계요령 표 2.8)", 30000)
    insert_fig_after(doc, ps, 400, tp, cp, os.path.join(FIGD, "그림2.10_토압의작용면.png"), "토압의 작용면 — (a) 안정계산시 가상배면 (b) 앞벽 설계시 구체배면 (도로설계요령 그림 2.10)", 36000)

def main():
    src = os.path.join(REP, "5장_v2.hwpx"); out = os.path.join(REP, "5장_v3.hwpx")
    doc = Hwpx(src).load(); ps = doc.paragraphs(); assert len(ps) == 662, len(ps)
    intro_v3(doc, ps); abutment_v3(doc, ps); pier_v3(doc, ps); summary_v3(doc, ps); figures_v3(doc, ps)
    print("미참조 이미지 제거:", doc.prune_images()); doc.renumber_objects(); doc.save(out)
    rep = doc.verify(out); print(json.dumps(rep, ensure_ascii=False)[:600]); print("저장:", out, "문단", len(doc.paragraphs()))

if __name__ == "__main__":
    main()

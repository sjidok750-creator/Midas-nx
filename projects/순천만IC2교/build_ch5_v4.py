# -*- coding: utf-8 -*-
"""
제5장 v4 — 도로설계편람 제5편(2008) 검토예제 [단계] 흐름으로 하부구조 절 재구성, 상부구조 허용응력(표 3.9.4·3.4.3)·항복검토 갱신, 지진 제외, 한계상태 제거, 레이아웃 정리
  입력: report/5장_v3.hwpx, runs/abutment/A1_v3_result.json(abutment3.py), runs/pier3/P*_result.json(pier_model3.py), runs/stress3_gov.json(stress3.py), png/report/*.png, runs/abutment/A1_v3_*.png
  출력: report/5장_v4.hwpx
  원칙: 원본 XML 복제(hwpx_table.new_table/new_para), 인덱스는 편집 전 문단 목록(ps)에서만 취하고 삭제·삽입은 요소 참조로 수행
"""
import sys, os, json, copy, glob
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\Midas\core\tools"); PJ = r"D:\Midas\projects\순천만IC2교"; sys.path.insert(0, PJ)
from hwpx_edit import Hwpx, para_text, P
from hwpx_table import new_table, new_para, insert_after, fix_layout, merge_cells
from derive import abutment_lines, pier_lines
RUNS = os.path.join(PJ, "runs"); REP = os.path.join(PJ, "report"); PNG = os.path.join(PJ, "png", "report")
A = json.load(open(os.path.join(RUNS, "abutment", "A1_v3_result.json"), encoding="utf-8"))
PR = {n: json.load(open(os.path.join(RUNS, "pier3", f"{n}_result.json"), encoding="utf-8")) for n in ("P1", "P2", "P3", "P4", "P5")}
GOV = json.load(open(os.path.join(RUNS, "stress3_gov.json"), encoding="utf-8"))
CB = json.load(open(os.path.join(PJ, "combos_2010.json"), encoding="utf-8")); SUB = json.load(open(os.path.join(PJ, "하부_제원서.json"), encoding="utf-8"))
RX = json.load(open(os.path.join(RUNS, "reactions_summary.json"), encoding="utf-8"))["support"]
p3 = PR["P3"]; g3 = p3["geom"]
f0 = lambda x: f"{x:,.0f}"; f1 = lambda x: f"{x:,.1f}"; f2 = lambda x: f"{x:.2f}"; f3 = lambda x: f"{x:.3f}"
def setc(doc, tbl, r, c, text):
    """(rowAddr, colAddr) 주소로 셀 지정 (병합 셀 대응)"""
    for tc in tbl.iter(P + "tc"):
        ca = tc.find(P + "cellAddr")
        if ca is not None and int(ca.get("rowAddr")) == r and int(ca.get("colAddr")) == c: doc.set_cell_text(tc, text); return
    raise KeyError((r, c))
def grade(sf): return "A" if sf > 1.0 else ("C" if sf >= 0.9 else ("D" if sf >= 0.75 else "E"))
def ok(r): return "O.K" if r <= 1.0 else "N.G"
def first(pattern):
    return sorted(glob.glob(pattern))[0]

def load_png(path):
    from PIL import Image
    im = Image.open(path); return open(path, "rb").read(), path.rsplit(".", 1)[-1].lower(), im.size[0], im.size[1]

class Builder:
    def __init__(self, doc, ps):
        self.doc = doc; self.T = dict(h2=copy.deepcopy(ps[352]), h3=copy.deepcopy(ps[353]), h4=copy.deepcopy(ps[354]), body=copy.deepcopy(ps[355]), text=copy.deepcopy(ps[398]),
                                    fig=copy.deepcopy(ps[399]), figcap=copy.deepcopy(ps[400]), tblcap=copy.deepcopy(ps[593]), tbl=copy.deepcopy(ps[594]), tbl6=copy.deepcopy(ps[597]), spacer=copy.deepcopy(ps[443]), num=copy.deepcopy(ps[490]))
        self.anchor = None
    def _add(self, el): self.anchor = insert_after(self.anchor, [el]); return el
    def h2(self, t): return self._add(new_para(self.T["h2"], t))
    def h3(self, t): return self._add(new_para(self.T["h3"], t))
    def h4(self, t): return self._add(new_para(self.T["h4"], t))
    def body(self, t): return self._add(new_para(self.T["body"], t))
    def text(self, t): return self._add(new_para(self.T["text"], t))
    def spacer(self): return self._add(new_para(self.T["spacer"], ""))
    def table(self, caption, data, widths=None, header_rows=1, tmpl="tbl"):
        if caption: self._add(new_para(self.T["tblcap"], caption))
        ncols = max(len(r) for r in data); t = new_table(self.doc, self.T[tmpl], len(data), ncols, data, widths, header_rows); self._add(t); self.spacer(); return t
    def fig(self, path, caption, max_w=30000):
        fp = copy.deepcopy(self.T["fig"]); cp = copy.deepcopy(self.T["figcap"]); self._add(fp); self._add(cp)
        pic = list(fp.iter(P + "pic"))[0]; data, ext, w, h = load_png(path); ref = self.doc.add_image(data, ext); self.doc.swap_pic(pic, ref, w, h, max_width_hu=max_w); self.doc.set_para_text(cp, caption)
        cp.set("styleIDRef", "16"); cp.set("paraPrIDRef", "71")   # 문서 표준 그림제목(【그림 5.x】 자동번호) — 템플릿 400은 번호 없는 '<그림>' 스타일
        for r in cp.findall(P + "run"): r.set("charPrIDRef", "2")
        for q in (fp, cp):
            for la in q.findall(P + "linesegarray"): q.remove(la)
        return fp

# ───────────────────────── 상부구조 갱신 ─────────────────────────
def refill_stress_table(doc, tbl, tag):
    """정/부모멘트부 응력 검토 결과 12×13: rows 3..11 = case 1..9; cols 1-3 바닥판 상연, 4-6 바닥판 하연, 7-9 강재 상연, 10-12 강재 하연 (작용, 허용, S.F)"""
    G = GOV[tag]["cases"]
    for cid in range(1, 10):
        c = G[str(cid)]; r = 2 + cid
        for blk, ii, kind in ((1, 2, "conc"), (4, 4, "conc"), (7, 0, "steel_top"), (10, 1, "steel_bot")):
            v = max(c["max"][ii], c["min"][ii], key=abs)
            if kind == "conc":
                if cid == 1 or abs(v) < 0.005: vals = ("-", "-", "-")
                else: fa_ = c["fc"]; vals = (f"{v:.2f}", f"{fa_:.1f}", f"{fa_/abs(v):.2f}" if abs(v) > 0.01 else "-")
            else:
                fa_ = c["fa"] if v >= 0 else (c["fca_top"] if kind == "steel_top" else c["fca_bot"]); vals = (f"{v:.2f}", f"{fa_:.1f}", f"{fa_/abs(v):.2f}")
            for k, x in enumerate(vals): setc(doc, tbl, r, blk + k, x)

def yield_table(doc, ps, i0, i1, tag, B):
    """항복 안전도 문단(i0~i1)을 표로 교체"""
    yc = GOV["yield_check"][tag]; anchor = ps[i0 - 1]
    for p in ps[i0:i1 + 1]: p.getparent().remove(p)
    data = [["구분", "1.3D", "2.15(L+i)", "크리프", "건조수축", "온도차", "Σf (MPa)", "허용 (MPa)", "비", "판정"]]
    for y in yc: data.append([f"{y['fiber']} ({y['sign']})", f2(y["D13"]), f2(y["L215"]), f2(y["creep"]), f2(y["shrink"]), f2(y["temp"]), f2(y["sum"]), f1(y["fy"]), f3(y["ratio"]), "O.K" if y["ok"] else "N.G"])
    B.anchor = anchor; B.text("∑f = 1.3 × (합성전 + 합성후 고정하중 응력) + 2.15 × 활하중(충격 포함) 응력 + 크리프 + 건조수축 + 온도차 (각각 불리한 부호만 포함) ≤ 항복점 응력 (SM490 320 MPa, 콘크리트 3/5·fck, 철근 fy) [도로교설계기준 2010 3.9.3.2]")
    B.table("", data, widths=[2.2, 1, 1.1, 1, 1, 1, 1.1, 1.1, 0.8, 0.8])

def superstructure(doc, ps, B):
    refill_stress_table(doc, ps[232].find(".//" + P + "tbl"), "pos"); refill_stress_table(doc, ps[304].find(".//" + P + "tbl"), "neg")
    # 요약표 655 (14×13): case rows 3..11, 최소안전율 12, 평가 13
    t = ps[655].find(".//" + P + "tbl"); mins = [99.0] * 4
    for cid in range(1, 10):
        r = 2 + cid
        for k, (tag, ii) in enumerate((("pos", 0), ("pos", 1), ("neg", 0), ("neg", 1))):
            c = GOV[tag]["cases"][str(cid)]; v = max(c["max"][ii], c["min"][ii], key=abs); fa_ = c["fa"] if v >= 0 else (c["fca_top"] if ii == 0 else c["fca_bot"]); sf = fa_ / abs(v)
            setc(doc, t, r, 1 + 3 * k, f"{v:.2f}"); setc(doc, t, r, 2 + 3 * k, f"{fa_:.1f}"); setc(doc, t, r, 3 + 3 * k, f"{sf:.2f}"); mins[k] = min(mins[k], sf)
    for k in range(4): setc(doc, t, 12, 1 + 3 * k, f"{mins[k]:.2f}"); setc(doc, t, 13, 1 + 3 * k, grade(mins[k]))
    # 항복검토: 뒤(neg 315~339)부터
    yield_table(doc, ps, 315, 339, "neg", B); yield_table(doc, ps, 243, 267, "pos", B)
    # 절 제목을 편람 단계 표기로
    ren = {51: "[단계 1] 검토조건", 99: "[단계 3] 바닥판 검토", 141: "[단계 2] 단면제원·유효폭 및 [단계 4-2] 해석 모델", 164: "[단계 4-1] 하중 산정", 183: "[단계 4-3] 단면력 산정",
           195: "[단계 4-4] 정모멘트부 응력 검토", 269: "[단계 4-4] 부모멘트부 응력 검토", 340: "상부구조 안전성 검토 결과 요약 (단계 5~10·13 이음·보강재·가로보·다이아프램·전단연결재·부대시설은 진단 범위에서 제외, 11 피로는 상태평가로 대체)"}
    for i, tx in ren.items(): doc.set_para_text(ps[i], tx)
    doc.set_para_text(ps[96], "설계방법")
    # 결론 상부 문장
    sp, sn = GOV["sf_pos"], GOV["sf_neg"]
    doc.set_para_text(ps[663], f"허용응력설계법(도로교설계기준 2010, 표 3.9.4 연·모멘트부호별 증가율, 표 3.4.3 국부좌굴)에 의한 STB 거더 응력 검토 결과, 정모멘트부 최소 안전율 {sp:.2f}, 부모멘트부 최소 안전율 {sn:.2f}로 모든 하중조합에서 허용응력 이내이며 항복에 대한 안전도 검사도 만족하여 안전성 평가 결과는 '{grade(min(sp, sn))}' 등급으로 판단된다.")

# ───────────────────────── 하부구조 재구성 ─────────────────────────
def abutment(B):
    g, c, cond, brg, pl, s, rb, ps_ = A["geom"], A["cases"], A["cond"], A["bearing"], A["piles"], A["section"], A["rebar"], A["pile_spec"]; soil = A["soil"]
    B.h2("교대(A1) 안전성 검토 — 도로설계편람 제5편 509.1 역T형 교대 검토 단계 적용")
    B.text("검토 흐름은 도로설계편람 제5편 교량(2008) 509.1의 역T형식 교대 설계 예 [단계 1]~[단계 9]를 따르되, 진단이므로 단면 가정·조정 대신 준공도면의 단면·배근을 입력하고 안전율·강도비로 판정한다. 설계법은 안정검토 허용응력설계법, 단면검토 강도설계법(도로교설계기준 2010 식 ① 1.3D + 2.15(L+i) + 1.7H)이며, 지진하중은 내진성능평가에서 별도 검토하므로 제외한다.")
    B.h3("[단계 1] 검토조건 및 제원")
    for ln in [f"형식·규모 : 역T형 교대(말뚝기초), 폭 {g['LW']} m, 전체높이 {g['z_top']:.3f} m (기초저면 EL {SUB['교대']['A1']['기초저면_EL']} ~ 노면 EL {SUB['교대']['A1']['노면_EL']})",
               f"단면(도면 자동판독) : 앞굽 {g['toe']} m, 벽체 {g['stem']} m, 뒷굽 {g['heel']} m (배면 1:1 헌치 {g['hh']} m), 기초 B = {g['B']} m × t = {g['tf']} m, 흉벽 {g['t_par']} m × {g['Hp']:.3f} m, 받침면 높이 {g['z_seat']:.3f} m",
               f"말뚝 : 강관말뚝 Ø{ps_['D']*1000:.0f}×{ps_['t']*1000:.0f} t, {ps_['n']}본({len(ps_['rows_from_toe'])}열 × {ps_['per_row']}), 열 위치(앞굽 연단 기준) {ps_['rows_from_toe']} m, 길이 {ps_['L']} m",
               f"재료 : 콘크리트 fck = {SUB['재료']['fck_구체']} MPa, 철근 SD30 fy = {SUB['재료']['fy']:.0f} MPa, γc = {SUB['재료']['gamma_c']} kN/m³",
               f"배근(교대 배근도 C0051105-005) : 벽체 배면 {rb['벽체_배면_주철근']}, 전면 {rb['벽체_전면_주철근']}, 수평철근 {rb['벽체_수평철근']}, 흉벽 {rb['흉벽_주철근']}, 기초 {rb['기초_주철근']}"]: B.body(ln)
    B.fig(os.path.join(PJ, "png", "sub", "crop", "A1_front.png"), "교대 A1 일반도 (준공도면 C0051105-001, 정면)")
    B.fig(os.path.join(RUNS, "abutment", "A1_v3_section.png"), "교대 A1 검토 단면 — 자중 블록 ①~⑤, 가상배면(안정검토)·구체배면(단면검토), 토압 분포, 말뚝 열")
    B.h3("[단계 2] 지진변위 검토 — 제외"); B.body("받침 연단거리·최소 받침지지길이·여유간격 검토는 내진성능평가 항목이므로 본 안전성 검토에서 제외한다.")
    B.h3("[단계 3] 받침 용량 검토")
    B.table("교대(A1) 받침 용량 검토", [["받침", "수직 용량 (kN)", "반력 (D+L)/받침 (kN)", "용량비", "판정"], [brg["name"], f0(brg["cap"]), f0(brg["R"]), f2(brg["ratio"]), ok(brg["ratio"])]], widths=[2.4, 1.2, 1.5, 0.8, 0.8])
    B.h3("[단계 4] 설계조건")
    for ln in [f"받침 마찰계수 : 탄성받침(고무) 겉보기 정지마찰계수 0.15 [편람 509.1 단계 4-1] → 온도·마찰 수평력 = 0.15 × 고정하중 반력", f"뒷채움 : γ = {soil['gamma']} kN/m³, φ = {soil['phi']}° (지반조사 없음 → 도로설계요령 표준값), 상재하중 q = {soil['q']} kN/m² [2016 국도건설공사 설계실무요령]",
               f"토압 작용면 : 안정검토는 뒷굽 연단의 연직 가상배면(Rankine, δ = 0), 벽체·흉벽 단면검토는 구체 배면(Coulomb, δ = φ/3) [편람 단계 4-7·5-3, 2020 도로설계요령 4.6]",
               f"상부구조 반력(격자해석, 단위폭 환산 1/{g['LW']}) : 고정하중 {f2(cond['D'])} kN/m, 활하중(DB-24, 충격 포함) {f2(cond['LL'])} kN/m"]: B.body(ln)
    B.table("토압계수", [["구분", "안정검토 (가상배면)", "벽체·흉벽 단면검토 (구체배면)"]] + [[r[0], str(r[1]), str(r[2])] for r in cond["table"]], widths=[1.4, 1.5, 1.8])
    LA = abutment_lines(A)
    for ln in LA["step4"]: B.body(ln)
    B.h3("[단계 5] 설계력 산정")
    B.text("단위폭(1 m)당 하중을 앞굽 연단 기준으로 집계한다. 저항모멘트 Mr은 연직력, 전도모멘트 Mo는 수평력에 의한 값이며, ξ = (Mr − Mo)/ΣV, 편심 e = B/2 − ξ 이다.")
    data = [["구분", "수직력 (kN)", "수평력 (kN)", "x (m) [합계: ξ]", "y (m) [합계: e]", "M저항 (kN·m)", "M전도 (kN·m)"]]
    for r in A["loads"]: data.append([r["name"], f2(r["V"]), f2(r["H"]), f3(r["x"]), f3(r["y"]), f2(r["Mr"]), f2(r["Mo"])])
    for k, v in c.items(): data.append([k, f2(v["V"]), f2(v["H"]), f3(v["xi"]), f3(v["e"]), f2(v["Mr"]), f2(v["Mo"])])
    B.table("교대(A1) 하중집계 (단위폭, 앞굽 연단 기준)", data, widths=[2.6, 1, 1, 1, 1, 1.1, 1.1])
    for ln in LA["step5"]: B.body(ln)
    B.fig(os.path.join(RUNS, "abutment", "A1_v3_wall_loads.png"), "벽체·흉벽 단면검토 하중 (구체배면 토압, 받침 마찰력, 흉벽 윤하중)")
    B.h3("[단계 6] 안정검토 — 말뚝 반력")
    B.text(f"말뚝기초이므로 전도·활동·지지력 검토는 말뚝 반력 검토로 대체한다 [편람 509.2.5 단계 7-2]. 말뚝 반력은 확대기초를 강체로 보는 관용법(연직력·모멘트 분담, 수평력 균등 분담) [2020 도로설계요령 6.1.2 식 6.1]. 강관 유효단면(부식 2 mm 공제) Ae = {pl['Ap']*1e4:.1f} cm², 허용축력 Ra = Ae × 140 MPa = {f0(pl['Ra'])} kN, 허용전단 80 MPa. 지반 지지력·침하·수평변위는 지반조사·시공기록이 없어 산정하지 않는다.")
    keys = list(next(iter(pl["cases"].values()))["R"].keys())
    data = [["하중조합", "ΣV (kN)", "ΣH (kN)", "e (m)"] + keys + ["수평/본", "f (MPa)", "v (MPa)", "판정"]]
    for k, v in pl["cases"].items(): data.append([k, f0(v["V"]), f0(v["H"]), f3(v["e"])] + [f0(x) for x in v["R"].values()] + [f1(v["Hp"]), f1(v["f"]), f1(v["v"]), "O.K" if v["ok_R"] and v["ok_v"] and v["ok_t"] else "N.G"])
    B.table("교대(A1) 말뚝 반력 (사용하중, kN/본)", data, widths=[2] + [0.9] * (len(data[0]) - 1))
    for ln in LA["step6"]: B.body(ln)
    B.h3("[단계 7] 단면검토")
    st, hz, pa, ft = s["stem"], s["horiz"], s["parapet"], s["footing"]
    B.text(f"강도설계법 하중조합 ①(1.3D + 2.15(L+i) + 1.7H)로 단면력을 산정하고, 도면 배근의 설계강도(φ 휨 0.85, 전단 0.80)와 비교한다. 벽체는 기초 접합부를 고정단으로 하는 캔틸레버(계산높이 {g['Hw']:.3f} m), 흉벽은 토압과 윤하중(DB-24 후륜 96 kN, 접지 0.2×0.5 m, 지표 1 m 범위, 1.5 m 분포) [2020 도로설계요령 4.6 식 4.16~4.18], 앞굽·뒷굽은 계수하중 말뚝반력(본당 {', '.join(f0(x) for x in ft['Ru'])} kN)과 자중·토사로 검토한다.")
    data = [["부재", "하중", "산정식", "전단력 (kN/m)", "팔길이 (m)", "모멘트 (kN·m/m)", "하중계수"]]
    for r in st["rows"]: data.append(["벽체", r["name"], r["formula"], f2(r["V"]), f3(r["arm"]), f2(r["M"]), f2(r["f"])])
    data.append(["벽체", "계수 단면력", "", f2(st["Vu"]), "", f2(st["Mu"]), "Vu, Mu"])
    for r in pa["rows"]: data.append(["흉벽", r["name"], r["formula"], f2(r["V"]), f3(r["arm"]), f2(r["M"]), f2(r["f"])])
    data.append(["흉벽", "계수 단면력 A (토압+상재)", "", f2(pa["VuA"]), "", f2(pa["MuA"]), "Vu, Mu"]); data.append(["흉벽", "계수 단면력 B (토압+윤하중)", "", f2(pa["Vu"]), "", f2(pa["Mu"]), "Vu, Mu"])
    B.table("벽체·흉벽 단면력", data, widths=[0.8, 1.9, 2.2, 1, 0.9, 1.2, 0.9])
    data = [["부재", "배근", "As (mm²/m)", "d (mm)", "Mu (kN·m/m)", "φMn", "Mu/φMn", "Vu (kN/m)", "φVc", "Vu/φVc", "판정"],
            ["벽체 기부", st["bar"], f0(st["As"]), f0(st["d"]), f1(st["Mu"]), f1(st["phiMn"]), f3(st["ratio_M"]), f1(st["Vu"]), f1(st["phiVc"]), f3(st["ratio_V"]), ok(max(st["ratio_M"], st["ratio_V"]))],
            ["흉벽 A (토압+상재)", pa["bar"], f0(pa["As"]), f0(pa["d"]), f1(pa["MuA"]), f1(pa["phiMn"]), f3(pa["ratio_MA"]), f1(pa["VuA"]), f1(pa["phiVc"]), f3(pa["ratio_VA"]), ok(max(pa["ratio_MA"], pa["ratio_VA"]))],
            ["흉벽 B (토압+윤하중)", pa["bar"], f0(pa["As"]), f0(pa["d"]), f1(pa["Mu"]), f1(pa["phiMn"]), f3(pa["ratio_M"]), f1(pa["Vu"]), f1(pa["phiVc"]), f3(pa["ratio_V"]), ok(max(pa["ratio_M"], pa["ratio_V"]))],
            ["앞굽판", ft["bar"], f0(ft["As"]), f0(ft["d"]), f1(ft["toe"]["Mu"]), f1(ft["phiMn"]), f3(ft["toe"]["ratio_M"]), f1(ft["toe"]["Vu"]), f1(ft["phiVc"]), f3(ft["toe"]["ratio_V"]), ok(max(ft["toe"]["ratio_M"], ft["toe"]["ratio_V"]))],
            ["뒷굽판", ft["bar"], f0(ft["As"]), f0(ft["d"]), f1(ft["heel"]["Mu"]), f1(ft["phiMn"]), f3(ft["heel"]["ratio_M"]), f1(ft["heel"]["Vu"]), f1(ft["phiVc"]), f3(ft["heel"]["ratio_V"]), ok(max(ft["heel"]["ratio_M"], ft["heel"]["ratio_V"]))]]
    B.table("교대(A1) 부재별 강도 검토 (도면 배근)", data, widths=[1.1, 1.1, 1, 0.8, 1, 0.9, 0.9, 0.9, 0.8, 0.9, 0.8])
    for ln in LA["step7"]: B.body(ln)
    B.text(f"흉벽은 준공 당시 설계 방식(토압 + 상재하중 10 kN/m², 경우 A)으로는 강도비 {f3(pa['ratio_MA'])}로 안전하나, 2020 도로설계요령 4.6의 윤하중(경우 B)을 고려하면 {f3(pa['ratio_M'])}로 설계강도를 초과한다. 흉벽 두께 {g['t_par']} m·배근 {pa['bar']}은 도면 판독값이므로 현장 확인 후 보수·보강 여부를 판단한다.")
    B.fig(first(os.path.join(PNG, "A1_배근_단면AA", "*.png")), "교대 A1 배근 단면 A-A (준공도면 C0051105-005)")
    B.h3("[단계 8·9] 접속슬래브·날개벽 — 제외"); B.body("접속슬래브와 날개벽은 상태평가 항목으로 대체하고 본 검토에서 제외한다.")

def piers(B):
    B.h2("교각(P1~P5) 안전성 검토 — 도로설계편람 제5편 509.2 콘크리트교각 검토 단계 적용")
    B.text("검토 흐름은 편람 509.2의 T형 교각 설계 예 [단계 1]~[단계 8]을 따른다. 대표 교각은 기둥 높이가 가장 크고 고정단 받침이 놓인 P3이며, P1·P2·P4·P5는 같은 절차로 검토하여 결과표에 함께 정리한다. 하중조합은 도로교설계기준 2010 강도설계 ①~⑥·⑧·⑨(지진 ⑦ 제외)와 사용조합이고, 표 2.2.6의 최소 축하중(고정하중계수 1.0/0.95/0.9) 조합을 편심 검토에 포함한다.")
    B.h3("[단계 1] 검토조건")
    rb = p3["rebar"]
    for ln in [f"형식 : Y형 코핑 + 사각기둥 {g3['by']}×{g3['bx']} m + 사각 확대기초 {g3['foot'][0]}×{g3['foot'][1]}×{g3['foot'][2]} m, 강관말뚝 Ø508×9 t {g3['piles']['본수']}본 (P3)",
               f"높이 : 기둥 {g3['Hc']} m, 코핑 {g3['Hcop']} m (상단 수직부 {g3['cop_v']} m + 곡선부 5.0 m), 받침면 EL {g3['EL_seat'][0]} / {g3['EL_seat'][1]}, 기초 저면 EL {SUB['교각']['P3']['기초저면_EL']}",
               f"재료 : fck = {SUB['재료']['fck_구체']} MPa, fy = {SUB['재료']['fy']:.0f} MPa (SD30), γc = {SUB['재료']['gamma_c']} kN/m³, Ec = {SUB['재료']['Ec']:,} MPa",
               f"배근(교각 배근도 C0051105-033~035) : 기둥 {rb['기둥_주철근']}, 띠철근 {rb['기둥_띠철근']}; 코핑 {rb['코핑_주철근']}, {rb['코핑_띠철근']}; 기초 {rb['기초_주철근']}",
               "설계방법 : 안정성(말뚝 반력) 허용응력설계법(사용하중), 단면 강도설계법(φ 휨 0.85·전단 0.80·기둥 0.70). 지진·응답수정계수·심부구속철근은 내진성능평가에서 별도 검토"]: B.body(ln)
    B.fig(first(os.path.join(PNG, "P3_일반도_정면측면", "*.png")), "교각 P3 일반도 (준공도면 C0051105-020, 정면도·단면 A-A)")
    B.h3("[단계 2] 단면제원 및 제상수")
    data = [["위치", "b (m)", "h (m)", "A (m²)", "Iy 교축 (m⁴)", "Ix 교축직각 (m⁴)"]]
    for r in p3["props"]: data.append([r["name"], "-" if r["b"] is None else f3(r["b"]), f3(r["h"]), f3(r["A"]) if r["Iy"] is not None else r.get("note", ""), "-" if r["Iy"] is None else f3(r["Iy"]), "-" if r["Ix"] is None else f3(r["Ix"])])
    B.table("교각 P3 단면 제상수 (코핑은 정면 폭 b·두께 h, Y형 곡선부는 선형 변단면 근사)", data, widths=[1.6, 0.9, 0.9, 1.6, 1.2, 1.2])
    B.body(f"코핑 자중은 도면 호(R = 8.20 / 17.00 m)를 적분한 실제 Y형 정면적 {g3['cop_area']:.3f} m²(선형 변단면 근사 {30.809:.3f} m²의 {g3['cop_area']/30.809*100:.0f} %)로 산정하고, 해석모델의 변단면 코핑 재료 밀도를 같은 비율로 보정하였다.")
    B.fig(first(os.path.join(PNG, "P3_배근_기둥단면", "*.png")), "교각 P3 배근 (준공도면 C0051105-034: 코핑 평면·단면 E-E·F-F)")
    B.h3("[단계 3] 하중계산")
    rx = RX["P3"]; L1 = rx["L_one"]
    data = [["받침", "고정하중 (합성전+후)", "활하중 만재 (max)", "활하중 편재 L1 (G1측)", "활하중 편재 L2 (G2측)"],
            ["G1", f1(rx["D_g"]["G1"]), f1(rx["L_g"]["G1"][0]), f1(L1["L1"]["G1"]), f1(L1["L2"]["G1"])], ["G2", f1(rx["D_g"]["G2"]), f1(rx["L_g"]["G2"][0]), f1(L1["L1"]["G2"]), f1(L1["L2"]["G2"])],
            ["계", f1(rx["D"]), f1(rx["Lmax"]), f1(L1["L1"]["G1"] + L1["L1"]["G2"]), f1(L1["L2"]["G1"] + L1["L2"]["G2"])]]
    B.table("교각 P3 상부반력 (격자해석, kN; 활하중 DB-24·DL-24 충격 포함)", data, widths=[0.8, 1.5, 1.3, 1.4, 1.4])
    H = rx["H"]; inf = p3["loads_info"]
    for ln in [f"풍하중 : 상부(격자 반력) 교축직각 {f1(H['W'][1])} kN(작용높이 수압면 중심), 활하중 풍하중 {f1(H['WL'][1])} kN(노면 위 1.8 m), 하부구조 각형 3.0 kN/m² × 투영폭 [도로교설계기준 2010 표 2.1.16]",
               f"제동하중 : DB-24의 10 % = {f1(H['LF'][0])} kN (고정단 P3만, 노면 위 1.8 m), 원심하중 {f1(H['CF'][1])} kN, 온도하중 : 고정단은 온도 이동량이 없어 미고려, 가동단 교각은 받침 마찰력 μ·R_D (μ = 0.05)",
               "지진하중 : 내진성능평가에서 별도 검토 (제외). 수압·충돌하중 : 하천·하부도로 없음 → 미고려"]: B.body(ln)
    B.fig(os.path.join(PNG, "P3_loads.png"), "교각 P3 하중 재하 (받침별 상부반력, kN)")
    B.h3("[단계 4] 하중조합")
    data = [["조합", "식", "D", "L+i", "CF", "H", "W", "WL", "BK", "G", "D 최소(편심)"]]
    for cid, f in CB["강도"].items():
        if f.get("E"): continue
        data.append([f"강도 {cid}", f["식"], f2(f["D"]), f2(f["L"]), f2(f["CF"]), f2(f["H"]), f2(f["W"]), f2(f["WL"]), f2(f["BK"]), f2(f["G"]), f2(f["D_min"])])
    for cid, f in CB["사용"].items():
        if f.get("E"): continue
        data.append([f"사용 {cid}", f["식"], f2(f["D"]), f2(f["L"]), f2(f["CF"]), f2(f["H"]), f2(f["W"]), f2(f["WL"]), f2(f["BK"]), f2(f["G"]), "-"])
    B.table("하중조합 및 하중계수 (도로교설계기준 2010 2.2.3.2 식 ①~⑥·⑧·⑨, 표 2.2.6, 표 2.2.3; 지진 ⑦·6 제외)", data, widths=[0.9, 3.4, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.9])
    B.h3("[단계 5] 구조해석 및 단면력")
    B.text("MIDAS CIVIL NX 2026 프레임 모델(기둥 2요소, 코핑 줄기 변단면 2요소·머리 1요소, 받침 좌석 절점까지 무게 0 강성 팔 2요소, 기초 상면 고정)에 하중별 케이스를 재하하여 요소력·반력을 구하고, 조합은 파이썬에서 수행하였다. 자중은 NX 자중(DEAD)이 도면 기준 코핑·기둥 무게와 일치함을 매 해석마다 검증하였다(차이 0.0 %).")
    B.fig(os.path.join(RUNS, "pier3", "P3_My_RD.jpg"), "교각 P3 휨모멘트도 (고정하중 반력 RD, NX 캡처)", max_w=14000)   # 세로로 긴 캡처 — 한 쪽을 통째로 차지하지 않도록
    data = [["하중", "P (kN)", "Vx 교축 (kN)", "Vy 교축직각 (kN)", "Mx 교축직각 (kN·m)", "My 교축 (kN·m)"]]
    for k, v in p3["per_load"].items(): b = v["base"]; data.append([k, f1(b["P"]), f1(b["Vx"]), f1(b["Vy"]), f1(b["Mx"]), f1(b["My"])])
    B.table("교각 P3 하중별 기둥 하단(기초 상면) 단면력", data, widths=[1.2, 1, 1.1, 1.2, 1.3, 1.2])
    data = [["대표 조합", "조합", "P (kN)", "Mx (kN·m)", "My (kN·m)", "Vx (kN)", "Vy (kN)"]]
    for nm, key in p3["rep"].items():
        c = next(x for x in p3["combos"] if x["key"] == key); data.append([nm, key, f0(c["P"]), f0(c["Mx"]), f0(c["My"]), f0(c["Vx"]), f0(c["Vy"])])
    B.table("교각 P3 대표 조합 기둥 하단 단면력", data, widths=[1.5, 2.2, 0.9, 1, 1, 0.8, 0.8])
    B.h3("[단계 6] 부재검토 — 코핑·기둥")
    cp = p3["coping"]
    B.text(f"코핑 팔은 기둥면을 위험단면으로 하고 av/d = {f3(cp['av_d'])} ≤ 1.0이므로 브래킷으로 검토한다 [편람 단계 6-2, 도로교설계기준 2010 4.4.6.8]. Vu = 1.3D + 2.15L의 받침 1개 최대 반력, Nuc = 0.2Vu, Mu = Vu·av + Nuc(h − d). 소요 As = max(Af + An, 2Af/3 + An), 브래킷 최소철근 As,min = 0.04(fck/fy)·b·d.")
    data = [["교각", "av (m)", "d (m)", "Vu (kN)", "Mu (kN·m)", "φVn,max (kN)", "As 소요 (mm²)", "As 사용", "As 비", "As,min", "As,min 비", "Ah 소요/사용", "판정"]]
    for n, r in PR.items():
        c = r["coping"]; data.append([n, f3(c["av"]), f3(c["d"]), f0(c["Vu"]), f0(c["Mu"]), f0(c["phiVn_max"]), f0(c["As_req"]), f0(c["As_use"]), f3(c["ratio_As"]), f0(c["As_min"]), f2(c["ratio_Asmin"]), f"{f0(c['Ah_req'])}/{f0(c['Ah_use'])}", ok(c["ratio_As"]) + ("" if c["ratio_Asmin"] <= 1 else "(최소철근 미달)")])
    B.table("코핑 브래킷 검토 (기둥면, 강도 ①)", data, widths=[0.6, 0.7, 0.7, 0.9, 0.9, 1, 1, 0.9, 0.7, 0.9, 0.8, 1.3, 1.2])
    LP = pier_lines(p3)
    for ln in LP["coping"]: B.body("P3: " + ln)
    col = p3["column"]
    B.text(f"기둥은 캔틸레버 비횡구속 부재(k = 2.1)로 세장비 λ = k·Lu/r (교축 {f1(col['lambda_x'])}, 교축직각 {f1(col['lambda_y'])}) ≥ 22 → 장주이며, 모멘트확대계수 δs = 1/(1 − Pu/0.75Pc), Pc = π²EI/(kLu)², EI = 0.4EcIg/(1 + βd)로 계수모멘트를 확대하여 P–M 상관도(φ = 0.70)로 검토한다 [편람 단계 6-8~6-10]. 주철근 As = {f0(col['As'])} mm² (ρ = {col['rho']*100:.2f} %).")
    B.fig(os.path.join(PNG, "P3_PM.png"), "교각 P3 기둥 P–M 상관도와 계수하중 조합 (교축·교축직각)")
    data = [["교각", "As (mm²)", "ρ (%)", "λ 교축/직각", "최불리 조합", "방향", "Pu (kN)", "Mu (kN·m)", "δs", "δs·Mu", "Mu/φMn", "전단 Vu/φVn", "판정"]]
    for n, r in PR.items():
        c = r["column"]; w = c["worst"]; data.append([n, f0(c["As"]), f2(c["rho"] * 100), f"{c['lambda_x']:.0f}/{c['lambda_y']:.0f}", w["key"], w["dirn"], f0(w["P"]), f0(w["M"]), f3(w["ds"]), f0(w["Mmag"]), f3(w["ratio"]), f3(c["shear"]["ratio"]), ok(max(w["ratio"], c["shear"]["ratio"]))])
    B.table("기둥 검토 (P–M 강도비·전단)", data, widths=[0.6, 0.9, 0.6, 0.9, 2.2, 0.5, 0.8, 0.8, 0.6, 0.8, 0.7, 0.8, 0.6])
    for ln in LP["column"]: B.body("P3: " + ln)
    B.h3("[단계 7] 기초 및 말뚝")
    fd = p3["footing"]
    B.text(f"확대기초 강체 판정 βλ ≤ 1.0 [도로교설계기준 2010 5.4.5.2]: 말뚝 축방향 스프링정수 Kv = a·Ap·Ep/L (a = 0.014(L/D) + 0.78) = {f0(fd['Kv'])} kN/m, kp = Kv·n/(L·B), β = (3kp/(E·h³))^0.25. 말뚝 반력은 강체 캡(연직력 균등 + 모멘트 분담)으로 사용하중 조합에서 구하고 [도로교설계기준 2010 2.2.3.2(6)], 허용축력 Ra = Ae × 140 MPa(부식 2 mm 공제). 기초 단면은 기둥면에서 계수하중 말뚝반력 − 기초 자중으로 검토한다(기초 {p3['rebar']['기초_주철근']}).")
    B.fig(os.path.join(PNG, "P3_piles.png"), "교각 P3 말뚝 배치 및 반력 (사용하중 최대 조합)")
    data = [["교각", "Kv (kN/m)", "βλ", "강체", "말뚝 max (kN)", "조합", "말뚝 min (kN)", "수평/본 (kN)", "Ra (kN)", "R/Ra", "기초 Mu (kN·m)", "φMn", "Mu/φMn", "Vu/φVc", "판정"]]
    for n, r in PR.items():
        f = r["footing"]; s = f["section"]; data.append([n, f0(f["Kv"]), f3(f["beta_lam"]), "O.K" if f["rigid"] else "N.G", f0(f["pile_max"]), f["pile_max_key"], f0(f["pile_min"]), f0(f["pile_h"]), f0(f["Ra"]), f3(f["ratio_pile"]), f0(s["Mu"]), f0(s["phiMn"]), f3(s["ratio_M"]), f3(s["ratio_V"]), ok(max(f["ratio_pile"], s["ratio_M"], s["ratio_V"]))])
    B.table("기초·말뚝 검토 (P1~P5)", data, widths=[0.6, 1, 0.6, 0.6, 0.9, 1.6, 0.9, 0.8, 0.8, 0.6, 1, 0.9, 0.7, 0.7, 0.6])
    for ln in LP["footing"]: B.body("P3: " + ln)
    B.h3("[단계 8] 받침 용량")
    data = [["교각", "받침", "수직 용량 (kN)", "(D+L)max/받침 (kN)", "용량비", "판정"]]
    for n, r in PR.items(): b = r["bearing"]; data.append([n, f"{b['ton']}톤", f0(b["cap"]), f0(b["R"]), f2(b["ratio"]), ok(b["ratio"])])
    B.table("교각 받침 용량 검토", data, widths=[0.7, 1, 1.2, 1.4, 0.8, 0.8])
    B.body("확인 필요 : P4·P5 말뚝 배치(도면 격자 판독), P5 코핑 상폭 8.0 m·PSC측 받침 반력. 말뚝 지반 지지력·침하·수평변위는 지반조사·시공기록 없음 → 미산정.")
    B.text("교대·교각의 모든 하중별·조합별 단면력, 말뚝 반력, 부재검토 중간값과 풀이 문장은 부록 계산근거 엑셀(부록_계산근거_5장.xlsx)의 시트 '교대_*', '교각_*'에 수록하였다.")

def summary_and_conclusion(doc, ps, B):
    # 요약표 658 교체
    s = A["section"]; st, pa, ft = s["stem"], s["parapet"], s["footing"]; pl = A["piles"]; pmax = max(v["f"] for v in pl["cases"].values())
    hdr = ["구분", "부재", "검토 항목", "발생값", "허용/설계값", "비 (발생/허용)", "판정", "등급"]; data = [hdr]
    for nm, a, b, r in (("벽체 기부", st["Mu"], st["phiMn"], st["ratio_M"]), ("흉벽 A(토압+상재)", pa["MuA"], pa["phiMn"], pa["ratio_MA"]), ("흉벽 B(토압+윤하중)", pa["Mu"], pa["phiMn"], pa["ratio_M"]), ("앞굽판", ft["toe"]["Mu"], ft["phiMn"], ft["toe"]["ratio_M"]), ("뒷굽판", ft["heel"]["Mu"], ft["phiMn"], ft["heel"]["ratio_M"])):
        data.append(["교대 A1", nm, "휨 Mu/φMn (kN·m/m)", f1(a), f1(b), f3(r), ok(r), grade(1 / r)])
    data.append(["교대 A1", "말뚝", "축응력 f/fa (MPa)", f1(pmax), "140.0", f3(pmax / 140), ok(pmax / 140), grade(140 / pmax)])
    data.append(["교대 A1", "받침", "반력/용량 (kN)", f0(A["bearing"]["R"]), f0(A["bearing"]["cap"]), f2(A["bearing"]["ratio"]), ok(A["bearing"]["ratio"]), grade(1 / A["bearing"]["ratio"])])
    t_ab = new_table(doc, B.T["tbl"], len(data), 8, data, widths=[1, 1.4, 1.8, 1, 1, 1, 0.7, 0.6], height=1900)
    cap_pr = new_para(B.T["tblcap"], "교각(P1~P5) 안전성평가 결과 (지진 제외)"); data = [hdr]
    for n, r in PR.items():
        c, cw, f, b = r["coping"], r["column"]["worst"], r["footing"], r["bearing"]
        data.append([f"교각 {n}", "코핑(브래킷)", "As 소요/사용", f0(c["As_req"]), f0(c["As_use"]), f3(c["ratio_As"]), ok(c["ratio_As"]), grade(1 / c["ratio_As"])])
        data.append([f"교각 {n}", "기둥", "P–M δs·Mu/φMn (kN·m)", f0(cw["Mmag"]), f0(cw["Mmag"] / cw["ratio"]), f3(cw["ratio"]), ok(cw["ratio"]), grade(1 / cw["ratio"])])
        data.append([f"교각 {n}", "말뚝", "축력 R/Ra (kN)", f0(f["pile_max"]), f0(f["Ra"]), f3(f["ratio_pile"]), ok(f["ratio_pile"]), grade(1 / f["ratio_pile"])])
        data.append([f"교각 {n}", "기초", "휨 Mu/φMn (kN·m)", f0(f["section"]["Mu"]), f0(f["section"]["phiMn"]), f3(f["section"]["ratio_M"]), ok(f["section"]["ratio_M"]), grade(1 / f["section"]["ratio_M"])])
        data.append([f"교각 {n}", "받침", "반력/용량 (kN)", f0(b["R"]), f0(b["cap"]), f2(b["ratio"]), ok(b["ratio"]), grade(1 / b["ratio"])])
    t = new_table(doc, B.T["tbl"], len(data), 8, data, widths=[1, 1.1, 1.8, 1, 1, 1, 0.7, 0.6], height=1900); old = ps[658]
    old.getparent().replace(old, t_ab); insert_after(t_ab, [new_para(B.T["spacer"], ""), cap_pr, t])
    doc.set_para_text(ps[657], "교대(A1) 안전성평가 결과")
    worst_ab = max(st["ratio_M"], ft["toe"]["ratio_M"], ft["heel"]["ratio_M"], pmax / 140)
    doc.set_para_text(ps[666], f"교대(A1)는 도로설계편람 제5편 509.1 역T형 교대 검토 단계에 따라 허용응력설계법(안정: 말뚝 반력)과 강도설계법(단면: 1.3D + 2.15(L+i) + 1.7H)으로 검토하였다. 벽체 기부 강도비 {f3(st['ratio_M'])}, 앞굽판 {f3(ft['toe']['ratio_M'])}, 뒷굽판 {f3(ft['heel']['ratio_M'])}, 말뚝 축응력 {f1(pmax)} MPa(허용 140)로 안전하며, 흉벽은 토압과 윤하중에 대해 강도비 {f3(pa['ratio_M'])}로 {'초과하여 두께·배근을 재확인한 뒤 보수·보강 여부를 판단할 필요가 있다' if pa['ratio_M'] > 1 else '안전하다'}.")
    wc = max(PR.values(), key=lambda r: r["column"]["worst"]["ratio"]); wp = max(PR.values(), key=lambda r: r["footing"]["ratio_pile"])
    doc.set_para_text(ps[667], f"교각(P1~P5)은 편람 509.2 T형 교각 검토 단계에 따라 NX 프레임 해석과 도로교설계기준 2010 하중조합(지진 제외)으로 검토하였다. 기둥 P–M 강도비 최대 {f3(wc['column']['worst']['ratio'])}({wc['name']}), 코핑 브래킷 강도 소요철근비 최대 {f3(max(r['coping']['ratio_As'] for r in PR.values()))}, 말뚝 축력비 최대 {f3(wp['footing']['ratio_pile'])}({wp['name']}), 기초 휨 강도비 최대 {f3(max(r['footing']['section']['ratio_M'] for r in PR.values()))}로 모두 안전하다. 다만 코핑 브래킷의 최소철근량(0.04·fck/fy·b·d) 대비 사용 철근이 {f2(max(r['coping']['ratio_Asmin'] for r in PR.values()))}배 부족한 것은 강도 부족이 아닌 규정 미달 사항으로 기록한다.")

def intro(doc, ps):
    doc.set_para_text(ps[20], "구조검토는 준공도면·구조계산서·현장조사 자료를 바탕으로 MIDAS CIVIL NX 2026 격자·프레임 모델로 부재력을 산정하고, 상부구조는 허용응력설계법(강재)·강도설계법(바닥판), 하부구조는 도로설계편람 제5편 교량(2008) 검토예제의 단계별 흐름에 따라 안정검토(허용응력)·단면검토(강도설계법)로 평가하였다. 설계기준은 도로교설계기준(2010)을 기본으로 하고 세부 규정은 최신 기준(2020 도로설계요령 등)을 따르며, 지진하중은 내진성능평가에서 별도로 검토하므로 제외하였다.")
    refs = ["도로교 설계기준 (국토해양부, 2010) — 하중·하중조합, 강교편, 하부구조편", "도로교 설계기준 해설 (2008)", "콘크리트구조기준 (2012)", "도로설계편람 제5편 교량 (국토해양부, 2008) — 509 하부구조 검토예제, 506 강교", "도로설계요령 제3권 교량 (한국도로공사, 2020) — 8-3편 교량 하부 구조물",
            "2016 국도건설공사 설계실무요령 (국토교통부) 4-02 구조물공", "강도로교 상세부 설계지침 (1997)", "시설물의 안전 및 유지관리 실시 세부지침 (교량)", "순천만IC2교 준공도면 (C0051101~C0051105)"]
    for i, ln in zip(range(25, 34), refs): doc.set_para_text(ps[i], f"{i-24}) {ln}")
    # 조건비교표: 하부구조 하중조합에서 지진 제외 표기
    i, _ = doc.find_para("구조검토 조건비교")
    for j in range(i, i + 3):
        t = ps[j].find(".//" + P + "tbl")
        if t is not None:
            for tc in t.iter(P + "tc"):
                tx = para_text(tc)
                if "지진하중+편심하중" in tx: doc.set_cell_text(tc, "∙고정하중+활하중+풍하중+마찰수평력+편심하중 (지진하중은 내진성능평가에서 별도 검토)")
            break

def main():
    src = os.path.join(REP, "5장_v3.hwpx"); out = os.path.join(REP, "5장_v4.hwpx")
    doc = Hwpx(src); doc.load(); ps = doc.paragraphs(); B = Builder(doc, ps)
    intro(doc, ps); summary_and_conclusion(doc, ps, B); superstructure(doc, ps, B)
    # 하부구조: 352~604 삭제 후 351 뒤에 재구성
    for p in ps[352:605]: p.getparent().remove(p)
    B.anchor = ps[351]; doc.set_para_text(ps[351], "하부구조 안전성 검토"); abutment(B); piers(B)
    from hwpx_layout import keep_with_next, drop_pagebreaks, compact_tables
    doc.prune_images(); lay = fix_layout(doc)
    lay["compact"] = compact_tables(doc, min_rows=12, h_body=1900, h_head=2100)
    lay["dropped_pb"] = drop_pagebreaks(doc, (8, 10, 15, 26))                         # 본문·소항목·표제목 스타일의 강제 쪽나눔 제거 (5.x 절 제목·그림 쪽은 유지)
    lay["keep"] = keep_with_next(doc, ("70", "2", "3", "5", "9", "25", "140", "66", "37", "134", "142", "131"))   # 표 캡션·모든 수준 제목: 다음 문단과 함께
    doc.renumber_objects(); doc.save(out); v = doc.verify(out)
    print("layout", lay); print("verify", v); print("문단", len(doc.paragraphs()), "저장", out)

if __name__ == "__main__":
    main()

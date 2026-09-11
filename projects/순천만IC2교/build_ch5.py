# -*- coding: utf-8 -*-
"""
제5장 안전성평가 — STB 거더 부분을 초안 hwpx(2021 내용)에 금회 해석값으로 교체 (HWPX 편집 작업지침 v2~v3.3 준수)
  입력: report/원본_5장_초안.hwpx, runs/*.json (model_info, forces_summary, stress3_gov, stress3_all, slab_result)
  출력: report/5장_STB_v1.hwpx (+ 검증 결과)
단위: kN, kN·m, MPa (도로교설계기준 2010, 2024 IC1교 양식)
"""
import sys, os, json, copy, re
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\Midas\tools"); PJ = r"D:\Midas\projects\순천만IC2교"; sys.path.insert(0, PJ)
from hwpx_edit import Hwpx, para_text, P
import gen_model as G
from lxml import etree

RUNS = os.path.join(PJ, "runs"); REP = os.path.join(PJ, "report")
INFO = json.load(open(os.path.join(RUNS, "model_info.json"), encoding="utf-8"))
FS = json.load(open(os.path.join(RUNS, "forces_summary.json"), encoding="utf-8"))
GOV = json.load(open(os.path.join(RUNS, "stress3_gov.json"), encoding="utf-8"))
SLAB = json.load(open(os.path.join(RUNS, "slab_result.json"), encoding="utf-8"))
TONF = 9.80665
CASE_TXT = {1: "합성전 고정하중", 2: "합성전+합성후 고정하중+활하중(충격)+지점침하+원심하중", 3: "case2 + 크리프", 4: "case3 + 건조수축",
            5: "case4 + 온도(+)", 6: "case4 + 온도(−)", 7: "case4 + 풍하중(W, WL, 제동)", 8: "case5 + 풍하중", 9: "case6 + 풍하중"}
CASE_FAC = {1: "100 %", 2: "100 %", 3: "115 %", 4: "115 %", 5: "130 %", 6: "130 %", 7: "125 %", 8: "135 %", 9: "135 %"}

def cell(tbl, r, c):
    for tc in tbl.iter(P + "tc"):
        ca = tc.find(P + "cellAddr")
        if ca is not None and int(ca.get("rowAddr")) == r and int(ca.get("colAddr")) == c: return tc
    return None

def setc(doc, tbl, r, c, text):
    tc = cell(tbl, r, c)
    if tc is None: raise KeyError(f"cell ({r},{c}) 없음")
    doc.set_cell_text(tc, text)

def fmt(v, nd=1): return f"{v:,.{nd}f}" if abs(v) >= 1000 else f"{v:.{nd}f}"

def table_of(doc, idx):
    return doc.paragraphs()[idx].find(".//" + P + "tbl")

def caption_units(doc, idx):
    p = doc.paragraphs()[idx]; t = para_text(p)
    t2 = re.sub(r"tonf\s*[・･·.・･]\s*m", "kN·m", t); t2 = t2.replace("tonf", "kN").replace("kgf/㎠", "MPa").replace("kg/㎠", "MPa")
    if "전단력" in t2: t2 = t2.replace("kN·m", "kN")
    if t2 != t: doc.set_para_text(p, t2)

KGF = 0.0980665   # kgf/㎠ → MPa

def allowable_block(doc, start, t_cm, n_panel, fa, fca, sub, b_cm=200.0):
    """2021 양식의 압축플랜지 허용응력 유도 문단(*인장 ... ~ 따라서, fca = ...)을 MPa 값으로 갱신.
    sub: 'u'(상판) 또는 'l'(하판). 식 문단(㎝)은 hp:script 값만 교체."""
    ps = doc.paragraphs(); j = doc.find_para("*인장 (", start=start)[0]
    if j is None: return None
    r1, r2, r3 = b_cm / (24 * n_panel), b_cm / (48 * n_panel), b_cm / (80 * n_panel)
    f2 = (1900 - 39 * (b_cm / (t_cm * n_panel) - 24)) * KGF; f3 = 2200000 * (t_cm * n_panel / b_cm) ** 2 * KGF
    tv = f"t{sub}"; dot = "․" if sub == "u" else "ㆍ"
    scripts = [f"rm {tv}` GEQ ` {{b}} over {{24 CDOT i CDOT n}} `=` {{{b_cm:.0f}}} over {{24` TIMES `1.000` TIMES {n_panel}}} `=`{r1:.3f}`",
               f"rm ` {{b}} over {{24 CDOT i CDOT n}} ` GEQ `{tv}` GEQ  {{b}} over {{48 CDOT i CDOT n}} ``=` {{{b_cm:.0f}}} over {{48` TIMES `1.000` TIMES `{n_panel}}} `=`{r2:.3f}`",
               f"rm ` {{b}} over {{48 CDOT i CDOT n}} `>``{tv}` GEQ  {{b}} over {{80 CDOT i CDOT n}} ``=` {{{b_cm:.0f}}} over {{80` TIMES `1.000` TIMES `{n_panel}}} `=`{r3:.3f}`"]
    texts = {1: f"fta = {fa:.1f} MPa", 4: f"인 경우  : fca = {fa:.3f} MPa",
             6: f"인 경우  : fca = {{1900 – 39 ( b / ({tv} {dot} i {dot} n) – 24 )}} × 0.0980665 = {f2:.3f} MPa",
             8: f"인 경우  : fca = 2200000 × {{ ({tv} {dot} i {dot} n) / b }}² × 0.0980665 = {f3:.3f} MPa",
             9: f"사용 {tv} = {t_cm:.3f} ㎝   ( b = {b_cm:.0f} ㎝, i = 1.000, n = {n_panel} )", 10: f"따라서, fca = {fca:.1f} MPa"}
    for off, txt in texts.items(): doc.set_para_text(ps[j + off], txt)
    for off, sc in zip((3, 5, 7), scripts):
        e = ps[j + off].find(".//" + P + "script")
        if e is not None: e.text = sc
    return j

def materials_mpa(doc):
    """5.2 사용재료 문단(kgf/㎠) → MPa"""
    rep = {"- 설계기준강도 : fck = 270.0 kgf/㎠": "- 설계기준강도 : fck = 27.0 MPa", "- 탄성계수 : Ec = 252,762 kgf/㎠": "- 탄성계수 : Ec = 25,000 MPa (n = Es/Ec = 8)",
           "- 설계기준강도 : fck = 400.0 kgf/㎠": "- 설계기준강도 : fck = 40.0 MPa", "- 탄성계수 : Ec = 280,000 kgf/㎠": "- 탄성계수 : Ec = 27,459 MPa",
           "- 항복강도 : fy = 400.0 kgf/㎠": "- 항복강도 : fy = 400 MPa (SD400)", "- 항복강도 : fy = 3000.0 kgf/㎠": "- 항복강도 : fy = 300 MPa (SD300)",
           "- 탄성계수 : Es = 2,000,000 kgf/㎠": "- 탄성계수 : Es = 200,000 MPa", "∙ 탄성계수 : Es = 2,000,000 kgf/㎠": "∙ 탄성계수 : Es = 200,000 MPa", "철근(SD30)": "철근", "∙ 인장강도 : fpu = 19,000 kgf/㎠": "∙ 인장강도 : fpu = 1,900 MPa", "∙ 항복응력 : fpy = 16,000 kgf/㎠": "∙ 항복응력 : fpy = 1,600 MPa"}
    for p in doc.paragraphs()[:160]:
        t = para_text(p).strip()
        if t in rep: doc.set_para_text(p, rep[t])

def cell_paras(tc): return tc.find(P + "subList").findall(P + "p")

def deck_section(doc):
    """5.3 바닥판 구조검토(STB 구간) — 초안 표(2021 값)에 slab.py 결과 기입. 표 위치(초안 문단 인덱스)는 고정 양식 기준"""
    import slab as S
    L_, R_, IB, IT = SLAB[0], SLAB[1], SLAB[2], SLAB[3]
    dims = ["방호벽 본체 0.23×0.97 m", "경사부 0.07×0.97 m", "기부 0.30×0.35 m", "헌치 0.12×0.175 m", "연석 0.12×0.175 m", "바닥판 1.14×0.24 m", "변단면 1.03×0.107 m", "단부 0.11×0.107 m", "포장층 0.69×0.05 m", "윤하중 위치 X = 0.39 m", "(슬래브 일반도 치수)"]
    def dead_table(pidx, res):
        t = table_of(doc, pidx)
        for tc in t.findall(P + "tr")[0].findall(P + "tc"):
            tx = para_text(tc).strip()
            if "tonf" in tx: doc.set_cell_text(tc, tx.replace("(tonf․m)", "(kN·m/m)").replace("(tonf)", "(kN/m)"))
        trs = t.findall(P + "tr")
        for r, (nm, ex, w, a) in enumerate(res["items"], start=1):
            tcs = trs[r].findall(P + "tc")
            doc.set_cell_text(tcs[0], nm.split()[0] if r == 10 else para_text(tcs[0]).strip())
            doc.set_cell_text(tcs[1], ex if ex else ("0.1 tonf/m" if w > 0 else "없음")); doc.set_cell_text(tcs[3], f"{w * S.TONF:.3f}"); doc.set_cell_text(tcs[4], f"{a:.3f}"); doc.set_cell_text(tcs[5], f"{w * a * S.TONF:.3f}")
        last = [tc for tc in trs[-1].findall(P + "tc") if para_text(tc).strip() and para_text(tc).strip() != "계"]
        doc.set_cell_text(last[0], f"{res['Wd']:.3f}"); doc.set_cell_text(last[-1], f"{res['Md']:.3f}")
        doc.set_cell_lines(cell(t, 1, 7), dims)
    def live_table(pidx, r):
        t = table_of(doc, pidx)
        doc.set_cell_lines(cell(t, 1, 1), [f"·E = 0.8X+1.14 = 0.8 × {r['X']:.2f} + 1.14 = {r['E']:.3f} m", f"·i = 15 / (40+{r['X']:.2f}) = {r['i0']:.3f} > 0.3  ∴ i = 0.3",
                                            f"·Ml+i = Pr/E × X × (1+i) = ({S.PR:.0f}/{r['E']:.3f}) × {r['X']:.2f} × (1+0.3) = {r['Ml_i']:.3f} kN·m/m"])
        doc.set_cell_lines(cell(t, 2, 1), [f"·H = {{(V/60)²×750+250}} kgf/m = ({S.V_KMH:.0f}/60)²×750+250 = {r['H1'] / S.TONF * 1000:.1f} kgf/m = {r['H1']:.3f} kN/m",
                                            f"·최소 1.0 tonf/m = {r['H2']:.3f} kN/m  (R>200 m, 큰 값 적용)  ∴ H = {r['H']:.3f} kN/m",
                                            f"·Mco = H × h = {r['H']:.3f} × {S.H_BARRIER:.3f} = {r['Mco']:.3f} kN·m/m  (h = 방호벽 높이)"])
        doc.set_cell_lines(cell(t, 3, 1), [f"·Pw = {S.P_WIND:.1f} kN/㎡ × {S.H_WIND:.3f} m = {r['Pw']:.3f} kN/m", f"·Mw = {r['Pw']:.3f} kN/m × {S.H_WIND / 2:.3f} m = {r['Mw']:.3f} kN·m/m"])
        doc.set_cell_lines(cell(t, 4, 1), [f"·CF = 0.79(V²/R)(%) = 0.79({S.V_KMH:.0f}²/{S.R_M:.0f}) = {r['cf']:.3f} %", f"·Pcf = Pr/E × {r['cf']:.3f}/100 = {r['Pcf']:.3f} kN/m", f"·Mcf = {r['Pcf']:.3f} × {S.H_CF:.1f} = {r['Mcf']:.3f} kN·m/m"])
    def combo_table(pidx, r):
        t = table_of(doc, pidx)
        f = [f"Mu1 = 1.3Md + 2.15(Ml+I) + 1.3Mcf = {r['Mu1']:.3f} kN·m/m", f"Mu2 = 1.3Md + 1.3(Ml+I) + 1.3Mcf + 1.3Mco = {r['Mu2']:.3f} kN·m/m",
             f"Mu3 = 1.3Md + 1.3(Ml+I) + 1.3Mcf + 0.65Mw = {r['Mu3']:.3f} kN·m/m", f"Mu4 = 1.2Md + 1.2Mw + 1.2Mco = {r['Mu4']:.3f} kN·m/m"]
        for k in range(4):
            setc(doc, t, k + 1, 1, f[k]); setc(doc, t, k + 1, 2, "적용" if r["gov"] == k + 1 else "")
    def sect_table(pidx, r):
        t = table_of(doc, pidx)
        setc(doc, t, 1, 1, f"fck = {S.FCK:.0f} MPa"); setc(doc, t, 2, 1, f"fy = {S.FY:.0f} MPa"); setc(doc, t, 3, 1, "100.00 ㎝"); setc(doc, t, 4, 1, f"{r['h'] * 100:.2f} ㎝")
        setc(doc, t, 5, 1, f"{r['bar']} = {r['As'] * 1e4:.3f} ㎠"); setc(doc, t, 6, 1, f"{r['dc'] * 100:.2f} ㎝"); setc(doc, t, 7, 1, f"{r['h'] * 100:.2f} − {r['dc'] * 100:.2f} = {r['d'] * 100:.2f} ㎝")
        pp = cell_paras(cell(t, 8, 1))
        doc.set_para_runs(pp[0], [" ∙ ", f"= {r['As'] * 1e4:.3f}×{S.FY:.0f}/(0.85×{S.FCK:.0f}×100) = {r['a'] * 100:.3f} ㎝"])
        doc.set_para_runs(pp[1], [" ∙ ", f"= 0.85 × {r['As'] * 1e4:.3f} × {S.FY:.0f} × ({r['d'] * 100:.2f} − {r['a'] * 100:.3f}/2) × 10⁻⁴ = {r['phiMn']:.3f} kN·m/m"])
        doc.set_para_text(pp[3], f"   φMn = {r['phiMn']:.3f} kN·m/m > Mu = {r['Mu']:.3f} kN·m/m (안전율 = {r['SF']:.2f})")
    dead_table(148, L_); live_table(151, L_); combo_table(153, L_); sect_table(156, L_)
    dead_table(160, R_); live_table(163, R_); combo_table(166, R_); sect_table(169, R_)
    t = table_of(doc, 173)
    setc(doc, t, 1, 1, f"{IB['t']:.3f} × {S.G_RC:.1f}"); setc(doc, t, 1, 3, f"{IB['w_rc']:.3f} kN/m²"); setc(doc, t, 2, 0, "포장층"); setc(doc, t, 2, 1, f"0.050 × {S.G_PAVE:.1f}"); setc(doc, t, 2, 3, f"{IB['w_pv']:.3f} kN/m²")
    setc(doc, t, 3, 1, f"{IB['w']:.3f} kN/m²"); setc(doc, t, 4, 1, f"Md = (wL²) / 10 = ({IB['w']:.3f} × {IB['L']:.2f}²) / 10 = {IB['Md']:.3f} kN·m/m")
    t = table_of(doc, 176)
    doc.set_cell_lines(cell(t, 1, 1), [f"·i = 15 / (40+{IB['L']:.2f}) = {IB['i0']:.3f} > 0.3  ∴ i = 0.3", f"·Ml+i = ((L+0.6)/9.6) × Pr × (1+i) = (({IB['L']:.2f}+0.6)/9.6) × {S.PR:.0f} × (1+0.3) = {IB['Ml0']:.3f} kN·m/m",
                                        f"·연속바닥판 이므로 0.8 × {IB['Ml0']:.3f} = {IB['Ml_i']:.3f} kN·m/m"])
    doc.set_cell_lines(cell(t, 2, 1), [f"·CF = 0.79(V²/R)(%) = {IB['cf']:.3f} %", "·내측 바닥판에 대한 원심하중의 영향은 미소하므로 무시 (Mcf ≈ 0)"])
    t = table_of(doc, 178); setc(doc, t, 1, 1, f"Mu1 = 1.3Md + 2.15(Ml+i) + 1.3Mcf = 1.3×{IB['Md']:.3f} + 2.15×{IB['Ml_i']:.3f} = {IB['Mu']:.3f} kN·m/m")
    sect_table(181, IT); sect_table(184, IB)

def grade(sf): return "A" if sf > 1.0 else ("C" if sf >= 0.9 else ("D" if sf >= 0.75 else "E"))

def summary_section(doc):
    """5.6 안전성평가 결과 요약 — 바닥판 극한강도(STB), 거더 휨응력 검토 결과(case 1~9)"""
    i0 = doc.find_para("안전성평가 결과 요약")[0]
    i = doc.find_para("극한강도 검토 결과", start=i0)[0]; t = table_of(doc, i + 1)
    setc(doc, t, 0, 1, "설계강도(kN·m/m)"); setc(doc, t, 0, 2, "소요강도(kN·m/m)")
    for r, res in zip((1, 2, 3), SLAB):
        setc(doc, t, r, 1, f"{res['phiMn']:.3f}"); setc(doc, t, r, 2, f"{res['Mu']:.3f}"); setc(doc, t, r, 3, f"{res['SF']:.2f}")
    setc(doc, t, 1, 4, grade(min(r["SF"] for r in SLAB[:3])))
    i = doc.find_para("휨응력 검토 결과[(+)", start=i0)[0]; t = table_of(doc, i + 1)
    ncase = int(t.get("rowCnt")) - 5                                  # 헤더 3 + 최소안전율 + 평가결과
    if ncase < 9: doc.clone_row(t, 2 + ncase, count=9 - ncase)
    mins = [99.0] * 4
    for cid in range(1, 10):
        r = 2 + cid; setc(doc, t, r, 0, f"case {cid}")
        for k, (tag, ii) in enumerate((("pos", 0), ("pos", 1), ("neg", 0), ("neg", 1))):
            c_ = GOV[tag]["cases"][str(cid)]; v = max(c_["max"][ii], c_["min"][ii], key=abs)
            fa_ = c_["fa"] if v >= 0 else (c_["fca_top"] if ii == 0 else c_["fca_bot"]); sf = fa_ / abs(v) if abs(v) > 0.01 else 99.0
            base = 1 + 3 * k; setc(doc, t, r, base, f"{v:.2f}"); setc(doc, t, r, base + 1, f"{fa_:.1f}"); setc(doc, t, r, base + 2, f"{sf:.2f}"); mins[k] = min(mins[k], sf)
    for k in range(4):
        setc(doc, t, 12, 1 + 3 * k, f"{mins[k]:.2f}"); setc(doc, t, 13, 1 + 3 * k, grade(mins[k]))
    doc.mark_header(t, 3)

def load_fig(name):
    """PNG 읽기. 300 KB 초과면 JPEG(q92)로 변환 (§17-5). 반환 (bytes, ext, w_px, h_px)"""
    import io
    from PIL import Image
    path = os.path.join(RUNS, "fig", name); im = Image.open(path); w, h = im.size; data = open(path, "rb").read(); ext = "png"
    if len(data) > 300 * 1024:
        buf = io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=92); data = buf.getvalue(); ext = "jpg"
    return data, ext, w, h

def figures_section(doc):
    """그림 교체·추가 (§17): 검토단면(p224), 거더 일반도(p225 ×2), 모델링 평면(p261) 교체, 부재력도 신설(비틀림 표 뒤)"""
    ps = doc.paragraphs()
    def swap(para, k, name):
        pic = list(para.iter(P + "pic"))[k]; data, ext, w, h = load_fig(name); ref = doc.add_image(data, ext); return doc.swap_pic(pic, ref, w, h)
    i = doc.find_para("검 토 단 면")[0]; swap(ps[i], 0, "fig_section.png")
    i = doc.find_para("단면특성 구분")[0]; swap(ps[i], 0, "fig_girder_top.png"); swap(ps[i], 1, "fig_girder_bot.png")
    i = doc.find_para("상부구조 모델링(STB 구간)")[0]; pic_p, cap_p = ps[i - 1], ps[i]
    swap(pic_p, 0, "fig_model_plan.png")
    # 부재력도: 비틀림모멘트 표 문단 뒤에 [그림 문단, 캡션 문단] 복제 삽입
    j = doc.find_para("비틀림모멘트 산출 결과")[0]; tbl_p = ps[j + 1]; assert tbl_p.find(".//" + P + "tbl") is not None
    new_pic = copy.deepcopy(pic_p); new_cap = copy.deepcopy(cap_p)
    parent = tbl_p.getparent(); pos = parent.index(tbl_p) + 1; parent.insert(pos, new_pic); parent.insert(pos + 1, new_cap)
    swap(new_pic, 0, "fig_diagrams.png"); doc.set_para_text(new_cap, "G1 부재력도 (합성전·합성후 고정하중, 활하중 포락)")
    for p_ in (new_pic, new_cap):
        for la in p_.findall(P + "linesegarray"): p_.remove(la)

def intro_section(doc):
    """5.1 개요·5.2 구조검토 조건: 현장자료 없는 항목은 도면값(대표님 지시), 참고문헌·단위 갱신"""
    ps = doc.paragraphs()
    i = doc.find_para("구조검토 조건비교")[0]; t = table_of(doc, i + 1)
    setc(doc, t, 8, 2, "∙철콘 : γc = 25.0 kN/㎥  ∙포장 : γa = 23.5 kN/㎥  ∙강재 : γs = 78.5 kN/㎥")
    setc(doc, t, 13, 2, "∙콘크리트 : 25,000 ㎫ (n = 8)  ∙철근 : 200,000 ㎫  ∙강재 : 210,000 ㎫")
    setc(doc, t, 15, 2, "∙바닥판 H19@125 (상·하면) / 피복 상면 60 ㎜, 하면 40 ㎜ (슬래브 배근도)")
    setc(doc, t, 15, 3, "∙금회 현장 측정자료 없음 → 준공도면 값 적용")
    setc(doc, t, 16, 3, "∙금회 현장 측정자료 없음 → 준공도면 값 적용")
    setc(doc, t, 17, 2, "∙금회 안전성 검토는 준공도면(단면·배근·재료)을 기준으로 수행하였으며, 현장 측정자료(단면측정·비파괴강도·철근탐사)가 확보되면 그 값으로 갱신한다  ∙설계기준강도 적용 (바닥판 27.0 ㎫, 하부 24.0 ㎫)  ∙콘크리트 탄성계수는 n = Es/Ec = 8 (구조계산서)")
    i = doc.find_para("하중 조합(STB거더)")[0]; doc.set_para_text(ps[i], "하중 조합(STB 구간 바닥판, 강도설계법)")
    t = table_of(doc, i + 1); setc(doc, t, 2, 1, "∙Mu2 = 1.3Md + 1.3(Ml+I) + 1.3Mcf + 1.3Mco")
    for key, txt in (("1) 도로교 설계기준(2005)", "1) 도로교 설계기준(2010)"), ("2) 도로교 설계기준 해설편(2008)", "2) 도로교 설계기준 해설(2008)"),
                     ("3) 콘크리트 구조 설계기준(2004)", "3) 콘크리트구조기준(2012)"),
                     ("구조 검토 기준은 설계 당시 적용기준을 적용하였다.", "구조 검토 기준은 도로교 설계기준(2010)을 적용하였다. 도로교설계기준에 없는 내용에 대해서는 아래에 적혀있는 국토교통부 및 관련 학회 제정 각종 표준시방서, 설계기준 및 설계편람 등을 참고하여 적용하였다."),
                     ("∙ 인장강도 :fpu = 19,000 kgf/㎠", "∙ 인장강도 : fpu = 1,900 MPa"), ("∙ 항복응력 :fpy = 16,000 kgf/㎠", "∙ 항복응력 : fpy = 1,600 MPa")):
        j = doc.find_para(key)[0]
        if j is not None: doc.set_para_text(ps[j], txt)

def main():
    src = os.path.join(REP, "원본_5장_초안.hwpx"); out = os.path.join(REP, "5장_STB_v1.hwpx")
    doc = Hwpx(src).load(); ps = doc.paragraphs()
    idx = lambda text, start=0: doc.find_para(text, start)[0]

    # ── 0. 제원 문장 ──
    i = idx("교량연장 : L"); doc.set_para_text(ps[i], "교량연장 : L = 49.840 + 50.000 + 70.000 + 49.996 + 49.876 = 269.711 m (준공도면 받침 좌표 기준)")
    i = idx("탄성계수 Es = 2,100,000 kgf/㎠"); doc.set_para_text(ps[i], "탄성계수 Es = 210,000 MPa")
    i = idx("- 콘크리트 : 설계기준강도 fck= 270.0 kgf/㎠"); doc.set_para_text(ps[i], "- 콘크리트 : 설계기준강도 fck = 27.0 MPa,  탄성계수 Ec = 26,250 MPa (n = Es/Ec = 8)")

    deck_section(doc)

    # ── 1. 단면제원표 (p227): 22단면 + 가로보 ──
    t = table_of(doc, 227)
    Pl, spans, rot = G.geometry(); eff = G.eff_width_table(spans); top, bot = G.plate_segments("top"), G.plate_segments("bot")
    secs = {}
    for e, g, s1, s2, sc in INFO["elems"]:
        sm = (s1 + s2) / 2
        secs.setdefault(sc, (G.thick_at(top, sm), G.thick_at(bot, sm), G.thick_at(top, sm) >= 0.020 - 1e-9))
    nsec = len(secs); cur = int(t.get("rowCnt")) - 4          # 현재 단면 행 수 (헤더 3 + 가로보 1 제외)
    if nsec > cur: doc.clone_row(t, src_row=3 + cur - 1, count=nsec - cur)
    elif nsec < cur: doc.delete_rows(t, list(range(3 + nsec, 3 + cur)))
    for k, sc in enumerate(sorted(secs)):
        tft, tfb, neg = secs[sc]; r = 3 + k
        for c, v in enumerate([f"단면 {sc}", "2240", f"{tft*1000:.0f}", "2240", f"{tfb*1000:.0f}", "2300", "12", "2" if neg else "5", "5" if neg else "2"]): setc(doc, t, r, c, v)
    xr = 3 + nsec
    for c, v in enumerate(["가로보", "300", "12", "300", "12", "1200", "12", "-", "-"]): setc(doc, t, xr, c, v)
    doc.mark_header(t, 3)

    # ── 2. 유효폭 표 (p237 플랜지, p243 바닥판) ──
    order = ["S1mid", "P1sup", "S2mid", "P2sup", "S3mid", "P3sup", "S4mid", "P4sup", "S5mid"]
    E = {nm: (B, l) for nm, a, b, B, l in eff}
    t = table_of(doc, 237)
    for c, nm in enumerate(order, start=1):
        l = E[nm][1]; setc(doc, t, 1, c, f"{2 * G.lam(G.WEB_SP / 2, l) + 0.24:.3f}")
    t = table_of(doc, 243)
    for c, nm in enumerate(order, start=2):
        setc(doc, t, 1, c, f"{E[nm][0]:.3f}"); setc(doc, t, 2, c, f"{E[nm][0]:.3f}")

    # ── 3. 하중 산정 표 ──
    t = table_of(doc, 248)
    setc(doc, t, 0, 1, "총강재중량(kN)"); setc(doc, t, 0, 2, "모델링 강재중량(kN)"); setc(doc, t, 0, 3, "할증율")
    setc(doc, t, 1, 1, fmt(G.STEEL_TOTAL_KN)); setc(doc, t, 1, 2, fmt(INFO["model_steel_kN"])); setc(doc, t, 1, 3, f"{INFO['f_steel']:.3f}"); setc(doc, t, 1, 4, "강재재료표(22) 총계 902,129 kgf")
    t = table_of(doc, 249)
    setc(doc, t, 0, 0, "- 바닥판 RC 두께: 캔틸레버 단부 0.30 m → 주형 위 0.24 m, 내측 0.24 m, 헌치 0.06 m × 2.24 m (슬래브 일반도·계산서 Tc)   - 단위중량 25.0 kN/m³")
    rows_lab = {"P1": None, "P2": None, "Pt": None, "Mt": None}
    for r in range(1, int(t.get("rowCnt"))):
        tc1 = cell(t, r, 1); txt = para_text(tc1).strip() if tc1 is not None else ""
        for k in rows_lab:
            if txt.startswith(k): rows_lab[k] = r
    w1, w2 = INFO["w_slab"]["G1"], INFO["w_slab"]["G2"]; m1, m2 = INFO["mx_slab"]["G1"], INFO["mx_slab"]["G2"]
    vals = {"P1": ("캔틸레버측 (kN/m)", None), "P2": ("내측 (kN/m)", None), "Pt": ("Pt (kN/m)", (w1, w2)), "Mt": ("Mt (kN·m/m)", (m1, m2))}
    for k, r in rows_lab.items():
        if r is None: continue
        lab, vv = vals[k]; setc(doc, t, r, 1, lab)
        if vv: setc(doc, t, r, 2, f"{vv[0]:.3f}"); setc(doc, t, r, 3, f"{vv[1]:.3f}")
        else: setc(doc, t, r, 2, "-"); setc(doc, t, r, 3, "-")
    t = table_of(doc, 253)
    setc(doc, t, 0, 0, f"- 좌측방호벽 : {G.BARRIER['G1']:.2f} kN/m,  - 우측방호벽(난간 포함) : {G.BARRIER['G2']:.2f} kN/m,  - 포장층 : 0.05 m × 23.5 = 1.175 kN/m²,  - 부속설비 : 0.49 kN/m²")
    rows_lab = {"P1": None, "P2": None, "Pt": None, "Mt": None}
    for r in range(1, int(t.get("rowCnt"))):
        tc1 = cell(t, r, 1); txt = para_text(tc1).strip() if tc1 is not None else ""
        for k in rows_lab:
            if txt.startswith(k): rows_lab[k] = r
    s1, s2 = INFO["sdl"]["G1"], INFO["sdl"]["G2"]; n1, n2 = INFO["mx_sdl"]["G1"], INFO["mx_sdl"]["G2"]
    vals = {"P1": ("방호벽 (kN/m)", (G.BARRIER["G1"], G.BARRIER["G2"])), "P2": ("포장층+부속설비 (kN/m)", (s1 - G.BARRIER["G1"], s2 - G.BARRIER["G2"])), "Pt": ("Pt (kN/m)", (s1, s2)), "Mt": ("Mt (kN·m/m)", (n1, n2))}
    for k, r in rows_lab.items():
        if r is None: continue
        lab, vv = vals[k]; setc(doc, t, r, 1, lab); setc(doc, t, r, 2, f"{vv[0]:.3f}"); setc(doc, t, r, 3, f"{vv[1]:.3f}")
    t = table_of(doc, 254); setc(doc, t, 1, 1, "거더당 작용 = 0.49 kN/m² × 8.670 m / 2 = 2.13 kN/m"); setc(doc, t, 1, 2, "2021년 진단 적용값(0.05 tonf/m²) 준용")
    # 활하중 모델 표: tonf → kN 환산 (표 258 전체 셀)
    def tonf_to_kn(txt):
        def rep(m):
            v = float(m.group(1)); unit = m.group(2)
            return f"{v * 9.80665:.1f} {unit.replace('tonf', 'kN')}"
        return re.sub(r"(\d+\.?\d*)\s*(tonf(?:/m²|/m)?)", rep, txt)
    t = table_of(doc, 258)
    for tc in list(t.iter(P + "tc")):
        txt = para_text(tc)
        if "tonf" in txt: doc.set_cell_text(tc, tonf_to_kn(txt.strip()))
    # 활하중 검토 표: 해석지간·충격계수
    t = table_of(doc, 258); setc(doc, t, 1, 1, "49.840 + 50.000 + 70.000 + 49.996 + 49.876 = 269.711 m")
    for r in range(int(t.get("rowCnt"))):
        for c in range(int(t.get("colCnt"))):
            tc = cell(t, r, c)
            if tc is None: continue
            txt = para_text(tc)
            if "15 / (40+" in txt:
                L = spans; lines = ["·1지간 : 15 / (40+%.2f) = %.3f" % (L[0], 15 / (40 + L[0])), "·2지간 : 15 / (40+%.2f) = %.3f" % (L[1], 15 / (40 + L[1])),
                                    "·3지간 : 15 / (40+%.2f) = %.3f" % (L[2], 15 / (40 + L[2])), "·4지간 : 15 / (40+%.2f) = %.3f" % (L[3], 15 / (40 + L[3])),
                                    "·5지간 : 15 / (40+%.2f) = %.3f" % (L[4], 15 / (40 + L[4]))] if "지간" in txt else \
                        ["·%d지점 : 15 / (40+(%.2f+%.2f)/2) = %.3f" % (i, L[i-1], L[i], min(0.3, 15 / (40 + (L[i-1] + L[i]) / 2))) for i in range(1, 5)]
                doc.set_cell_text(tc, "  ".join(lines))

    # ── 4. 부재력 집계표 ×3 (p267 휨, p270 전단, p273 비틀림) ──
    labels = ["S1", "P1", "S2", "P2", "S3", "P3", "S4", "P4", "S5"]
    for pidx, comp in ((267, "My"), (270, "Fz"), (273, "Mx")):
        t = table_of(doc, pidx); caption_units(doc, pidx - 1)
        for k, lb in enumerate(labels):
            for j, g in enumerate(("G1", "G2")):
                r = 3 + 2 * k + j; v = FS[f"{comp}|{lb}|{g}"]
                cols = [v["d1"], v["sl"], v["d2"], v["lmax"], v["lmin"], v["smax"], v["smin"], v["tmax"], v["tmin"]]
                for c, x in enumerate(cols, start=2): setc(doc, t, r, c, f"{x:.1f}")
                setc(doc, t, r, 11, v["e"])
        setc(doc, t, 0, 11, "위치(요소)"); doc.mark_header(t, 3)

    # ── 5. 정모멘트부 / 부모멘트부 ──
    delta = 0      # 앞 단계에서 문단을 지우고 넣은 만큼 뒤 인덱스 보정
    for tag, p_sec, p_in, p_comb, p_res, p_fstart, p_fend in (("pos", 276, 279, 367, 395, 280, 366), ("neg", 434, 436, 519, 546, 437, 518)):
        p_sec, p_in, p_comb, p_res, p_fstart, p_fend = (x + delta for x in (p_sec, p_in, p_comb, p_res, p_fstart, p_fend))
        delta += 2 - (p_fend - p_fstart)
        r_ = GOV[tag]; f = r_["forces"]; sec_idx = r_["sc"]
        tft, tfb, neg = secs[sec_idx]; be = None
        for nm, a, b, B, l in eff:
            pass
        ps = doc.paragraphs()
        # 5-1 단면 제원 문장
        t = table_of(doc, p_sec)
        setc(doc, t, 0, 0, f"- 검토 위치 : {r_['g']} s = {r_['s']:.2f} m (요소 {r_['elem']}{r_['part']})  - H = 2.300 m  - 상판 2240×{tft*1000:.0f}  - 하판 2240×{tfb*1000:.0f}  - 복부 2300×12 (2)  - 종리브 150×14 상 {'2' if neg else '5'} / 하 {'5' if neg else '2'}")
        setc(doc, t, 0, 1, f"- Tc = 0.240 m  - Th = 0.060 m  - n = 8  - 2차 부정정력 계수 k = {r_['k']:.3f}"); setc(doc, t, 0, 2, "- 크리프 Φ1 = 2 (n1 = 16)  - 건조수축 εs = 200×10⁻⁶, Φ2 = 4 (n2 = 24)  - 온도차 10 ℃")
        # 5-2 입력자료 표: 라벨로 값 채우기, 단위 MPa/kN
        t = table_of(doc, p_in)
        LM = f["LLmax"]["My"] + f["SDmax"]; Lm = f["LLmin"]["My"] + f["SDmin"]
        vals = {"Es": ("MPa", "210,000"), "Ec": ("MPa", "26,250"), "εs": ("", "0.00020"), "α": ("", "0.000012"), "Φ1": ("", "2"), "Φ2": ("", "4"), "n": ("", "8"), "t": ("℃", "10"),
                "Ms": ("kN·m", fmt(f["D1"]["My"])), "Msc": ("kN·m", fmt(f["D2"]["My"])), "Mv": ("kN·m", f"{fmt(LM)} / {fmt(Lm)}"),
                "Ss": ("kN", fmt(f["D1"]["Fz"])), "Ssc": ("kN", fmt(f["D2"]["Fz"])), "Sv": ("kN", f"{fmt(f['LLmax']['Fz'])} / {fmt(f['LLmin']['Fz'])}"),
                "Mst": ("kN·m", fmt(f["D1"]["Mx"])), "Msct": ("kN·m", fmt(f["D2"]["Mx"])), "Mvt": ("kN·m", f"{fmt(f['LLmax']['Mx'])} / {fmt(f['LLmin']['Mx'])}")}
        nrow = int(t.get("rowCnt"))
        for r in range(1, nrow):
            c0 = cell(t, r, 0); key = para_text(c0).strip() if c0 is not None else ""
            key = key.replace(" ", "")
            if key in vals:
                u, v = vals[key]
                if cell(t, r, 8) is not None: setc(doc, t, r, 8, u)
                setc(doc, t, r, 9, v)
        # 단면 부재 표(같은 표 하단): 1-U.F 등 행 → 치수 갱신 (cm)
        st = G.steel_section(tft, tfb, G.RIB_NEG if neg else G.RIB_POS)
        rib_t, rib_b = (2, 5) if neg else (5, 2)
        parts = {"U.F": (224.0, tft * 100, 224.0 * tft * 100), "U.Rib": (1.4, 15.0, rib_t * 1.4 * 15.0), "Web": (1.2, 230.0, 2 * 1.2 * 230.0), "L.Rib": (1.4, 15.0, rib_b * 1.4 * 15.0), "L.F": (224.0, tfb * 100, 224.0 * tfb * 100)}
        for r in range(1, nrow):
            c0 = cell(t, r, 0); key = para_text(c0).strip() if c0 is not None else ""
            for pk, (b_, h_, a_) in parts.items():
                if pk.replace(".", "") in key.replace(".", "").replace(" ", "").replace("–", "-").replace("-", ""):
                    for c, v in ((1, f"{b_:.1f}"), (2, f"{h_:.1f}"), (3, f"{a_:.2f}")):
                        if cell(t, r, c) is not None: setc(doc, t, r, c, v)
            if key.startswith("강단면 합계") and cell(t, r, 3) is not None: setc(doc, t, r, 3, f"{st['A']*1e4:.2f}")
        # 5-3 계산 과정(공식 문단) 삭제 → 하중별 응력표(5열)로 대체
        ps = doc.paragraphs()
        block = ps[p_fstart:p_fend]
        donor = copy.deepcopy(ps[248])          # 5열 표 문단
        parent = ps[p_fstart].getparent(); pos_i = list(parent).index(ps[p_fstart])
        for p in block: parent.remove(p)
        parent.insert(pos_i, donor); dt = donor.find(".//" + P + "tbl")
        pt = r_["parts"]; rowsS = [("합성전 고정하중 (강재단면)", pt["D1"]), ("합성후 고정하중", pt["D2"]), ("활하중+충격+지점침하 (max)", pt["LLmax"]), ("활하중+충격+지점침하 (min)", pt["LLmin"]),
                                   ("원심하중", pt["CF"]), ("크리프 (k 포함)", pt["CR"] + [0]), ("건조수축 (k 포함)", pt["SH"] + [0]), ("온도차 +10℃ (k 포함)", pt["TD"] + [0]), ("풍하중 W", pt["W"]), ("활하중 풍하중 WL", pt["WL"]), ("제동하중 LF", pt["LF"]), ("온도변화 +15℃", pt["TP"])]
        doc.clone_row(dt, 1, count=len(rowsS) - 1)
        for c, h in enumerate(["하중 (MPa, 인장 +)", "강재 상연", "강재 하연", "바닥판 상연" if tag == "pos" else "철근", "비고"]): setc(doc, dt, 0, c, h)
        for r, (nm, v) in enumerate(rowsS, start=1):
            setc(doc, dt, r, 0, nm); setc(doc, dt, r, 1, f"{v[0]:.2f}"); setc(doc, dt, r, 2, f"{v[1]:.2f}")
            setc(doc, dt, r, 3, f"{v[2]:.2f}" if tag == "pos" else (f"{v[3]:.2f}" if len(v) > 3 else "-")); setc(doc, dt, r, 4, "")
        doc.mark_header(dt, 1)
        cap = copy.deepcopy(ps[p_in - 1]); doc.set_para_text(cap, f"{'정' if tag == 'pos' else '부'}모멘트부 하중별 응력 산정 결과 (단위 : MPa, 인장(+), 압축(−))"); parent.insert(pos_i, cap)
        # 5-4 하중조합 표 → case 1~9
        ps = doc.paragraphs(); shift = 2 - (p_fend - p_fstart)     # 문단 수 변화
        t = table_of(doc, p_comb + shift)
        cur = int(t.get("rowCnt")) - 1
        if cur < 9: doc.clone_row(t, cur, count=9 - cur)
        for cid in range(1, 10):
            setc(doc, t, cid, 0, f"case {cid}"); setc(doc, t, cid, 1, CASE_TXT[cid]); setc(doc, t, cid, 2, f"허용응력 {CASE_FAC[cid]}")
        # 5-5 응력 검토 결과 표 → case 1~9
        caption_units(doc, p_res - 1 + shift); t = table_of(doc, p_res + shift)
        cur = int(t.get("rowCnt")) - 3
        if cur < 9: doc.clone_row(t, 2 + cur, count=9 - cur)
        if tag == "neg": setc(doc, t, 0, 1, "바닥판 철근 (허용 160 MPa)")
        for cid in range(1, 10):
            c_ = r_["cases"][str(cid)]; r = 2 + cid; mx, mn = c_["max"], c_["min"]
            def pick(i): return max(mx[i], mn[i], key=abs)
            setc(doc, t, r, 0, f"case {cid}")
            if tag == "pos":
                ct, cb = min(mx[2], mn[2]), min(mx[4], mn[4])
                for c, v in ((1, ct), (4, cb)):
                    setc(doc, t, r, c, f"{v:.2f}" if cid > 1 else "-"); setc(doc, t, r, c + 1, f"{c_['fc']:.1f}" if cid > 1 else "-")
                    setc(doc, t, r, c + 2, f"{c_['fc']/abs(v):.2f}" if (cid > 1 and v < -0.01) else "-")
            else:
                rb = pick(3); fa_r = 160 * float(GOV["fac"][str(cid)])
                setc(doc, t, r, 1, f"{rb:.2f}" if cid > 1 else "-"); setc(doc, t, r, 2, f"{fa_r:.1f}" if cid > 1 else "-"); setc(doc, t, r, 3, f"{fa_r/abs(rb):.2f}" if (cid > 1 and abs(rb) > 0.01) else "-")
                for c in (4, 5, 6): setc(doc, t, r, c, "-")
            for c, i in ((7, 0), (10, 1)):
                v = pick(i); fa_ = c_["fa"] if v >= 0 else (c_["fca_top"] if i == 0 else c_["fca_bot"])
                setc(doc, t, r, c, f"{v:.2f}"); setc(doc, t, r, c + 1, f"{fa_:.1f}"); setc(doc, t, r, c + 2, f"{fa_/abs(v):.2f}" if abs(v) > 0.01 else "-")
        doc.mark_header(t, 3)
        # 5-6 항복에 대한 안전도 검사 문단 갱신 (∑f = 1.3(D1+D2) + 2.15·LL + 크리프 + 건조수축 + 온도차)
        ps = doc.paragraphs(); pr = p_res + shift; pt = r_["parts"]
        fy = 315.0 if max(tft, tfb) <= 0.016 else 295.0
        def yield_block(label, iD1, iD2, iLL, iCR, iSH, iTD, limit, lim_txt, use_d1=True):
            j = doc.find_para(label, start=pr)[0]
            if j is None: return
            d1v = pt["D1"][iD1] if use_d1 else 0.0; d2v = pt["D2"][iD2]
            llc = [pt["LLmax"][iLL], pt["LLmin"][iLL]]; ll = max(llc, key=abs)
            cr, sh, td = pt["CR"][iCR], pt["SH"][iSH], pt["TD"][iTD]
            s_all = 1.3 * (d1v + d2v) + 2.15 * ll + cr + sh + td; s_t = 1.3 * (d1v + d2v) + 2.15 * ll + td
            lines = [f"합성전 사하중 응력 = {d1v:.2f} MPa" if use_d1 else f"합성후 사하중 응력 = {d2v:.2f} MPa",
                     f"합성후 사하중 응력 = {d2v:.2f} MPa" if use_d1 else f"활하중(충격) 응력 = {ll:.2f} MPa",
                     f"활하중(충격) 응력 = {ll:.2f} MPa" if use_d1 else f"∑f = 1.3 × {d2v:.2f} + 2.15 × {ll:.2f} + ({cr:.2f}) + ({sh:.2f}) + ({td:.2f})",
                     f"∑f = 1.3 × ({d1v:.2f} + {d2v:.2f}) + 2.15 × {ll:.2f} + ({cr:.2f}) + ({sh:.2f}) + ({td:.2f})" if use_d1 else f"= {s_all:.2f} MPa < {lim_txt} = {limit:.1f} MPa  ⇒  {'O.K.' if abs(s_all) < limit else 'N.G.'}  (크리프, 건조수축 포함)",
                     f"= {s_all:.2f} MPa < {lim_txt} = {limit:.1f} MPa  ⇒  {'O.K.' if abs(s_all) < limit else 'N.G.'}  (크리프, 건조수축 포함)" if use_d1 else f"∑f = 1.3 × {d2v:.2f} + 2.15 × {ll:.2f} + ({td:.2f})",
                     f"∑f = 1.3 × ({d1v:.2f} + {d2v:.2f}) + 2.15 × {ll:.2f} + ({td:.2f})" if use_d1 else f"= {s_t:.2f} MPa < {lim_txt} = {limit:.1f} MPa  ⇒  {'O.K.' if abs(s_t) < limit else 'N.G.'}  (온도차만 포함)",
                     f"= {s_t:.2f} MPa < {lim_txt} = {limit:.1f} MPa  ⇒  {'O.K.' if abs(s_t) < limit else 'N.G.'}  (온도차만 포함)" if use_d1 else ""]
            k = j + 1
            for ln in lines:
                if ln == "": break
                doc.set_para_text(ps[k], ln); k += 1
            for m in range(k, j + 8):        # 남은 옛 줄 비우기 (다음 소제목 전까지)
                if m < len(ps) and ps[m].get("styleIDRef") == "13" and para_text(ps[m]).strip(): doc.set_para_text(ps[m], "")
        if tag == "pos":
            yield_block("∙ 바닥판 콘크리트", 2, 2, 2, 2, 2, 2, 0.6 * 27, "(3/5)fck", use_d1=False)
            yield_block("∙ 강재주형 상판", 0, 0, 0, 0, 0, 0, fy, "fy"); yield_block("∙ 강재주형 하판", 1, 1, 1, 1, 1, 1, fy, "fy")
        else:
            yield_block("∙ 상부바닥판 REBAR", 3, 3, 3, 3, 3, 3, 400.0, "fy", use_d1=False)
            yield_block("∙ 강재주형 상판", 0, 0, 0, 0, 0, 0, fy, "fy"); yield_block("∙ 강재주형 하판", 1, 1, 1, 1, 1, 1, fy, "fy")
        for j in range(pr + 1, pr + 40):
            if j < len(ps) and "도로교 설계기준 해설(2003)" in para_text(ps[j]): doc.set_para_text(ps[j], "항복에 대한 안전도 검사 (도로교설계기준 2010, 강교편 합성응력)")
        # 5-3 허용응력 유도 문단 (압축플랜지 국부좌굴) → MPa
        fa0 = r_["cases"]["1"]["fa"] if "1" in r_["cases"] else r_["cases"][1]["fa"]
        if tag == "pos":
            j = allowable_block(doc, p_comb + shift, tft * 100, G.RIB_POS[0] + 1, fa0, r_["fca"][0], "u")
            if j is not None:
                ps = doc.paragraphs(); doc.set_para_text(ps[j + 12], "fca = 0.4 fck = 10.8 MPa       ( fck = 27 MPa 사용 )"); doc.set_para_text(ps[j + 13], "fta = 0.07 fck = 1.89 MPa")
        else:
            j = allowable_block(doc, p_comb + shift, tfb * 100, G.RIB_NEG[1] + 1, fa0, r_["fca"][1], "l")
            if j is not None:
                ps = doc.paragraphs(); doc.set_para_text(ps[j + 13], "fta = 160.0 MPa          fca = 180.0 MPa   ( SD 40 사용 )")

    # ── 6. 5.5 결과 요약 ──
    ps = doc.paragraphs()
    i = idx("바닥판 안전성 평가결과"); t = table_of(doc, i + 1)
    for r, res in zip((1, 2, 3), SLAB):
        Mu, Mn, d = res["Mu"], res["phiMn"], res["d"] * 100
        As_req = Mu * 1e6 / (0.85 * 400 * 0.9 * res["d"] * 1000) / 100        # Mu(N·mm)/(φ·fy·0.9d) → mm² → cm²/m
        setc(doc, t, r, 2, f"{As_req:.3f}"); setc(doc, t, r, 3, "100"); setc(doc, t, r, 4, f"{d:.2f}"); setc(doc, t, r, 5, f"{res['dc'] * 100:.2f}")
        setc(doc, t, r, 6, f"H19@125={res['As']*1e4:.3f}"); setc(doc, t, r, 7, f"{Mu:.2f}"); setc(doc, t, r, 8, f"{Mn:.2f}"); setc(doc, t, r, 9, "O.K" if Mn >= Mu else "N.G")
    setc(doc, t, 0, 7, "Mu (kN·m/m)"); setc(doc, t, 0, 8, "ΦMn (kN·m/m)")
    i = idx("STB거더 안전성 평가결과"); t = table_of(doc, i + 1); cur = int(t.get("rowCnt")) - 3
    if cur < 9: doc.clone_row(t, 2 + cur, count=9 - cur)
    for cid in range(1, 10):
        r = 2 + cid; setc(doc, t, r, 0, f"case {cid}"); ok = True
        for tag, base in (("pos", 1), ("neg", 7)):
            c_ = GOV[tag]["cases"][str(cid)]; mx, mn = c_["max"], c_["min"]
            for k, ii in ((0, 0), (3, 1)):
                v = max(mx[ii], mn[ii], key=abs); sf = c_["fa"] / abs(v) if abs(v) > 0.01 else 99
                setc(doc, t, r, base + k, f"{v:.2f}"); setc(doc, t, r, base + k + 1, f"{c_['fa']:.1f}"); setc(doc, t, r, base + k + 2, f"{sf:.2f}"); ok &= sf >= 1
        setc(doc, t, r, 13, "O.K" if ok else "N.G")
    doc.mark_header(t, 3)
    i = idx("허용응력법에 의한 강박스거더의 내하력 평가 결과"); caption_units(doc, i); t = table_of(doc, i + 1)
    rf = GOV["rfs"]; pp, nn = GOV["pos"]["parts"], GOV["neg"]["parts"]
    fd_p = pp["D1"][1] + pp["D2"][1]; fl_p = max(pp["LLmax"][1], pp["LLmin"][1]); fd_n = nn["D1"][1] + nn["D2"][1]; fl_n = min(nn["LLmax"][1], nn["LLmin"][1])
    setc(doc, t, 1, 1, f"∙fa = 190.0 MPa (하부플랜지, 인장) ∙fd = {fd_p:.1f} MPa ∙fl(1+i) = {fl_p:.1f} MPa ∙내하율(RF) = (190.0 − {fd_p:.1f}) / {fl_p:.1f} = {(190 - fd_p) / fl_p:.3f}")
    setc(doc, t, 2, 1, f"∙fa = 190.0 MPa (하부플랜지, 압축) ∙fd = {fd_n:.1f} MPa ∙fl(1+i) = {fl_n:.1f} MPa ∙내하율(RF) = (190.0 − {abs(fd_n):.1f}) / {abs(fl_n):.1f} = {(190 - abs(fd_n)) / abs(fl_n):.3f}")
    i = idx("강도설계법에 의한 기본내하력 평가 결과"); t = table_of(doc, i + 1)
    for r, res in zip((1, 2, 3), SLAB):
        mcf = res.get("Mcf", 0.0)
        setc(doc, t, r, 1, f"∙φMn = {res['phiMn']:.2f} kN·m/m ∙Md = {res['Md']:.2f} ∙Ml(1+i) = {res['Ml_i']:.2f} ∙Mcf = {mcf:.2f} ∙내하율(RF) = ({res['phiMn']:.2f} − 1.3×{res['Md']:.2f} − 1.3×{mcf:.2f}) / (2.15×{res['Ml_i']:.2f}) = {res['RF']:.3f}")
        setc(doc, t, r, 2, "DB-24 이상" if res["RF"] >= 1 else "DB-24 미만")
    # 결론 문장
    ps = doc.paragraphs()
    i = idx("강도설계법에 의한 상부 바닥판슬래브의 안전성 검토 결과")
    doc.set_para_text(ps[i], f"강도설계법에 의한 상부 바닥판슬래브의 안전성 검토 결과, 최소 안전율 {min(r['SF'] for r in SLAB):.2f}(STB 구간 캔틸레버부)로서 안전성을 확보하고 있는 것으로 검토되었다.")
    i = idx("허용응력설계법에 의한 상부 STB 거더의 안전성 검토 결과")
    doc.set_para_text(ps[i], f"허용응력설계법에 의한 상부 STB 거더의 안전성 검토 결과, 거더 상·하연에 발생되는 최대응력은 허용응력 범위 이내로 검토되었으며, 최소 안전율은 {min(GOV['sf_pos'], GOV['sf_neg']):.2f}(정모멘트부 하연, case 2)로 검토되어 구조적인 안전성을 확보하고 있는 것으로 평가되었다.")
    i = idx("충격을 고려한 활하중에 대한 기본내하율 검토결과")
    rmin = min(SLAB, key=lambda r: r["RF"])
    doc.set_para_text(ps[i], f"충격을 고려한 활하중에 대한 기본내하율 검토결과, 바닥판은 {rmin['RF']:.3f}(최소, {rmin['name']}), 강박스 거더는 {min(rf):.3f}(최소, 정모멘트부)로 검토되어 1등급 설계활하중(DB/DL-24) 이상의 기본내하력을 확보하고 있는 것으로 평가되었다.")
    summary_section(doc)

    # ── 저장·검증 ──
    materials_mpa(doc); intro_section(doc); figures_section(doc)
    print("미참조 이미지 제거:", doc.prune_images()); doc.renumber_objects(); doc.save(out)
    rep = doc.verify(out); print(json.dumps(rep, ensure_ascii=False)[:800]); print("저장:", out)

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
단면응력·안전성 계산기 v3 (허용응력설계법, 도로교설계기준 2010 · 정밀안전진단 보고서 양식)
입력 : runs/model_info.json, A_steel_*.json, C_comp_*.json (run3.py 산출)
방법 : 합성전 D1 → 강재단면 / 합성후(D2, L+I, SD, W, WL, CF, LF, T) → 합성단면 n=8
       크리프(Φ1=2, n1=2n) · 건조수축(εs=200×10⁻⁶, Φ2=4, n2=3n) · 강-바닥판 온도차(10℃, n) → 계산서 방식 + 2차 부정정력 계수 k(UNITM 해석)
       부모멘트부(합성후 사하중+활하중 최소모멘트 < 0)는 콘크리트 무시, 강재+철근 단면 (상면 H16@100, 하면 H22@100 — 슬래브 배근도 S2/B12)
하중 case(2024 순천만IC1교 보고서 양식) :
  1 합성전 | 2 +합성후+활하중(+충격)+지점침하+원심 | 3 +크리프 | 4 +건조수축 | 5 +온도(+) | 6 +온도(−) | 7 case4+풍(W, WL, LF) | 8 case5+풍 | 9 case6+풍
허용응력(SM490 t≤40 → 190 MPa, 40<t≤75 → 175) 증가율 (도로교설계기준 강교편 표 3.9.4 강재 주거더의 허용응력 증가율 · 표 2.2.1 부하중 조합) — 연(압축/인장)·모멘트부별 :
  case1·2 1.00 | case3·4(크리프·건조수축, 주하중) 정모멘트부 압축연 1.15 / 인장연 1.00, 부모멘트부 1.00 / 1.00
  case5·6(+온도차) 정모멘트부 압축연 1.30 / 인장연 1.15, 부모멘트부 1.15 / 1.15 | case7(+풍) 전 연 1.25 | case8·9(온도+풍) 전 연 1.35 (표 2.2.1, 표 3.9.4와 중복 적용 않음)
  압축연/인장연은 해당 case·연의 응력 부호로 판정. 바닥판 허용압축 0.4fck = 10.8 MPa(압축연 증가율), 국부좌굴 fca(표 3.4.3)도 압축연 증가율. 허용전단 SM490 110 MPa.
항복 안전도(3.9.3.2) : f = 1.3(D1+D2) + 2.15(L+I) + 크리프 + 건조수축 + 온도차(각각 불리한 방향만) ≤ fy(SM490 320 / t>40 300, 바닥판 3/5·fck) → "yield_check"
안전율 SF = 허용/작용, 등급(세부지침 표 1.34): A SF>1.0, C 0.9≤SF<1.0, D 0.75≤SF<0.9, E SF<0.75 (B는 공용내하력 조건)
내하율 RF = (fa − fd)/fl(1+i)  [세부지침 허용응력법]
"""
import sys, os, json, math
sys.stdout.reconfigure(encoding="utf-8")
PJ = r"D:\Midas\projects\순천만IC2교"; RUNS = os.path.join(PJ, "runs"); sys.path.insert(0, PJ)
import gen_model as G

INFO = json.load(open(os.path.join(RUNS, "model_info.json"), encoding="utf-8"))
TONF = 9.80665; MPA = 1e-3
N = G.N_SHORT; PHI1, PHI2 = 2.0, 4.0; N1, N2 = N * (1 + PHI1 / 2), N * (1 + PHI2 / 2)
EPS_S, ALPHA, DT = 200e-6, 1.2e-5, 10.0
EC = G.ES / N
REBAR_TOP, REBAR_BOT, COV_TOP, COV_BOT = 19.87e-4, 38.71e-4, 0.060, 0.040     # m²/m, m  (H16@100 / H22@100)
FA_STEEL = lambda t: 190.0 if t <= 0.040 else 175.0
FY_STEEL = lambda t: 320.0 if t <= 0.040 else 300.0          # SM490 항복점 (t≤40 → 320, 40<t≤100 → 300 MPa)
FY_REBAR, FCK = 400.0, 27.0                                    # SD40 철근, 바닥판 fck
def fca_local(t, n_rib, b=2.0, i=1.0):
    """종리브로 보강된 압축플랜지(양연지지판)의 국부좌굴 허용압축응력 — 도로교설계기준(2005/2010) 강교편 표 3.4.3 (SM490, MPa)
    b: 복부 사이 플랜지 폭(B = 2.0 m), 종리브 n_rib개 → 리브 사이 판 폭 b₁ = B/(n_rib+1), r = b₁/(t·i)
      t ≤ 40 mm  : r ≤ 34.0 → 190 ; 34.0 < r ≤ 80 → 220,000·(t·i/b₁)² = 220,000/r²
      40 < t ≤ 100: r ≤ 35.5 → 175 ; 35.5 < r ≤ 80 → 220,000/r²
    (r > 80은 표 적용범위 밖 — 220,000/r²을 그대로 연장 적용)"""
    b1 = b / (n_rib + 1); r = b1 / (t * i)
    r0 = 34.0 if t <= 0.040 else 35.5
    if r <= r0: return FA_STEEL(t)
    return 220000.0 / r ** 2
FA_CONC, FA_SHEAR = 0.4 * FCK, 110.0
# 허용응력 증가율 (표 3.9.4 + 표 2.2.1): {case: {"pos": (압축연, 인장연), "neg": (압축연, 인장연)}}
FAC = {1: dict(pos=(1.00, 1.00), neg=(1.00, 1.00)), 2: dict(pos=(1.00, 1.00), neg=(1.00, 1.00)),
       3: dict(pos=(1.15, 1.00), neg=(1.00, 1.00)), 4: dict(pos=(1.15, 1.00), neg=(1.00, 1.00)),
       5: dict(pos=(1.30, 1.15), neg=(1.15, 1.15)), 6: dict(pos=(1.30, 1.15), neg=(1.15, 1.15)),
       7: dict(pos=(1.25, 1.25), neg=(1.25, 1.25)), 8: dict(pos=(1.35, 1.35), neg=(1.35, 1.35)), 9: dict(pos=(1.35, 1.35), neg=(1.35, 1.35))}
def fac_of(cid, hog): return FAC[cid]["neg" if hog else "pos"]          # → (압축연, 인장연)
CASE_NAMES = {1: "합성전", 2: "합성전+합성후+활하중+지점침하", 3: "+크리프", 4: "+건조수축", 5: "+온도(+)", 6: "+온도(−)", 7: "case4+풍하중", 8: "case5+풍하중", 9: "case6+풍하중"}
# 하위호환(build_ch5*: GOV["fac"] → 철근 허용 160×fac): 둘째 원소 = 부모멘트부 인장연 증가율
CASES = {cid: (nm, FAC[cid]["neg"][1]) for cid, nm in CASE_NAMES.items()}
CAP_KN = {"A1": 250 * TONF, "P1": 600 * TONF, "P2": 700 * TONF, "P3": 700 * TONF, "P4": 600 * TONF, "P5": 250 * TONF}
COMPS = {"My": "Moment-y", "Mz": "Moment-z", "Fx": "Axial", "Fz": "Shear-z", "Mx": "Torsion"}

# ───────── 표 읽기 ─────────
def load_table(tag):
    tb = json.load(open(os.path.join(RUNS, f"{tag}_beamforce.json"), encoding="utf-8"))["SS_Table"]
    h = tb["HEAD"]; ie, il, ip = h.index("Elem"), h.index("Load"), h.index("Part"); idx = {k: h.index(v) for k, v in COMPS.items()}
    out = {}
    for r in tb["DATA"]:
        out[(r[il], int(r[ie]), r[ip][0])] = {k: float(r[i]) for k, i in idx.items()}
    return out

ZERO = {k: 0.0 for k in COMPS}
def F(tbl, ld, e, part): return tbl.get((ld, e, part), ZERO)

# ───────── 단면 ─────────
def sections():
    Pl, spans, rot = G.geometry(); eff = G.eff_width_table(spans); top, bot = G.plate_segments("top"), G.plate_segments("bot")
    keys = {}
    for e, g, s1, s2, sc in INFO["elems"]:
        sm = (s1 + s2) / 2
        keys.setdefault(sc, (round(G.thick_at(top, sm), 4), round(G.thick_at(bot, sm), 4), G.thick_at(top, sm) >= 0.020 - 1e-9, round(G.beff_at(eff, sm), 3)))
    secs = {}
    for sc, (tft, tfb, neg, be) in keys.items():
        st = G.steel_section(tft, tfb, G.RIB_NEG if neg else G.RIB_POS)
        cp = {n: G.composite_section(st, be, n) for n in (N, N1, N2)}
        y_top = G.H_WEB / 2 + tft - st["ys"]; y_bot = -(G.H_WEB / 2 + tfb) - st["ys"]
        # 철근 합성단면 (부모멘트부): 강재 + 상·하면 철근 (콘크리트 무시)
        y_slab_bot = G.H_WEB / 2 + tft + G.TH - st["ys"]
        Ar_t, Ar_b = REBAR_TOP * be, REBAR_BOT * be
        y_rt, y_rb = y_slab_bot + G.TC - COV_TOP, y_slab_bot + COV_BOT
        Av_r = st["A"] + Ar_t + Ar_b
        d_r = (Ar_t * y_rt + Ar_b * y_rb) / Av_r                              # 강재도심 → 철근합성 도심
        I_r = st["I33"] + st["A"] * d_r ** 2 + Ar_t * (y_rt - d_r) ** 2 + Ar_b * (y_rb - d_r) ** 2
        Fk = (G.WEB_SP + G.TW) * (G.H_WEB + tft / 2 + tfb / 2)                # 폐단면 면적 (비틀림)
        secs[sc] = dict(tft=tft, tfb=tfb, neg=neg, be=be, st=st, cp=cp, y_top=y_top, y_bot=y_bot, Aw=2 * G.H_WEB * G.TW, Fk=Fk,
                        reb=dict(A=Av_r, I=I_r, d=d_r, y_rt=y_rt, y_rb=y_rb, Ar=Ar_t + Ar_b))
    return secs

def sig(sec, f, stage, n=None):
    """(σ_st, σ_sb, σ_ct, σ_reb, τ)  MPa. 인장 +. stage: steel | comp | rebar"""
    My, Mz, Fx, Fz, Mx = f["My"], f["Mz"], f["Fx"], f["Fz"], f["Mx"]
    lat = abs(Mz) * (G.BF / 2)
    if stage == "steel":
        s = sec["st"]; I, A, I22 = s["I33"], s["A"], s["I22"]
        st_ = -My * sec["y_top"] / I + Fx / A; sb_ = -My * sec["y_bot"] / I + Fx / A; ct_ = 0.0; rb_ = 0.0; cb_ = 0.0
    elif stage == "rebar":
        r = sec["reb"]; I, A, I22 = r["I"], r["A"], sec["st"]["I22"]
        yt, yb, yr = sec["y_top"] - r["d"], sec["y_bot"] - r["d"], r["y_rt"] - r["d"]
        st_ = -My * yt / I + Fx / A; sb_ = -My * yb / I + Fx / A; ct_ = 0.0; rb_ = -My * yr / I + Fx / A; cb_ = 0.0
    else:
        c = sec["cp"][n or N]; I, A, I22 = c["I33"], c["A"], c["I22"]
        yt, yb, yc, ycb = sec["y_top"] - c["dvs"], sec["y_bot"] - c["dvs"], c["dvc"] + G.TC / 2, c["dvc"] - G.TC / 2
        st_ = -My * yt / I + Fx / A; sb_ = -My * yb / I + Fx / A; ct_ = (-My * yc / I + Fx / A) / (n or N); rb_ = 0.0; cb_ = (-My * ycb / I + Fx / A) / (n or N)
    tau = abs(Fz) / sec["Aw"] + abs(Mx) / (2 * sec["Fk"] * G.TW)
    return tuple(v * MPA for v in (st_, sb_, ct_, rb_, tau, lat / I22, cb_))

def eccentric_force(sec, n, P, k):
    """바닥판 도심에 축력 P(압축 −)가 작용할 때 합성단면(n)의 응력: σ = P/Av + k·(P·dvc)·y/Iv  (y: 합성도심 기준 +위). 콘크리트는 /n"""
    c = sec["cp"][n]; M = P * c["dvc"]
    yt, yb, yc, ycb = sec["y_top"] - c["dvs"], sec["y_bot"] - c["dvs"], c["dvc"] + G.TC / 2, c["dvc"] - G.TC / 2
    st_ = P / c["A"] + k * M * yt / c["I33"]; sb_ = P / c["A"] + k * M * yb / c["I33"]; ct_ = (P / c["A"] + k * M * yc / c["I33"]) / n; cb_ = (P / c["A"] + k * M * ycb / c["I33"]) / n
    return st_ * MPA, sb_ * MPA, ct_ * MPA, cb_ * MPA

def creep(sec, msc, k):
    """크리프 (계산서 p.7486 방식, Φ1=2 → n1=16): 합성후 사하중이 만든 바닥판 압축력이 이완되어 강재로 옮겨감"""
    c = sec["cp"][N]; Nc = -msc * c["dvc"] * c["Ac"] / (N * c["I33"])          # 바닥판 압축력(정모멘트 → 음수=압축)
    P = Nc * 2 * PHI1 / (2 + PHI1)
    st_, sb_, ct_, cb_ = eccentric_force(sec, N1, P, k)
    fc = sig(sec, {"My": msc, "Fz": 0, "Mz": 0, "Fx": 0, "Mx": 0}, "comp")          # 합성후 사하중에 의한 바닥판 응력 (상연 [2], 하연 [6])
    ct_ = ct_ - fc[2] * PHI1 / (1 + PHI1 / 2); cb_ = cb_ - fc[6] * PHI1 / (1 + PHI1 / 2)   # 계산서: − Ec1·fcu·Φ1/Ec
    return st_, sb_, ct_, cb_

def shrinkage(sec, k):
    """건조수축 (n2=24): 콘크리트를 원길이로 붙드는 인장력 P2 = Es·εs·Ac/n2 → 합성단면에 −P2"""
    Ac = sec["cp"][N2]["Ac"]; P2 = G.ES * EPS_S * Ac / N2
    st_, sb_, ct_, cb_ = eccentric_force(sec, N2, -P2, k)
    ct_ += G.ES * EPS_S / N2 * MPA; cb_ += G.ES * EPS_S / N2 * MPA
    return st_, sb_, ct_, cb_

def tempdiff(sec, k, sign=+1):
    """강-바닥판 온도차 10℃ (바닥판이 낮음 = 수축과 같은 방향, sign=+1). n=8"""
    Ac = sec["cp"][N]["Ac"]; P1 = G.ES * ALPHA * DT * Ac / N * sign
    st_, sb_, ct_, cb_ = eccentric_force(sec, N, -P1, k)
    ct_ += G.ES * ALPHA * DT * sign / N * MPA; cb_ += G.ES * ALPHA * DT * sign / N * MPA
    return st_, sb_, ct_, cb_

def yield_check(rec):
    """항복에 대한 안전도 검사 (도로교설계기준 강교편 3.9.3.2)
    f = 1.3·(합성전 고정 + 합성후 고정) + 2.15·(활하중+충격) + 크리프 + 건조수축 + 온도차 ≤ fy
    · 연별로 총응력 |f|가 커지는 방향(sign)을 택함: 활하중은 그 방향의 포락값(LLmax/LLmin, 지점침하 포함), 크리프·건조수축·온도차(강-바닥판 10℃, ±)는 그 방향으로 작용할 때만 가산.
    · 강재 fy: SM490 t≤40 → 320, t>40 → 300 MPa. 바닥판 압축연: 3/5·fck. 부모멘트부 철근: fy = 400 MPa(SD40).
    · 응력성분은 rec["parts"] (n = 8 합성단면, 부모멘트부는 철근단면) 그대로 사용. v 인덱스: 0 강재상연, 1 강재하연, 2 바닥판상연, 3 철근 / CR·SH·TD: (st, sb, ct, cb)"""
    p = rec["parts"]; hog = rec["hog"]
    fibers = [("강재 상연", 0, 0, FY_STEEL(rec["tft"])), ("강재 하연", 1, 1, FY_STEEL(rec["tfb"]))]
    fibers += [("철근", 3, None, FY_REBAR)] if hog else [("바닥판 상연", 2, 2, 3.0 / 5.0 * FCK)]
    out = []
    for nm, iv, ic, fy in fibers:
        D = 1.3 * (p["D1"][iv] + p["D2"][iv])
        cands = []
        for sgn in (+1, -1):
            L = 2.15 * (max(p["LLmax"][iv], p["LLmin"][iv], 0.0) if sgn > 0 else min(p["LLmax"][iv], p["LLmin"][iv], 0.0))
            cr = p["CR"][ic] if ic is not None else 0.0; sh = p["SH"][ic] if ic is not None else 0.0; td = p["TD"][ic] if ic is not None else 0.0
            cr = cr if cr * sgn > 0 else 0.0; sh = sh if sh * sgn > 0 else 0.0
            td = abs(td) * sgn if abs(td) > 1e-9 else 0.0                       # 온도차는 ±10℃ 모두 가능 → 항상 불리한 방향
            f = D + L + cr + sh + td
            cands.append((abs(f), sgn, D, L, cr, sh, td, f))
        _, sgn, D, L, cr, sh, td, f = max(cands) if nm != "바닥판 상연" else cands[1]     # 콘크리트는 압축(−) 방향만 검사
        ratio = abs(f) / fy if not (nm == "바닥판 상연" and f > 0) else 0.0
        out.append(dict(fiber=nm, sign="인장" if f > 0 else "압축", D13=round(D, 2), L215=round(L, 2), creep=round(cr, 2), shrink=round(sh, 2), temp=round(td, 2),
                        sum=round(f, 2), fy=fy, ratio=round(ratio, 3), ok=ratio <= 1.0))
    return out

# ───────── 메인 ─────────
def main():
    A, C = load_table("A_steel"), load_table("C_comp")
    secs = sections(); names = {kk[0] for kk in C}
    ll_max = [n for n in names if n.endswith("(max)")]; ll_min = [n for n in names if n.endswith("(min)")]
    sd_names = sorted(n for n in names if n.startswith("SD_"))
    sup_s, spans = INFO["sup_s"], INFO["spans"]
    # k 계수: UNITM 해석 My를 A1 단부 값으로 정규화
    def k_of(e, part, g):
        first = [x for x in INFO["elems"] if x[1] == g][0][0]
        ref = F(C, "UNITM", first, "I")["My"]
        return F(C, "UNITM", e, part)["My"] / ref if abs(ref) > 1e-9 else 0.0
    rows = []
    for e, g, s1, s2, sc in INFO["elems"]:
        sec = secs[sc]
        for part, s in (("I", s1), ("J", s2)):
            fD1 = F(A, "D1", e, part); fD2 = F(C, "SDL", e, part)
            fLmax = max((F(C, n, e, part) for n in ll_max), key=lambda f: f["My"]); fLmin = min((F(C, n, e, part) for n in ll_min), key=lambda f: f["My"])
            sd_pos = max([F(C, n, e, part)["My"] for n in sd_names] + [0.0]); sd_neg = min([F(C, n, e, part)["My"] for n in sd_names] + [0.0])
            fCF, fW, fWL, fLF = (F(C, n, e, part) for n in ("CF", "W", "WL", "LF"))
            fTP, fTM = F(C, "TP", e, part), F(C, "TM", e, part)
            k = k_of(e, part, g)
            hog = (fD2["My"] + fLmin["My"] + sd_neg) < 0
            stage = "rebar" if hog else "comp"
            # 활하중+지점침하 포락 (max/min) — 부모멘트 측은 철근단면
            def S(f, stg=None, n=None): return sig(sec, f, stg or stage, n)
            d1 = sig(sec, fD1, "steel"); d2 = S(fD2)
            Lmax = S({**fLmax, "My": fLmax["My"] + sd_pos}, "comp"); Lmin = S({**fLmin, "My": fLmin["My"] + sd_neg})
            cf = S(fCF); w = S(fW); wl = S(fWL); lf = S(fLF); tp = S(fTP); tm = S(fTM)
            cr = creep(sec, fD2["My"], k); sh = shrinkage(sec, k); td = tempdiff(sec, k)
            # 정(+)측 / 부(−)측 포락별 case 응력 (st, sb, ct, rb)
            IDX = [0, 1, 2, 3, 6]          # v = [강재상연, 강재하연, 콘크리트상연, 철근, 콘크리트하연]
            CI = {0: 0, 1: 1, 2: 2, 4: 3}  # 크리프·건조수축·온도차 반환 (st, sb, ct, cb) → v 인덱스
            def combo(cid, side):
                L = Lmax if side == "max" else Lmin
                v = [d1[i] + d2[i] for i in IDX] if cid >= 2 else [d1[0], d1[1], 0.0, 0.0, 0.0]
                sg = 1 if side == "max" else -1
                if cid >= 2:
                    for j, i in enumerate(IDX): v[j] += L[i] + sg * abs(cf[i])
                    v[0] += sg * cf[5]; v[1] += sg * cf[5]
                if cid >= 3:
                    for j, i in CI.items(): v[j] += cr[i]
                if cid >= 4:
                    for j, i in CI.items(): v[j] += sh[i]
                if cid in (5, 6, 8, 9):
                    tsg = 1 if cid in (5, 8) else -1
                    for j, i in CI.items(): v[j] += tsg * td[i]
                    for j, i in enumerate(IDX): v[j] += max(tp[i], tm[i]) if side == "max" else min(tp[i], tm[i])
                if cid >= 7:
                    for j, i in enumerate(IDX): v[j] += sg * (abs(w[i]) + abs(wl[i]) + abs(lf[i]))
                    lat = w[5] + wl[5] + lf[5]; v[0] += sg * lat; v[1] += sg * lat
                if hog and side == "min": v[2] = 0.0; v[4] = 0.0        # 부모멘트부 콘크리트 무시
                if not hog: v[3] = 0.0
                return v
            tau = d1[4] + d2[4] + max(Lmax[4], Lmin[4])
            rec = dict(elem=e, g=g, part=part, s=round(s, 3), sc=sc, tft=sec["tft"], tfb=sec["tfb"], hog=hog, k=round(k, 4), tau=round(tau, 2),
                       parts=dict(D1=[round(d1[i], 2) for i in IDX], D2=[round(d2[i], 2) for i in IDX], LLmax=[round(Lmax[i], 2) for i in IDX], LLmin=[round(Lmin[i], 2) for i in IDX],
                                  CR=[round(x, 2) for x in cr], SH=[round(x, 2) for x in sh], TD=[round(x, 2) for x in td], W=[round(w[i], 2) for i in IDX],
                                  CF=[round(cf[i], 2) for i in IDX], WL=[round(wl[i], 2) for i in IDX], LF=[round(lf[i], 2) for i in IDX], TP=[round(tp[i], 2) for i in IDX]),
                       forces=dict(D1=fD1, D2=fD2, LLmax=fLmax, LLmin=fLmin, SDmax=sd_pos, SDmin=sd_neg, W=fW, CF=fCF, WL=fWL, LF=fLF), cases={})
            fa0 = FA_STEEL(max(sec["tft"], sec["tfb"]))
            nt, nb = (G.RIB_NEG if sec["neg"] else G.RIB_POS)
            fca_top, fca_bot = min(fa0, fca_local(sec["tft"], nt)), min(fa0, fca_local(sec["tfb"], nb))   # 압축 시 허용 (국부좌굴)
            rec["fca"] = (round(fca_top, 1), round(fca_bot, 1))
            for cid, (nm, _) in CASES.items():
                mx, mn = combo(cid, "max"), combo(cid, "min")
                fac_c, fac_t = fac_of(cid, hog)                       # 표 3.9.4: 압축연 / 인장연 증가율 (정·부모멘트부별)
                fa, fc = fa0 * fac_t, FA_CONC * fac_c                 # fa = 인장연 허용, fc = 바닥판 압축 허용(압축연 증가율)
                # 위치별 응력비: 인장(+)은 fa0×인장연 증가율, 압축(−)은 fca(국부좌굴)×압축연 증가율
                def ratio_of(v, fca): return abs(v) / ((fa if v >= 0 else fca * fac_c) if abs(v) > 1e-9 else 1e9)
                peak_ratio = max(ratio_of(mx[0], fca_top), ratio_of(mn[0], fca_top), ratio_of(mx[1], fca_bot), ratio_of(mn[1], fca_bot))
                peak = max(abs(mx[0]), abs(mn[0]), abs(mx[1]), abs(mn[1]))
                cmin = min(mx[2], mn[2], mx[4], mn[4], 0.0)
                rec["cases"][cid] = dict(max=[round(x, 2) for x in mx], min=[round(x, 2) for x in mn], fa=fa, fc=fc, fca_top=round(fca_top * fac_c, 1), fca_bot=round(fca_bot * fac_c, 1),
                                         fac_c=fac_c, fac_t=fac_t, fa_c=round(fa0 * fac_c, 1),
                                         sf=round(1 / peak_ratio, 3) if peak_ratio > 0 else 99.0,
                                         sf_c=round(fc / max(abs(cmin), 1e-9), 3) if cmin < 0 else 99.0)
            rec["yield_check"] = yield_check(rec)
            rows.append(rec)
    json.dump(rows, open(os.path.join(RUNS, "stress3_all.json"), "w", encoding="utf-8"), ensure_ascii=False)
    summary(rows, secs, A, C, ll_max, ll_min)

def grade(sf):
    return "A" if sf > 1.0 else ("C" if sf >= 0.9 else ("D" if sf >= 0.75 else "E"))

def summary(rows, secs, A, C, ll_max, ll_min):
    sup_s, spans = INFO["sup_s"], INFO["spans"]
    # 검토 단면: case2 정모멘트 최대(하연 인장 최대) / 부모멘트 최대(상연 인장 최대) — 주형 무관 최댓값
    pos = max(rows, key=lambda r: r["cases"][2]["max"][1]); neg = max(rows, key=lambda r: r["cases"][2]["min"][0])
    rep = ["# 순천만IC2교 강박스 — 안전성 검토 v3 (허용응력설계법)", "",
           "합성전 강재단면, 합성후 합성단면(n=8), 크리프(Φ=2)·건조수축(ε=200×10⁻⁶, Φ=4)·온도차(10℃)는 계산서 방식 + 2차 부정정력 계수 k(단위모멘트 해석). 부모멘트부는 강재+철근 단면. 응력 MPa(인장 +).", ""]
    def sec_block(title, r):
        L = [f"## {title} — {r['g']} s = {r['s']} m (요소 {r['elem']}{r['part']}, 판두께 {int(r['tft']*1000)}/{int(r['tfb']*1000)} mm, {'부모멘트부(철근단면)' if r['hog'] else '정모멘트부(합성단면)'}, k = {r['k']})", ""]
        fz = r["forces"]
        L += ["| 하중 | M (kN·m) | S (kN) | Mt (kN·m) | Mz 횡방향 (kN·m) | N (kN) |", "| :-- | --: | --: | --: | --: | --: |"]
        for nm, key in [("합성전 고정하중 Ms", "D1"), ("합성후 고정하중 Msc", "D2"), ("활하중+충격 최대", "LLmax"), ("활하중+충격 최소", "LLmin"), ("풍하중 W", "W"), ("활하중 풍하중 WL", "WL"), ("원심하중 CF", "CF"), ("제동하중 LF", "LF")]:
            f = fz[key]; L.append(f"| {nm} | {f['My']:.1f} | {f['Fz']:.1f} | {f['Mx']:.1f} | {f['Mz']:.1f} | {f['Fx']:.1f} |")
        L.append(f"| 지점침하 max/min | {fz['SDmax']:.1f} / {fz['SDmin']:.1f} | | | | |")
        L += ["", "| case | 내용 | σ상연 max/min | σ하연 max/min | σ바닥판 max/min | σ철근 | 증가율 압축/인장 | 허용 인장연 | 허용 압축연 상/하(국부좌굴) | 허용(콘) | SF | 판정 |", "| --: | :-- | :-- | :-- | :-- | :-- | :-- | --: | :-- | --: | --: | :-- |"]
        for cid, (nm, _) in CASES.items():
            c = r["cases"][cid]
            L.append(f"| {cid} | {nm} | {c['max'][0]:.1f} / {c['min'][0]:.1f} | {c['max'][1]:.1f} / {c['min'][1]:.1f} | {c['max'][2]:.2f} / {c['min'][2]:.2f} | {max(c['max'][3], c['min'][3], key=abs):.1f} | {c['fac_c']:.2f} / {c['fac_t']:.2f} | {c['fa']:.1f} | {c['fca_top']:.1f} / {c['fca_bot']:.1f} | {c['fc']:.1f} | {c['sf']:.2f} | {'O.K' if c['sf'] >= 1 and c['sf_c'] >= 1 else 'N.G'} |")
        L += ["", f"증가율: 표 3.9.4({'부모멘트부' if r['hog'] else '정모멘트부'}) — case3·4 압축/인장 {FAC[3]['neg' if r['hog'] else 'pos'][0]:.2f}/{FAC[3]['neg' if r['hog'] else 'pos'][1]:.2f}, case5·6 {FAC[5]['neg' if r['hog'] else 'pos'][0]:.2f}/{FAC[5]['neg' if r['hog'] else 'pos'][1]:.2f}; case7 1.25, case8·9 1.35(표 2.2.1). 국부좌굴 fca(표 3.4.3, 증가율 미적용) 상/하 = {r['fca'][0]:.1f} / {r['fca'][1]:.1f} MPa",
              f"전단·비틀림 응력 τ = {r['tau']:.1f} MPa ≤ 허용 {FA_SHEAR} MPa → {'O.K' if r['tau'] <= FA_SHEAR else 'N.G'}", ""]
        L += ["### 항복에 대한 안전도 검사 (3.9.3.2) — f = 1.3D + 2.15(L+I) + 크리프 + 건조수축 + 온도차 ≤ fy", "",
              "| 연 | 1.3D | 2.15L | 크리프 | 건조수축 | 온도차 | 합계 f | fy | f/fy | 판정 |", "| :-- | --: | --: | --: | --: | --: | --: | --: | --: | :-- |"]
        for y in r["yield_check"]:
            L.append(f"| {y['fiber']}({y['sign']}) | {y['D13']:.1f} | {y['L215']:.1f} | {y['creep']:.1f} | {y['shrink']:.1f} | {y['temp']:.1f} | {y['sum']:.1f} | {y['fy']:.1f} | {y['ratio']:.3f} | {'O.K' if y['ok'] else 'N.G'} |")
        L.append("")
        return L
    rep += sec_block("정모멘트부", pos) + sec_block("부모멘트부", neg)
    # 내하율 (case2 기준: fd = D1+D2, fl = LL(1+i)+SD)
    rep += ["## 기본 내하율 (허용응력법, D+L(1+i))", "", "| 구분 | 위치 | fa | fd | fl(1+i) | RF | 판정 |", "| :-- | :-- | --: | --: | --: | --: | :-- |"]
    rfs = []
    for title, r, fiber in (("정모멘트부", pos, 1), ("정모멘트부", pos, 0), ("부모멘트부", neg, 0), ("부모멘트부", neg, 1)):
        p = r["parts"]; fd = p["D1"][fiber] + p["D2"][fiber]
        fl = max(p["LLmax"][fiber], p["LLmin"][fiber]) if fd >= 0 else min(p["LLmax"][fiber], p["LLmin"][fiber])   # 사하중과 같은 부호로 더해지는 활하중 응력
        fa = FA_STEEL(max(r["tft"], r["tfb"])) * (1 if fd >= 0 else -1)
        rf = (fa - fd) / fl if abs(fl) > 1e-6 else 99.0; rfs.append(rf)
        rep.append(f"| {title} {'하연' if fiber else '상연'} | {r['g']} s={r['s']} | {fa:.0f} | {fd:.1f} | {fl:.1f} | {rf:.3f} | {'DB-24 이상' if rf >= 1 else 'DB-24 미만'} |")
    # 처짐
    rep += ["", "## 활하중 처짐 (충격 포함, 허용 L/500)", "", "| 경간 | L (m) | 최대 처짐 (mm) | 허용 (mm) | 판정 |", "| :-- | --: | --: | --: | :-- |"]
    try:
        td = json.load(open(os.path.join(RUNS, "C_comp_disp.json"), encoding="utf-8"))["SS_Table"]; h = td["HEAD"]
        iz, inode, il = h.index("DZ"), h.index("Node"), h.index("Load")
        s_of = {n: s for g in ("G1", "G2") for n, s in INFO["nodes_G"][g]}
        for i, L in enumerate(spans):
            a, b = sup_s[i], sup_s[i + 1]
            dz = max((abs(float(r[iz])) for r in td["DATA"] if a < s_of.get(int(r[inode]), -1) < b), default=0.0) * 1000
            allow = L / 500 * 1000
            rep.append(f"| S{i+1} | {L:.3f} | {dz:.1f} | {allow:.1f} | {'O.K' if dz <= allow else 'N.G'} |")
    except Exception as ex:
        rep.append(f"| (변위표 없음: {ex}) | | | | |")
    # 받침
    rep += ["", "## 받침용량 및 부반력 (kN)", "", "| 지점 | 주형 | 받침 | 고정하중 | 활하중 max | 활하중 min | 합계 max | 용량 | 판정 | 부반력 |", "| :-- | :-- | :-- | --: | --: | --: | --: | --: | :-- | :-- |"]
    def reac(tag):
        t = json.load(open(os.path.join(RUNS, f"{tag}_reaction.json"), encoding="utf-8"))["SS_Table"]; h = t["HEAD"]
        out = {}
        for r in t["DATA"]: out[(r[h.index("Load")], int(r[h.index("Node")]))] = float(r[h.index("FZ")])
        return out
    RA, RC = reac("A_steel"), reac("C_comp")
    for b in sorted(INFO["bearings"], key=lambda b: (["A1", "P1", "P2", "P3", "P4", "P5"].index(b["pier"]), b["girder"])):
        nd = b["node"]; d = RA.get(("D1", nd), 0) + RC.get(("SDL", nd), 0)
        lmax = max([RC.get((n, nd), 0) for n in ll_max] + [0]); lmin = min([RC.get((n, nd), 0) for n in ll_min] + [0])
        cap = CAP_KN[b["pier"]]
        rep.append(f"| {b['pier']} | {b['girder']} | {b['kind']} | {d:.0f} | {lmax:.0f} | {lmin:.0f} | {d+lmax:.0f} | {cap:.0f} | {'O.K' if d + lmax <= cap else 'N.G'} | {'없음' if d + lmin > 0 else '★발생'} |")
    # 요약·등급
    sf_pos = min(pos["cases"][c]["sf"] for c in CASES); sf_neg = min(neg["cases"][c]["sf"] for c in CASES)
    rep += ["", "## 안전성 평가 결과 요약 (세부지침 표 1.34)", "", "| 구분 | 최소 안전율 | 지배 case | 등급 |", "| :-- | --: | --: | :-- |",
            f"| 정모멘트부 강재 | {sf_pos:.2f} | {min(CASES, key=lambda c: pos['cases'][c]['sf'])} | {grade(sf_pos)} |",
            f"| 부모멘트부 강재 | {sf_neg:.2f} | {min(CASES, key=lambda c: neg['cases'][c]['sf'])} | {grade(sf_neg)} |",
            f"| 기본내하율 최소 | {min(rfs):.3f} | — | {'DB-24 이상' if min(rfs) >= 1 else 'DB-24 미만'} |", ""]
    open(os.path.join(RUNS, "결과_안전성검토_v3.md"), "w", encoding="utf-8").write("\n".join(rep))
    json.dump(dict(pos=pos, neg=neg, rfs=rfs, sf_pos=sf_pos, sf_neg=sf_neg, cases={k: v[0] for k, v in CASES.items()}, fac={k: v[1] for k, v in CASES.items()},
                   fac_tbl={k: dict(pos=list(v["pos"]), neg=list(v["neg"])) for k, v in FAC.items()},
                   yield_check=dict(pos=pos["yield_check"], neg=neg["yield_check"])),
              open(os.path.join(RUNS, "stress3_gov.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"정모멘트부 {pos['g']} s={pos['s']} SF {sf_pos:.2f} | 부모멘트부 {neg['g']} s={neg['s']} SF {sf_neg:.2f} | RF min {min(rfs):.3f}")
    print("저장:", os.path.join(RUNS, "결과_안전성검토_v3.md"))

if __name__ == "__main__":
    main()

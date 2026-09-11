# -*- coding: utf-8 -*-
"""
단면응력 계산기 (허용응력설계법, 계산서 방식)
  합성전 하중(D1)      → 강재단면 (As, Is)
  합성후 하중(D2, L+I, W, WL, CF, LF, T) → 합성단면 (n=8)
  건조수축(S)          → 합성단면 n_s=2n, ε_s = 200×10⁻⁶ (도로교설계기준 2005 강합성)
응력 위치: 강재 상플랜지 상연(st), 강재 하플랜지 하연(sb), 바닥판 상연(ct)
부호: 인장 +, 압축 −.  MIDAS My는 정모멘트(상연 압축) +, Axial은 인장 +.
조합: combine2.COMBOS (I~VI) + S는 IV·V·VI에 포함. 허용응력 SM490 t≤40: 190 MPa, 40<t≤75: 175 MPa (인장·압축 동일, 국부좌굴 별도),
      바닥판 콘크리트 압축 0.4 fck = 10.8 MPa. 조합별 허용응력 증가율 적용.
"""
import sys, os, json, math
sys.stdout.reconfigure(encoding="utf-8")
PJ = r"D:\Midas\projects\순천만IC2교"; RUNS = os.path.join(PJ, "runs")
sys.path.insert(0, PJ)
import gen_model as G
from combine2 import load_table, COMBOS

INFO = json.load(open(os.path.join(RUNS, "model_info.json"), encoding="utf-8"))
EPS_S, N_S = 200e-6, 2 * G.N_SHORT
FA_STEEL = lambda t: 190.0 if t <= 0.040 else 175.0        # MPa
FA_CONC = 0.4 * 27.0
SHRINK_COMBOS = {"IV", "V", "VI"}
MPA = 1e-3   # kN/m² → MPa

def section_of(sc):
    tft, tfb, neg, be = [k for k, v in G_SEC_KEYS.items() if v == sc][0]
    st = G.steel_section(tft, tfb, G.RIB_NEG if neg else G.RIB_POS)
    cp = G.composite_section(st, be, G.N_SHORT)
    cs = G.composite_section(st, be, N_S)
    y_top = G.H_WEB / 2 + tft - st["ys"]           # 강재 도심 → 상플랜지 상연 (+위)
    y_bot = -(G.H_WEB / 2 + tfb) - st["ys"]        # 강재 도심 → 하플랜지 하연 (−)
    return dict(tft=tft, tfb=tfb, neg=neg, be=be, st=st, cp=cp, cs=cs, y_top=y_top, y_bot=y_bot)

def stresses_from(F, sec, stage):
    """F: dict(My, Mz, Fx) kN·m/kN → (σ_st, σ_sb, σ_ct) MPa. stage: 'steel' | 'comp'"""
    My, Mz, Fx = F["My"], F["Mz"], F["Fx"]
    if stage == "steel":
        s = sec["st"]; I, A, I22 = s["I33"], s["A"], s["I22"]
        st_ = (-My * sec["y_top"] / I + Fx / A) * MPA
        sb_ = (-My * sec["y_bot"] / I + Fx / A) * MPA
        ct_ = 0.0
    else:
        c = sec["cp"]; I, A, I22, n = c["I33"], c["A"], c["I22"], c["n"]
        yt, yb = sec["y_top"] - c["dvs"], sec["y_bot"] - c["dvs"]      # 합성도심 기준
        yc = c["dvc"] + G.TC / 2
        st_ = (-My * yt / I + Fx / A) * MPA
        sb_ = (-My * yb / I + Fx / A) * MPA
        ct_ = (-My * yc / I + Fx / A) / n * MPA
    lat = abs(Mz) * (G.BF / 2) / I22 * MPA        # 횡방향 휨 → 플랜지 끝 ± (불리한 쪽)
    return st_, sb_, ct_, lat

def shrinkage(sec):
    """건조수축: 1) 콘크리트에 인장력 P=ε·Es/n_s·Ac 가해 원길이 유지 → 2) 합성단면(n_s)에 −P 를 바닥판 도심에 작용"""
    c = sec["cs"]; Ec_eff = G.ES / N_S
    P = EPS_S * Ec_eff * c["Ac"]                    # kN
    e = c["dvc"] + 0.0                              # 합성도심 → 바닥판 도심 (위로 +)
    N, M = -P, -P * e                               # 축력(압축), 모멘트 (바닥판 위쪽 → 상연 인장 방향: sagging 반대)
    yt, yb = sec["y_top"] - c["dvs"], sec["y_bot"] - c["dvs"]; yc = c["dvc"] + G.TC / 2
    # 축력 N: σ = N/A ; 모멘트 M(= −P·e, 부호: MIDAS 정모멘트 + 와 같은 규약으로 두고 아래 식 사용)
    s_top = (N / c["A"] - M * yt / c["I33"]) * MPA
    s_bot = (N / c["A"] - M * yb / c["I33"]) * MPA
    c_top = ((N / c["A"] - M * yc / c["I33"]) / N_S + EPS_S * Ec_eff) * MPA
    return s_top, s_bot, c_top

def main():
    global G_SEC_KEYS
    # 단면 키 복원 (gen_model.build 와 같은 규칙)
    Pl, spans, rot = G.geometry(); eff = G.eff_width_table(spans)
    top, bot = G.plate_segments("top"), G.plate_segments("bot")
    G_SEC_KEYS = {}
    for e, g, s1, s2, sc in INFO["elems"]:
        sm = (s1 + s2) / 2
        key = (round(G.thick_at(top, sm), 4), round(G.thick_at(bot, sm), 4), G.thick_at(top, sm) >= 0.020 - 1e-9, round(G.beff_at(eff, sm), 3))
        G_SEC_KEYS.setdefault(key, sc)
        assert G_SEC_KEYS[key] == sc, (key, sc)
    secs = {sc: section_of(sc) for sc in set(G_SEC_KEYS.values())}
    A, C = load_table("A_steel"), load_table("C_comp")
    names = {k[0] for k in C}
    llmax = [n for n in names if n.endswith("(max)")]; llmin = [n for n in names if n.endswith("(min)")]
    sup_s, spans = INFO["sup_s"], INFO["spans"]
    rows, gov = [], {}
    for e, g, s1, s2, sc in INFO["elems"]:
        sec = secs[sc]
        for part, s in (("I", s1), ("J", s2)):
            key = lambda ld, tbl: tbl.get((ld, e, part), {"My": 0, "Mz": 0, "Fx": 0})
            base = {"D1": stresses_from(key("D1", A), sec, "steel")}
            baseS = {}   # 부모멘트부용: 합성후 하중도 강재단면(콘크리트 인장 무시)
            for ld in ("SDL", "W", "WL", "CF", "LF", "TP", "TM"):
                base[ld] = stresses_from(key(ld, C), sec, "comp"); baseS[ld] = stresses_from(key(ld, C), sec, "steel")
            ll_cands = [stresses_from(key(n, C), sec, "comp") for n in llmax + llmin]
            ll_candsS = [stresses_from(key(n, C), sec, "steel") for n in llmax + llmin]
            # 부모멘트 판정: 합성후 사하중 + 활하중 최소(부) 모멘트가 음(hogging)이면 부(−)측 포락은 강재단면으로
            m_hog = key("SDL", C)["My"] + min(key(n, C)["My"] for n in llmin) if llmin else key("SDL", C)["My"]
            hog = m_hog < 0
            sh = shrinkage(sec)
            rec = dict(elem=e, g=g, part=part, s=round(s, 3), sc=sc, tft=sec["tft"], tfb=sec["tfb"], hog=hog, combos={})
            for name, fac, terms in COMBOS:
                out = {}
                for loc in (0, 1, 2):     # st, sb, ct
                    def side(B, LLc, pick):   # pick: max(+측) / min(−측)
                        v = base["D1"][loc] + terms["D"] * B["SDL"][loc]
                        if "LL" in terms and LLc: v += pick(c[loc] for c in LLc)
                        for k in ("W", "WL", "CF", "LF"):
                            if k in terms:
                                a = abs(terms[k] * B[k][loc]) + (abs(terms[k] * B[k][3]) if loc < 2 else 0)
                                v += a if pick is max else -a
                        if "T" in terms: v += pick(B["TP"][loc], B["TM"][loc])
                        if name in SHRINK_COMBOS and loc < 2: v += sh[loc]
                        if name in SHRINK_COMBOS and loc == 2 and B is base: v += sh[loc]
                        return v
                    hi = side(base, ll_cands, max)
                    lo = side(baseS if hog else base, ll_candsS if hog else ll_cands, min)
                    if hog and loc == 2: lo = 0.0          # 부모멘트부 콘크리트는 무시(균열)
                    out[("st", "sb", "ct")[loc]] = (round(hi, 2), round(lo, 2))
                fa_s = FA_STEEL(max(sec["tft"], sec["tfb"])) * fac; fa_c = FA_CONC * fac
                ratio = max(abs(out["st"][0]), abs(out["st"][1]), abs(out["sb"][0]), abs(out["sb"][1])) / fa_s
                ratio_c = max(abs(min(out["ct"][1], 0.0)), 0.0) / fa_c
                out["fa_s"], out["fa_c"], out["ratio_s"], out["ratio_c"] = fa_s, fa_c, round(ratio, 3), round(ratio_c, 3)
                rec["combos"][name] = out
                gk = (g, name)
                if gk not in gov or ratio > gov[gk]["ratio_s"]:
                    gov[gk] = dict(ratio_s=ratio, s=s, elem=e, part=part, st=out["st"], sb=out["sb"], ct=out["ct"], fa_s=fa_s, tft=sec["tft"], tfb=sec["tfb"], ratio_c=ratio_c)
            rows.append(rec)
    json.dump(rows, open(os.path.join(RUNS, "stress_all.json"), "w", encoding="utf-8"), ensure_ascii=False)
    # 보고
    rep = ["# 순천만IC2교 강박스 — 단면응력 검토 (허용응력설계법)", "",
           "합성전 D1은 강재단면, 합성후 하중은 합성단면(n=8), 건조수축은 n=16·ε=200×10⁻⁶(조합 IV·V·VI). 응력 MPa, 인장 +. 허용응력 SM490 190 MPa(t≤40)·175(40<t≤75), 바닥판 0.4fck=10.8 MPa, 조합별 증가율 적용.", ""]
    print("== 조합별 지배 단면 (강재 응력비 최대)")
    rep += ["## 조합별 지배 단면", "", "| 주형 | 조합 | 위치 s(m) | 요소 | t상/하(mm) | σ상연 max/min | σ하연 max/min | σ바닥판 max/min | 허용 | 응력비(강재) | 응력비(콘크리트) |",
            "| :-- | :-- | --: | --: | :-- | :-- | :-- | :-- | --: | --: | --: |"]
    for g in ("G1", "G2"):
        for name, fac, terms in COMBOS:
            v = gov[(g, name)]
            rep.append(f"| {g} | {name} | {v['s']:.2f} | {v['elem']}{v['part']} | {int(v['tft']*1000)}/{int(v['tfb']*1000)} | {v['st'][0]:.1f} / {v['st'][1]:.1f} | {v['sb'][0]:.1f} / {v['sb'][1]:.1f} | {v['ct'][0]:.2f} / {v['ct'][1]:.2f} | {v['fa_s']:.0f} | **{v['ratio_s']:.3f}** | {v['ratio_c']:.3f} |")
            print(f"  {g} 조합{name:4s} s={v['s']:7.2f} t={int(v['tft']*1000)}/{int(v['tfb']*1000)}  σst {v['st'][0]:7.1f}/{v['st'][1]:7.1f}  σsb {v['sb'][0]:7.1f}/{v['sb'][1]:7.1f}  σct {v['ct'][0]:6.2f}/{v['ct'][1]:6.2f}  fa {v['fa_s']:.0f}  비 {v['ratio_s']:.3f} (콘크리트 {v['ratio_c']:.3f})")
    # 지점·경간별 조합 I 응력 (G1)
    rep += ["", "## 조합 I — 지점부·경간 중앙부 응력 (G1)", "", "| 위치 | s(m) | σ상연 (max/min) | σ하연 (max/min) | σ바닥판 (max/min) | 응력비 |", "| :-- | --: | :-- | :-- | :-- | --: |"]
    def pick(g, s_target, tol):
        cands = [r for r in rows if r["g"] == g and abs(r["s"] - s_target) < tol]
        return max(cands, key=lambda r: r["combos"]["I"]["ratio_s"]) if cands else None
    labels = [("P1", sup_s[1], 0.6), ("P2", sup_s[2], 0.6), ("P3", sup_s[3], 0.6), ("P4", sup_s[4], 0.6)]
    labels += [(f"S{i+1}", (sup_s[i] + sup_s[i+1]) / 2, spans[i] * 0.3) for i in range(5)]
    for lb, s0, tol in labels:
        r = pick("G1", s0, tol)
        if r:
            c1 = r["combos"]["I"]
            rep.append(f"| {lb} | {r['s']:.2f} | {c1['st'][0]:.1f} / {c1['st'][1]:.1f} | {c1['sb'][0]:.1f} / {c1['sb'][1]:.1f} | {c1['ct'][0]:.2f} / {c1['ct'][1]:.2f} | {c1['ratio_s']:.3f} |")
    rep += ["", "주: 부모멘트부(합성후 사하중+활하중 최소모멘트 < 0인 위치)의 부(−)측 포락은 콘크리트 인장을 무시하고 **강재단면**으로 계산(철근 미포함, 안전측). 정(+)측 포락과 정모멘트부는 합성단면(n=8).", ""]
    open(os.path.join(RUNS, "결과_단면응력.md"), "w", encoding="utf-8").write("\n".join(rep))
    print("저장:", os.path.join(RUNS, "결과_단면응력.md"))

if __name__ == "__main__":
    main()

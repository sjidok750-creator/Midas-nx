# -*- coding: utf-8 -*-
"""
하중조합 (도로교설계기준 2005 허용응력설계법) — A_steel(D1) + C_comp(D2, W, WL, CF, LF, TP/TM, L+I) 부재력 조합
조합 I~VI 별로 주형 My 포락(최대·최소)을 절점 위치마다 만들고, 지점부·경간 중앙부 극값과 정답지(단면 요약도)를 대조한다.
"""
import sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
PJ = r"D:\Midas\projects\순천만IC2교"; RUNS = os.path.join(PJ, "runs")
INFO = json.load(open(os.path.join(RUNS, "model_info.json"), encoding="utf-8"))
TONF = 9.80665
REF_NEG = {"P1": -2306.6, "P2": -3643.9, "P3": -3642.9, "P4": -2326.1}
REF_POS = {"S1": 1935.5, "S2": 547.3, "S3": 2278.3, "S4": 546.7, "S5": 1957.4}
COMBOS = [  # (이름, 허용응력 증가, 하중: 계수)   ± 는 부호 불리한 쪽, LL은 max/min 포락, T는 TP/TM 중 불리한 쪽
    ("I",   1.00, {"D": 1, "LL": 1, "CF": 1}),
    ("II",  1.25, {"D": 1, "W": 1}),
    ("III", 1.25, {"D": 1, "LL": 1, "CF": 1, "W": 0.3, "WL": 1, "LF": 1}),
    ("IV",  1.25, {"D": 1, "LL": 1, "CF": 1, "T": 1}),
    ("V",   1.40, {"D": 1, "W": 1, "T": 1}),
    ("VI",  1.40, {"D": 1, "LL": 1, "CF": 1, "W": 0.3, "WL": 1, "LF": 1, "T": 1}),
]
COMPS = {"My": "Moment-y", "Fz": "Shear-z", "Mz": "Moment-z", "Fx": "Axial", "Mx": "Torsion"}

def load_table(tag):
    tb = json.load(open(os.path.join(RUNS, f"{tag}_beamforce.json"), encoding="utf-8"))["SS_Table"]
    h = tb["HEAD"]; ie, il, ip = h.index("Elem"), h.index("Load"), h.index("Part")
    idx = {k: h.index(v) for k, v in COMPS.items()}
    out = {}
    for r in tb["DATA"]:
        out[(r[il], int(r[ie]), r[ip][0])] = {k: float(r[i]) for k, i in idx.items()}
    return out

def line(tbl, load, g, comp):
    pts = []
    for e, gg, s1, s2, sc in INFO["elems"]:
        if gg != g: continue
        for part, s in (("I", s1), ("J", s2)):
            v = tbl.get((load, e, part))
            if v is not None: pts.append((round(s, 4), v[comp]))
    return dict(pts)

def envelope(g, comp, A, C):
    S = sorted(line(A, "D1", g, comp).keys())
    D = {s: line(A, "D1", g, comp)[s] + line(C, "SDL", g, comp).get(s, 0) for s in S}
    names = {k[0] for k in C}
    llmax = {s: max(line(C, n, g, comp).get(s, -1e18) for n in names if n.endswith("(max)")) for s in S}
    llmin = {s: min(line(C, n, g, comp).get(s, 1e18) for n in names if n.endswith("(min)")) for s in S}
    st = {k: line(C, k, g, comp) for k in ("W", "WL", "CF", "LF", "TP", "TM")}
    res = {}
    for name, fac, terms in COMBOS:
        mx, mn = {}, {}
        for s in S:
            hi = lo = terms["D"] * D[s]
            if "LL" in terms: hi += terms["LL"] * llmax[s]; lo += terms["LL"] * llmin[s]
            for k in ("W", "WL", "CF", "LF"):
                if k in terms: v = terms[k] * st[k].get(s, 0); hi += abs(v); lo -= abs(v)
            if "T" in terms:
                tp, tm = st["TP"].get(s, 0), st["TM"].get(s, 0); hi += max(tp, tm); lo += min(tp, tm)
            mx[s], mn[s] = hi, lo
        res[name] = dict(fac=fac, max=mx, min=mn)
    return S, D, llmax, llmin, st, res

def extremes(vals, sup_s, spans):
    neg = {f"P{i}": min(v for s, v in vals.items() if abs(s - ss) < 0.6) for i, ss in enumerate(sup_s[1:-1], start=1)}
    pos = {f"S{i+1}": max(v for s, v in vals.items() if sup_s[i] + 0.5 < s < sup_s[i + 1] - 0.5) for i in range(len(spans))}
    return neg, pos

def main():
    A, C = load_table("A_steel"), load_table("C_comp")
    sup_s, spans = INFO["sup_s"], INFO["spans"]
    rep = ["# 순천만IC2교 강박스 — 하중조합별 주형 휨모멘트 (허용응력설계법)", "",
           "합성전(D1: 강재자중×할증 + 바닥판) + 합성후(D2: 포장층+방호벽, W, WL, CF, LF, T±15℃, L+I DB-24/DL-24 포락). 단위 kN·m. 정답지 = 준공도면 단면 요약도 모멘트도(ton·m 환산).", ""]
    out = {}
    for g in ("G1", "G2"):
        S, D, llmax, llmin, st, res = envelope(g, "My", A, C)
        out[g] = dict(S=S, D=D, llmax=llmax, llmin=llmin, static={k: [v.get(s, 0) for s in S] for k, v in st.items()},
                      combos={n: dict(fac=r["fac"], max=[r["max"][s] for s in S], min=[r["min"][s] for s in S]) for n, r in res.items()})
        rep += [f"## {g}", "", "| 위치 | D=D1+D2 | LL max/min | 조합 I | 조합 II | 조합 III | 조합 IV | 조합 V | 조합 VI | 정답지 | I/정답 |",
                "| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |"]
        negD, posD = extremes(D, sup_s, spans); negL, _ = extremes(llmin, sup_s, spans); _, posL = extremes(llmax, sup_s, spans)
        ext = {n: (extremes(r["min"], sup_s, spans)[0], extremes(r["max"], sup_s, spans)[1]) for n, r in res.items()}
        print(f"\n== {g}  (kN·m)")
        for k in ["P1", "P2", "P3", "P4"]:
            ref = REF_NEG[k] * TONF; row = [ext[n][0][k] for n, _, _ in COMBOS]
            rep.append(f"| {k} 지점 | {negD[k]:.0f} | {negL[k]:.0f} | " + " | ".join(f"{v:.0f}" for v in row) + f" | {ref:.0f} | {row[0]/ref:.2f} |")
            print(f"  {k}: D {negD[k]:8.0f} LL {negL[k]:7.0f} | I {row[0]:8.0f} II {row[1]:8.0f} III {row[2]:8.0f} IV {row[3]:8.0f} V {row[4]:8.0f} VI {row[5]:8.0f} | 정답 {ref:8.0f} | I/정답 {row[0]/ref:.2f}")
        for k in ["S1", "S2", "S3", "S4", "S5"]:
            ref = REF_POS[k] * TONF; row = [ext[n][1][k] for n, _, _ in COMBOS]
            rep.append(f"| {k} 경간 | {posD[k]:.0f} | {posL[k]:.0f} | " + " | ".join(f"{v:.0f}" for v in row) + f" | {ref:.0f} | {row[0]/ref:.2f} |")
            print(f"  {k}: D {posD[k]:8.0f} LL {posL[k]:7.0f} | I {row[0]:8.0f} II {row[1]:8.0f} III {row[2]:8.0f} IV {row[3]:8.0f} V {row[4]:8.0f} VI {row[5]:8.0f} | 정답 {ref:8.0f} | I/정답 {row[0]/ref:.2f}")
        rep.append("")
    rep += ["허용응력 증가: I 100 %, II·III·IV 125 %, V·VI 140 %. W·WL·CF·LF는 부호가 불리한 쪽으로, T는 +15/−15 중 불리한 쪽으로 더함.", ""]
    json.dump(out, open(os.path.join(RUNS, "combos_My.json"), "w", encoding="utf-8"), ensure_ascii=False)
    open(os.path.join(RUNS, "결과_하중조합_모멘트.md"), "w", encoding="utf-8").write("\n".join(rep))
    print("\n저장:", os.path.join(RUNS, "결과_하중조합_모멘트.md"))

if __name__ == "__main__":
    main()

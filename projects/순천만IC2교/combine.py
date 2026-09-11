# -*- coding: utf-8 -*-
"""
합성전(A) + 합성후 장기(B) + 합성후 단기(C, 이동하중) 결과 합산 → 주형 모멘트 포락, 정답지(단면 요약도 모멘트도) 대조
"""
import sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
PJ = r"D:\Midas\projects\순천만IC2교"
RUNS = os.path.join(PJ, "runs")
INFO = json.load(open(os.path.join(RUNS, "model_info.json"), encoding="utf-8"))
TONF = 9.80665
# 정답지: 단면 요약도(1) 모멘트도 (ton·m)
REF_NEG = {"P1": -2306.6, "P2": -3643.9, "P3": -3642.9, "P4": -2326.1}
REF_POS = {"S1": 1935.5, "S2": 547.3, "S3": 2278.3, "S4": 546.7, "S5": 1957.4}

def load_table(tag):
    p = os.path.join(RUNS, f"{tag}_beamforce.json")
    if not os.path.exists(p):
        return None
    tb = json.load(open(p, encoding="utf-8"))["SS_Table"]
    h = tb["HEAD"]
    ie, il, ip, im = h.index("Elem"), h.index("Load"), h.index("Part"), h.index("Moment-y")
    out = {}   # (load, elem, part) → My
    for r in tb["DATA"]:
        out[(r[il], int(r[ie]), r[ip][0])] = float(r[im])   # part 'I' / 'J'
    return out

def moment_line(tbl, load, girder):
    """[(s, My)] — 요소 I/J 단부 값을 위치순으로"""
    pts = []
    for e, g, s1, s2, sc in INFO["elems"]:
        if g != girder:
            continue
        for part, s in (("I", s1), ("J", s2)):
            v = tbl.get((load, e, part))
            if v is not None:
                pts.append((s, v))
    return sorted(pts)

def extremes(line, sup_s, spans):
    """지점부 최소(부모멘트), 경간 중앙부 최대(정모멘트)"""
    neg, pos = {}, {}
    for i, ss in enumerate(sup_s[1:-1], start=1):
        near = [v for s, v in line if abs(s - ss) < 0.6]
        neg[f"P{i}"] = min(near) if near else None
    for i in range(len(spans)):
        a, b = sup_s[i], sup_s[i + 1]
        inside = [v for s, v in line if a + 0.5 < s < b - 0.5]
        pos[f"S{i+1}"] = max(inside) if inside else None
    return neg, pos

def main():
    A, B, C = load_table("A_steel"), load_table("B_comp3n"), load_table("C_compn")
    sup_s, spans = INFO["sup_s"], INFO["spans"]
    ll_names = sorted({k[0] for k in C}) if C else []
    print("모델 C 하중명:", ll_names)
    ll_max = next((n for n in ll_names if "max" in n.lower()), None)
    ll_min = next((n for n in ll_names if "min" in n.lower()), None)
    report = ["# 순천만IC2교 강박스 — 주형 휨모멘트 합산 결과 (2026-09-10)", "",
              "합성전(강재단면, D1 = 강재자중×할증 + 바닥판) + 합성후 장기(n=24, D2 = 마모층+방호벽) + 합성후 단기(n=8, 활하중 DB-24 이동하중). 단위 kN·m, 괄호는 ton·m.", ""]
    for g in ("G1", "G2"):
        d1 = moment_line(A, "D1", g)
        d2 = dict(moment_line(B, "D2", g))
        # 활하중 포락: DB-24와 DL-24 중 불리한 값 (각각 max/min)
        maxes = [dict(moment_line(C, n, g)) for n in ll_names if n.endswith("(max)")]
        mins = [dict(moment_line(C, n, g)) for n in ll_names if n.endswith("(min)")]
        keys = set().union(*[m.keys() for m in maxes]) if maxes else set()
        lmax = {k: max(m.get(k, -1e18) for m in maxes) for k in keys}
        lmin = {k: min(m.get(k, 1e18) for m in mins) for k in keys}
        tot_max = [(s, v + d2.get(s, 0) + lmax.get(s, 0)) for s, v in d1]
        tot_min = [(s, v + d2.get(s, 0) + lmin.get(s, 0)) for s, v in d1]
        negD1, posD1 = extremes(d1, sup_s, spans)
        negD2, posD2 = extremes(list(d2.items()), sup_s, spans)
        negL, _ = extremes(list(lmin.items()), sup_s, spans) if lmin else ({}, {})
        _, posL = extremes(list(lmax.items()), sup_s, spans) if lmax else ({}, {})
        negT, _ = extremes(tot_min, sup_s, spans)
        _, posT = extremes(tot_max, sup_s, spans)
        report += [f"## {g}", "", "| 위치 | D1 합성전 | D2 합성후 | LL(DB-24) | 합계 | 정답지 | 비 |", "| :-- | --: | --: | --: | --: | --: | --: |"]
        print(f"\n== {g}")
        for k in ["P1", "P2", "P3", "P4"]:
            ref = REF_NEG[k] * TONF
            tot = negT[k]
            report.append(f"| {k} 지점 | {negD1[k]:.0f} | {negD2.get(k, 0):.0f} | {negL.get(k, 0) or 0:.0f} | **{tot:.0f}** ({tot/TONF:.0f}) | {ref:.0f} ({REF_NEG[k]:.0f}) | {tot/ref:.2f} |")
            print(f"  {k} 지점: D1 {negD1[k]:8.0f}  D2 {negD2.get(k,0):7.0f}  LL {negL.get(k,0) or 0:8.0f}  합 {tot:8.0f} kN·m ({tot/TONF:7.0f} t·m)  정답 {REF_NEG[k]:7.0f}  비 {tot/ref:.2f}")
        for k in ["S1", "S2", "S3", "S4", "S5"]:
            ref = REF_POS[k] * TONF
            tot = posT[k]
            report.append(f"| {k} 경간 | {posD1[k]:.0f} | {posD2.get(k, 0):.0f} | {posL.get(k, 0) or 0:.0f} | **{tot:.0f}** ({tot/TONF:.0f}) | {ref:.0f} ({REF_POS[k]:.0f}) | {tot/ref:.2f} |")
            print(f"  {k} 경간: D1 {posD1[k]:8.0f}  D2 {posD2.get(k,0):7.0f}  LL {posL.get(k,0) or 0:8.0f}  합 {tot:8.0f} kN·m ({tot/TONF:7.0f} t·m)  정답 {REF_POS[k]:7.0f}  비 {tot/ref:.2f}")
        report.append("")
        json.dump(dict(D1=d1, D2=sorted(d2.items()), LLmax=sorted(lmax.items()), LLmin=sorted(lmin.items()), tot_max=tot_max, tot_min=tot_min),
                  open(os.path.join(RUNS, f"moment_{g}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    open(os.path.join(RUNS, "결과_모멘트_대조.md"), "w", encoding="utf-8").write("\n".join(report))
    print("\n저장:", os.path.join(RUNS, "결과_모멘트_대조.md"))

if __name__ == "__main__":
    main()

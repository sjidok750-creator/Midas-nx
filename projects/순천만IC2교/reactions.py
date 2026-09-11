# -*- coding: utf-8 -*-
"""
상부 반력 집계 (하부구조 하중용) — runs/A_steel_reaction.json + runs/C_comp_reaction.json
  받침 절점(model_info.bearings)별 전역 반력을 받침 국부축(교축 x, 교축직각 y)으로 회전해 지점(A1, P1~P5)·주형(G1, G2)별 정리
  출력: runs/reactions_summary.json, runs/결과_상부반력.md
  부호: 반력은 구조물이 받는 힘(위 +). 수평력 Fx(교축, 종점 방향 +), Fy(교축직각, 좌측 +)
"""
import sys, os, json, math
sys.stdout.reconfigure(encoding="utf-8")
PJ = r"D:\Midas\projects\순천만IC2교"; RUNS = os.path.join(PJ, "runs")
INFO = json.load(open(os.path.join(RUNS, "model_info.json"), encoding="utf-8"))
SUP = ["A1", "P1", "P2", "P3", "P4", "P5"]

def load(name):
    d = json.load(open(os.path.join(RUNS, name), encoding="utf-8"))["SS_Table"]; H = d["HEAD"]
    out = {}
    for r in d["DATA"]:
        rec = dict(zip(H, r)); out.setdefault((int(rec["Node"]), rec["Load"]), [float(rec[k]) for k in ("FX", "FY", "FZ", "MX", "MY", "MZ")])
    return out

def rotate(v, ang_deg):
    """전역 (X=북, Y=동) → 국부 (x=교축 접선, y=교축직각). angle_deg는 절점 국부축 회전각(/db/skew ANGLE_Z)"""
    c, s = math.cos(math.radians(ang_deg)), math.sin(math.radians(ang_deg))
    fx, fy = v[0], v[1]
    return [c * fx + s * fy, -s * fx + c * fy, v[2]]

def main():
    A, C = load("A_steel_reaction.json"), load("C_comp_reaction.json")
    cases_A = ["DEAD", "SLAB"]; cases_C = ["SDL", "DB-24(max)", "DB-24(min)", "DL-24(max)", "DL-24(min)", "W", "WL", "LF", "CF", "TP", "TM"] + [f"SD_{s}" for s in SUP]
    cases_C += [f"{v}_{l}({m})" for v in ("DB-24", "DL-24") for l in ("L1", "L2") for m in ("max", "min")]     # 편재(1차선) 케이스 (run3 case1)
    res = {}
    for b in INFO["bearings"]:
        key = f"{b['pier']}|{b['girder']}"; rec = dict(node=b["node"], kind=b["kind"], type=b["type"], angle=b["angle_deg"], cases={})
        for cs, src in ((cases_A, A), (cases_C, C)):
            for c in cs:
                v = src.get((b["node"], c))
                if v: rec["cases"][c] = [round(x, 2) for x in rotate(v, b["angle_deg"])]
        res[key] = rec
    # 지점별 합계·요약
    summ = {}
    for s in SUP:
        g1, g2 = res.get(f"{s}|G1"), res.get(f"{s}|G2")
        if not g1 or not g2: continue
        def tot(c, i): return g1["cases"].get(c, [0, 0, 0])[i] + g2["cases"].get(c, [0, 0, 0])[i]
        D1 = tot("DEAD", 2) + tot("SLAB", 2); D2 = tot("SDL", 2)
        Lmax = max(tot("DB-24(max)", 2), tot("DL-24(max)", 2)); Lmin = min(tot("DB-24(min)", 2), tot("DL-24(min)", 2))
        # 편측(주형별) 활하중 — 편심 모멘트용
        L_g = {g: (max(r["cases"].get("DB-24(max)", [0, 0, 0])[2], r["cases"].get("DL-24(max)", [0, 0, 0])[2]), min(r["cases"].get("DB-24(min)", [0, 0, 0])[2], r["cases"].get("DL-24(min)", [0, 0, 0])[2])) for g, r in (("G1", g1), ("G2", g2))}
        # 편재(1차선): 차선 L1(G1측)/L2(G2측)만 재하했을 때 각 주형 반력 max — 같은 케이스의 두 값을 동시값으로 사용(트럭이 지점 위에 있을 때 둘 다 최대)
        def one(lane, g):
            r = g1 if g == "G1" else g2; return max(r["cases"].get(f"DB-24_{lane}(max)", [0, 0, 0])[2], r["cases"].get(f"DL-24_{lane}(max)", [0, 0, 0])[2])
        L_one = {"L1": {"G1": round(one("L1", "G1"), 1), "G2": round(one("L1", "G2"), 1)}, "L2": {"G1": round(one("L2", "G1"), 1), "G2": round(one("L2", "G2"), 1)}}
        summ[s] = dict(D1=round(D1, 1), D2=round(D2, 1), D=round(D1 + D2, 1), Lmax=round(Lmax, 1), Lmin=round(Lmin, 1), L_one=L_one,
                       D_g={"G1": round(g1["cases"]["DEAD"][2] + g1["cases"]["SLAB"][2] + g1["cases"]["SDL"][2], 1), "G2": round(g2["cases"]["DEAD"][2] + g2["cases"]["SLAB"][2] + g2["cases"]["SDL"][2], 1)},
                       L_g={g: [round(a, 1), round(b_, 1)] for g, (a, b_) in L_g.items()},
                       H={c: [round(tot(c, 0), 1), round(tot(c, 1), 1)] for c in ("W", "WL", "LF", "CF", "TP", "TM")},
                       kinds=[g1["kind"], g2["kind"]])
    json.dump(dict(bearings=res, support=summ), open(os.path.join(RUNS, "reactions_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    rep = ["# 상부구조 반력 집계 (kN, 받침 국부축: x 교축, y 교축직각)", "", "| 지점 | 받침 | 합성전 D1 | 합성후 D2 | 고정하중 D | 활하중 max | 활하중 min | G1 D | G2 D | G1 L(max/min) | G2 L(max/min) | W(x,y) | WL | LF | CF | TP | TM |", "|" + " :-- |" * 17]
    for s, v in summ.items():
        H = v["H"]; rep.append(f"| {s} | {'/'.join(v['kinds'])} | {v['D1']} | {v['D2']} | {v['D']} | {v['Lmax']} | {v['Lmin']} | {v['D_g']['G1']} | {v['D_g']['G2']} | {v['L_g']['G1'][0]}/{v['L_g']['G1'][1]} | {v['L_g']['G2'][0]}/{v['L_g']['G2'][1]} | {H['W']} | {H['WL']} | {H['LF']} | {H['CF']} | {H['TP']} | {H['TM']} |")
        print(f"{s}: D {v['D']:8.1f}  Lmax {v['Lmax']:7.1f}  Lmin {v['Lmin']:7.1f}  W {H['W']}  LF {H['LF']}  TP {H['TP']}")
    open(os.path.join(RUNS, "결과_상부반력.md"), "w", encoding="utf-8").write("\n".join(rep)); print("저장 reactions_summary.json, 결과_상부반력.md")

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
보고서 표 생성기 — 2021 초안·2024 양식의 부재력 집계표(휨모멘트·전단력·비틀림), 하중산정표, 유효폭표, 단면제원표를 markdown/JSON으로
  python tables.py
"""
import sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
PJ = r"D:\Midas\projects\순천만IC2교"; RUNS = os.path.join(PJ, "runs"); sys.path.insert(0, PJ)
import gen_model as G
from stress3 import load_table, F, INFO

def summary_positions():
    """S1~S5 중앙, P1~P4 지점 위치(s)"""
    sup, sp = INFO["sup_s"], INFO["spans"]
    pos = [(f"S{i+1}", (sup[i] + sup[i+1]) / 2) for i in range(5)]
    pos += [(f"P{i}", sup[i]) for i in range(1, 5)]
    return pos

def pick(rows_by_g, g, s0, comp, sign):
    """위치 s0 근처(±1 m)에서 comp 최대/최소인 요소단"""
    cands = [(e, part, s) for e, part, s in rows_by_g[g] if abs(s - s0) <= 1.0]
    return cands

def main():
    A, C = load_table("A_steel"), load_table("C_comp")
    names = {k[0] for k in C}
    llmax = [n for n in names if n.endswith("(max)")]; llmin = [n for n in names if n.endswith("(min)")]; sds = sorted(n for n in names if n.startswith("SD_"))
    ends = {"G1": [], "G2": []}
    for e, g, s1, s2, sc in INFO["elems"]:
        ends[g] += [(e, "I", s1), (e, "J", s2)]
    rep = ["# 부재력 집계표 (kN, kN·m) — 격자모델 v3", "", "합성전 = 강재자중(할증 1.381) + 바닥판, 합성후 = 포장층+방호벽+부속설비, 활하중 = DB-24/DL-24 포락(충격 포함), 지점침하 = 10 mm 각 지점 포락. 위치는 경간 중앙·지점 ±1 m 범위의 극값.", ""]
    out = {}
    for comp, title, unit in (("My", "휨모멘트", "kN·m"), ("Fz", "전단력", "kN"), ("Mx", "비틀림모멘트", "kN·m")):
        rep += [f"## {title} ({unit})", "", "| 위치 | 주형 | 강재자중 | 바닥판 | 합성후 고정 | 활하중 max | 활하중 min | 침하 max | 침하 min | 계 max | 계 min | 요소 |",
                "| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | :-- |"]
        for lb, s0 in summary_positions():
            for g in ("G1", "G2"):
                best = None
                for e, part, s in pick(ends, g, s0, comp, None):
                    d1 = F(A, "DEAD", e, part)[comp]; sl = F(A, "SLAB", e, part)[comp]; d2 = F(C, "SDL", e, part)[comp]
                    lmax = max(F(C, n, e, part)[comp] for n in llmax); lmin = min(F(C, n, e, part)[comp] for n in llmin)
                    smax = max([F(C, n, e, part)[comp] for n in sds] + [0]); smin = min([F(C, n, e, part)[comp] for n in sds] + [0])
                    tmax = d1 + sl + d2 + lmax + smax; tmin = d1 + sl + d2 + lmin + smin
                    key = max(abs(tmax), abs(tmin)) if lb.startswith("P") or comp != "My" else tmax
                    if best is None or key > best[0]:
                        best = (key, dict(d1=d1, sl=sl, d2=d2, lmax=lmax, lmin=lmin, smax=smax, smin=smin, tmax=tmax, tmin=tmin, e=f"{e}{part}", s=s))
                v = best[1]; out[(comp, lb, g)] = v
                rep.append(f"| {lb} | {g} | {v['d1']:.1f} | {v['sl']:.1f} | {v['d2']:.1f} | {v['lmax']:.1f} | {v['lmin']:.1f} | {v['smax']:.1f} | {v['smin']:.1f} | **{v['tmax']:.1f}** | **{v['tmin']:.1f}** | {v['e']} (s={v['s']:.1f}) |")
        rep.append("")
    # 하중 산정표
    rep += ["## 하중 산정 (주형당)", "", "| 구분 | G1 | G2 | 비고 |", "| :-- | --: | --: | :-- |",
            f"| 강재 자중 할증 | {INFO['f_steel']:.3f} | {INFO['f_steel']:.3f} | 재료표 {G.STEEL_TOTAL_KN:.0f} kN / 모델 {INFO['model_steel_kN']:.0f} kN |",
            f"| 바닥판 콘크리트 (kN/m) | {INFO['w_slab']['G1']:.2f} | {INFO['w_slab']['G2']:.2f} | RC 0.24 (캔틸레버 0.24~0.30) + 헌치, 25 kN/m³ |",
            f"| 바닥판 편심 비틀림 (kN·m/m) | {INFO['mx_slab']['G1']:.2f} | {INFO['mx_slab']['G2']:.2f} | |",
            f"| 합성후 고정하중 (kN/m) | {INFO['sdl']['G1']:.2f} | {INFO['sdl']['G2']:.2f} | 포장층 0.05×23.5 + 방호벽 9.66/10.44 + 부속설비 0.49 kN/m² |",
            f"| 합성후 편심 비틀림 (kN·m/m) | {INFO['mx_sdl']['G1']:.2f} | {INFO['mx_sdl']['G2']:.2f} | 방호벽 도심 연석에서 0.25 m |",
            f"| 풍하중 W (kN/m) | {INFO['w_wind']:.2f} | {INFO['w_wind']:.2f} | 3.0 kN/m² × 노출높이 3.6 m ÷ 2 |",
            f"| 활하중 풍하중 WL (kN/m) | {INFO['w_wl']:.2f} | {INFO['w_wl']:.2f} | 1.5 kN/m ÷ 2 |",
            f"| 원심하중 CF (kN/m) | {INFO['w_cf']:.3f} | {INFO['w_cf']:.3f} | 활하중 등분포의 3.29 % (V=50 km/h, R=600) |",
            f"| 제동하중 LF (kN/m) | {INFO['w_lf']:.3f} | {INFO['w_lf']:.3f} | 차선하중의 5 % |",
            f"| 온도변화 | ±{INFO['temp']} ℃ | | 강-바닥판 온도차 10 ℃는 응력 단계 |",
            f"| 지점침하 | {INFO['settle']*1000:.0f} mm | | A1~P5 각 지점 |", ""]
    # 유효폭
    rep += ["## 바닥판 유효폭 (도로교설계기준 강교편)", "", "| 구간 | 등가지간 l (m) | 유효폭 B (m) |", "| :-- | --: | --: |"]
    for nm, a, b, B, l in INFO["eff"]: rep.append(f"| {nm} | {l:.3f} | {B:.3f} |")
    # 단면제원
    Pl, spans, rot = G.geometry(); eff = G.eff_width_table(spans); top, bot = G.plate_segments("top"), G.plate_segments("bot")
    rep += ["", "## 단면 제원 (단면 종류별)", "", "| 단면 | 상판 (mm) | 하판 (mm) | 복부 (mm) | 종리브 상/하 | 유효폭 (m) | As (cm²) | Is (cm⁴) | Iv (cm⁴, n=8) |", "| --: | --: | --: | --: | :-- | --: | --: | --: | --: |"]
    seen = {}
    for e, g, s1, s2, sc in INFO["elems"]:
        if sc in seen: continue
        sm = (s1 + s2) / 2; tft, tfb = G.thick_at(top, sm), G.thick_at(bot, sm); neg = tft >= 0.020 - 1e-9; be = G.beff_at(eff, sm)
        st = G.steel_section(tft, tfb, G.RIB_NEG if neg else G.RIB_POS); cp = G.composite_section(st, be, 8.0); seen[sc] = 1
        rep.append(f"| {sc} | {tft*1000:.0f} | {tfb*1000:.0f} | {G.TW*1000:.0f} | {'2/5' if neg else '5/2'} | {be:.3f} | {st['A']*1e4:.1f} | {st['I33']*1e8:.0f} | {cp['I33']*1e8:.0f} |")
    open(os.path.join(RUNS, "결과_부재력집계.md"), "w", encoding="utf-8").write("\n".join(rep))
    json.dump({f"{k[0]}|{k[1]}|{k[2]}": v for k, v in out.items()}, open(os.path.join(RUNS, "forces_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("저장 결과_부재력집계.md")
    for lb, s0 in summary_positions():
        v = out[("My", lb, "G1")]; print(f"  {lb} G1 My: 합성전 {v['d1']+v['sl']:9.1f} 합성후 {v['d2']:8.1f} LL {v['lmax']:8.1f}/{v['lmin']:8.1f} 침하 {v['smax']:6.1f}/{v['smin']:6.1f} 계 {v['tmax']:9.1f}/{v['tmin']:9.1f}")

if __name__ == "__main__":
    main()

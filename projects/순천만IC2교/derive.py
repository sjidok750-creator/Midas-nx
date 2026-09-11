# -*- coding: utf-8 -*-
"""
풀이과정 문장 생성기 — 계산기 결과 JSON(runs/abutment/A1_v3_result.json, runs/pier3/P*_result.json)에서 편람 예제 형식의 '식 = 대입 = 결과' 문장을 만든다.
  보고서 본문(요약 표 아래)과 엑셀 부록(근거 시트)에서 함께 쓴다. 출력: dict(section → [문장])
"""
import json, os, math
PJ = r"D:\Midas\projects\순천만IC2교"; RUNS = os.path.join(PJ, "runs")
SUB = json.load(open(os.path.join(PJ, "하부_제원서.json"), encoding="utf-8")); CB = json.load(open(os.path.join(PJ, "combos_2010.json"), encoding="utf-8"))
f = lambda x, n=2: f"{x:,.{n}f}"

def abutment_lines(A):
    g, c, s, pl, cases, info = A["geom"], A["cond"], A["section"], A["piles"], A["cases"], A["info"]; soil = A["soil"]; ps = A["pile_spec"]
    phi, gam, q = soil["phi"], soil["gamma"], soil["q"]; H = g["z_top"]; Hw, Hp = g["Hw"], g["Hp"]
    L = {}
    L["step4"] = [f"안정검토 토압계수(Rankine) Ka = tan²(45° − φ/2) = tan²(45 − {phi:.0f}/2) = {c['Ka_stab']:.3f}",
                  f"단면검토 토압계수(Coulomb, δ = φ/3 = {c['delta_wall']:.1f}°, α = β = 0) Ka = cos²φ / [cosδ·(1 + √(sin(φ+δ)·sinφ / cosδ))²] = {c['Ka_wall']:.3f}",
                  f"상부반력 단위폭 환산: 고정하중 R_D = {f(SUB['교대']['A1']['폭'] * c['D'])} / {g['LW']} = {f(c['D'])} kN/m, 활하중 R_L = {f(c['LL'] * g['LW'])} / {g['LW']} = {f(c['LL'])} kN/m",
                  f"받침 수평력(온도·마찰) FR = 0.15 × R_D = 0.15 × {f(c['D'])} = {f(info['FR'])} kN/m"]
    L["step5"] = [f"배면 토압 Pa = ½·Ka·γ·H² = ½ × {c['Ka_stab']:.3f} × {gam} × {H:.3f}² = {f(info['Pa'])} kN/m, 작용점 H/3 = {H/3:.3f} m",
                  f"상재하중 토압 Pq = Ka·q·H = {c['Ka_stab']:.3f} × {q} × {H:.3f} = {f(info['Pq'])} kN/m, 작용점 H/2 = {H/2:.3f} m",
                  f"뒷굽 위 상재하중 = q × 뒷굽 = {q} × {g['heel']} = {f(q * g['heel'])} kN/m"]
    for k, v in cases.items():
        L["step5"].append(f"{k}: ΣV = {f(v['V'])}, ΣH = {f(v['H'])}, Mr = {f(v['Mr'])}, Mo = {f(v['Mo'])} → ξ = (Mr − Mo)/ΣV = ({f(v['Mr'])} − {f(v['Mo'])})/{f(v['V'])} = {v['xi']:.3f} m, e = B/2 − ξ = {g['B']/2:.3f} − {v['xi']:.3f} = {v['e']:.3f} m")
    n = pl["n"]; Sx2 = pl["Sx2"]
    L["step6"] = [f"말뚝 유효단면 Ae = π/4·[D² − (D − 2t')²] = π/4·[{ps['D']*1000:.0f}² − ({ps['D']*1000:.0f} − 2×{(ps['t']-ps['corr'])*1000:.0f})²] = {pl['Ap']*1e6:,.0f} mm² (부식 2 mm 공제), Ra = Ae × 140 MPa = {f(pl['Ra'], 0)} kN",
                  f"Σx² = {ps['per_row']} × Σ(x_i − B/2)² = {ps['per_row']} × Σ({', '.join(f'{r - g['B']/2:+.2f}' for r in ps['rows_from_toe'])})² = {Sx2:.3f} m²"]
    for k, v in pl["cases"].items():
        L["step6"].append(f"{k}: V = {f(v['V'], 0)} kN(전폭), M = V·e = {f(v['V'], 0)} × {v['e']:.3f} = {f(v['M'], 0)} kN·m → R_i = V/n ± M·x_i/Σx² = {f(v['V'], 0)}/{n} ± {f(v['M'], 0)}·x_i/{Sx2:.3f} → " + ", ".join(f"{kk} {f(x, 0)}" for kk, x in v["R"].items()) + f" kN; 수평 H/n = {f(v['H'], 0)}/{n} = {v['Hp']:.1f} kN/본; f = R_max/Ae = {v['f']:.1f} MPa ≤ 140")
    st, pa, ft, hz = s["stem"], s["parapet"], s["footing"], s["horiz"]
    L["step7"] = [f"벽체 계산높이 H = {Hw:.3f} m(기초 상면~노면). 토압 = ½·Ka·γ·H²·cosδ = ½ × {c['Ka_wall']:.3f} × {gam} × {Hw:.3f}² × cos{c['delta_wall']:.1f}° = {f(st['rows'][1]['V'])} kN/m (팔길이 H/3 = {Hw/3:.3f})",
                  f"노면하중 토압 = Ka·q·H·cosδ = {c['Ka_wall']:.3f} × {q} × {Hw:.3f} × cos{c['delta_wall']:.1f}° = {f(st['rows'][2]['V'])} kN/m (팔길이 H/2 = {Hw/2:.3f})",
                  f"Mu = 1.3 × {f(st['rows'][0]['M'])} + 1.7 × ({f(st['rows'][1]['M'])} + {f(st['rows'][2]['M'])}) = {f(st['Mu'])} kN·m/m, Vu = 1.3 × {f(st['rows'][0]['V'])} + 1.7 × ({f(st['rows'][1]['V'])} + {f(st['rows'][2]['V'])}) = {f(st['Vu'])} kN/m",
                  f"φMn = φ·As·fy·(d − a/2), a = As·fy/(0.85·fck·b) = {st['As']:.0f} × 300 / (0.85 × 24 × 1000) = {st['As']*300/(0.85*24*1000):.1f} mm → φMn = 0.85 × {st['As']:.0f} × 300 × ({st['d']:.0f} − {st['As']*300/(0.85*24*1000)/2:.1f}) × 10⁻⁶ = {f(st['phiMn'], 1)} kN·m/m → Mu/φMn = {st['ratio_M']:.3f}",
                  f"φVc = 0.80 × (√fck/6)·b·d = 0.80 × (√24/6) × 1000 × {st['d']:.0f} × 10⁻³ = {f(st['phiVc'], 1)} kN/m → Vu/φVc = {st['ratio_V']:.3f}",
                  f"흉벽(h = {Hp:.3f} m): 토압 ½·Ka·γ·h²·cosδ = {f(pa['rows'][0]['V'])} kN/m; 상재 Ka·q·h·cosδ = {f(pa['rows'][1]['V'])}; 윤하중 P(x) = Ka·T/((a+x)(b+x)), T = 96 kN, a = 0.2, b = 0.5 m, 0~1 m 적분 후 1.5 m 분포 → {f(pa['wheel']['F'])} kN/m, 작용점 지표 아래 {pa['wheel']['z']:.3f} m",
                  f"흉벽 경우 A(토압+상재): Mu = 1.7 × ({f(pa['rows'][0]['M'])} + {f(pa['rows'][1]['M'])}) = {f(pa['MuA'])} → Mu/φMn = {pa['ratio_MA']:.3f}; 경우 B(토압+윤하중): Mu = 1.7 × ({f(pa['rows'][0]['M'])} + {f(pa['rows'][2]['M'])}) = {f(pa['Mu'])} → {pa['ratio_M']:.3f} (φMn = {f(pa['phiMn'], 1)}, {pa['bar']}, d = {pa['d']:.0f} mm)",
                  f"기초(계수하중 1.3D + 2.15L + 1.7H): 말뚝 반력 본당 {', '.join(f(x, 0) for x in ft['Ru'])} kN (e = {ft['e']:.3f} m) → 단위폭 열 반력 {', '.join(f(x, 1) for x in ft['Rm'])} kN/m",
                  f"앞굽 Mu = ΣR_열·팔길이 − 1.3·자중 = {f(ft['toe']['Mu'], 1)} kN·m/m, 뒷굽 Mu = 1.3·(흙+자중)·팔 + 2.15·상재 − ΣR·팔 = {f(ft['heel']['Mu'], 1)} kN·m/m; φMn({ft['bar']}, d = {ft['d']:.0f}) = {f(ft['phiMn'], 1)} → 비 {ft['toe']['ratio_M']:.3f} / {ft['heel']['ratio_M']:.3f}",
                  s.get("shear_note", "") + f"; 앞굽 Vu = {f(ft['toe']['Vu'], 1)}, 뒷굽 Vu = {f(ft['heel']['Vu'], 1)} kN/m vs φVc = {f(ft['phiVc'], 1)}",
                  f"수평철근: {hz['bar']} 양면 As = {hz['As']:.0f} mm²/m ≥ 0.0015·b·h = 0.0015 × 1000 × {min(g['stem'], 1.2)*1000:.0f} = {hz['req']:.0f} mm²/m"]
    return L

def pier_lines(r):
    g, cp, col, fd, brg = r["geom"], r["coping"], r["column"], r["footing"], r["bearing"]; w = col["worst"]; rx = r["loads_info"]
    L = {}
    L["coping"] = [f"위험단면: 기둥면. 팔길이 av = 받침 간격/2 − 기둥 폭/2 = {g['s_brg']/2:.3f} − {g['by']/2:.3f} = {cp['av']:.3f} m, d = h − 피복 = {cp['h']:.3f} − 0.150 = {cp['d']:.3f} m → av/d = {cp['av_d']:.3f} ≤ 1.0 → 브래킷",
                   f"Vu = 1.3·R_D + 2.15·R_L(받침 1개 최대) = {f(cp['Vu'], 0)} kN, Nuc = 0.2·Vu = {f(cp['Nuc'], 0)} kN, Mu = Vu·av + Nuc·(h − d) = {f(cp['Vu'], 0)} × {cp['av']:.3f} + {f(cp['Nuc'], 0)} × {cp['h'] - cp['d']:.3f} = {f(cp['Mu'], 0)} kN·m",
                   f"φVn,max = 0.80 × min(0.2·fck·b·d, 5.6·b·d) = {f(cp['phiVn_max'], 0)} kN ≥ Vu → {'O.K' if cp['ok_Vn'] else 'N.G'}; 전단마찰철근 Avf = Vu/(φ·fy·μ) = {f(cp['Vu'], 0)}×10³/(0.80 × 300 × 1.4) = {f(cp['Avf'], 0)} mm²",
                   f"휨철근 Af = {f(cp['Af'], 0)} mm² (Mu/φ = Af·fy·(d − a/2)), An = Nuc/(φ·fy) = {f(cp['Nuc'], 0)}×10³/(0.85 × 300) = {f(cp['An'], 0)} mm² → As,req = max(Af + An, 2Af/3 + An) = {f(cp['As_req'], 0)} mm²; As,min = 0.04·(fck/fy)·b·d = {f(cp['As_min'], 0)} mm²",
                   f"사용 As = {f(cp['As_use'], 0)} mm² (코핑 주철근 {r['rebar']['코핑_주철근']}) → As,req/As = {cp['ratio_As']:.3f}, As,min/As = {cp['ratio_Asmin']:.2f}; 폐쇄띠철근 Ah,req = 0.5(As,req − An) = {f(cp['Ah_req'], 0)} vs 사용 {f(cp['Ah_use'], 0)} mm²"]
    L["column"] = [f"세장비 λ = k·Lu/r, k = 2.1(캔틸레버), Lu = {col['Lu']} m, r = h/√12 → 교축 {col['lambda_x']:.1f}, 교축직각 {col['lambda_y']:.1f} ≥ 22 → 장주(모멘트확대 적용)",
                   f"최불리 조합 {w['key']} ({'교축' if w['dirn'] == 'x' else '교축직각'}): Pu = {f(w['P'], 0)} kN, Mu = {f(w['M'], 0)} kN·m, βd = {w['bd']:.3f}, Pc = π²·(0.4·Ec·Ig/(1+βd))/(k·Lu)² = {f(w['Pc'], 0)} kN → δs = 1/(1 − Pu/0.75Pc) = {w['ds']:.3f}, δs·Mu = {f(w['Mmag'], 0)} kN·m",
                   f"P–M 상관도(φ = 0.70, As = {f(col['As'], 0)} mm², ρ = {col['rho']*100:.2f} %)에서 Pu = {f(w['P'], 0)} kN일 때 φMn = {f(w['Mmag']/w['ratio'], 0)} kN·m → δs·Mu/φMn = {w['ratio']:.3f}",
                   f"전단: Vu = {f(col['shear']['Vu'], 0)} kN ({col['shear']['key']}), φVc = 0.80·(√fck/6)·b·d = {f(col['shear']['phiVc'], 0)} kN, φ(Vc+Vs) = {f(col['shear']['phiVn'], 0)} kN (띠철근 D16@300) → {col['shear']['ratio']:.3f}"]
    sec = fd["section"]
    L["footing"] = [f"말뚝 축방향 스프링정수 Kv = a·Ap·Ep/L, a = 0.014(L/D) + 0.78 = {fd['a']:.3f}, Ap = {fd['Ap']*1e6:,.0f} mm², Ep = 210,000 MPa, L = {g['piles']['길이']} m → Kv = {f(fd['Kv'], 0)} kN/m",
                    f"기초 강체판정: kp = Kv·n/(L·B) = {f(fd['kp'], 0)} kN/m³, β = (3kp/(E·h³))^0.25 = {fd['beta']:.3f} m⁻¹, λ = {fd['lam']:.3f} m → βλ = {fd['beta_lam']:.3f} ≤ 1.0 → {'O.K' if fd['rigid'] else 'N.G'}",
                    f"말뚝 반력(사용조합 {fd['pile_max_key']}): R = V/n ± My·x/Σx² ± Mx·y/Σy² → 최대 {f(fd['pile_max'], 0)} kN, 최소 {f(fd['pile_min'], 0)} kN, 수평 {f(fd['pile_h'], 0)} kN/본; Ra = Ae × 140 = {f(fd['Ra'], 0)} kN → R/Ra = {fd['ratio_pile']:.3f}",
                    f"기초 단면({sec['dirn']} 방향, {sec['key']}): 기둥면 바깥 말뚝열 반력 {', '.join(f(x, 0) for x in sec['R'])} kN, 캔틸레버 길이 {sec['lc']:.3f} m → Mu = ΣR·팔 − 1.3·자중·lc²/2 = {f(sec['Mu'], 0)} kN·m, φMn({sec['bar']}, As = {f(sec['As'], 0)} mm², d = {sec['d']:.0f}) = {f(sec['phiMn'], 0)} → {sec['ratio_M']:.3f}; Vu = {f(sec['Vu'], 0)} vs φVc = {f(sec['phiVc'], 0)} → {sec['ratio_V']:.3f}"]
    L["bearing"] = [f"받침 {brg['ton']}톤 = {f(brg['cap'], 0)} kN ≥ (R_D + R_L)max/받침 = {f(brg['R'], 0)} kN → 용량비 {brg['ratio']:.2f}"]
    return L

if __name__ == "__main__":
    import sys; sys.stdout.reconfigure(encoding="utf-8")
    A = json.load(open(os.path.join(RUNS, "abutment", "A1_v3_result.json"), encoding="utf-8"))
    for k, v in abutment_lines(A).items(): print("##", k); [print(" -", x) for x in v]
    P3 = json.load(open(os.path.join(RUNS, "pier3", "P3_result.json"), encoding="utf-8"))
    for k, v in pier_lines(P3).items(): print("##", k); [print(" -", x) for x in v]

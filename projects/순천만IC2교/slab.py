# -*- coding: utf-8 -*-
"""
바닥판 안전성 계산기 (강도설계법) — 캔틸레버부(좌·우) · 내측 중앙부(하면인장·상면인장)
근거 : 구조계산서 pp.7450~7469 산정 방식, 도로교설계기준(2010) 바닥판 활하중 분포폭·충격, 콘크리트구조기준 휨강도
       2021 보고서(순천만IC1교) 양식의 하중조합 ①~④ (충돌·풍·원심 포함) 재현
입력 : 슬래브 일반도·배근도(캔틸레버 상면 S1 H19@125, 내측 하면 B1 H19@125, 피복 상 60 / 하 40 mm), 방호벽 치수(계산서 p.7450)
현장자료 없음 → 도면값 적용 (대표님 지시 2026-09-10)
단위 : kN, m, MPa (내부 계산은 tonf 항목표를 9.80665 로 환산)
"""
import sys, os, json, math
sys.stdout.reconfigure(encoding="utf-8")
RUNS = r"D:\Midas\projects\순천만IC2교\runs"
TONF = 9.80665
FCK, FY, PHI = 27.0, 400.0, 0.85               # MPa
G_RC, G_PAVE = 25.0, 23.5                      # kN/m³
PR = 96.0                                      # DB-24 후륜 (kN)
V_KMH, R_M = 50.0, 600.0                       # 설계속도(계산서 원심하중 CF 3.29 % 역산), 교량구간 곡선반경(종평면도 R=600)
H_CF = 1.8                                     # 원심하중 작용높이 (m, 노면 위)
H_BARRIER = 0.97 + 0.35                        # 방호벽 높이 (본체 0.97 + 기부 0.35) = 충돌하중 팔길이 (m) — 확인 필요(계산서 p.7452)
H_WIND = H_BARRIER + 0.107                     # 풍하중 수압면 높이 (방호벽 + 바닥판 단부) (m)
P_WIND = 3.0                                   # 풍하중 (kN/m²)
BAR = {"H13": 1.267e-4, "H16": 1.986e-4, "H19": 2.865e-4, "H22": 3.871e-4}   # m²/본

def As_per_m(bar, spacing_mm): return BAR[bar] / (spacing_mm / 1000)      # m²/m

def flex(As, d, b=1.0):
    a = As * FY / (0.85 * FCK * b)               # m
    return a, PHI * As * FY * (d - a / 2) * 1000  # kN·m/m

def cf_percent(): return 0.79 * V_KMH ** 2 / R_M   # 도로교설계기준 원심하중 CF = 0.79 V²/R (%)

def collision():
    """차량충돌하중 H (kN/m): 도로교표준시방서 (V/60)²×750+250 kgf/m, 최소 1.0 tonf/m (2021 보고서 방식)"""
    h1 = ((V_KMH / 60) ** 2 * 750 + 250) / 1000 * TONF; h2 = 1.0 * TONF
    return h1, h2, max(h1, h2)

def cantilever(side):
    """캔틸레버부. 고정하중 항목: 계산서 p.7451(좌)/p.7457(우) 도면 치수 기준 (tonf, m). 난간 0.1 tonf/m는 우측"""
    items = [("방호벽 본체 0.23×0.97", "0.23×0.97×2.5", 0.23 * 0.97 * 2.5, 0.995), ("방호벽 경사부 ½×0.07×0.97", "1/2×0.07×0.97×2.5", 0.5 * 0.07 * 0.97 * 2.5, 0.857),
             ("방호벽 기부 0.30×0.35", "0.3×0.35×2.5", 0.30 * 0.35 * 2.5, 0.960), ("헌치 ½×0.12×0.175", "1/2×0.12×0.175×2.5", 0.5 * 0.12 * 0.175 * 2.5, 0.770),
             ("연석 0.12×0.175", "0.12×0.175×2.5", 0.12 * 0.175 * 2.5, 0.750), ("바닥판 1.14×0.24", "1.14×0.24×2.5", 1.14 * 0.24 * 2.5, 0.570),
             ("바닥판 변단면 ½×1.03×0.107", "1/2×1.03×0.107×2.5", 0.5 * 1.03 * 0.107 * 2.5, 0.453), ("바닥판 단부 0.11×0.107", "0.11×0.107×2.5", 0.11 * 0.107 * 2.5, 0.055),
             ("포장층 0.69×0.05 (2.35)", "0.69×0.05×2.35", 0.69 * 0.05 * 2.35, 0.345), ("난간", "", 0.1 if side == "R" else 0.0, 0.995)]
    Wd = sum(w for _, _, w, a in items) * TONF; Md = sum(w * a for _, _, w, a in items) * TONF          # kN/m, kN·m/m
    X = 0.39; E = 0.8 * X + 1.14; i0 = 15 / (40 + X); i = min(i0, 0.3)   # 계산서 p.7451: 윤하중 위치 X, 분포폭 E, 충격
    Ml_i = PR / E * X * (1 + i)
    h1, h2, H = collision(); Mco = H * H_BARRIER
    Pw = P_WIND * H_WIND; Mw = Pw * H_WIND / 2
    cf = cf_percent(); Pcf = PR / E * cf / 100; Mcf = Pcf * H_CF
    Mu1 = 1.3 * Md + 2.15 * Ml_i + 1.3 * Mcf; Mu2 = 1.3 * Md + 1.3 * Ml_i + 1.3 * Mcf + 1.3 * Mco
    Mu3 = 1.3 * Md + 1.3 * Ml_i + 1.3 * Mcf + 0.65 * Mw; Mu4 = 1.2 * Md + 1.2 * Mw + 1.2 * Mco
    Mu = max(Mu1, Mu2, Mu3, Mu4); gov = [Mu1, Mu2, Mu3, Mu4].index(Mu) + 1
    As = As_per_m("H19", 125); h = 0.300; dc = 0.060; d = h - dc; a, Mn = flex(As, d)
    return dict(name=f"캔틸레버부({'좌' if side == 'L' else '우'})", items=items, Wd=Wd, Md=Md, X=X, E=E, i0=i0, i=i, Ml_i=Ml_i,
                H1=h1, H2=h2, H=H, Mco=Mco, Pw=Pw, Mw=Mw, cf=cf, Pcf=Pcf, Mcf=Mcf, Mu1=Mu1, Mu2=Mu2, Mu3=Mu3, Mu4=Mu4, Mu=Mu, gov=gov,
                bar="H19@125", As=As, d=d, dc=dc, a=a, phiMn=Mn, SF=Mn / Mu, RF=(Mn - 1.3 * Md - 1.3 * Mcf) / (2.15 * Ml_i), h=h)

def interior(face="bot"):
    """내측 중앙부 (계산서 p.7462): 계산지간 L=2.15 m, 연속판 n=3, Md = wL²/10, Ml = (L+0.6)/9.6·P·(1+i)·0.8
    face='bot' 하면인장(B1 H19@125, 피복 40) / 'top' 상면인장(S1 H19@125, 피복 60)"""
    L = 2.15; t = 0.28; w_rc = t * G_RC; w_pv = 0.05 * G_PAVE; w = w_rc + w_pv
    Md = w * L ** 2 / 10
    i0 = 15 / (40 + L); i = min(i0, 0.3); Ml0 = (L + 0.6) / 9.6 * PR * (1 + i); Ml_i = Ml0 * 0.8
    cf = 0.79 * V_KMH ** 2 / R_M * 0.0 if False else cf_percent(); Pcf = PR / (L + 0.6) * cf / 100 * 0.0   # 내측: 원심 영향 미소 (2021: 0.002 tonf·m) → 0 처리
    Mcf = 0.0
    Mu = 1.3 * Md + 2.15 * Ml_i + 1.3 * Mcf
    h = 0.240; dc = 0.040 if face == "bot" else 0.060; d = h - dc; As = As_per_m("H19", 125); a, Mn = flex(As, d)
    return dict(name="내측 중앙부" + ("" if face == "bot" else "(상면인장)"), t=t, w_rc=w_rc, w_pv=w_pv, w=w, L=L, Md=Md, i0=i0, i=i, Ml0=Ml0, Ml_i=Ml_i, cf=cf, Mcf=Mcf, Mu=Mu,
                bar="H19@125", As=As, d=d, dc=dc, a=a, phiMn=Mn, SF=Mn / Mu, RF=(Mn - 1.3 * Md) / (2.15 * Ml_i), h=h)

def grade(sf): return "A" if sf > 1.0 else ("C" if sf >= 0.9 else ("D" if sf >= 0.75 else "E"))

def main():
    res = [cantilever("L"), cantilever("R"), interior("bot"), interior("top")]
    rep = ["# 바닥판 안전성 검토 (강도설계법)", "", "Mu = max(①1.3Md+2.15(Ml+I)+1.3Mcf, ②1.3Md+1.3(Ml+I)+1.3Mcf+1.3Mco, ③1.3Md+1.3(Ml+I)+1.3Mcf+0.65Mw, ④1.2Md+1.2Mw+1.2Mco), φMn = φ·As·fy·(d − a/2), φ=0.85, fck 27 MPa, fy 400 MPa.",
           f"철근: 캔틸레버 상면 H19@125 (d=240), 내측 하면 H19@125 (d=200), 내측 상면 H19@125 (d=180) — 슬래브 배근도 S1/B1. V={V_KMH:.0f} km/h, R={R_M:.0f} m, 충돌 팔길이 {H_BARRIER:.3f} m(확인 필요).", "",
           "| 구분 | Md (kN·m/m) | Ml(1+i) | Mco | Mw | Mcf | Mu (지배) | As (cm²/m) | d (mm) | φMn | SF | 기본내하율 RF | 등급 |", "| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | :-- |"]
    for r in res:
        rep.append(f"| {r['name']} | {r['Md']:.2f} | {r['Ml_i']:.2f} | {r.get('Mco', 0):.2f} | {r.get('Mw', 0):.2f} | {r['Mcf']:.2f} | {r['Mu']:.2f} (①~④ 중 {r.get('gov', 1)}) | {r['As']*1e4:.2f} | {r['d']*1000:.0f} | {r['phiMn']:.2f} | {r['SF']:.2f} | {r['RF']:.3f} | {grade(r['SF'])} |")
        print(f"{r['name']:14s} Md {r['Md']:6.2f} Ml+i {r['Ml_i']:6.2f} Mu {r['Mu']:7.2f} (조합 {r.get('gov', 1)}) φMn {r['phiMn']:7.2f} SF {r['SF']:.2f} RF {r['RF']:.3f}")
    rep += ["", "### 캔틸레버 고정하중 산정 (tonf/m, 팔길이 m — 도면 치수)", "", "| 항목 | 하중 | 팔길이 | 모멘트 |", "| :-- | --: | --: | --: |"]
    for nm, ex, w, a in res[1]["items"]: rep.append(f"| {nm} | {w:.3f} | {a:.3f} | {w*a:.3f} |")
    json.dump(res, open(os.path.join(RUNS, "slab_result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(RUNS, "결과_바닥판.md"), "w", encoding="utf-8").write("\n".join(rep)); print("저장 결과_바닥판.md")

if __name__ == "__main__":
    main()

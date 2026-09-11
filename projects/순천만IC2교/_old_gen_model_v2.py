# -*- coding: utf-8 -*-
"""
순천만IC 2교 강박스(A1~P5) 2주형 격자모델 생성기 v2 — MCT 2종 (2026-09-10 대표님 결정 반영)
  A_steel : 합성전 (강재단면)          DEAD(강재자중×할증) + SLAB(바닥판 콘크리트)
  C_comp  : 합성후 (합성단면, n=8)     SDL(포장층+방호벽) + W + WL + CF + LF + TP/TM (+ 이동하중 L+I는 API JSON으로)
합성전·후 강성이 다르므로 모델을 나누고, 조합은 파이썬(combine2.py)에서 한다.

근거
  - 제원: 제원서.json(준공도면) + 확인표 답변(2026-09-10)
  - 단면: 구조계산서 pp.7484~7497 방식 (리브 포함, K = 4bk²hk²/(2hk/tw + bk/tu + bk/tl)), 단면-2와 대조 검증
  - 유효폭: 도로교설계기준(2005) 강교편 플랜지 유효폭 — b/l ≤ 0.02: λ=b, 0.02<b/l<0.30: λ={1.06−3.2(b/l)+4.5(b/l)²}b, ≥0.30: 0.15l
            등가지간 단부경간 0.8L, 내측경간 0.6L, 지점부 0.2(L1+L2). B = 2λ(b=1.0)+0.24 + λ(b1=0.955) + λ(b2=1.08) + h(0.06)
  - 하중: 하중_하중조합_계획.md (계산서 p.7445, 7451~7457; 도로교설계기준 2005)
  - 받침: 교량받침 배치도 SHOE 좌표(받침좌표.json) → 주형별 종류. 국부축(접선) 각도는 model_info에 저장, run2.py가 API로 부여
"""
import sys, os, math, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\Midas\tools")

PJ = r"D:\Midas\projects\순천만IC2교"
OUT = os.path.join(PJ, "runs")
SPEC = json.load(open(os.path.join(PJ, "제원서.json"), encoding="utf-8"))
SHOES = json.load(open(os.path.join(PJ, "받침좌표.json"), encoding="utf-8"))   # [(종류, X(북), Y(동))] mm

# ───────── 기본 제원 ─────────
H_WEB   = 2.300          # 복부 높이 (계산서 단면-2~7, 강재재료표 복부판 2300)
BF      = 2.240          # 플랜지 폭 (계산서 b3 = 224 cm)
TW      = 0.012          # 복부 두께 (단면 요약도: 전장 12 mm)
WEB_SP  = 2.000          # 복부 간격
RIB     = (0.150, 0.014) # 종리브 150×14
RIB_POS = (5, 2)         # 정모멘트부 (상 5, 하 2)
RIB_NEG = (2, 5)         # 부모멘트부 (상 2, 하 5)
TC, TH  = 0.240, 0.060   # 바닥판 구조두께, 헌치 (계산서)
T_SLAB  = 0.300          # 바닥판 총두께 = 0.25 RC + 0.05 포장층
T_PAVE  = 0.050          # 포장층(콘크리트 마모층) 두께
B_DECK  = 8.670
N_SHORT = 8.0            # Es/Ec (계산서 n=8) — 합성후 모델 1개(대표님 결정)
ES      = 2.1e8          # kN/m²
G_RC, G_PAVE, G_STEEL = 25.0, 23.5, 78.5    # kN/m³
BARRIER = {"G1": 9.66, "G2": 10.44}          # kN/m — 계산서 p.7451/7457 방호벽 항목 1~5 (우측 난간 0.1 tonf/m 포함)
STEEL_TOTAL_KN = 902129.2 * 9.80665 / 1000  # 강재재료표(22) GRAND TOTAL
XBEAM_SP = 5.0
MAX_ELEM = 2.5
# 부가하중 (계획서 2절, 확인 완료)
WIND_P, WIND_H = 3.0, 2.3 + 0.3 + 1.0        # kN/m², 노출높이 (박스+바닥판+방호벽)
WL_TOTAL = 1.5                                # kN/m (활하중 풍하중, 교량 전체)
CF_RATIO = 0.0329                             # 원심하중 = 활하중의 3.29 % (계산서 p.7452, V=50 km/h, R=600)
DL_LANE_W = 12.7                              # DL-24 등분포 (kN/m/차선)
LF_RATIO = 0.05                               # 제동하중 = 차선하중의 5 %
TEMP = 15.0                                   # 온도변화 ±15 ℃

# ───────── 유효폭 ─────────
LAM_LIMIT = 0.02
def lam(b, l):
    r = b / l
    if r <= LAM_LIMIT: return b
    if r < 0.30: return (1.06 - 3.2 * r + 4.5 * r * r) * b
    return 0.15 * l

def eff_width_table(spans):
    b1, b2, h = 0.955, 1.080, TH
    flange_eff = lambda l: 2 * lam(WEB_SP / 2, l) + 2 * 0.120
    n = len(spans); cum = [0.0]
    for L in spans: cum.append(cum[-1] + L)
    tbl = []
    for i, L in enumerate(spans):
        l = (0.8 if i in (0, n - 1) else 0.6) * L
        tbl.append((f"S{i+1}mid", cum[i], cum[i + 1], round(flange_eff(l) + lam(b1, l) + lam(b2, l) + h, 3), round(l, 3)))
    for i in range(1, n):
        l = 0.2 * (spans[i - 1] + spans[i])
        a, b = cum[i] - 0.2 * spans[i - 1], cum[i] + 0.2 * spans[i]
        tbl.append((f"P{i}sup", a, b, round(flange_eff(l) + lam(b1, l) + lam(b2, l) + h, 3), round(l, 3)))
    return tbl

def beff_at(tbl, s):
    for nm, a, b, B, l in tbl:
        if nm.endswith("sup") and a <= s <= b: return B
    for nm, a, b, B, l in tbl:
        if nm.endswith("mid") and a <= s <= b: return B
    return tbl[0][3]

# ───────── 단면 (계산서 방식) ─────────
def steel_section(tft, tfb, ribs):
    nt, nb = ribs; rw, rt = RIB
    parts = [(BF * tft, H_WEB / 2 + tft / 2, BF * tft ** 3 / 12),
             (nt * rw * rt, H_WEB / 2 - rw / 2, nt * rt * rw ** 3 / 12),
             (2 * H_WEB * TW, 0.0, 2 * TW * H_WEB ** 3 / 12),
             (nb * rw * rt, -H_WEB / 2 + rw / 2, nb * rt * rw ** 3 / 12),
             (BF * tfb, -H_WEB / 2 - tfb / 2, BF * tfb ** 3 / 12)]
    A = sum(p[0] for p in parts); ys = sum(p[0] * p[1] for p in parts) / A
    I33 = sum(p[2] + p[0] * (p[1] - ys) ** 2 for p in parts)
    I22 = tft * BF ** 3 / 12 + tfb * BF ** 3 / 12 + 2 * (H_WEB * TW ** 3 / 12 + H_WEB * TW * (WEB_SP / 2 + TW / 2) ** 2)
    bk = WEB_SP + TW; hk = H_WEB + tft / 2 + tfb / 2
    K = 4 * bk ** 2 * hk ** 2 / (2 * hk / TW + bk / tft + bk / tfb)
    return dict(A=A, ys=ys, I33=I33, I22=I22, K=K, Asz=2 * H_WEB * TW, Asy=BF * (tft + tfb), tft=tft, tfb=tfb)

def composite_section(st, beff, n):
    Ac = beff * TC; Av = st["A"] + Ac / n
    dv = H_WEB / 2 - st["ys"] + TH + TC / 2
    dvc = dv * st["A"] / Av; dvs = dv - dvc
    Iv33 = st["I33"] + beff * TC ** 3 / 12 / n + st["A"] * dvs ** 2 + Ac / n * dvc ** 2
    Iv22 = st["I22"] + beff ** 3 * TC / 12 / n
    tcu = st["tft"] + TC / n; bk = WEB_SP + TW; hk = H_WEB + st["tft"] / 2 + st["tfb"] / 2
    K = 4 * bk ** 2 * hk ** 2 / (2 * hk / TW + bk / tcu + bk / st["tfb"])
    return dict(A=Av, I33=Iv33, I22=Iv22, K=K, Asz=st["Asz"], Asy=st["Asy"] + Ac / n, dvs=dvs, dvc=dvc, Ac=Ac, n=n)   # dvs: 강재도심→합성도심(위로 +), dvc: 합성도심→바닥판도심

def xbeam_section():
    bf, tf, hw, tw = 0.300, 0.012, 1.200, 0.012
    A = 2 * bf * tf + hw * tw
    I33 = 2 * (bf * tf ** 3 / 12 + bf * tf * (hw / 2 + tf / 2) ** 2) + tw * hw ** 3 / 12
    I22 = 2 * tf * bf ** 3 / 12 + hw * tw ** 3 / 12
    return dict(A=A, I33=I33, I22=I22, K=(2 * bf * tf ** 3 + hw * tw ** 3) / 3, Asz=hw * tw, Asy=2 * bf * tf)

def check_sections():
    st = steel_section(0.012, 0.012, RIB_POS); cp = composite_section(st, 4.335, 8.0)
    ref = [("As", st["A"], 1236.6e-4), ("I33", st["I33"], 11282040.8e-8), ("I22", st["I22"], 7834389.8e-8), ("K", st["K"], 12010391.6e-8),
           ("Iv33", cp["I33"], 21652621.9e-8), ("Iv22", cp["I22"], 28200463.6e-8), ("Kv", cp["K"], 14404094.4e-8)]
    ok = all(abs(a - b) / b < 0.01 for _, a, b in ref)
    print("단면 검증(계산서 단면-2):", "일치" if ok else "★차이", [f"{n} {(a-b)/b*100:+.2f}%" for n, a, b in ref])
    return ok

# ───────── 기하 ─────────
def geometry():
    sup = SPEC["supports"]; order = ["A1", "P1", "P2", "P3", "P4", "P5"]
    P = [(sup[k]["Y"], sup[k]["X"]) for k in order]           # (E, N): 한국 평면직각좌표 X=북, Y=동
    X0, Y0 = P[0]; th = math.atan2(P[-1][1] - Y0, P[-1][0] - X0)
    c, s = math.cos(-th), math.sin(-th)
    rot = lambda e, n: ((e - X0) * c - (n - Y0) * s, (e - X0) * s + (n - Y0) * c)
    Pl = [rot(*p) for p in P]
    spans = [math.hypot(Pl[i + 1][0] - Pl[i][0], Pl[i + 1][1] - Pl[i][1]) for i in range(5)]
    return Pl, spans, rot

def arc_interp(p0, p1, p2, t):
    (x0, y0), (x1, y1), (x2, y2) = p0, p1, p2
    d = 2 * (x0 * (y1 - y2) + x1 * (y2 - y0) + x2 * (y0 - y1))
    if abs(d) < 1e-9: return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
    ux = ((x0**2 + y0**2) * (y1 - y2) + (x1**2 + y1**2) * (y2 - y0) + (x2**2 + y2**2) * (y0 - y1)) / d
    uy = ((x0**2 + y0**2) * (x2 - x1) + (x1**2 + y1**2) * (x0 - x2) + (x2**2 + y2**2) * (x1 - x0)) / d
    R = math.hypot(x0 - ux, y0 - uy); a0 = math.atan2(y0 - uy, x0 - ux); a1 = math.atan2(y1 - uy, x1 - ux)
    while a1 - a0 > math.pi: a1 -= 2 * math.pi
    while a1 - a0 < -math.pi: a1 += 2 * math.pi
    a = a0 + (a1 - a0) * t
    return (ux + R * math.cos(a), uy + R * math.sin(a))

def plate_segments(key):
    segs, s = [], 0.0
    for L, th in SPEC["plates"][key]:
        segs.append((s, s + L / 1000, th / 1000)); s += L / 1000
    return segs

def thick_at(segs, x):
    for a, b, th in segs:
        if a - 1e-6 <= x < b + 1e-6: return th
    return segs[-1][2]

# ───────── MCT ─────────
def loadcomb(name, terms, itype=0):
    return f"   NAME={name}, GEN, ACTIVE, 0, {itype}, , 0, 0, 0, 1\n        " + ", ".join(f"{k}, {nm}, {f:g}" for k, nm, f in terms) + "\n"

def beamload_block(case, elem_loads, direction="GZ"):
    s = f"\n*USE-STLD, {case}\n*BEAMLOAD    ; Element Beam Loads\n"
    for e, w in elem_loads:
        s += f"{e:6d}, BEAM   , UNILOAD, {direction}, NO , NO, aDir[1], , , , 0, {w:.4f}, 1, {w:.4f}, 0, 0, 0, 0, , NO, 0, 0, NO, \n"
    return s

def mct_text(name, nodes, elems, sections, loads_text, cons_text, comb_text):
    s = f";  {name}\n;  generated by gen_model.py v2 (순천만IC2교)\n\n*VERSION\n   9.5.5\n\n*UNIT    ; Unit System\n   KN   , M, KCAL, C\n\n"
    s += "*STRUCTYPE    ; Structure Type\n     0, 1, 1, NO, YES, 9.806, 0, NO, NO, NO\n\n"
    s += "*NODE    ; Nodes\n" + "".join(f"{i:6d}, {x:.5f}, {y:.5f}, {z:.3f}\n" for i, (x, y, z) in sorted(nodes.items()))
    s += "\n*ELEMENT    ; Elements\n" + "".join(f"{e:6d}, BEAM  , {m:4d}, {sc:4d}, {n1:6d}, {n2:6d}, 0, 0\n" for e, m, sc, n1, n2 in elems)
    s += ("\n*MATERIAL    ; Material\n"
          f"    1, STEEL, SM490             , 0, 0, , C, YES, 0.02, 2,  {ES:.4e},   0.3,  1.2000e-05,  {G_STEEL:.2f},  {G_STEEL/9.80665:.4f}\n")
    s += "\n*SECT-PSCVALUE    ; PSC Value, General Section\n"
    for sid, nm, p in sections:
        s += (f" SECT={sid:4d}, VALUE     , {nm:<22s}, CC, 0, 0, 0, 0, 0, 0, YES, NO, GEN, YES, YES\n"
              f"       {p['A']:.6e}, {p['Asy']:.6e}, {p['Asz']:.6e}, {p['K']:.6e}, {p['I33']:.6e}, {p['I22']:.6e}\n"
              "       0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n       0, 0, 0, 0, 0, 0, 0, 0\n")
    return s + loads_text + cons_text + comb_text + "\n*ENDDATA\n"

# ───────── 조립 ─────────
def build():
    os.makedirs(OUT, exist_ok=True)
    Pl, spans, rot = geometry()
    tot = sum(spans); sup_s = [0.0]
    for L in spans: sup_s.append(sup_s[-1] + L)
    eff = eff_width_table(spans)
    top, bot = plate_segments("top"), plate_segments("bot")

    # 도로중심선 기준 주형 오프셋 (1.95 m 연석 쪽 박스 중심 = 연석에서 2.2 m)
    a1 = SPEC["supports"]["A1"]
    alt = [rot(c["Y"], c["X"]) for c in a1.get("alternatives", [])]
    near = min(alt, key=lambda p: abs(math.hypot(p[0] - Pl[0][0], p[1] - Pl[0][1]) - 1.95))
    sgn = 1.0 if near[1] > Pl[0][1] else -1.0
    off = {"G1": sgn * (1.95 - 2.20), "G2": sgn * (1.95 - 6.47)}

    cuts = {0.0, tot}
    for segs in (top, bot):
        for a, b, th in segs: cuts.update(v for v in (a, b) if 0 < v < tot)
    cuts.update(sup_s[1:-1])
    for nm, a, b, B, l in eff: cuts.update(v for v in (a, b) if 0 < v < tot)
    xb = [round(k * XBEAM_SP, 3) for k in range(int(tot / XBEAM_SP) + 1)]
    cuts.update(v for v in xb if 0 < v < tot)
    cuts = sorted(round(v, 4) for v in cuts)
    stations = []
    for a, b in zip(cuts, cuts[1:]):
        m = max(1, math.ceil((b - a) / MAX_ELEM)); stations += [a + (b - a) * k / m for k in range(m)]
    stations.append(tot); stations = sorted(set(round(v, 4) for v in stations))

    def cl_at(s):
        for i in range(5):
            if sup_s[i] - 1e-9 <= s <= sup_s[i + 1] + 1e-9:
                t = (s - sup_s[i]) / spans[i]; third = Pl[i + 2] if i + 2 < 6 else Pl[i - 1]
                p = arc_interp(Pl[i], Pl[i + 1], third, t); q = arc_interp(Pl[i], Pl[i + 1], third, min(1.0, t + 1e-4))
                return p, math.atan2(q[1] - p[1], q[0] - p[0])
        return Pl[-1], 0.0

    nodes, nG, nid, ang_at = {}, {"G1": [], "G2": []}, 0, {}
    for s in stations:
        (cx, cy), ang = cl_at(s); nx, ny = -math.sin(ang), math.cos(ang); ang_at[s] = ang
        for g in ("G1", "G2"):
            nid += 1; nodes[nid] = (cx + off[g] * nx, cy + off[g] * ny, 0.0); nG[g].append((nid, s))

    in_neg = lambda s: thick_at(top, s) >= 0.020 - 1e-9
    sec_keys, elems, eid = {}, [], 0
    for g in ("G1", "G2"):
        for (n1, s1), (n2, s2) in zip(nG[g], nG[g][1:]):
            sm = (s1 + s2) / 2
            key = (round(thick_at(top, sm), 4), round(thick_at(bot, sm), 4), in_neg(sm), round(beff_at(eff, sm), 3))
            sec_keys.setdefault(key, len(sec_keys) + 1); eid += 1
            elems.append((eid, 1, sec_keys[key], n1, n2, g, s1, s2))
    n_main = eid; xsec = len(sec_keys) + 1; xb_elems = []
    for j, s in enumerate(stations):
        if any(abs(s - v) < 0.01 for v in xb) or any(abs(s - v) < 1e-3 for v in sup_s):
            eid += 1; xb_elems.append((eid, 1, xsec, nG["G1"][j][0], nG["G2"][j][0]))
    main_elems = [(e, m, sc, n1, n2) for e, m, sc, n1, n2, g, s1, s2 in elems]

    # 강재 할증 (모델 강재량: 주형 + 가로보 실제 길이)
    key_of = {v: k for k, v in sec_keys.items()}
    steel_kn = sum(steel_section(*key_of[sc][:2], RIB_NEG if key_of[sc][2] else RIB_POS)["A"] * (s2 - s1) * G_STEEL for e, m, sc, n1, n2, g, s1, s2 in elems)
    xb_len = sum(math.dist(nodes[n1][:2], nodes[n2][:2]) for e, m, sc, n1, n2 in xb_elems)
    steel_kn += xbeam_section()["A"] * xb_len * G_STEEL
    f_steel = STEEL_TOTAL_KN / steel_kn

    # 하중 (주형당)
    w_slab = ((T_SLAB - T_PAVE) * B_DECK / 2 + 2 * BF * TH) * G_RC
    w_pave = T_PAVE * (B_DECK / 2) * G_PAVE
    sdl = {g: w_pave + BARRIER[g] for g in ("G1", "G2")}
    w_wind = WIND_P * WIND_H / 2               # 횡방향, 주형당
    w_wl = WL_TOTAL / 2
    w_cf = CF_RATIO * DL_LANE_W                # 차선당 → 주형당 (1차선/주형)
    w_lf = LF_RATIO * DL_LANE_W                # 종방향, 주형당

    # 받침: 배치도 SHOE 좌표 → 지점·주형 매핑
    bearings = []
    for kind, X, Y in SHOES:
        e, n = rot(Y / 1000, X / 1000)
        i = min(range(6), key=lambda k: math.hypot(Pl[k][0] - e, Pl[k][1] - n))
        j = min(range(len(stations)), key=lambda k: abs(stations[k] - sup_s[i]))
        g = min(("G1", "G2"), key=lambda gg: math.hypot(nodes[nG[gg][j][0]][0] - e, nodes[nG[gg][j][0]][1] - n))
        typ = "FIX" if "고정" in kind else ("UNI" if "일방향" in kind else "BI")
        bearings.append(dict(pier=["A1", "P1", "P2", "P3", "P4", "P5"][i], girder=g, node=nG[g][j][0], type=typ, kind=kind,
                             angle_deg=math.degrees(ang_at[stations[j]])))
    code = {"FIX": "111000", "UNI": "011000", "BI": "001000"}     # 국부축: x'=접선. 일방향은 접선 이동 허용, 양방향은 수평 자유
    cons = "\n*CONSTRAINT    ; Supports\n" + "".join(f"   {b['node']}, {code[b['type']]}, \n" for b in bearings)

    lane_ids = {g: [e for e, m, sc, n1, n2, gg, s1, s2 in elems if gg == g] for g in ("G1", "G2")}
    models = {}
    for tag, kind in (("A_steel", "steel"), ("C_comp", "comp")):
        secs = []
        for (tft, tfb, neg, be), sid in sorted(sec_keys.items(), key=lambda kv: kv[1]):
            st = steel_section(tft, tfb, RIB_NEG if neg else RIB_POS)
            p = st if kind == "steel" else composite_section(st, be, N_SHORT)
            secs.append((sid, f"T{int(tft*1000):02d}B{int(tfb*1000):02d}{'N' if neg else 'P'}E{int(be*1000):04d}", p))
        secs.append((xsec, "XBEAM", xbeam_section()))
        if kind == "steel":
            loads = "\n*STLDCASE    ; Static Load Cases\n   DEAD      , D , \n   SLAB      , D , \n"
            loads += f"\n*USE-STLD, DEAD\n*SELFWEIGHT    ; Self Weight\n0, 0, -{f_steel:.4f}, \n"
            loads += beamload_block("SLAB", [(e, -w_slab) for e, *_ in main_elems])
            comb = "\n*LOADCOMB    ; Combinations\n" + loadcomb("D1", [("ST", "DEAD", 1), ("ST", "SLAB", 1)])
        else:
            cases = [("SDL", "D"), ("W", "W"), ("WL", "W"), ("CF", "CF"), ("LF", "L"), ("TP", "T"), ("TM", "T")]
            loads = "\n*STLDCASE    ; Static Load Cases\n" + "".join(f"   {nm:<10s}, {ty} , \n" for nm, ty in cases)
            loads += beamload_block("SDL", [(e, -sdl[g]) for e, m, sc, n1, n2, g, s1, s2 in elems])
            loads += beamload_block("W", [(e, w_wind) for e, *_ in main_elems], "GY")
            loads += beamload_block("WL", [(e, w_wl) for e, *_ in main_elems], "GY")
            loads += beamload_block("CF", [(e, w_cf) for e, *_ in main_elems], "GY")
            loads += beamload_block("LF", [(e, w_lf) for e, *_ in main_elems], "GX")
            loads += f"\n*USE-STLD, TP\n*SYSTEMPER    ; System Temperature\n   {TEMP:.1f}\n"
            loads += f"\n*USE-STLD, TM\n*SYSTEMPER    ; System Temperature\n   {-TEMP:.1f}\n"
            comb = "\n*LOADCOMB    ; Combinations\n" + loadcomb("D2", [("ST", "SDL", 1)])
        path = os.path.join(OUT, f"{tag}.mct")
        open(path, "w", encoding="utf-8").write(mct_text(f"Suncheonman IC2 STB grillage v2 - {tag}", nodes, main_elems + xb_elems, secs, loads, cons, comb))
        models[tag] = path

    info = dict(spans=spans, total=tot, sup_s=sup_s, stations=stations, n_nodes=len(nodes), n_main=n_main, n_xb=len(xb_elems),
                n_sections=len(sec_keys), eff=eff, f_steel=f_steel, model_steel_kN=steel_kn, w_slab=w_slab, w_pave=w_pave, sdl=sdl,
                w_wind=w_wind, w_wl=w_wl, w_cf=w_cf, w_lf=w_lf, temp=TEMP, off=off, bearings=bearings, lane_ids=lane_ids,
                elems=[(e, g, s1, s2, sc) for e, m, sc, n1, n2, g, s1, s2 in elems],
                nodes_G={g: [(n, s) for n, s in nG[g]] for g in nG}, models=models, xb_sp=XBEAM_SP)
    json.dump(info, open(os.path.join(OUT, "model_info.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return info

if __name__ == "__main__":
    ok = check_sections(); I = build()
    print(f"경간 {[round(v, 3) for v in I['spans']]} 합 {I['total']:.3f} | 절점 {I['n_nodes']} 주형요소 {I['n_main']} 가로보 {I['n_xb']} 단면 {I['n_sections']}")
    print(f"강재 할증 {I['f_steel']:.3f} (모델 {I['model_steel_kN']:.0f} kN / 재료표 {STEEL_TOTAL_KN:.0f} kN)")
    print(f"하중(kN/m/주형): 바닥판 {I['w_slab']:.2f} | 포장층 {I['w_pave']:.2f} | SDL {I['sdl']} | W {I['w_wind']:.2f} | WL {I['w_wl']:.2f} | CF {I['w_cf']:.3f} | LF {I['w_lf']:.3f} | T ±{I['temp']}")
    print("받침:", [(b['pier'], b['girder'], b['type'], round(b['angle_deg'], 1)) for b in I['bearings']])
    sys.exit(0 if ok else 1)

# -*- coding: utf-8 -*-
"""
순천만IC 2교 강박스(A1~P5) 2주형 격자모델 생성기 — MCT 3종
  A_steel   : 합성전 (강재단면)            하중 DEAD(강재자중×할증), SLAB(바닥판 타설)
  B_comp3n  : 합성후 장기 (n=3×8=24)       하중 SDL(마모층·방호벽)
  C_compn   : 합성후 단기 (n=8)            하중 LL (DB-24 / DL-24 이동하중)
합성전·후 강성이 다르므로 모델을 나누고, 결과는 파이썬에서 합산한다 (계산서 방식).

근거
  - 제원: D:/Midas/projects/순천만IC2교/제원서.json (준공도면 추출) + 대표님 확인(2026-09-10)
  - 단면 산정: 구조계산서 pp.7484~7497 (합성전/후, 리브 포함, K = 4bk²hk²/(2hk/tw + bk/tu + bk/tl))
  - 유효폭: 도로교설계기준(2005) 플랜지 유효폭 — 구조계산서 pp.7478~7482 인용식
        b/l ≤ 0.05 : λ = b ;  0.05 < b/l < 0.30 : λ = {1.06 − 3.2(b/l) + 4.5(b/l)²}·b ;  b/l ≥ 0.30 : λ = 0.15·l
        등가지간 l : 단부경간 중앙 0.8L, 내측경간 중앙 0.6L, 중간지점부 0.2(L1+L2)
        B = 플랜지폭(2.240) + λ1(b1=0.955) + λ2(b2=1.080) + h(0.060)
  - 하중: 구조계산서 p.7445(단위중량), p.7450~7457(방호벽·마모층), 활하중 DB-24/DL-24 1등교
"""
import sys, os, math, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\Midas\core\tools")

PJ = r"D:\Midas\projects\순천만IC2교"
OUT = os.path.join(PJ, "runs")
SPEC = json.load(open(os.path.join(PJ, "제원서.json"), encoding="utf-8"))

# ───────── 기본 제원 ─────────
H_WEB   = 2.300          # 복부 높이 (계산서 단면-2~7, 강재재료표 복부판 2300)
BF      = 2.240          # 플랜지 폭 (계산서 b3 = 224 cm, 강재재료표 상·하판 2240)
TW      = 0.012          # 복부 두께 (단면 요약도: 전장 12 mm)
WEB_SP  = 2.000          # 복부 간격 (박스 폭)
RIB     = (0.150, 0.014) # 종리브 150×14
RIB_POS = (5, 2)         # 정모멘트부 (상 5, 하 2)  — 계산서 단면-1,2,3,7
RIB_NEG = (2, 5)         # 부모멘트부 (상 2, 하 5)  — 계산서 단면-4,5,6
TC, TH  = 0.240, 0.060   # 바닥판 구조두께, 헌치 (계산서)
T_SLAB  = 0.300          # 바닥판 총두께 (도면) = 0.25 RC + 0.05 마모층
T_WEAR  = 0.050
B_DECK  = 8.670
N_SHORT = 8.0            # Es/Ec (계산서 n=8)
N_LONG  = 3 * N_SHORT
ES      = 2.1e8          # kN/m² (계산서 2,100,000 kgf/cm²)
G_RC, G_WEAR, G_STEEL = 25.0, 23.5, 78.5    # kN/m³ (계산서 2.5 / 2.35 / 7.85 tonf/m³)
BARRIER = {"G1": 9.66, "G2": 10.64}          # kN/m — 계산서 p.7451/7457 방호벽 항목 1~5 (+우측 난간 0.1 tonf/m)
STEEL_TOTAL_KN = 902129.2 * 9.80665 / 1000  # 강재재료표(22) GRAND TOTAL 902,129.2 kgf
XBEAM_SP = 5.0           # 가로보 간격 (다이아프램 5 m)
MAX_ELEM = 2.5

# ───────── 유효폭 (도로교설계기준 2005, 계산서 인용식) ─────────
LAM_LIMIT = 0.02   # 강교편 규정: b/l ≤ 0.02 → λ=b. (계산서는 지점부 0.02, 중앙부 0.05 문구를 섞어 씀 — 기준 원문 확인 항목)
def lam(b, l):
    r = b / l
    if r <= LAM_LIMIT:
        return b
    if r < 0.30:
        return (1.06 - 3.2 * r + 4.5 * r * r) * b
    return 0.15 * l

def eff_width_table(spans):
    """[(name, s_from, s_to, B)] — 지간 중앙부/지점부 구간별 유효폭. 지점부 구간은 지점 ±0.2L(인접 경간 각각)"""
    b1, b2, h, bf = 0.955, 1.080, TH, BF     # 계산서 p.7479: b1=(2.27−2(0.12+0.06))/2, b2=1.2−0.12
    flange_eff = lambda l: 2 * lam(WEB_SP / 2, l) + 2 * 0.120   # 박스 플랜지 자체 유효폭: 2λ(b=1.0) + 돌출 2×0.12 (계산서 지점부 2.061/2.109 재현)
    n = len(spans)
    cum = [0.0]
    for L in spans:
        cum.append(cum[-1] + L)
    tbl = []
    for i, L in enumerate(spans):
        l = (0.8 if i in (0, n - 1) else 0.6) * L
        B = flange_eff(l) + lam(b1, l) + lam(b2, l) + h
        tbl.append((f"S{i+1}mid", cum[i], cum[i + 1], round(B, 3), round(l, 3)))
    for i in range(1, n):
        l = 0.2 * (spans[i - 1] + spans[i])
        B = flange_eff(l) + lam(b1, l) + lam(b2, l) + h
        a, b = cum[i] - 0.2 * spans[i - 1], cum[i] + 0.2 * spans[i]
        tbl.append((f"P{i}sup", a, b, round(B, 3), round(l, 3)))
    return tbl

def beff_at(tbl, s):
    for nm, a, b, B, l in tbl:
        if nm.endswith("sup") and a <= s <= b:
            return B
    for nm, a, b, B, l in tbl:
        if nm.endswith("mid") and a <= s <= b:
            return B
    return tbl[0][3]

# ───────── 단면 계산 (계산서 방식) ─────────
def steel_section(tft, tfb, ribs):
    """합성전 강재단면. 원점 = 복부 중앙높이(H/2). 반환 dict (m, m², m⁴)"""
    nt, nb = ribs
    rw, rt = RIB
    parts = []   # (A, y, Io)
    parts.append((BF * tft, H_WEB / 2 + tft / 2, BF * tft ** 3 / 12))                 # 상판
    parts.append((nt * rw * rt, H_WEB / 2 - rw / 2, nt * rt * rw ** 3 / 12))           # 상부 종리브
    parts.append((2 * H_WEB * TW, 0.0, 2 * TW * H_WEB ** 3 / 12))                       # 복부
    parts.append((nb * rw * rt, -H_WEB / 2 + rw / 2, nb * rt * rw ** 3 / 12))          # 하부 종리브
    parts.append((BF * tfb, -H_WEB / 2 - tfb / 2, BF * tfb ** 3 / 12))                 # 하판
    A = sum(p[0] for p in parts)
    ys = sum(p[0] * p[1] for p in parts) / A
    I33 = sum(p[2] + p[0] * (p[1] - ys) ** 2 for p in parts)
    I22 = (tft * BF ** 3 / 12 + tfb * BF ** 3 / 12 + 2 * (H_WEB * TW ** 3 / 12 + H_WEB * TW * (WEB_SP / 2 + TW / 2) ** 2))
    bk = WEB_SP + TW
    hk = H_WEB + tft / 2 + tfb / 2
    K = 4 * bk ** 2 * hk ** 2 / (2 * hk / TW + bk / tft + bk / tfb)
    return dict(A=A, ys=ys, I33=I33, I22=I22, K=K, Asz=2 * H_WEB * TW, Asy=BF * (tft + tfb), tft=tft, tfb=tfb)

def composite_section(st, beff, n):
    """합성후 단면 (계산서 p.7485 방식). 바닥판 Tc, 헌치 Th 위에 위치"""
    Ac = beff * TC
    Av = st["A"] + Ac / n
    dv = H_WEB / 2 - st["ys"] + TH + TC / 2                  # 강재 도심 → 바닥판 도심 (계산서 p.7485: H/2 − δs + Th + Tc/2)
    dvc = dv * st["A"] / Av
    dvs = dv - dvc
    Iv33 = st["I33"] + beff * TC ** 3 / 12 / n + st["A"] * dvs ** 2 + Ac / n * dvc ** 2
    Iv22 = st["I22"] + beff ** 3 * TC / 12 / n
    tcu = st["tft"] + TC / n
    bk = WEB_SP + TW
    hk = H_WEB + st["tft"] / 2 + st["tfb"] / 2
    K = 4 * bk ** 2 * hk ** 2 / (2 * hk / TW + bk / tcu + bk / st["tfb"])
    return dict(A=Av, I33=Iv33, I22=Iv22, K=K, Asz=st["Asz"], Asy=st["Asy"] + Ac / n)

def xbeam_section():
    """가로보 I형: 플랜지 300×12 ×2, 복부 1200×12"""
    bf, tf, hw, tw = 0.300, 0.012, 1.200, 0.012
    A = 2 * bf * tf + hw * tw
    I33 = 2 * (bf * tf ** 3 / 12 + bf * tf * (hw / 2 + tf / 2) ** 2) + tw * hw ** 3 / 12
    I22 = 2 * tf * bf ** 3 / 12 + hw * tw ** 3 / 12
    K = (2 * bf * tf ** 3 + hw * tw ** 3) / 3
    return dict(A=A, I33=I33, I22=I22, K=K, Asz=hw * tw, Asy=2 * bf * tf)

def check_sections():
    """계산서 단면-2 (t=12/12, 리브 5/2, B=4.335, n=8) 대조"""
    st = steel_section(0.012, 0.012, RIB_POS)
    cp = composite_section(st, 4.335, 8.0)
    ref = dict(As=1236.6e-4, I33=11282040.8e-8, I22=7834389.8e-8, K=12010391.6e-8, Iv33=21652621.9e-8, Iv22=28200463.6e-8, Kv=14404094.4e-8)
    rows = [("As", st["A"], ref["As"]), ("I33", st["I33"], ref["I33"]), ("I22", st["I22"], ref["I22"]), ("K", st["K"], ref["K"]),
            ("Iv33(n=8)", cp["I33"], ref["Iv33"]), ("Iv22", cp["I22"], ref["Iv22"]), ("Kv", cp["K"], ref["Kv"])]
    ok = True
    print("── 단면 검증 (계산서 단면-2) ──")
    for nm, a, b in rows:
        d = (a - b) / b * 100
        flag = "OK" if abs(d) < 1.0 else "★차이"
        ok &= abs(d) < 1.0
        print(f"  {nm:10s} 모델 {a:.6e}  계산서 {b:.6e}  차 {d:+.2f}%  {flag}")
    return ok

# ───────── 기하 ─────────
def geometry():
    sup = SPEC["supports"]
    order = ["A1", "P1", "P2", "P3", "P4", "P5"]
    P = [(sup[k]["Y"], sup[k]["X"]) for k in order]     # 한국 평면직각좌표: X=북, Y=동 → 그림 좌표는 (E, N)=(Y, X)
    X0, Y0 = P[0]
    th = math.atan2(P[-1][1] - Y0, P[-1][0] - X0)
    c, s = math.cos(-th), math.sin(-th)
    rot = lambda x, y: ((x - X0) * c - (y - Y0) * s, (x - X0) * s + (y - Y0) * c)
    Pl = [rot(*p) for p in P]                      # A1 원점, P5 방향 +X
    spans = [math.hypot(Pl[i + 1][0] - Pl[i][0], Pl[i + 1][1] - Pl[i][1]) for i in range(5)]
    return Pl, spans, rot

def arc_interp(p0, p1, p2, t):
    (x0, y0), (x1, y1), (x2, y2) = p0, p1, p2
    d = 2 * (x0 * (y1 - y2) + x1 * (y2 - y0) + x2 * (y0 - y1))
    if abs(d) < 1e-9:
        return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
    ux = ((x0 ** 2 + y0 ** 2) * (y1 - y2) + (x1 ** 2 + y1 ** 2) * (y2 - y0) + (x2 ** 2 + y2 ** 2) * (y0 - y1)) / d
    uy = ((x0 ** 2 + y0 ** 2) * (x2 - x1) + (x1 ** 2 + y1 ** 2) * (x0 - x2) + (x2 ** 2 + y2 ** 2) * (x1 - x0)) / d
    R = math.hypot(x0 - ux, y0 - uy)
    a0 = math.atan2(y0 - uy, x0 - ux); a1 = math.atan2(y1 - uy, x1 - ux)
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
        if a - 1e-6 <= x < b + 1e-6:
            return th
    return segs[-1][2]

# ───────── MCT 작성 ─────────
def mct_text(name, nodes, elems, sections, material_E, loads_text, constraint_text, comb_text, mvld_text=""):
    s = f";  {name}\n;  generated 2026-09-10 by gen_model.py (순천만IC2교)\n\n*VERSION\n   9.5.5\n\n*UNIT    ; Unit System\n   KN   , M, KCAL, C\n\n"
    s += "*STRUCTYPE    ; Structure Type\n     0, 1, 1, NO, YES, 9.806, 0, NO, NO, NO\n\n"
    s += "*NODE    ; Nodes\n" + "".join(f"{i:6d}, {x:.5f}, {y:.5f}, {z:.3f}\n" for i, (x, y, z) in sorted(nodes.items()))
    s += "\n*ELEMENT    ; Elements\n" + "".join(f"{e:6d}, BEAM  , {m:4d}, {sc:4d}, {n1:6d}, {n2:6d}, 0, 0\n" for e, m, sc, n1, n2 in elems)
    s += ("\n*MATERIAL    ; Material\n"
          f"    1, STEEL, SM490             , 0, 0, , C, YES, 0.02, 2,  {material_E:.4e},   0.3,  1.2000e-05,  {G_STEEL:.2f},  {G_STEEL/9.80665:.4f}\n")
    s += "\n*SECT-PSCVALUE    ; PSC Value, General Section\n"
    for sid, nm, p in sections:
        s += (f" SECT={sid:4d}, VALUE     , {nm:<22s}, CC, 0, 0, 0, 0, 0, 0, YES, NO, GEN, YES, YES\n"
              f"       {p['A']:.6e}, {p['Asy']:.6e}, {p['Asz']:.6e}, {p['K']:.6e}, {p['I33']:.6e}, {p['I22']:.6e}\n"
              "       0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n       0, 0, 0, 0, 0, 0, 0, 0\n")
    s += loads_text + mvld_text + constraint_text + comb_text + "\n*ENDDATA\n"
    return s

def beamload_block(case, elem_loads, direction="GZ"):
    s = f"\n*USE-STLD, {case}\n*BEAMLOAD    ; Element Beam Loads\n"
    for e, w in elem_loads:
        s += f"{e:6d}, BEAM   , UNILOAD, {direction}, NO , NO, aDir[1], , , , 0, {w:.4f}, 1, {w:.4f}, 0, 0, 0, 0, , NO, 0, 0, NO, \n"
    return s

def loadcomb(name, terms, itype=0):
    """*LOADCOMB 10-파라미터 형식 (실물 파일 대조: NAME, GEN, ACTIVE, 0, itype, , 0, 0, 0, 1)"""
    t = f"   NAME={name}, GEN, ACTIVE, 0, {itype}, , 0, 0, 0, 1\n        "
    return t + ", ".join(f"{k}, {nm}, {f:g}" for k, nm, f in terms) + "\n"

# ───────── 모델 조립 ─────────
def build():
    os.makedirs(OUT, exist_ok=True)
    Pl, spans, rot = geometry()
    tot = sum(spans)
    sup_s = [0.0]
    for L in spans: sup_s.append(sup_s[-1] + L)
    eff = eff_width_table(spans)
    top, bot = plate_segments("top"), plate_segments("bot")

    # 거더 횡방향 위치: 도로중심선 기준. 받침배치도 좌표(1.95 m 측 연석 / 6.72 m 측 연석)로 부호 결정
    # G1 = 1.95 m 연석 측(450+1500) 박스 중심 (연석에서 2.2 m), G2 = 반대측
    a1 = SPEC["supports"]["A1"]
    alt = [rot(c["Y"], c["X"]) for c in a1.get("alternatives", [])]
    y_g1_sign = +1.0
    if alt:   # 1.95 m 떨어진 점의 부호
        near = min(alt, key=lambda p: abs(math.hypot(p[0] - Pl[0][0], p[1] - Pl[0][1]) - 1.95))
        y_g1_sign = 1.0 if near[1] > Pl[0][1] else -1.0
    off = {"G1": y_g1_sign * (1.95 - 2.20), "G2": y_g1_sign * (1.95 - 6.47)}   # 도로중심선 기준 횡 오프셋 (m)

    # 절점 위치(종방향 s)
    cuts = {0.0, tot}
    for segs in (top, bot):
        for a, b, th in segs:
            cuts.update(v for v in (a, b) if 0 < v < tot)
    cuts.update(sup_s[1:-1])
    for nm, a, b, B, l in eff:
        cuts.update(v for v in (a, b) if 0 < v < tot)
    xb = [round(k * XBEAM_SP, 3) for k in range(int(tot / XBEAM_SP) + 1)]
    cuts.update(v for v in xb if 0 < v < tot)
    cuts = sorted(round(v, 4) for v in cuts)
    stations = []
    for a, b in zip(cuts, cuts[1:]):
        m = max(1, math.ceil((b - a) / MAX_ELEM))
        stations += [a + (b - a) * k / m for k in range(m)]
    stations.append(tot)
    stations = sorted(set(round(v, 4) for v in stations))

    def cl_at(s):
        for i in range(5):
            if sup_s[i] - 1e-9 <= s <= sup_s[i + 1] + 1e-9:
                t = (s - sup_s[i]) / spans[i]
                third = Pl[i + 2] if i + 2 < 6 else Pl[i - 1]
                p = arc_interp(Pl[i], Pl[i + 1], third, t)
                q = arc_interp(Pl[i], Pl[i + 1], third, min(1.0, t + 1e-4))
                return p, math.atan2(q[1] - p[1], q[0] - p[0])
        return Pl[-1], 0.0

    nodes, nG, nid = {}, {"G1": [], "G2": []}, 0
    for s in stations:
        (cx, cy), ang = cl_at(s)
        nx, ny = -math.sin(ang), math.cos(ang)
        for g in ("G1", "G2"):
            nid += 1
            nodes[nid] = (cx + off[g] * nx, cy + off[g] * ny, 0.0)
            nG[g].append((nid, s))

    # 단면 (모델별): key → (tft, tfb, ribs, beff)
    def in_neg_zone(s):          # 상판 두께 ≥ 20 mm 구간 = 지점부 → 리브 2/5
        return thick_at(top, s) >= 0.020 - 1e-9
    sec_keys, elems, eid = {}, [], 0
    for g in ("G1", "G2"):
        arr = nG[g]
        for (n1, s1), (n2, s2) in zip(arr, arr[1:]):
            sm = (s1 + s2) / 2
            key = (round(thick_at(top, sm), 4), round(thick_at(bot, sm), 4), in_neg_zone(sm), round(beff_at(eff, sm), 3))
            sec_keys.setdefault(key, len(sec_keys) + 1)
            eid += 1
            elems.append((eid, 1, sec_keys[key], n1, n2, g, s1, s2))
    n_main = eid
    xsec = len(sec_keys) + 1
    xb_elems = []
    for j, s in enumerate(stations):
        if any(abs(s - v) < 0.01 for v in xb) or any(abs(s - v) < 1e-3 for v in sup_s):   # 지점(A1~P5) 가로보 반드시 포함
            eid += 1
            xb_elems.append((eid, 1, xsec, nG["G1"][j][0], nG["G2"][j][0]))
    main_elems = [(e, m, sc, n1, n2) for e, m, sc, n1, n2, g, s1, s2 in elems]

    # 강재 자중 할증 계수: 재료표 총량 / 모델 강재량
    steel_len_kn = 0.0
    for e, m, sc, n1, n2, g, s1, s2 in elems:
        tft, tfb, neg, be = [k for k, v in sec_keys.items() if v == sc][0]
        st = steel_section(tft, tfb, RIB_NEG if neg else RIB_POS)
        steel_len_kn += st["A"] * (s2 - s1) * G_STEEL
    xb_kn = xbeam_section()["A"] * (4.270 - WEB_SP) * G_STEEL * len(xb_elems)
    model_steel = steel_len_kn + xb_kn
    f_steel = STEEL_TOTAL_KN / model_steel

    # 하중 (주형당)
    haunch_area = 2 * (BF * TH)                                    # 헌치 (근사: 플랜지 폭 × Th)
    w_slab = ((T_SLAB - T_WEAR) * B_DECK / 2 + haunch_area) * G_RC  # 바닥판 RC (마모층 제외)
    w_wear = T_WEAR * (B_DECK / 2) * G_WEAR                        # 마모층
    sdl = {g: w_wear + BARRIER[g] for g in ("G1", "G2")}

    # 경계: 지점 절점. P3 고정(Dx,Dy,Dz), 나머지 (Dy,Dz) + 회전 자유. 곡선교라 Dy 구속은 근사(일방향 받침 방향 = 접선)
    fix, mov = [], []
    for nm, ss in zip(["A1", "P1", "P2", "P3", "P4", "P5"], sup_s):
        j = min(range(len(stations)), key=lambda k: abs(stations[k] - ss))
        for g in ("G1", "G2"):
            (fix if nm == "P3" else mov).append(str(nG[g][j][0]))
    cons = "\n*CONSTRAINT    ; Supports\n" + f"   {' '.join(fix)}, 111000, \n" + f"   {' '.join(mov)}, 011000, \n"

    # 차선 (이동하중): G1, G2 요소열에 각각 1차선
    lanes = ""
    for li, g in enumerate(("G1", "G2"), start=1):
        ids = [e for e, m, sc, n1, n2, gg, s1, s2 in elems if gg == g]
        lanes += f"   NAME=L{li}, CROSS, CROSS, 0, 0, FORWARD, 3, 0, NO\n"
        buf = [f"{e:6d}, 0, 0, {'YES' if k == 0 else 'NO'}, 0" for k, e in enumerate(ids)]
        for k in range(0, len(buf), 3):
            lanes += "        " + ",   ".join(buf[k:k + 3]) + "\n"
    mvld = ("\n*MVLDCODE    ; Moving Load Code\n   CODE=KOREA\n\n*LINELANE    ; Traffic Line Lanes\n" + lanes +
            "\n*VEHICLE    ; Vehicles\n   NAME=DB-24, 1, DB-24, 0, KS-RB\n   NAME=DL-24, 1, DL-24, 0, KS-RB\n"
            "\n*MVLDCASE   ; Moving Load Cases\n")
    for si, veh in enumerate(("DB-24", "DL-24"), start=1):
        mvld += (f"   NAME={veh}, 0, 1, 1, 0.9, 0.75, 0.75, 0.75, INDEPENDENT, , 0, {si}\n"
                 "        1, 1, 1, 1, 0.5, 0.5, 0.25\n"
                 f"        VL, {veh}, 1, 1, 2, L1, L2\n")

    models = {}
    for tag, kind, n in (("A_steel", "steel", None), ("B_comp3n", "comp", N_LONG), ("C_compn", "comp", N_SHORT)):
        secs = []
        for (tft, tfb, neg, be), sid in sorted(sec_keys.items(), key=lambda kv: kv[1]):
            st = steel_section(tft, tfb, RIB_NEG if neg else RIB_POS)
            p = st if kind == "steel" else composite_section(st, be, n)
            nm = f"T{int(tft*1000):02d}B{int(tfb*1000):02d}{'N' if neg else 'P'}E{int(be*1000):04d}"
            secs.append((sid, nm, p))
        secs.append((xsec, "XBEAM", xbeam_section()))
        if kind == "steel":
            loads = "\n*STLDCASE    ; Static Load Cases\n   DEAD      , D , \n   SLAB      , D , \n"
            loads += f"\n*USE-STLD, DEAD\n*SELFWEIGHT    ; Self Weight\n0, 0, -{f_steel:.4f}, \n"
            loads += beamload_block("SLAB", [(e, -w_slab) for e, *_ in main_elems])
            comb = "\n*LOADCOMB    ; Combinations\n" + loadcomb("D1", [("ST", "DEAD", 1), ("ST", "SLAB", 1)])
            mv = ""
        elif tag == "B_comp3n":
            loads = "\n*STLDCASE    ; Static Load Cases\n   SDL       , D , \n"
            loads += beamload_block("SDL", [(e, -sdl[g]) for e, m, sc, n1, n2, g, s1, s2 in elems])
            comb = "\n*LOADCOMB    ; Combinations\n" + loadcomb("D2", [("ST", "SDL", 1)])
            mv = ""
        else:
            loads = "\n*STLDCASE    ; Static Load Cases\n   DUMMY     , D , \n"
            comb = "\n*LOADCOMB    ; Combinations\n" + loadcomb("LL", [("MV", "DB-24", 1)], itype=1)
            mv = mvld
        txt = mct_text(f"Suncheonman IC2 STB grillage - {tag}", nodes, main_elems + xb_elems, secs, ES, loads, cons, comb, mv)
        path = os.path.join(OUT, f"{tag}.mct")
        open(path, "w", encoding="utf-8").write(txt)
        models[tag] = path

    info = dict(spans=spans, total=tot, sup_s=sup_s, stations=stations, n_nodes=len(nodes), n_main=n_main, n_xb=len(xb_elems),
                n_sections=len(sec_keys), eff=eff, f_steel=f_steel, model_steel_kN=model_steel, w_slab=w_slab, w_wear=w_wear, sdl=sdl,
                off=off, y_g1_sign=y_g1_sign, elems=[(e, g, s1, s2, sc) for e, m, sc, n1, n2, g, s1, s2 in elems],
                nodes_G={g: [(n, s) for n, s in nG[g]] for g in nG}, models=models, xb_sp=XBEAM_SP)
    json.dump(info, open(os.path.join(OUT, "model_info.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return info

if __name__ == "__main__":
    ok = check_sections()
    I = build()
    print("── 모델 ──")
    print(f"  경간 {[round(v, 3) for v in I['spans']]} 합 {I['total']:.3f}")
    print(f"  절점 {I['n_nodes']}  주형요소 {I['n_main']}  가로보 {I['n_xb']}  단면종류 {I['n_sections']}")
    print("  유효폭:", [(nm, B, l) for nm, a, b, B, l in I['eff']])
    print(f"  강재 모델량 {I['model_steel_kN']:.0f} kN vs 재료표 {STEEL_TOTAL_KN:.0f} kN → 자중 할증 {I['f_steel']:.3f}")
    print(f"  바닥판 {I['w_slab']:.2f} kN/m/주형, 마모층 {I['w_wear']:.2f}, SDL {I['sdl']}")
    print(f"  거더 횡오프셋(도로중심선 기준) {I['off']}")
    print("  MCT:", list(I["models"].values()))
    sys.exit(0 if ok else 1)

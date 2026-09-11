# -*- coding: utf-8 -*-
"""
순천만IC 2교 강박스 (A1~P5) — 2주형 그릴리지 MCT 생성.

구성
  · G1, G2 두 열의 보요소 + 가로보로 연결
  · 절점은 판두께 구간 경계에 맞춰 배치 (단면 변화 그대로 반영)
  · 곡선: 각 경간을 원호 보간
  · 좌표: 교축 = +X (시점 좌측 → 종점 우측)

제원 출처 (전부 준공도면 DXF 실측)
  경간   : 받침 실좌표 역산 (종평면도와 50mm 이내 일치)
  단면   : 단면요약도(1)=G1 / (2)=G2 의 구간장·두께
  박스   : 가로보 상세도 도형 실측 (웨브 수직, 중심간격 2.258m)
  받침   : 교량받침 집계표 (고정단 P3, 지점당 G1·G2 각 1개)
  바닥판 : t=300mm, fck=27MPa
"""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mct_syntax as M
from verify import Check, parse_mct

HERE = os.path.dirname(os.path.abspath(__file__))
SCR  = os.path.abspath(os.path.join(HERE, ".."))

SPEC = {
    "spans":    [49.8756, 49.9955, 70.0000, 50.0000, 49.8400],
    "supports": ["A1", "P1", "P2", "P3", "P4", "P5"],
    # 측량좌표(mm) — 교축 정렬 회전은 아래에서 수행
    "support_xy": [(155445278.7, 243636316.5), (155470976.3, 243679062.4),
                   (155499779.7, 243719927.0), (155540694.4, 243776724.8),
                   (155569919.2, 243817294.6), (155599050.5, 243857734.6)],
    "girder_offset": 4.270/2,      # 교축 중심에서 G1/G2 까지 (받침간격 4.270)
    "box": {"H": 2.300, "H_end": 2.100, "tw": 0.012, "tw_sup": 0.020,
            "web_spacing": 2.258, "bf_top": 3.950, "bf_bot": 3.550},
    "deck": {"t": 0.300, "fck": 27.0, "B_total": 8.670},
    "steel": {"Es": 210000.0},
    "fixed_support": "P3",
    "xbeam_spacing": 12.5,         # 가로보 간격 (다이어프램 간격 상당)
    "max_elem": 5.0,               # 구간 내 최대 요소길이
}
GAMMA_S, GAMMA_C = 76.98, 24.5


# ───────────────────── 단면 특성 ─────────────────────
def sect_props(H, tw, bft, tft, bfb, tfb, t_deck, b_eff, n, s_web):
    A_w, A_ft, A_fb = 2*H*tw, bft*tft, bfb*tfb
    A_s = A_w + A_ft + A_fb
    y_fb, y_w, y_ft = tfb/2, tfb + H/2, tfb + H + tft/2
    y_s = (A_fb*y_fb + A_w*y_w + A_ft*y_ft)/A_s
    I_s = (bfb*tfb**3/12 + A_fb*(y_fb-y_s)**2) \
        + (2*tw*H**3/12  + A_w *(y_w -y_s)**2) \
        + (bft*tft**3/12 + A_ft*(y_ft-y_s)**2)
    b_tr = b_eff/n
    A_c  = b_tr*t_deck
    y_c  = tfb + H + tft + t_deck/2
    A_v  = A_s + A_c
    y_v  = (A_s*y_s + A_c*y_c)/A_v
    I_v  = I_s + A_s*(y_s-y_v)**2 + (b_tr*t_deck**3/12 + A_c*(y_c-y_v)**2)
    I_z  = 2*(H*tw*(s_web/2)**2) + tft*bft**3/12 + tfb*bfb**3/12 + t_deck*b_tr**3/12
    b_m  = (bft+bfb)/2
    Am   = b_m*H
    J    = 4*Am**2/(2*(H/tw) + b_m/tft + b_m/tfb)
    return dict(A=A_v, Iy=I_v, Iz=I_z, J=J, Asz=2*H*tw, Asy=bft*tft+bfb*tfb,
                A_s=A_s, I_s=I_s)


def thick_at(segs, x):
    """구간 리스트에서 위치 x 의 두께"""
    for s, e, L, th in segs:
        if s - 1e-6 <= x < e + 1e-6:
            return th
    return segs[-1][3]


# ───────────────────── 기하 ─────────────────────
def axis_points(spec):
    """교축 정렬 + 원호 보간용 지점좌표 반환"""
    XY = spec["support_xy"]
    X0, Y0 = XY[0]
    P = [((x-X0)/1000.0, (y-Y0)/1000.0) for x, y in XY]
    th = math.atan2(P[-1][1]-P[0][1], P[-1][0]-P[0][0])
    c, s = math.cos(-th), math.sin(-th)
    return [(x*c - y*s, x*s + y*c) for x, y in P]


def arc_interp(p0, p1, p2, t):
    """p0,p1,p2 를 지나는 원호 위에서 p0→p1 구간을 t(0~1) 보간"""
    (x0, y0), (x1, y1), (x2, y2) = p0, p1, p2
    d = 2*(x0*(y1-y2) + x1*(y2-y0) + x2*(y0-y1))
    if abs(d) < 1e-9:
        return (x0 + (x1-x0)*t, y0 + (y1-y0)*t)
    ux = ((x0**2+y0**2)*(y1-y2) + (x1**2+y1**2)*(y2-y0) + (x2**2+y2**2)*(y0-y1))/d
    uy = ((x0**2+y0**2)*(x2-x1) + (x1**2+y1**2)*(x0-x2) + (x2**2+y2**2)*(x1-x0))/d
    R  = math.hypot(x0-ux, y0-uy)
    a0 = math.atan2(y0-uy, x0-ux)
    a1 = math.atan2(y1-uy, x1-ux)
    while a1 - a0 >  math.pi: a1 -= 2*math.pi
    while a1 - a0 < -math.pi: a1 += 2*math.pi
    a = a0 + (a1-a0)*t
    return (ux + R*math.cos(a), uy + R*math.sin(a))


# ───────────────────── 모델 생성 ─────────────────────
def build(spec, outpath):
    G = json.load(open(os.path.join(SCR, "girder_sections.json"), encoding="utf-8"))
    box, deck = spec["box"], spec["deck"]
    Ec = 8500.0*((deck["fck"]+4.0)**(1.0/3.0))
    n  = spec["steel"]["Es"]/Ec
    b_eff = deck["B_total"]/2.0          # 주형당 유효폭

    P   = axis_points(spec)
    tot = sum(spec["spans"])
    sup_s = [0.0]
    for L in spec["spans"]:
        sup_s.append(sup_s[-1] + L)

    # ── 단면 목록: G1/G2 각각의 (top,bot) 두께 조합을 유니크화 ──
    cuts = {0.0, tot}
    for g in ("G1", "G2"):
        for k in ("top", "bot"):
            for s, e, L, th in G[g][k]:
                if 0.0 < s < tot: cuts.add(round(s, 4))
                if 0.0 < e < tot: cuts.add(round(e, 4))
    for s in sup_s[1:-1]: cuts.add(round(s, 4))
    cuts = sorted(cuts)

    # 요소 분할: 구간 경계 + max_elem 로 세분
    stations = []
    for i in range(len(cuts)-1):
        a, b = cuts[i], cuts[i+1]
        m = max(1, int(math.ceil((b-a)/spec["max_elem"])))
        for k in range(m):
            stations.append(a + (b-a)*k/m)
    stations.append(tot)
    # 가로보 위치도 절점으로
    xb = set()
    x = 0.0
    while x < tot:
        xb.add(round(x, 4)); x += spec["xbeam_spacing"]
    for v in sorted(xb):
        if not any(abs(v-s) < 0.05 for s in stations):
            stations.append(v)
    stations = sorted(set(round(v, 4) for v in stations))

    # ── 절점 ──
    def xy_at(s):
        """교축좌표 s(누적거리) → 평면 (x,y), 접선각"""
        for i in range(5):
            if sup_s[i] - 1e-9 <= s <= sup_s[i+1] + 1e-9:
                t = (s - sup_s[i])/spec["spans"][i]
                i0 = max(0, min(i, 3))
                p = arc_interp(P[i], P[i+1], P[i+2] if i+2 < 6 else P[i-1], t)
                # 접선: 수치미분
                dt = 1e-4
                q = arc_interp(P[i], P[i+1], P[i+2] if i+2 < 6 else P[i-1],
                               min(1.0, t+dt))
                return p, math.atan2(q[1]-p[1], q[0]-p[0])
        return P[-1], 0.0

    off = spec["girder_offset"]
    nodes, nG = {}, {"G1": [], "G2": []}
    nid = 0
    for s in stations:
        (cx, cy), ang = xy_at(s)
        nx, ny = -math.sin(ang), math.cos(ang)     # 법선
        for g, sgn in (("G1", +1), ("G2", -1)):
            nid += 1
            nodes[nid] = (cx + sgn*off*nx, cy + sgn*off*ny, 0.0)
            nG[g].append((nid, s))

    # ── 단면 정의 ──
    sec_key, sec_list = {}, []
    def sec_id(g, s_mid):
        tft = thick_at(G[g]["top"], s_mid)/1000.0
        tfb = thick_at(G[g]["bot"], s_mid)/1000.0
        tw  = box["tw_sup"] if min(abs(s_mid-v) for v in sup_s) < 5.0 else box["tw"]
        key = (round(tft, 4), round(tfb, 4), round(tw, 4))
        if key not in sec_key:
            p = sect_props(box["H"], tw, box["bf_top"], tft,
                           box["bf_bot"], tfb, deck["t"], b_eff, n,
                           box["web_spacing"])
            sec_key[key] = len(sec_list)+1
            sec_list.append((sec_key[key],
                             "T%02d-B%02d-W%02d" % (tft*1000, tfb*1000, tw*1000), p))
        return sec_key[key]

    # ── 요소 ──
    elems, eid = [], 0
    for g in ("G1", "G2"):
        arr = nG[g]
        for i in range(len(arr)-1):
            (n1, s1), (n2, s2) = arr[i], arr[i+1]
            eid += 1
            elems.append((eid, 1, sec_id(g, (s1+s2)/2), n1, n2))
    n_main = eid
    # 가로보: 같은 station 의 G1-G2 연결
    xsec = len(sec_list)+1
    p_x = sect_props(box["H"], 0.012, 0.400, 0.012, 0.400, 0.012,
                     0.0, 1.0, n, 0.400)     # 가로보(개략 I형) — 바닥판 미합성
    sec_list.append((xsec, "XBEAM", p_x))
    for j, s in enumerate(stations):
        if any(abs(s-v) < 0.05 for v in xb) or any(abs(s-v) < 1e-6 for v in sup_s):
            eid += 1
            elems.append((eid, 1, xsec, nG["G1"][j][0], nG["G2"][j][0]))
    n_xb = eid - n_main

    # ── MCT ──
    s = M.header("Suncheonman IC2 - Steel Box (A1~P5) 2-Girder Grillage", [
        "Spans 49.876+49.996+70.000+50.000+49.840 = %.3f m" % tot,
        "G1/G2 sections per 단면요약도(1)/(2), %d section types" % len(sec_list),
        "Curved (arc-interpolated), axis rotated to +X",
        "Composite deck t=300mm fck=27MPa, n=%.3f, b_eff=%.3fm/girder" % (n, b_eff),
        "Fixed bearing: P3 only",
    ])
    s += M.version() + M.unit() + M.structype()
    s += M.nodes(nodes) + M.elements(elems)
    s += ("\n*MATERIAL    ; Material\n"
          "    1, STEEL, SM490             , 0, 0, , C, YES, 0.02, 2, "
          " %.4e,   0.3,  1.2000e-05,     0,     0\n" % (spec["steel"]["Es"]*1000))
    s += "\n*SECT-PSCVALUE    ; PSC Value, General Section\n"
    for sid, nm, p in sec_list:
        s += (" SECT=%4d, VALUE     , %-18s, CC, 0, 0, 0, 0, 0, 0, YES, NO, GEN, YES, YES\n"
              "       %.6e, %.6e, %.6e, %.6e, %.6e, %.6e\n"
              "       0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
              "       0, 0, 0, 0, 0, 0, 0, 0\n" %
              (sid, nm, p["A"], p["Asy"], p["Asz"], p["J"], p["Iy"], p["Iz"]))

    s += M.stldcase([("DEAD", "D"), ("SDL", "D")])
    s += M.selfweight("DEAD")
    s += "\n*USE-STLD, SDL\n;  포장/방호벽 미입력 — 값 확정 후 BEAMLOAD 추가\n"

    # 지점: 각 지점의 G1/G2 절점
    fix, mov = [], []
    for nm, ss in zip(spec["supports"], sup_s):
        j = min(range(len(stations)), key=lambda k: abs(stations[k]-ss))
        for g in ("G1", "G2"):
            (fix if nm == spec["fixed_support"] else mov).append(str(nG[g][j][0]))
    s += "\n*CONSTRAINT    ; Supports\n"
    s += "   %s, 111100, \n" % " ".join(fix)
    s += "   %s, 011100, \n" % " ".join(mov)
    s += M.loadcomb("DL", [("DEAD", 1), ("SDL", 1)])
    s += M.enddata()
    open(outpath, "w", encoding="utf-8").write(s)
    return dict(nodes=nodes, elems=elems, sec=sec_list, n=n, b_eff=b_eff,
                stations=stations, nG=nG, sup_s=sup_s, P=P,
                n_main=n_main, n_xb=n_xb, G=G, tot=tot)


# ───────────────────── 검증 ─────────────────────
def verify(spec, I, path):
    c = Check(); b = parse_mct(path)
    c.add("절점 수", len(I["nodes"]), len(b.get("NODE", [])), 0)
    c.add("요소 수", len(I["elems"]), len(b.get("ELEMENT", [])), 0)
    c.add("주형요소", None, I["n_main"]); c.add("가로보요소", None, I["n_xb"])
    c.add("단면 종류", None, len(I["sec"]))

    nd, nG, sup_s, st = I["nodes"], I["nG"], I["sup_s"], I["stations"]
    # 경간장: G1 열의 지점절점 간 호길이 근사(요소길이 합)
    for gi, g in enumerate(("G1", "G2")):
        arr = nG[g]; tot = 0.0
        for i in range(len(arr)-1):
            a, bn = nd[arr[i][0]], nd[arr[i+1][0]]
            tot += math.hypot(bn[0]-a[0], bn[1]-a[1])
        c.add(f"{g} 총연장(호)", None, tot, unit="m")
    # 좌표 방향
    x_first = nd[nG["G1"][0][0]][0]
    x_last  = nd[nG["G1"][-1][0]][0]
    c.add("시점 X", None, x_first, unit="m")
    c.add("종점 X", None, x_last, unit="m")
    c.add("시점<종점 (1=OK)", 1.0, 1.0 if x_first < x_last else 0.0, 0)
    c.add("최대 Y 편차", None, max(abs(v[1]) for v in nd.values()), unit="m")

    # 단면: 최소/최대 Iy
    Iys = [p["Iy"] for _, nm, p in I["sec"] if nm != "XBEAM"]
    c.add("Iy 최소", None, min(Iys), unit="m4")
    c.add("Iy 최대", None, max(Iys), unit="m4")
    c.add("Iy 최대/최소", None, max(Iys)/min(Iys))
    c.add("유효폭/주형", None, I["b_eff"], unit="m")
    c.add("탄성계수비 n", None, I["n"])

    # 하중
    A_s = [p["A_s"] for _, nm, p in I["sec"] if nm != "XBEAM"]
    w_s = sum(A_s)/len(A_s)*GAMMA_S
    w_c = spec["deck"]["t"]*I["b_eff"]*GAMMA_C
    c.add("강재자중(평균,주형당)", None, w_s, unit="kN/m")
    c.add("바닥판자중(주형당)", None, w_c, unit="kN/m")
    c.add("합계(주형당)", None, w_s+w_c, unit="kN/m")
    c.add("전폭 환산 합계", None, 2*(w_s+w_c), unit="kN/m")
    return c


if __name__ == "__main__":
    out = os.path.join(SCR, "SCB_SuncheonmanIC2_Grillage.mct")
    I = build(SPEC, out)
    ck = verify(SPEC, I, out)
    print(ck.report())
    print("\n생성: " + out)
    sys.exit(1 if ck.failed else 0)

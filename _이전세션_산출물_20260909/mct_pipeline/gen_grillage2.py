# -*- coding: utf-8 -*-
"""
순천만IC 2교 강박스 (A1~P5) — 2주형 그릴리지 MCT  [rev.2]

rev.1 대비 변경
  ★ 플랜지 폭 수정 : 3950/3550(종방향 판길이) → 2240 (실제 폭, 계산서 b3=224.0cm)
  ★ 슬래브 유효두께 : 300 → 240 mm (계산서 Tc=24.0cm, 마모층 50 별도)
  ★ 헌치 Th=60mm 반영
  ★ 유효폭 : 일괄 4.335 → 계산서 경간별 9개 값 (G1/G2 별도)
  ★ 하중 : 2차 고정하중(마모층·방호벽) + 활하중 DB-24/DL-24 + 풍하중 + 온도

제원 출처
  준공도면 DXF 실측 + 구조계산서(05-01 순천만IC2교 구조계산서.pdf) 대조
"""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mct_syntax as M
from verify import Check, parse_mct

HERE = os.path.dirname(os.path.abspath(__file__))
SCR  = os.path.abspath(os.path.join(HERE, ".."))

SPEC = {
    "spans": [49.8756, 49.9955, 70.0000, 50.0000, 49.8400],
    "supports": ["A1", "P1", "P2", "P3", "P4", "P5"],
    "support_xy": [(155445278.7, 243636316.5), (155470976.3, 243679062.4),
                   (155499779.7, 243719927.0), (155540694.4, 243776724.8),
                   (155569919.2, 243817294.6), (155599050.5, 243857734.6)],
    "girder_offset": 4.270/2,
    "box": {
        "H": 2.300,            # 계산서 H=230.0cm
        "tw": 0.012,           # 웨브 t=1.2cm
        "tw_sup": 0.020,
        "web_spacing": 2.000,  # 계산서 b2=200.0cm (박스폭)
        "bf": 2.240,           # ★ 플랜지 폭 (계산서 b3=224.0cm)
        "rib_top": (5, 0.150, 0.014),   # 상부리브 5-150x14
        "rib_bot": (2, 0.150, 0.014),   # 하부리브 2-150x14
    },
    "deck": {"t_eff": 0.240,   # ★ 유효두께 (계산서 Tc)
             "t_act": 0.300,   # 실제 두께 (자중용)
             "haunch": 0.060,  # 헌치 Th
             "fck": 27.0, "B_total": 8.670},
    "steel": {"Es": 210000.0},
    "n_fixed": 8.0,            # 계산서 n=8 (단기), 장기는 3n
    "fixed_support": "P3",
    "xbeam_spacing": 12.5,
    "max_elem": 5.0,
    # ── 하중 (계산서 기준, kN 환산) ──
    "load": {
        "g_RC": 25.0, "g_steel": 78.5, "g_wearing": 23.5,
        "t_wearing": 0.050,        # 마모층 콘크리트 T=50mm
        "barrier": 10.0,           # 방호벽 kN/m (양측 각) — 가정, 아래 주석
        "DB24": {"Pr": 96.0, "Pf": 24.0},
        "DL24": {"Wl": 12.7, "Pm": 108.0, "Ps": 156.0},
        "wind": 1.50,              # kN/m2 (도로교설계기준 상부공)
        "temp": 15.0,              # ±15℃
        "temp_grad": 5.0,          # 온도구배 ℃
    },
}
GAMMA_S, GAMMA_C = 78.5, 25.0


def rib_area(n, w, t):
    return n*w*t


def sect_props(H, tw, bf, tft, tfb, t_deck, haunch, b_eff, n, s_web, box):
    """합성 박스 단면 — 계산서 방식(리브 포함)"""
    nt, wt, tt = box["rib_top"]; nb, wb, tb = box["rib_bot"]
    A_rt, A_rb = rib_area(nt, wt, tt), rib_area(nb, wb, tb)
    A_w  = 2*H*tw
    A_ft, A_fb = bf*tft, bf*tfb
    A_s  = A_w + A_ft + A_fb + A_rt + A_rb
    # 하부플랜지 하면 기준 도심
    y_fb = tfb/2
    y_rb = tfb + wb/2
    y_w  = tfb + H/2
    y_rt = tfb + H - wt/2
    y_ft = tfb + H + tft/2
    y_s  = (A_fb*y_fb + A_rb*y_rb + A_w*y_w + A_rt*y_rt + A_ft*y_ft)/A_s
    I_s  = (bf*tfb**3/12 + A_fb*(y_fb-y_s)**2) \
         + (A_rb*(y_rb-y_s)**2) \
         + (2*tw*H**3/12 + A_w*(y_w-y_s)**2) \
         + (A_rt*(y_rt-y_s)**2) \
         + (bf*tft**3/12 + A_ft*(y_ft-y_s)**2)
    # 합성
    b_tr = b_eff/n
    A_c  = b_tr*t_deck
    y_c  = tfb + H + tft + haunch + t_deck/2
    A_v  = A_s + A_c
    y_v  = (A_s*y_s + A_c*y_c)/A_v
    I_v  = I_s + A_s*(y_s-y_v)**2 + (b_tr*t_deck**3/12 + A_c*(y_c-y_v)**2)
    I_z  = 2*(H*tw*(s_web/2)**2) + tft*bf**3/12 + tfb*bf**3/12 + t_deck*b_tr**3/12
    # 비틀림 (계산서 K식: 폐단면)
    bk = s_web + tw
    hk = H + tft/2 + tfb/2
    K  = (4*bk**2*hk**2)/(2*hk/tw + bk/tft + bk/tfb)
    return dict(A=A_v, Iy=I_v, Iz=I_z, J=K, Asz=A_w, Asy=A_ft+A_fb,
                A_s=A_s, I_s=I_s, y_v=y_v)


def thick_at(segs, x):
    for s, e, L, th in segs:
        if s - 1e-6 <= x < e + 1e-6:
            return th
    return segs[-1][3]


def beff_at(tbl, x):
    """계산서 유효폭: 지점 ±0.2L 구간은 지점값, 그 외 지간값"""
    best, bd = tbl[0][3], 1e18
    for nm, s, e, v in tbl:
        c = (s+e)/2 if e > s else s
        d = abs(x-c)
        if d < bd: bd, best = d, v
    return best


def axis_points(spec):
    XY = spec["support_xy"]; X0, Y0 = XY[0]
    P = [((x-X0)/1000.0, (y-Y0)/1000.0) for x, y in XY]
    th = math.atan2(P[-1][1]-P[0][1], P[-1][0]-P[0][0])
    c, s = math.cos(-th), math.sin(-th)
    return [(x*c - y*s, x*s + y*c) for x, y in P]


def arc_interp(p0, p1, p2, t):
    (x0, y0), (x1, y1), (x2, y2) = p0, p1, p2
    d = 2*(x0*(y1-y2) + x1*(y2-y0) + x2*(y0-y1))
    if abs(d) < 1e-9:
        return (x0 + (x1-x0)*t, y0 + (y1-y0)*t)
    ux = ((x0**2+y0**2)*(y1-y2) + (x1**2+y1**2)*(y2-y0) + (x2**2+y2**2)*(y0-y1))/d
    uy = ((x0**2+y0**2)*(x2-x1) + (x1**2+y1**2)*(x0-x2) + (x2**2+y2**2)*(x1-x0))/d
    R  = math.hypot(x0-ux, y0-uy)
    a0 = math.atan2(y0-uy, x0-ux); a1 = math.atan2(y1-uy, x1-ux)
    while a1-a0 >  math.pi: a1 -= 2*math.pi
    while a1-a0 < -math.pi: a1 += 2*math.pi
    a = a0 + (a1-a0)*t
    return (ux + R*math.cos(a), uy + R*math.sin(a))


def build(spec, outpath):
    G   = json.load(open(os.path.join(SCR, "girder_sections.json"), encoding="utf-8"))
    EFF = json.load(open(os.path.join(SCR, "effective_width.json"), encoding="utf-8"))
    box, deck, LD = spec["box"], spec["deck"], spec["load"]
    n_ratio = spec["n_fixed"]
    P = axis_points(spec)
    tot = sum(spec["spans"])
    sup_s = [0.0]
    for L in spec["spans"]: sup_s.append(sup_s[-1]+L)

    cuts = {0.0, tot}
    for g in ("G1", "G2"):
        for k in ("top", "bot"):
            for s, e, L, th in G[g][k]:
                if 0 < s < tot: cuts.add(round(s, 4))
                if 0 < e < tot: cuts.add(round(e, 4))
    for s in sup_s[1:-1]: cuts.add(round(s, 4))
    cuts = sorted(cuts)
    stations = []
    for i in range(len(cuts)-1):
        a, b = cuts[i], cuts[i+1]
        m = max(1, int(math.ceil((b-a)/spec["max_elem"])))
        for k in range(m): stations.append(a + (b-a)*k/m)
    stations.append(tot)
    xb = set()
    x = 0.0
    while x < tot: xb.add(round(x, 4)); x += spec["xbeam_spacing"]
    for v in sorted(xb):
        if not any(abs(v-s) < 0.05 for s in stations): stations.append(v)
    stations = sorted(set(round(v, 4) for v in stations))

    def xy_at(s):
        for i in range(5):
            if sup_s[i]-1e-9 <= s <= sup_s[i+1]+1e-9:
                t = (s-sup_s[i])/spec["spans"][i]
                p = arc_interp(P[i], P[i+1], P[i+2] if i+2 < 6 else P[i-1], t)
                q = arc_interp(P[i], P[i+1], P[i+2] if i+2 < 6 else P[i-1], min(1, t+1e-4))
                return p, math.atan2(q[1]-p[1], q[0]-p[0])
        return P[-1], 0.0

    off = spec["girder_offset"]
    nodes, nG, nid = {}, {"G1": [], "G2": []}, 0
    for s in stations:
        (cx, cy), ang = xy_at(s)
        nx, ny = -math.sin(ang), math.cos(ang)
        for g, sgn in (("G1", +1), ("G2", -1)):
            nid += 1
            nodes[nid] = (cx + sgn*off*nx, cy + sgn*off*ny, 0.0)
            nG[g].append((nid, s))

    sec_key, sec_list = {}, []
    def sec_id(g, sm):
        tft = thick_at(G[g]["top"], sm)/1000.0
        tfb = thick_at(G[g]["bot"], sm)/1000.0
        tw  = box["tw_sup"] if min(abs(sm-v) for v in sup_s) < 5.0 else box["tw"]
        be  = beff_at(EFF[g], sm)
        key = (round(tft, 4), round(tfb, 4), round(tw, 4), round(be, 3))
        if key not in sec_key:
            p = sect_props(box["H"], tw, box["bf"], tft, tfb,
                           deck["t_eff"], deck["haunch"], be, n_ratio,
                           box["web_spacing"], box)
            sec_key[key] = len(sec_list)+1
            sec_list.append((sec_key[key],
                             "T%02d-B%02d-W%02d-E%04d" % (tft*1000, tfb*1000,
                                                          tw*1000, be*1000), p))
        return sec_key[key]

    elems, eid = [], 0
    for g in ("G1", "G2"):
        arr = nG[g]
        for i in range(len(arr)-1):
            (n1, s1), (n2, s2) = arr[i], arr[i+1]
            eid += 1
            elems.append((eid, 1, sec_id(g, (s1+s2)/2), n1, n2))
    n_main = eid
    xsec = len(sec_list)+1
    p_x = sect_props(box["H"], 0.012, 0.400, 0.012, 0.012, 0.0, 0.0,
                     1.0, n_ratio, 0.400, box)
    sec_list.append((xsec, "XBEAM", p_x))
    for j, s in enumerate(stations):
        if any(abs(s-v) < 0.05 for v in xb) or any(abs(s-v) < 1e-6 for v in sup_s):
            eid += 1
            elems.append((eid, 1, xsec, nG["G1"][j][0], nG["G2"][j][0]))
    n_xb = eid - n_main

    # ── 하중 산정 (주형당) ──
    w_deck = deck["t_act"]*(deck["B_total"]/2)*LD["g_RC"]          # 바닥판 자중
    w_wear = LD["t_wearing"]*(deck["B_total"]/2)*LD["g_wearing"]   # 마모층
    w_barr = LD["barrier"]                                          # 방호벽(주형당 1개)
    w_sdl  = w_wear + w_barr
    w_wind = LD["wind"]*(box["H"] + deck["t_act"])                  # 수평 풍하중 kN/m

    s = M.header("Suncheonman IC2 - Steel Box 2-Girder Grillage [rev.2]", [
        "Spans %.3f m, curved (arc), axis +X" % tot,
        "Flange width 2.240m (calc b3=224.0cm), deck Tc=240mm + haunch 60mm",
        "Effective width per span (calc report, G1/G2 separate)",
        "%d section types" % len(sec_list),
        "Loads: DEAD + SDL(wearing %.1f + barrier %.1f) + LL(DB24/DL24) + WIND + TEMP"
        % (w_wear, w_barr),
    ])
    s += M.version() + M.unit() + M.structype()
    s += M.nodes(nodes) + M.elements(elems)
    s += ("\n*MATERIAL    ; Material\n"
          "    1, STEEL, SM490             , 0, 0, , C, YES, 0.02, 2, "
          " %.4e,   0.3,  1.2000e-05,     0,     0\n" % (spec["steel"]["Es"]*1000))
    s += "\n*SECT-PSCVALUE    ; PSC Value, General Section\n"
    for sid, nm, p in sec_list:
        s += (" SECT=%4d, VALUE     , %-22s, CC, 0, 0, 0, 0, 0, 0, YES, NO, GEN, YES, YES\n"
              "       %.6e, %.6e, %.6e, %.6e, %.6e, %.6e\n"
              "       0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
              "       0, 0, 0, 0, 0, 0, 0, 0\n" %
              (sid, nm, p["A"], p["Asy"], p["Asz"], p["J"], p["Iy"], p["Iz"]))

    # 하중케이스
    s += M.stldcase([("DEAD", "D"), ("SDL", "D"), ("WIND", "W"), ("TEMP", "T")])
    s += M.selfweight("DEAD")
    # 바닥판 자중 + 2차하중을 주형 요소에 등분포로
    s += "\n*USE-STLD, DEAD\n*BEAMLOAD    ; Element Beam Loads\n"
    for (e, m, sc, n1, n2) in elems[:n_main]:
        s += ("%6d, BEAM   , UNILOAD, GZ, NO , NO, aDir[1], , , , 0, %.4f, 1, %.4f, "
              "0, 0, 0, 0, , NO, 0, 0, NO, \n" % (e, -w_deck, -w_deck))
    s += "\n*USE-STLD, SDL\n*BEAMLOAD    ; Element Beam Loads\n"
    for (e, m, sc, n1, n2) in elems[:n_main]:
        s += ("%6d, BEAM   , UNILOAD, GZ, NO , NO, aDir[1], , , , 0, %.4f, 1, %.4f, "
              "0, 0, 0, 0, , NO, 0, 0, NO, \n" % (e, -w_sdl, -w_sdl))
    # 풍하중 (횡방향 GY)
    s += "\n*USE-STLD, WIND\n*BEAMLOAD    ; Element Beam Loads\n"
    for (e, m, sc, n1, n2) in elems[:n_main]:
        s += ("%6d, BEAM   , UNILOAD, GY, NO , NO, aDir[1], , , , 0, %.4f, 1, %.4f, "
              "0, 0, 0, 0, , NO, 0, 0, NO, \n" % (e, w_wind/2, w_wind/2))
    # 온도
    s += ("\n*USE-STLD, TEMP\n*SYSTEMPER    ; System Temperature\n   %.1f\n"
          % spec["load"]["temp"])

    # ── 활하중 (이동하중) — 신형산교 실물 MCT 문법 검증 ──
    s += "\n*MVLDCODE    ; Moving Load Code\n   CODE=KOREA\n"
    # 차선: G1/G2 요소열을 각각 1개 차선으로. 요소를 이어서 나열
    s += "\n*LINELANE    ; Traffic Line Lanes\n"
    e_of = {"G1": [], "G2": []}
    for (e, m, sc, n1, n2) in elems[:n_main]:
        for g in ("G1", "G2"):
            ids = [x[0] for x in nG[g]]
            if n1 in ids and n2 in ids:
                e_of[g].append(e); break
    for li, g in enumerate(("G1", "G2"), start=1):
        s += "   NAME=L%d, CROSS, CROSS, 0, 0, FORWARD, 3, 0, NO\n" % li
        buf = []
        for k, e in enumerate(e_of[g]):
            buf.append("%6d, 0, 0, %s, 0" % (e, "YES" if k == 0 else "NO"))
        for k in range(0, len(buf), 3):
            s += "        " + ",   ".join(buf[k:k+3]) + "\n"
    # 차량: 표준 DB-24 / DL-24
    s += ("\n*VEHICLE    ; Vehicles\n"
          "   NAME=DB-24, 1, DB-24, 0, KS-RB\n"
          "   NAME=DL-24, 1, DL-24, 0, KS-RB\n")
    # 이동하중 케이스: 2차선
    s += "\n*MVLDCASE   ; Moving Load Cases\n"
    for si, veh in enumerate(("DB-24", "DL-24"), start=1):
        s += ("   NAME=%s, 0, 1, 1, 0.9, 0.75, 0.75, 0.75, INDEPENDENT, , 0, %d\n"
              "        1, 1, 1, 1, 0.5, 0.5, 0.25\n"
              "        VL, %s, 1, 1, 2, L1, L2\n" % (veh, si, veh))
    # 경계
    fix, mov = [], []
    for nm, ss in zip(spec["supports"], sup_s):
        j = min(range(len(stations)), key=lambda k: abs(stations[k]-ss))
        for g in ("G1", "G2"):
            (fix if nm == spec["fixed_support"] else mov).append(str(nG[g][j][0]))
    s += "\n*CONSTRAINT    ; Supports\n"
    s += "   %s, 111100, \n" % " ".join(fix)
    s += "   %s, 011100, \n" % " ".join(mov)

    # ── 하중조합 (ST=정적, MV=이동, CB=조합) ──
    def comb(name, terms, itype=0):
        t = "\n   NAME=%s, GEN, ACTIVE, 0, %d, , 0, 0\n        " % (name, itype)
        return t + ", ".join("%s, %s, %g" % (k, nm, f) for k, nm, f in terms) + "\n"
    s += "\n*LOADCOMB    ; Combinations\n"
    s += comb("DL",   [("ST", "DEAD", 1), ("ST", "SDL", 1)])
    s += comb("LL",   [("MV", "DB-24", 1), ("MV", "DL-24", 1)], itype=1)
    s += comb("DL+LL", [("CB", "DL", 1), ("CB", "LL", 1)])
    s += comb("SLS",  [("CB", "DL", 1), ("CB", "LL", 1),
                       ("ST", "WIND", 1), ("ST", "TEMP", 1)])
    s += M.enddata()
    open(outpath, "w", encoding="utf-8").write(s)
    return dict(nodes=nodes, elems=elems, sec=sec_list, stations=stations,
                nG=nG, sup_s=sup_s, n_main=n_main, n_xb=n_xb, tot=tot,
                w_deck=w_deck, w_wear=w_wear, w_barr=w_barr, w_wind=w_wind,
                EFF=EFF)


def verify(spec, I, path):
    c = Check(); b = parse_mct(path)
    c.add("절점 수", len(I["nodes"]), len(b.get("NODE", [])), 0)
    c.add("요소 수", len(I["elems"]), len(b.get("ELEMENT", [])), 0)
    c.add("주형/가로보", None, I["n_main"]); c.add("가로보", None, I["n_xb"])
    c.add("단면 종류", None, len(I["sec"]))
    # 계산서 단면-2 대조 (t_top=12,t_bot=12,tw=12,beff=4.335)
    tgt = [p for _, nm, p in I["sec"] if nm.startswith("T12-B12-W12-E4335")]
    if tgt:
        p = tgt[0]
        c.add("[대조] A  vs 계산서 0.2537", 0.2537, p["A"], 0.05, "m2")
        c.add("[대조] Iy vs 계산서 0.2166", 0.2166, p["Iy"], 0.10, "m4")
    Iys = [p["Iy"] for _, nm, p in I["sec"] if nm != "XBEAM"]
    c.add("Iy 최소", None, min(Iys), unit="m4")
    c.add("Iy 최대", None, max(Iys), unit="m4")
    c.add("유효폭 종류", None, len(set(round(beff_at(I["EFF"]["G1"], s), 3)
                                    for s in I["stations"])))
    c.add("[하중] 바닥판", None, I["w_deck"], unit="kN/m")
    c.add("[하중] 마모층", None, I["w_wear"], unit="kN/m")
    c.add("[하중] 방호벽", None, I["w_barr"], unit="kN/m")
    c.add("[하중] 풍하중", None, I["w_wind"], unit="kN/m")
    return c


if __name__ == "__main__":
    out = os.path.join(SCR, "SCB_SuncheonmanIC2_Grillage_rev2.mct")
    I = build(SPEC, out)
    ck = verify(SPEC, I, out)
    print(ck.report())
    print("\n생성: " + out)
    sys.exit(1 if ck.failed else 0)

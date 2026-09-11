# -*- coding: utf-8 -*-
"""
순천만IC 2교 강박스 구간 (A1~P5, 5경간 269.630m) 상부구조 MCT 생성.

제원 출처는 모두 준공도면 DXF 실측/추출:
  경간      : 받침 실좌표 역산 + 종평면도 (50mm 이내 일치)
  박스형상  : 가로보 상세도 도형 실측 (웨브 수직, 중심간격 2258)
  플랜지폭  : 상세도 TF/BF 부재 (상 3950 / 하 3550)
  구간분할  : 단면요약도 21구간 (지점부 3950이 P1~P4와 정확히 일치)
  바닥판    : t=300mm (준공 실제), fck=27MPa (제원표 25-270-15)
  받침      : 교량받침 집계표 (고정단 P3 1개소)
"""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mct_syntax as M
from verify import Check, parse_mct

# ─────────────────────────── 제원 ───────────────────────────
SPEC = {
    "name": "SCB_SuncheonmanIC2",
    "spans": [49.876, 49.996, 70.000, 50.000, 49.840],   # 좌표역산 (합 269.712)
    "supports": ["A1", "P1", "P2", "P3", "P4", "P5"],
    "support_xy": [                        # 실좌표 (mm) — 곡선 배치
        (155445278.7, 243636316.5),
        (155470976.3, 243679062.4),
        (155499779.7, 243719927.0),
        (155540694.4, 243776724.8),
        (155569919.2, 243817294.6),
        (155599050.5, 243857734.6),
    ],
    "box": {
        "H_mid": 2.300, "H_end": 2.100,    # 박스높이 (중앙부/단부)
        "tw": 0.012,                        # 웨브두께 (지배)
        "tw_sup": 0.020,                    # 지점부 웨브
        "web_spacing": 2.258,               # 웨브 중심간격 (도형 실측)
        "bf_top": 3.950, "bf_bot": 3.550,   # 플랜지 폭
        "tf_top": 0.020, "tf_bot": 0.022,   # 일반부 플랜지 두께
        "tf_top_sup": 0.038, "tf_bot_sup": 0.038,   # 지점부
    },
    "deck": {"t": 0.300, "B": 8.670, "fck": 27.0},
    "steel": {"Es": 210000.0, "fy": 315.0, "grade": "SM490B"},
    "mesh": 2.0,                            # 절점 간격 목표 (m)
    "fixed_support": "P3",                  # 고정단 (받침 집계표)
}

GAMMA_S = 76.98   # kN/m3 강재
GAMMA_C = 24.5    # kN/m3 콘크리트


# ────────────────────── 단면 특성 산정 ──────────────────────
def steel_props(H, tw, bft, tft, bfb, tfb):
    """강재 박스 단면 (하부플랜지 하면 기준)"""
    A_w, A_ft, A_fb = 2*H*tw, bft*tft, bfb*tfb
    A = A_w + A_ft + A_fb
    y_fb, y_w, y_ft = tfb/2, tfb + H/2, tfb + H + tft/2
    y = (A_fb*y_fb + A_w*y_w + A_ft*y_ft)/A
    I = (bfb*tfb**3/12 + A_fb*(y_fb-y)**2) \
      + (2*tw*H**3/12  + A_w *(y_w -y)**2) \
      + (bft*tft**3/12 + A_ft*(y_ft-y)**2)
    return A, I, y


def composite_props(H, tw, bft, tft, bfb, tfb, t_deck, B, n, s_web):
    """합성단면 — 환산단면법"""
    A_s, I_s, y_s = steel_props(H, tw, bft, tft, bfb, tfb)
    b_tr = B/n
    A_c = b_tr*t_deck
    y_c = tfb + H + tft + t_deck/2
    A_v = A_s + A_c
    y_v = (A_s*y_s + A_c*y_c)/A_v
    I_v = I_s + A_s*(y_s-y_v)**2 + (b_tr*t_deck**3/12 + A_c*(y_c-y_v)**2)

    # 약축 Iz (박스 폐단면)
    I_z = 2*(H*tw*(s_web/2)**2) + (tft*bft**3/12) + (tfb*bfb**3/12) \
        + (t_deck*b_tr**3/12)/1.0
    # 비틀림 J — 폐단면 Bredt: J = 4*Am^2 / ∮(ds/t)
    b_m = (bft+bfb)/2
    Am = b_m * H
    ds_t = 2*(H/tw) + b_m/tft + b_m/tfb
    J = 4*Am**2/ds_t
    # 전단유효면적: 강축전단은 웨브, 약축전단은 플랜지가 부담
    Asz = 2*H*tw                       # 연직전단 → 웨브 2매
    Asy = bft*tft + bfb*tfb            # 수평전단 → 상하 플랜지
    return dict(A=A_v, Iy=I_v, Iz=I_z, J=J, yv=y_v, Asy=Asy, Asz=Asz,
                A_s=A_s, I_s=I_s, y_s=y_s, b_tr=b_tr, Am=Am)


# ──────────────────────── 모델 생성 ────────────────────────
def build(spec, outpath):
    box, deck = spec["box"], spec["deck"]
    Ec = 8500.0*((deck["fck"]+4.0)**(1.0/3.0))
    n = spec["steel"]["Es"]/Ec

    # 단면 2종: 일반부 / 지점부
    sec = {}
    sec["MID"] = composite_props(box["H_mid"], box["tw"],
                                 box["bf_top"], box["tf_top"],
                                 box["bf_bot"], box["tf_bot"],
                                 deck["t"], deck["B"], n, box["web_spacing"])
    sec["SUP"] = composite_props(box["H_mid"], box["tw_sup"],
                                 box["bf_top"], box["tf_top_sup"],
                                 box["bf_bot"], box["tf_bot_sup"],
                                 deck["t"], deck["B"], n, box["web_spacing"])

    # 절점: 곡선 배치 — 지점 실좌표를 잇고 그 사이를 등분
    XY = spec["support_xy"]
    X0, Y0 = XY[0]
    nodes, node_at_support = {}, []
    nid = 0
    cum = 0.0
    for i in range(len(XY)-1):
        L = spec["spans"][i]
        m = max(2, int(round(L/spec["mesh"])))
        for k in range(m + (1 if i == len(XY)-2 else 0)):
            f = k/m
            x = (XY[i][0] + (XY[i+1][0]-XY[i][0])*f - X0)/1000.0
            y = (XY[i][1] + (XY[i+1][1]-XY[i][1])*f - Y0)/1000.0
            nid += 1
            nodes[nid] = (x, y, 0.0)
            if k == 0:
                node_at_support.append(nid)
        cum += L
    node_at_support.append(nid)   # P5

    # 요소: 지점 ±5m 는 지점부 단면(2), 그 외 일반부(1)
    elems = []
    sup_nodes = set(node_at_support)
    for e in range(1, nid):
        n1, n2 = e, e+1
        xm = (nodes[n1][0]+nodes[n2][0])/2, (nodes[n1][1]+nodes[n2][1])/2
        near = False
        for sn in node_at_support:
            d = math.hypot(xm[0]-nodes[sn][0], xm[1]-nodes[sn][1])
            if d < 5.0: near = True; break
        elems.append((e, 1, 2 if near else 1, n1, n2))

    # ── MCT 조립 ──
    s  = M.header("Suncheonman IC2 Bridge - Steel Box Girder (A1~P5)", [
        "5 spans: 49.876+49.996+70.000+50.000+49.840 = 269.712 m",
        "Curved alignment - node coords from as-built bearing coordinates",
        "Composite: steel box + RC deck t=300mm, fck=27MPa, n=%.3f" % n,
        "Fixed bearing at P3 only (per bearing schedule)",
    ])
    s += M.version() + M.unit() + M.structype()
    s += M.nodes(nodes) + M.elements(elems)

    # 재료: 1=강재 (합성단면 강성을 강재기준 환산했으므로 Es 사용)
    s += ("\n*MATERIAL    ; Material\n"
          "    1, STEEL, SM490             , 0, 0, , C, YES, 0.02, 2, "
          " %.4e,   0.3,  1.2000e-05,     0,     0\n" % (spec["steel"]["Es"]*1000))

    # 단면: VALUE 타입 (강성 직접 입력) — 산정값을 그대로 쓰므로 검증 가능
    #   실물 검증(금남1교 mct): *SECT-PSCVALUE 블록, " SECT=" 접두,
    #   값 6개는 Area, Asy, Asz, Ixx(비틀림), Iyy, Izz 순서
    s += "\n*SECT-PSCVALUE    ; PSC Value, General Section\n"
    for i, k in enumerate(["MID", "SUP"], start=1):
        p = sec[k]
        s += (" SECT=%4d, VALUE     , BOX-%-14s, CC, 0, 0, 0, 0, 0, 0, YES, NO, GEN, YES, YES\n"
              "       %.6e, %.6e, %.6e, %.6e, %.6e, %.6e\n"
              "       0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
              "       0, 0, 0, 0, 0, 0, 0, 0\n" %
              (i, k, p["A"], p["Asy"], p["Asz"], p["J"], p["Iy"], p["Iz"]))

    # 하중
    cases = [("DEAD", "D"), ("SDL", "D")]
    s += M.stldcase(cases)
    s += M.selfweight("DEAD")

    # 2차 고정하중(포장·방호벽) — 도면 미확인이므로 0 처리, 사용자 입력 대기
    s += "\n*USE-STLD, SDL\n;  포장/방호벽 하중 미입력 (도면 확인 후 BEAMLOAD 추가)\n"

    # 경계: 받침 = ELASTICLINK 대신 CONSTRAINT (분리모델, 하부 반력 추출용)
    #   고정단 P3: 3방향 구속 / 그 외: 연직+횡 (종방향 자유)
    grp_fix, grp_mov = [], []
    for nm, sn in zip(spec["supports"], node_at_support):
        (grp_fix if nm == spec["fixed_support"] else grp_mov).append(str(sn))
    s += "\n*CONSTRAINT    ; Supports\n"
    s += "   %s, 111100, \n" % " ".join(grp_fix)   # 고정단 Dx,Dy,Dz,Rx
    s += "   %s, 011100, \n" % " ".join(grp_mov)   # 가동단 Dy,Dz,Rx (Dx 자유)

    s += M.loadcomb("DL", [(c, 1) for c, _ in cases])
    s += M.enddata()
    open(outpath, "w", encoding="utf-8").write(s)
    return dict(nodes=nodes, elems=elems, sec=sec, n=n, Ec=Ec,
                sup_nodes=node_at_support)


# ────────────────────────── 검증 ──────────────────────────
def verify(spec, info, outpath):
    c = Check()
    b = parse_mct(outpath)
    c.add("절점 수", len(info["nodes"]), len(b.get("NODE", [])), 0)
    c.add("요소 수", len(info["elems"]), len(b.get("ELEMENT", [])), 0)
    c.add("지점 수", 6, len(info["sup_nodes"]), 0)

    # 경간장 재확인 (절점 좌표에서)
    nd, sn = info["nodes"], info["sup_nodes"]
    tot = 0.0
    for i in range(5):
        a, bb = nd[sn[i]], nd[sn[i+1]]
        d = math.hypot(bb[0]-a[0], bb[1]-a[1])
        tot += d
        c.add(f"경간 S{i+1}", spec["spans"][i], d, 2e-3, "m")
    c.add("총연장", sum(spec["spans"]), tot, 1e-3, "m")

    # 단면 특성
    p = info["sec"]["MID"]
    c.add("[MID] A", None, p["A"], unit="m2")
    c.add("[MID] Iy", None, p["Iy"], unit="m4")
    c.add("[MID] Iz", None, p["Iz"], unit="m4")
    c.add("[MID] J", None, p["J"], unit="m4")
    c.add("[MID] 강재만 A", None, p["A_s"], unit="m2")
    q = info["sec"]["SUP"]
    c.add("[SUP] A", None, q["A"], unit="m2")
    c.add("[SUP] Iy", None, q["Iy"], unit="m4")
    c.add("Iy 지점/일반 비", None, q["Iy"]/p["Iy"])
    c.add("탄성계수비 n", None, info["n"])

    # 자중 개략 (강재 + 바닥판)
    w_s = p["A_s"]*GAMMA_S
    w_c = spec["deck"]["t"]*spec["deck"]["B"]*GAMMA_C
    c.add("[하중] 강재자중", None, w_s, unit="kN/m")
    c.add("[하중] 바닥판자중", None, w_c, unit="kN/m")
    c.add("[하중] 합계", None, w_s+w_c, unit="kN/m")

    # 이론 검토: 5경간 연속보 중앙경간(70m) 개략 부모멘트
    w = w_s + w_c
    L = spec["spans"][2]
    c.add("[이론] 70m경간 wL²/12", None, -w*L*L/12, unit="kN.m")
    c.add("[이론] 70m경간 wL²/24", None,  w*L*L/24, unit="kN.m")
    return c


if __name__ == "__main__":
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                       "SCB_SuncheonmanIC2_Super.mct"))
    info = build(SPEC, out)
    ck = verify(SPEC, info, out)
    print(ck.report())
    print("\n생성: " + out)
    sys.exit(1 if ck.failed else 0)

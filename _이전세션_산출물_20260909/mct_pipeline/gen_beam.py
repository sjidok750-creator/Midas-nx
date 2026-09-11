# -*- coding: utf-8 -*-
"""제원표(dict) -> MCT 생성. 5m 보를 첫 회귀 케이스로 삼는다."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mct_syntax as M
from verify import Check, parse_mct, rect_props, fixed_fixed_moments

SPEC = {
    "title": "Fixed-Fixed RC Beam (regression case)",
    "length": 5.0, "dx": 0.1,
    "support_x": [0.1, 4.9],
    "section": {"H": 0.6, "B": 1.0, "name": "RECT600x1000"},
    "material": {"fck": 24.0, "name": "C24"},
    "point_load": {"x": 2.5, "Fz": -5.0},
    "selfweight": True, "gamma_c": 24.5,
}

def build(spec, outpath):
    L, dx = spec["length"], spec["dx"]
    n = int(round(L/dx))
    nodes = {i+1: (round(i*dx,6), 0.0, 0.0) for i in range(n+1)}
    elems = [(e+1, 1, 1, e+1, e+2) for e in range(n)]
    def nid(x): return int(round(x/dx))+1

    fck = spec["material"]["fck"]
    Ec = 8500.0*((fck+4.0)**(1.0/3.0))      # MPa, KDS
    Ec_kn = Ec*1000.0                        # kN/m2
    H,B = spec["section"]["H"], spec["section"]["B"]

    s  = M.header(spec["title"], [
            f"L={L}m, supports at x={spec['support_x']}",
            f"Section {B*1000:.0f}x{H*1000:.0f}, fck={fck}MPa, Ec={Ec:.0f}MPa"])
    s += M.version() + M.unit() + M.structype()
    s += M.nodes(nodes) + M.elements(elems)
    s += M.material_conc(1, spec["material"]["name"], Ec_kn)
    s += M.section_rect(1, spec["section"]["name"], H, B)

    cases=[]
    if spec.get("selfweight"): cases.append(("SELFWEIGHT","D"))
    if spec.get("point_load"): cases.append(("POINT","D"))
    s += M.stldcase(cases)
    if spec.get("selfweight"): s += M.selfweight("SELFWEIGHT")
    if spec.get("point_load"):
        pl=spec["point_load"]
        s += M.conload("POINT", [(nid(pl["x"]),0,0,pl["Fz"],0,0,0)])
    s += M.constraint([(" ".join(str(nid(x)) for x in spec["support_x"]), "111111")])
    s += M.loadcomb("ALL", [(c,1) for c,_ in cases])
    s += M.enddata()
    open(outpath,"w",encoding="utf-8").write(s)
    return dict(nodes=nodes, elems=elems, Ec=Ec, H=H, B=B, nid=nid)

def verify(spec, info, outpath):
    c = Check()
    b = parse_mct(outpath)
    c.add("절점 수", len(info["nodes"]), len(b.get("NODE",[])), 0)
    c.add("요소 수", len(info["elems"]), len(b.get("ELEMENT",[])), 0)
    p = rect_props(info["H"], info["B"])
    c.add("단면적 A", p["A"], p["A"], 0, "m2")
    c.add("Iy (강축)", p["Iy"], p["Iy"], 0, "m4")
    c.add("비틀림 J", p["J"], p["J"], 0, "m4")
    c.add("Ec (KDS)", 8500*((spec['material']['fck']+4)**(1/3)), info["Ec"], 1e-9, "MPa")

    Ls = spec["support_x"][1]-spec["support_x"][0]
    w  = spec["gamma_c"]*p["A"]
    P  = abs(spec["point_load"]["Fz"])
    th = fixed_fixed_moments(P, w, Ls)
    c.add("[이론] 지간", None, Ls, unit="m")
    c.add("[이론] 자중 w", None, w, unit="kN/m")
    c.add("[이론] 중앙M(집중)", None, th["mid_P"], unit="kN.m")
    c.add("[이론] 중앙M(자중)", None, th["mid_w"], unit="kN.m")
    c.add("[이론] 중앙M(합계)", None, th["mid_tot"], unit="kN.m")
    c.add("[이론] 단부M(합계)", None, th["end_tot"], unit="kN.m")

    # 지점/하중 절점이 실제로 그 좌표에 있는지
    for x in spec["support_x"]:
        c.add(f"지점절점 x={x}", x, info["nodes"][info["nid"](x)][0], 1e-9, "m")
    px = spec["point_load"]["x"]
    c.add(f"하중절점 x={px}", px, info["nodes"][info["nid"](px)][0], 1e-9, "m")
    return c

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "RC_Beam_5m.mct")
    out = os.path.abspath(out)
    info = build(SPEC, out)
    c = verify(SPEC, info, out)
    print(c.report())
    print(f"\n생성: {out}")
    sys.exit(1 if c.failed else 0)

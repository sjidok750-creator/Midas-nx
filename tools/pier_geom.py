# -*- coding: utf-8 -*-
"""
교각 일반도(DXF) 정면도에서 Y형 코핑의 정면 단면적·도심을 적분 (도면 판독기 4/4)
  python pier_geom.py <dxf파일|폴더> [--layer CS-CONC]
원리: 정면도의 코핑 외곽은 콘크리트 레이어의 호(ARC) 4개(좌·우 외측 호, 좌·우 내측 호)와 상단 수평선으로 구성된다.
  1) 기둥 상단 y0 = 내·외측 호 하단점 높이(내측 호는 기둥 중앙 홈 연단에서, 외측 호는 기둥 연단에서 시작)
  2) 상면 y_top = 호가 끝나는 높이 이상에 있는 가장 긴 수평선(코핑 상면, 횡단경사로 좌·우 다를 수 있음)
  3) 높이 y마다 외측 경계 xo(y)(외측 호 → 호 상단 이후는 연직), 내측 경계 xi(y)(내측 호) → 반폭 (xo−xi) 적분
출력: 면적(m²), 기둥 상단 기준 도심 높이(m), 호 반지름, 상폭, 내측 호 상단 개구폭. 단위는 도면 mm → m 환산.
검증: 순천만IC2교 P3(C0051105-020) 21.142 m², 도심 3.331 m (2026-09-11).
"""
import sys, os, glob, math, json
import ezdxf


def coping_area(path, layer="CS-CONC", n=6000):
    doc = ezdxf.readfile(path); msp = doc.modelspace()
    arcs = [e for e in msp if e.dxftype() == "ARC" and e.dxf.layer == layer and e.dxf.radius >= 3000]
    if len(arcs) < 4: return dict(file=os.path.basename(path), error=f"큰 호 {len(arcs)}개 (4개 필요)")

    def endpoints(a):
        c, r = a.dxf.center, a.dxf.radius
        p = [(c.x + r * math.cos(math.radians(t)), c.y + r * math.sin(math.radians(t))) for t in (a.dxf.start_angle, a.dxf.end_angle)]
        return sorted(p, key=lambda q: q[1])                      # (하단점, 상단점)
    # 정면도 후보: 하단점 높이가 비슷한 호 4개 묶음
    best = None
    for a in arcs:
        y0 = endpoints(a)[0][1]; x0 = endpoints(a)[0][0]
        grp = [b for b in arcs if abs(endpoints(b)[0][1] - y0) < 200 and abs(endpoints(b)[0][0] - x0) < 8000]   # 같은 뷰(정면도)의 호만
        if len(grp) >= 4 and (best is None or len(grp) > len(best)): best = grp
    if not best: return dict(file=os.path.basename(path), error="정면도 호 묶음 없음")
    y0 = sum(endpoints(a)[0][1] for a in best) / len(best)
    xc = sum(endpoints(a)[0][0] for a in best) / len(best)          # 기둥 중심 x
    left = sorted([a for a in best if endpoints(a)[0][0] < xc], key=lambda a: endpoints(a)[0][0])     # 바깥쪽부터
    right = sorted([a for a in best if endpoints(a)[0][0] >= xc], key=lambda a: -endpoints(a)[0][0])
    if len(left) < 2 or len(right) < 2: return dict(file=os.path.basename(path), error="좌/우 호 2개씩 필요")
    y_arc_top = max(endpoints(a)[1][1] for a in best)
    # 상면: 호 상단 근처(±1500) 위쪽의 긴 수평선 (좌·우 각각 가장 가까운 것)
    hl = [e for e in msp if e.dxftype() == "LINE" and e.dxf.layer == layer and abs(e.dxf.start.y - e.dxf.end.y) < 1 and abs(e.dxf.start.x - e.dxf.end.x) > 1500
          and y_arc_top - 1500 < e.dxf.start.y < y_arc_top + 1500 and min(e.dxf.start.x, e.dxf.end.x) > xc - 6000 and max(e.dxf.start.x, e.dxf.end.x) < xc + 6000]
    def top_y(sign):
        c = [e for e in hl if (max(e.dxf.start.x, e.dxf.end.x) + min(e.dxf.start.x, e.dxf.end.x)) / 2 * sign > xc * sign]
        return max(e.dxf.start.y for e in c) if c else y_arc_top
    def x_on(a, y, sign):
        c, r = a.dxf.center, a.dxf.radius; d = y - c.y
        if abs(d) > r: return None
        return c.x - sign * math.sqrt(r * r - d * d)             # 호는 코핑 반대쪽에 중심이 있음
    def half(outer, inner, sign):
        yt = top_y(sign); o_top = endpoints(outer)[1]; A = 0.0; Mz = 0.0; dy = (yt - y0) / n; xo_v = o_top[0]
        for k in range(n):
            y = y0 + (k + 0.5) * dy
            xo = x_on(outer, y, sign) if y <= o_top[1] else xo_v
            xi = x_on(inner, y, sign)
            if xo is None or xi is None: continue
            w = sign * (xo - xi)
            if w > 0: A += w * dy; Mz += w * dy * (y - y0)
        return A, Mz, yt, xo_v
    AR, MR, ytR, xoR = half(right[0], right[1], +1); AL, ML, ytL, xoL = half(left[0], left[1], -1)
    A = (AR + AL) / 1e6; zc = (MR + ML) / (AR + AL) / 1e3
    gap = (abs(x_on(right[1], ytR - 1, +1) - xc) + abs(x_on(left[1], ytL - 1, -1) - xc)) / 1e3 if x_on(right[1], ytR - 1, +1) and x_on(left[1], ytL - 1, -1) else None
    return dict(file=os.path.basename(path), area_m2=round(A, 3), centroid_above_column_m=round(zc, 3), top_width_m=round((xoR - xoL) / 1e3, 3),
                height_m=round((max(ytR, ytL) - y0) / 1e3, 3), height_LR_m=[round((ytL - y0) / 1e3, 3), round((ytR - y0) / 1e3, 3)],
                R_outer=[round(left[0].dxf.radius / 1e3, 2), round(right[0].dxf.radius / 1e3, 2)], R_inner=[round(left[1].dxf.radius / 1e3, 2), round(right[1].dxf.radius / 1e3, 2)],
                notch_top_opening_m=round(gap, 3) if gap else None, column_top_width_m=round((endpoints(right[0])[0][0] - endpoints(left[0])[0][0]) / 1e3, 3))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]; layer = "CS-CONC"
    if "--layer" in a: i = a.index("--layer"); layer = a[i + 1]; del a[i:i + 2]
    files = sorted(glob.glob(os.path.join(a[0], "*교각*.dxf"))) if os.path.isdir(a[0]) else [a[0]]
    for f in files:
        print(json.dumps(coping_area(f, layer), ensure_ascii=False))

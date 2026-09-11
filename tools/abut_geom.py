# -*- coding: utf-8 -*-
"""
교대 일반도(DXF 추출 JSON)에서 단면 A-A 형상과 말뚝 배치를 **좌표로** 읽어 방향(앞굽/뒷굽)까지 판정하는 판독기.
  python abut_geom.py <extract json> <dxf> <출력 json> [--check png]
판정 규칙 (2026-09-10 순천만IC2교 A1 오독 사례에서 정립):
  1. '단면 A-A' 제목 아래에서 같은 y줄에 있는 3개의 연속 치수(a, 벽체, b)를 찾는다 → 기초폭 = a+벽체+b
  2. 받침 쪽(교량 쪽 = 앞굽)은 'SHOE'/'받침' 문자 x가 벽체 중심의 어느 쪽인지로 정한다
  3. 흉벽 쪽(뒷채움 쪽 = 뒷굽)은 상단 치수(예 2.200) 아래 소치수(300, 500 …)가 벽체 중심의 어느 쪽인지로 교차검증
  4. 헌치 '1:1' 문자 위치로 헌치가 어느 면(앞/뒤)에 있는지
  5. 기초평면도의 열 치수(100|700|…|100)로 말뚝 열 위치, 말뚝 기호(INSERT/CIRCLE/ARC)를 세어 본수
  6. 판정 근거를 모두 json에 남기고 --check 로 판정 결과를 도면 위에 표시한 PNG를 만든다 (사람 확인용)
"""
import sys, os, json, re, math
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))

def num(t):
    t = t.replace(",", "").strip()
    return float(t) if re.fullmatch(r"\d+(\.\d+)?", t) else None

def find_title(T, pat):
    hs = [t for t in T if re.search(pat, t["text"].replace(" ", ""))]
    hs.sort(key=lambda t: -t["h"]); return hs[0] if hs else None

def section_geometry(T):
    """단면 A-A 영역의 문자에서 형상 추출"""
    ttl = find_title(T, r"^단면A-?A$"); assert ttl, "단면 A-A 제목 없음"
    sx, sy = ttl["x"], ttl["y"]
    reg = [t for t in T if abs(t["x"] - sx) < 9000 and sy - 20000 < t["y"] < sy + 500]
    nums = [(t, num(t["text"])) for t in reg]; nums = [(t, v) for t, v in nums if v is not None]
    # 1) 같은 y줄의 3연속 치수(m 단위 소수) 중 합이 3~12 m 인 조합 → 기초폭 행
    rows = {}
    for t, v in nums:
        if "." in t["text"] and 0.3 <= v <= 12: rows.setdefault(round(t["y"] / 150), []).append((t["x"], v, t))
    best = None
    for y, items in rows.items():
        items.sort()
        for i in range(len(items) - 2):
            a, s, b = items[i][1], items[i + 1][1], items[i + 2][1]
            if 0.6 <= s <= 2.5 and 3.0 <= a + s + b <= 12 and abs(items[i + 2][0] - items[i][0]) < 9000:
                cand = dict(y=items[i][2]["y"], left=a, stem=s, right=b, x_left=items[i][0], x_stem=items[i + 1][0], x_right=items[i + 2][0], B=round(a + s + b, 3))
                if best is None or cand["y"] > best["y"]: best = cand   # 여러 줄이면 위쪽(구체 치수) 우선
    assert best, "기초폭 3연속 치수 없음"
    xc = best["x_stem"]
    # 2) 받침 쪽
    # 2) 받침 쪽: 'SHOE'/'받침' 문자가 벽체 중심에서 400 이상 떨어져 있을 때만 판정에 사용 (벽체 바로 위면 판정 불가)
    shoe = [t for t in reg if re.search(r"SHOE|받침", t["text"], re.I) and abs(t["x"] - xc) > 400]
    seat_side = ("right" if shoe[0]["x"] > xc else "left") if shoe else None
    # 3) 흉벽 쪽(1차 판정): 상단(단면 제목 아래 7000 이내) mm 소치수(200~900)의 평균 x — 흉벽·받침 단차 치수는 뒷채움 쪽 상단에 몰린다
    top = [t for t, v in nums if sy - 7000 < t["y"] < sy and "." not in t["text"] and 200 <= v <= 900]
    par_side = None
    if top:
        mx = sum(t["x"] for t in top) / len(top); par_side = "left" if mx < xc else "right"
    # 4) 헌치: 정확히 '1:1'인 문자만 (축척 'S=1:100' 제외), 벽체 하단에 가장 가까운 것
    h = [t for t in reg if re.fullmatch(r"1\s*:\s*1", t["text"].strip())]
    h.sort(key=lambda t: abs(t["y"] - best["y"]))
    haunch_side = ("right" if h[0]["x"] > xc else "left") if h else None
    # 판정: 흉벽 쪽 반대가 앞굽(교량 쪽). 받침 쪽 판정이 있으면 교차검증
    front = {"left": "right", "right": "left"}[par_side] if par_side else seat_side
    flag = ""
    if seat_side and par_side and seat_side == par_side: flag = "★ 받침 쪽과 흉벽 쪽이 같은 방향으로 판정됨 — 사람 확인 필요"
    if front is None: flag = "★ 방향 판정 불가 — 사람 확인 필요"
    # 받침 중심의 앞굽 연단 기준 거리 (도면 1:100 → 1 m = 1000 단위). 'SHOE' 문자(벽체 위 포함) 중 벽체 하단 치수줄에 가장 가까운 것
    shoe_all = sorted([t for t in reg if re.search(r"SHOE|받침", t["text"], re.I)], key=lambda t: abs(t["y"] - best["y"]))
    x_shoe = None
    if shoe_all and front:
        sgn = 1 if front == "right" else -1
        toe_edge_x = xc + sgn * (best["stem"] / 2 + (best["right"] if front == "right" else best["left"])) * 1000
        x_shoe = round(abs(toe_edge_x - shoe_all[0]["x"]) / 1000, 3)
    toe = best["right"] if front == "right" else best["left"]; heel = best["left"] if front == "right" else best["right"]
    # 높이 치수: 단면 영역 세로 치수(1.200 기초, 8.000 전체 등) — 가장 큰 값 = 전체 높이, 1.0~1.5 하단 = 기초두께 (근사, 확인표에 표시)
    vert = sorted({v for t, v in nums if "." in t["text"] and 0.8 <= v <= 15 and abs(t["x"] - xc) > 3500}, reverse=True)
    return dict(B=best["B"], toe=toe, stem=best["stem"], heel=heel, front_side=front, seat_side=seat_side, parapet_side=par_side, haunch_side=haunch_side,
                haunch_on=("back" if haunch_side and haunch_side != front else ("front" if haunch_side else None)),
                x_shoe_from_toe=x_shoe, heights_found=vert[:8], flag=flag, dims_row=dict(left=best["left"], stem=best["stem"], right=best["right"], y=best["y"]))

def pile_layout(T, dxf_path):
    """기초평면도: 열 치수(mm, 100|700|…|100)와 말뚝 기호 개수"""
    ttl = find_title(T, r"^기초평면도$")
    if not ttl: return dict(flag="기초평면도 제목 없음")
    fx, fy = ttl["x"], ttl["y"]
    reg = [t for t in T if abs(t["x"] - fx) < 9000 and fy - 14000 < t["y"] < fy + 500]
    # 세로 열 치수: 같은 x(회전 문자)에서 mm 값 나열, 또는 같은 y줄의 mm 값 나열 → 100으로 시작·끝나는 나열 찾기
    mm = [(t, num(t["text"].replace("@", "").split("=")[-1])) for t in reg]
    mm = [(t, v) for t, v in mm if v is not None and "." not in t["text"] and 50 <= v <= 6000]
    by_y = {}; by_x = {}
    for t, v in mm: by_y.setdefault(round(t["y"] / 200), []).append((t["x"], v)); by_x.setdefault(round(t["x"] / 200), []).append((t["y"], v))
    def seq(groups, key):
        out = []
        for g in groups.values():
            g.sort(); vals = [v for _, v in g]
            if len(vals) >= 4 and vals[0] == 100 and vals[-1] == 100: out.append(vals)
        return out
    seqs = seq(by_y, "y") + seq(by_x, "x")
    rows = []
    for vals in seqs:
        inner = vals[1:-1]; pos = []; acc = 0.0
        for v in inner[:-1]:
            acc += v; pos.append(round(acc / 1000, 3))
        rows.append(dict(dims=vals, positions_from_edge=pos, width=round(sum(inner) / 1000, 3)))
    # 말뚝 기호 개수: DXF에서 기초평면도 영역의 INSERT/CIRCLE/ARC 중심 군집
    n_sym = None
    try:
        import ezdxf
        d = ezdxf.readfile(dxf_path); msp = d.modelspace(); pts = []
        for e in msp:
            c = None
            if e.dxftype() == "INSERT": c = (e.dxf.insert.x, e.dxf.insert.y)
            elif e.dxftype() in ("CIRCLE", "ARC"): c = (e.dxf.center.x, e.dxf.center.y)
            if c and abs(c[0] - fx) < 9000 and fy - 14000 < c[1] < fy: pts.append(c)
        # 반경 300 이내 군집을 하나로
        cl = []
        for p in pts:
            if not any(math.hypot(p[0] - q[0], p[1] - q[1]) < 300 for q in cl): cl.append(p)
        n_sym = len(cl); ys = sorted({round(p[1] / 500) for p in cl}); xs = sorted({round(p[0] / 500) for p in cl})
        grid = dict(n_rows=len(ys), n_cols=len(xs))
    except Exception as e:
        grid = dict(err=str(e)[:80])
    return dict(row_dims=rows, n_symbols=n_sym, grid=grid)

def main():
    a = sys.argv[1:]; ex, dxf, out = a[0], a[1], a[2]
    T = json.load(open(ex, encoding="utf-8"))["texts"]
    g = section_geometry(T); p = pile_layout(T, dxf)
    res = dict(source=os.path.basename(ex), section=g, piles=p)
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if "--check" in a:
        png = a[a.index("--check") + 1]
    return res

if __name__ == "__main__":
    main()

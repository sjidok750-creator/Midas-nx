# -*- coding: utf-8 -*-
"""
순천만IC2교 제원서 생성 — 추출 JSON(도면) → 제원서.json + 제원_확인표.md
도면에서 기계적으로 뽑을 수 있는 것은 뽑고, 사람이 읽은 값은 출처 도면번호와 함께 적는다.
"""
import json, os, re, sys, math
sys.stdout.reconfigure(encoding="utf-8")

PJ = r"D:\Midas\projects\순천만IC2교"
EX = os.path.join(PJ, "extract")
def load(name):
    return json.load(open(os.path.join(EX, name + ".json"), encoding="utf-8"))

# ---------- 1. 지점 좌표 (교량받침 배치도) ----------
def supports():
    d = load("C0051104-082-순천만IC 2교 교량받침 배치도")
    T = d["texts"]
    xs = [t for t in T if re.match(r"^X\s*=\s*[\d.]+$", t["text"])]
    ys = [t for t in T if re.match(r"^Y\s*=\s*[\d.]+$", t["text"])]
    labels = [t for t in T if re.match(r"^(A1|P[1-5])$", t["text"])]
    near = lambda t, c: min(c, key=lambda k: (k["x"]-t["x"])**2 + (k["y"]-t["y"])**2)
    groups = {}
    for xt in xs:
        yt, lb = near(xt, ys), near(xt, labels)
        groups.setdefault(lb["text"], []).append((xt["y"], float(xt["text"].split("=")[1]), float(yt["text"].split("=")[1])))
    # 각 라벨의 좌표 3개(받침1, 도로중심선, 받침2) 중 중심선은 "다른 두 점의 중점에 가장 가까운 점"
    def centre(pts):
        best = None
        for c in pts:
            others = [p for p in pts if p is not c]
            mx = sum(p[1] for p in others) / len(others); my = sum(p[2] for p in others) / len(others)
            err = math.hypot(c[1] - mx, c[2] - my)
            if best is None or err < best[0]:
                best = (err, c)
        return best[1]
    out, alt = {}, {}
    PLAN = {"A1": 49.840, "P4P5": 49.890}      # 종평면도 표기 (단부 경간) — A1·P5는 표가 둘이라 이 값에 맞는 쪽을 택함
    for lb, rows in groups.items():
        rows = sorted(set(rows))
        if len(rows) >= 6:                    # A1·P5: 표가 둘 → 후보 전부 보관, 아래서 종평면도 경간으로 선택
            alt[lb] = rows
        else:
            c = centre(rows)
            out[lb] = dict(X=c[1] / 1000, Y=c[2] / 1000)
    order = ["A1", "P1", "P2", "P3", "P4", "P5"]
    for lb, nb, key in [("A1", "P1", "A1"), ("P5", "P4", "P4P5")]:
        cands = alt[lb]
        span = lambda c: math.hypot(c[1] / 1000 - out[nb]["X"], c[2] / 1000 - out[nb]["Y"])
        best = min(cands, key=lambda c: abs(span(c) - PLAN[key]))
        out[lb] = dict(X=best[1] / 1000, Y=best[2] / 1000, plan_span=PLAN[key], picked_span=round(span(best), 3),
                       alternatives=[dict(X=c[1] / 1000, Y=c[2] / 1000, span=round(span(c), 3)) for c in cands if c is not best])
    spans = []
    for a, b in zip(order, order[1:]):
        dx, dy = out[b]["X"] - out[a]["X"], out[b]["Y"] - out[a]["Y"]
        spans.append(round(math.hypot(dx, dy), 3))
    return {k: out[k] for k in order}, spans

# ---------- 2. 판두께 분할 (단면 요약도) ----------
def plates():
    d = load("C0051104-080-순천만IC 2교 단면 요약도(1)")
    T = d["texts"]
    def row_at(label):
        lab = next(t for t in T if t["text"].replace(" ", "") == label)
        same = [t for t in T if abs(t["y"] - lab["y"]) < lab["h"] * 0.8 and t["x"] > lab["x"]]
        return lab, sorted(same, key=lambda t: t["x"])
    def thick_row_below(lab, ref_y):
        cands = [t for t in T if re.match(r"^\(\d+mm\)$", t["text"]) and ref_y - lab["h"] * 3 < t["y"] < ref_y - lab["h"] * 0.3]
        return sorted(cands, key=lambda t: t["x"])
    res = {}
    def segments(label, band=0.8):
        """라벨과 같은 줄(±band·h)의 길이 숫자 + 각 숫자에 x가 가장 가까운 두께 '(NNmm)' 문자"""
        lab = next(t for t in T if t["text"].replace(" ", "") == label)
        nums = [t for t in T if abs(t["y"] - lab["y"]) < lab["h"] * band and t["x"] > lab["x"] and re.match(r"^\d{3,6}$", t["text"])]
        nums.sort(key=lambda t: t["x"])
        ths = [t for t in T if re.match(r"^\(\d+mm\)$", t["text"]) and 0 < lab["y"] - t["y"] < lab["h"] * (band + 5)]
        out = []
        for t in nums:   # 두께 문자는 길이 숫자 바로 아래 → x·y 거리로 가장 가까운 것
            near = min(ths, key=lambda h: math.hypot(h["x"] - t["x"], h["y"] - t["y"]))
            out.append((int(t["text"]), int(near["text"][1:-3]), t["x"]))
        return lab, out
    lab, top = segments("상판")
    res["top"] = [(L, th) for L, th, _ in top]
    # 하판: 지점부(P2·P3) 5 m 구간 4개가 한 줄 아래에 따로 적혀 있음 → 넓은 띠로 수집
    lab, bot = segments("하판", band=4.0)
    res["bot"] = [(L, th) for L, th, _ in bot]
    # 복부판: '복부판 두께 | 269630' + '(12mm)' → 전장 균일
    lab = next(t for t in T if t["text"].replace(" ", "") == "복부판두께")
    full = [t for t in T if abs(t["y"] - lab["y"]) < lab["h"] * 0.8 and t["x"] > lab["x"] and re.match(r"^\d{6}$", t["text"])]
    ths = [t for t in T if re.match(r"^\(\d+mm\)$", t["text"]) and 0 < lab["y"] - t["y"] < lab["h"] * 3]
    near = min(ths, key=lambda h: math.hypot(h["x"] - full[0]["x"], h["y"] - full[0]["y"])) if full and ths else None
    res["web"] = dict(length_mm=[int(t["text"]) for t in full], thickness_mm=[int(near["text"][1:-3])] if near else [])
    res["girder_length"] = 269.630
    return res

def check_sum(segs, total):
    return round(sum(L for L, _ in segs) / 1000, 3), round(total, 3)

# ---------- 3. 사람이 읽은 값 (출처 병기) ----------
MANUAL = {
    "교량형식": ("합성형 STEEL BOX GIRDER 2련(G1, G2), 5경간 연속", "C0051101-001 교량제원, C0051104-001 슬래브 일반도(1)"),
    "경간구성(도면표기)": ("2@50+70+2@50 = 270 m (강박스), PSC BEAM 4@35 = 140.232 m 별도", "C0051101-001, 종평면도"),
    "폭원": (8.670, "C0051101-001 / C0051104-001 횡단면"),
    "횡단구성(m)": ("방호벽측 1.200 | 박스 2.000 | 박스간 2.270 | 박스 2.000 | 1.200 (합 8.670)", "C0051104-001 횡단면 확대"),
    "거더중심간격": (4.270, "C0051104-082 받침 간격 = 2.000 + 2.270"),
    "박스 폭(복부 내측)": (2.000, "C0051104-001 횡단면; 단면도(5) DIAP PL-2300x2000"),
    "복부": ("수직 (경사 없음)", "C0051104-001 횡단면 확대 — 박스 외곽이 직사각형"),
    "박스 높이": ("단부 2.100 m(A1측 단면), 지점부 2.300 m(DIAP PL-2300)", "C0051104-014 일반도(1), C0051104-067 단면도(5), 단면도(8) 잭업보강재 2100/2300"),
    "슬래브 두께": ("300 mm (박스 직상), 편경사로 346.8 mm까지 변화; 헌치 1:5", "C0051104-001 표 V1~V4"),
    "슬래브 콘크리트": ("fck = 270 kgf/cm² ≈ 27 MPa, SD40 (fy 4,000)", "C0051101-001 사용재료, C0051104-001 표제"),
    "강재": ("주부재 SM490B, 부부재 SM400B", "C0051104-080/082 표제"),
    "하부 콘크리트": ("교대·교각 fck 240 kgf/cm² ≈ 24 MPa, SD30; 기초 150", "C0051101-001"),
    "설계하중": ("DB-24, DL-24 (1등교)", "C0051101-001"),
    "내진": ("1등급, A = 0.154", "C0051101-001"),
    "사각": ("90° (직각)", "C0051101-001"),
    "평면선형": ("곡선 R=487.3 + 완화 + 곡선 R=600 (교량 구간 곡선)", "C0051101-001, 종평면도"),
    "종단경사": ("+4.0977 % ~ +2.4663 %", "C0051101-001"),
    "편경사": ("−2.0 % (일부 −2.5~−3.0 %)", "C0051104-071 가로보 치수표"),
    "다이아프램 간격": ("5.000 m (38@5.000 = 190 m 등)", "C0051104-001"),
    "받침": ("지점당 2개, 간격 4.270 m; A1 250톤, P1·P4 600톤, P2·P3 700톤; 고정단 P3 1개(나머지 일방향/양방향)", "C0051104-082 집계표 + 받침좌표"),
    "가로보(박스 사이)": ("I형: 상·하플랜지 PL-1430x300x12, 복부 PL-1430x1200x12 (높이 1,200, 길이 1,430), SM400B; 위치 1CR01~1CR55", "C0051104-072 가로보 상세도(1), C0051104-071 치수표"),
    "복부판 두께": ("12 mm 전장 균일 (요약도 '복부판 두께 269630 (12mm)'). 일반도(2)의 T=14/30/38 행은 상·하판 두께 행으로 확인", "C0051104-080 단면 요약도(1), C0051104-015 일반도(2)"),
    "설계방법": ("허용응력설계법 (주형), 강도설계법 (슬래브)", "C0051101-001"),
    "설계 휨모멘트(정답지, ton·m)": ("Max(−) P1 −2306.6, P2 −3643.9, P3 −3642.9, P4 −2326.1; Max(+) 1935.5 / 547.3 / 2278.3 / 546.7 / 1957.4", "C0051104-080 단면 요약도(1) 모멘트도 — 어느 하중조합인지 미확인"),
}

CHECK = [
    ("A1/P5 방향", "받침 배치도의 라벨 위치로 A1 = X 155599.05 / P5 = X 155445.28 로 읽었음. 9/9 추출은 반대였음. 종평면도 경간(49.840 … 49.890) 순서와 이번 판독이 일치하지만 도면에서 직접 확인 필요"),
    ("고정단 위치", "집계표는 P3 고정단 1개. 받침좌표표의 '700톤 고정단' 좌표(X 155503.4)도 P3에 해당 → 일치. 다만 배치도 첫 집계표에는 고정단 0으로 나오는 행이 있어 확인 필요"),
    ("경간장", "받침좌표 역산 49.84/50.00/70.00/50.00/49.88 vs 종평면도 49.840/50.000/70.000/50.000/49.890. 단면요약도의 49.290/49.340은 거더 단부 500 제외 분절 길이"),
    ("2차 고정하중", "포장 두께(도면 'T=50mm' 표기 확인), 방호벽 단면(450/620) 중량 — 구조계산서 값으로 확정 필요"),
    ("종리브·수평보강재", "단면 특성에 종리브(U-rib 등) 포함 여부 — 구조계산서 단면표와 대조"),
    ("모멘트도 하중조합", "단면 요약도의 Max 값이 어느 조합(합성전/후, D+L+I)인지 미확인"),
    ("슬래브 유효폭", "설계기준으로 계산(경간별) — 9/9 effective_width.json 재검토"),
]

def main():
    sup, spans = supports()
    pl = plates()
    spec = dict(
        bridge="순천만IC 2교 (강박스 구간)", date="2026-09-10",
        supports=sup, spans_from_coords=spans,
        plates=pl, manual={k: dict(value=v[0], source=v[1]) for k, v in MANUAL.items()},
        to_confirm=[dict(item=a, note=b) for a, b in CHECK],
    )
    with open(os.path.join(PJ, "제원서.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)

    L = ["# 순천만IC 2교 강박스 구간 — 제원 확인표", "", "작성 2026-09-10(목). 출처는 준공도면 번호. **확인 필요** 항목에 답을 주시면 모델 생성으로 넘어갑니다.", ""]
    L += ["## 1. 지점 좌표 (도로중심선, m) — 교량받침 배치도에서 자동 추출", "", "| 지점 | X | Y | 다음 지점까지 |", "| :-- | --: | --: | --: |"]
    keys = list(sup)
    for i, k in enumerate(keys):
        L.append(f"| {k} | {sup[k]['X']:.4f} | {sup[k]['Y']:.4f} | {spans[i] if i < len(spans) else ''} |")
    L.append(f"| 합계 | | | {round(sum(spans), 3)} |")
    L += ["", "## 2. 판두께 분할 (단면 요약도 자동 추출, mm) — 시점(A1)→종점(P5)", ""]
    for key, name in [("top", "상판"), ("bot", "하판")]:
        segs = pl[key]; s, tot = check_sum(segs, pl["girder_length"])
        L.append(f"**{name}** ({len(segs)}분할, 합 {s} m / 거더길이 {tot} m)")
        L.append("")
        L.append("| # | 길이 | 두께 |" + " ".join("" for _ in range(0)))
        L.append("| --: | --: | --: |")
        for i, (a, b) in enumerate(segs, 1):
            L.append(f"| {i} | {a} | {b} |")
        L.append("")
    L.append(f"**복부판**: 요약도 표기 길이 {pl['web']['length_mm']} mm, 두께 {pl['web']['thickness_mm']} mm (전장 균일로 읽힘 — 확인 필요 항목 참조)")
    L += ["", "## 3. 판독 값 (출처 병기)", "", "| 항목 | 값 | 출처 |", "| :-- | :-- | :-- |"]
    for k, (v, src) in MANUAL.items():
        L.append(f"| {k} | {v} | {src} |")
    L += ["", "## 4. 확인 필요 (모델 생성 전 답 필요)", ""]
    for i, (a, b) in enumerate(CHECK, 1):
        L.append(f"{i}. **{a}** — {b}")
    with open(os.path.join(PJ, "제원_확인표.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print("지점:", {k: (round(v['X'], 3), round(v['Y'], 3)) for k, v in sup.items()})
    print("경간:", spans, "합", round(sum(spans), 3))
    print("상판 분할", len(pl["top"]), "합", check_sum(pl["top"], pl["girder_length"]))
    print("하판 분할", len(pl["bot"]), "합", check_sum(pl["bot"], pl["girder_length"]))
    print("복부", pl["web"])
    print("하판:", pl["bot"])
    print("저장:", os.path.join(PJ, "제원서.json"), "/ 제원_확인표.md")

if __name__ == "__main__":
    main()

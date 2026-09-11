# -*- coding: utf-8 -*-
p = r"D:\Midas\projects\순천만IC2교\stress3.py"
s = open(p, encoding="utf-8").read()
if "def fca_local" in s:
    print("already"); raise SystemExit
old = 'FA_STEEL = lambda t: 190.0 if t <= 0.040 else 175.0'
new = '''FA_STEEL = lambda t: 190.0 if t <= 0.040 else 175.0
def fca_local(t, n_rib, b=2.0, i=1.0):
    """종리브로 보강된 압축플랜지 허용압축응력 (도로교설계기준 허용응력, 2021 보고서 산식: b/(t·i·n) 기준, kgf/cm² → MPa)
    r = b/(t·i·n): r ≤ 24 → 190 ; 24 < r ≤ 61 → 190 − 3.9(r − 24) ; r > 61 → 2,200,000/r² kgf/cm²"""
    n = n_rib + 1; r = (b * 100) / (t * 100 * i * n)
    if r <= 24: return 190.0
    if r <= 61: return (1900 - 39 * (r - 24)) * 0.0980665
    return 2200000 / r ** 2 * 0.0980665'''
assert old in s; s = s.replace(old, new)
# 압축연 허용응력 적용: 정모멘트부 상연(압축, 상부 리브), 부모멘트부 하연(압축, 하부 리브)
old2 = '''            fa0 = FA_STEEL(max(sec["tft"], sec["tfb"]))
            for cid, (nm, fac) in CASES.items():
                mx, mn = combo(cid, "max"), combo(cid, "min")
                fa, fc = fa0 * fac, FA_CONC * fac
                peak = max(abs(mx[0]), abs(mn[0]), abs(mx[1]), abs(mn[1]))'''
new2 = '''            fa0 = FA_STEEL(max(sec["tft"], sec["tfb"]))
            nt, nb = (G.RIB_NEG if sec["neg"] else G.RIB_POS)
            fca_top, fca_bot = min(fa0, fca_local(sec["tft"], nt)), min(fa0, fca_local(sec["tfb"], nb))   # 압축 시 허용 (국부좌굴)
            rec["fca"] = (round(fca_top, 1), round(fca_bot, 1))
            for cid, (nm, fac) in CASES.items():
                mx, mn = combo(cid, "max"), combo(cid, "min")
                fa, fc = fa0 * fac, FA_CONC * fac
                # 위치별 응력비: 인장은 fa, 압축은 fca(국부좌굴) 기준
                def ratio_of(v, fca): return abs(v) / ((fa if v >= 0 else fca * fac) if abs(v) > 1e-9 else 1e9)
                peak_ratio = max(ratio_of(mx[0], fca_top), ratio_of(mn[0], fca_top), ratio_of(mx[1], fca_bot), ratio_of(mn[1], fca_bot))
                peak = max(abs(mx[0]), abs(mn[0]), abs(mx[1]), abs(mn[1]))'''
assert old2 in s; s = s.replace(old2, new2)
old3 = '''                rec["cases"][cid] = dict(max=[round(x, 2) for x in mx], min=[round(x, 2) for x in mn], fa=fa, fc=fc, sf=round(fa / peak, 3) if peak else 99.0,'''
new3 = '''                rec["cases"][cid] = dict(max=[round(x, 2) for x in mx], min=[round(x, 2) for x in mn], fa=fa, fc=fc, fca_top=round(fca_top * fac, 1), fca_bot=round(fca_bot * fac, 1),
                                         sf=round(1 / peak_ratio, 3) if peak_ratio > 0 else 99.0,'''
assert old3 in s; s = s.replace(old3, new3)
open(p, "w", encoding="utf-8").write(s); print("patched fca")

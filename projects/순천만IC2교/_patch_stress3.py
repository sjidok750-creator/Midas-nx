# -*- coding: utf-8 -*-
import sys
p = r"D:\Midas\projects\순천만IC2교\stress3.py"
s = open(p, encoding="utf-8").read()
if "cb_" in s:
    print("already patched"); sys.exit(0)
rep = []
rep.append(('''        st_ = -My * sec["y_top"] / I + Fx / A; sb_ = -My * sec["y_bot"] / I + Fx / A; ct_ = 0.0; rb_ = 0.0
    elif stage == "rebar":''', '''        st_ = -My * sec["y_top"] / I + Fx / A; sb_ = -My * sec["y_bot"] / I + Fx / A; ct_ = 0.0; rb_ = 0.0; cb_ = 0.0
    elif stage == "rebar":'''))
rep.append(('''        st_ = -My * yt / I + Fx / A; sb_ = -My * yb / I + Fx / A; ct_ = 0.0; rb_ = -My * yr / I + Fx / A
    else:''', '''        st_ = -My * yt / I + Fx / A; sb_ = -My * yb / I + Fx / A; ct_ = 0.0; rb_ = -My * yr / I + Fx / A; cb_ = 0.0
    else:'''))
rep.append(('''        yt, yb, yc = sec["y_top"] - c["dvs"], sec["y_bot"] - c["dvs"], c["dvc"] + G.TC / 2
        st_ = -My * yt / I + Fx / A; sb_ = -My * yb / I + Fx / A; ct_ = (-My * yc / I + Fx / A) / (n or N); rb_ = 0.0
    tau = abs(Fz) / sec["Aw"] + abs(Mx) / (2 * sec["Fk"] * G.TW)
    return tuple(v * MPA for v in (st_, sb_, ct_, rb_, tau, lat / I22))''',
'''        yt, yb, yc, ycb = sec["y_top"] - c["dvs"], sec["y_bot"] - c["dvs"], c["dvc"] + G.TC / 2, c["dvc"] - G.TC / 2
        st_ = -My * yt / I + Fx / A; sb_ = -My * yb / I + Fx / A; ct_ = (-My * yc / I + Fx / A) / (n or N); rb_ = 0.0; cb_ = (-My * ycb / I + Fx / A) / (n or N)
    tau = abs(Fz) / sec["Aw"] + abs(Mx) / (2 * sec["Fk"] * G.TW)
    return tuple(v * MPA for v in (st_, sb_, ct_, rb_, tau, lat / I22, cb_))'''))
rep.append(('''    yt, yb, yc = sec["y_top"] - c["dvs"], sec["y_bot"] - c["dvs"], c["dvc"] + G.TC / 2
    st_ = P / c["A"] + k * M * yt / c["I33"]; sb_ = P / c["A"] + k * M * yb / c["I33"]; ct_ = (P / c["A"] + k * M * yc / c["I33"]) / n
    return st_ * MPA, sb_ * MPA, ct_ * MPA''',
'''    yt, yb, yc, ycb = sec["y_top"] - c["dvs"], sec["y_bot"] - c["dvs"], c["dvc"] + G.TC / 2, c["dvc"] - G.TC / 2
    st_ = P / c["A"] + k * M * yt / c["I33"]; sb_ = P / c["A"] + k * M * yb / c["I33"]; ct_ = (P / c["A"] + k * M * yc / c["I33"]) / n; cb_ = (P / c["A"] + k * M * ycb / c["I33"]) / n
    return st_ * MPA, sb_ * MPA, ct_ * MPA, cb_ * MPA'''))
rep.append(('''    st_, sb_, ct_ = eccentric_force(sec, N1, P, k)
    fcu = sig(sec, {"My": msc, "Fz": 0, "Mz": 0, "Fx": 0, "Mx": 0}, "comp")[2]     # 합성후 사하중에 의한 바닥판 응력
    ct_ = ct_ - fcu * PHI1 / (1 + PHI1 / 2)                                         # 계산서: − Ec1·fcu·Φ1/Ec, Ec1 = Ec/(1+Φ1/2)
    return st_, sb_, ct_''',
'''    st_, sb_, ct_, cb_ = eccentric_force(sec, N1, P, k)
    fc = sig(sec, {"My": msc, "Fz": 0, "Mz": 0, "Fx": 0, "Mx": 0}, "comp")          # 합성후 사하중에 의한 바닥판 응력 (상연 [2], 하연 [6])
    ct_ = ct_ - fc[2] * PHI1 / (1 + PHI1 / 2); cb_ = cb_ - fc[6] * PHI1 / (1 + PHI1 / 2)   # 계산서: − Ec1·fcu·Φ1/Ec
    return st_, sb_, ct_, cb_'''))
rep.append(('''    st_, sb_, ct_ = eccentric_force(sec, N2, -P2, k)
    ct_ += G.ES * EPS_S / N2 * MPA
    return st_, sb_, ct_''', '''    st_, sb_, ct_, cb_ = eccentric_force(sec, N2, -P2, k)
    ct_ += G.ES * EPS_S / N2 * MPA; cb_ += G.ES * EPS_S / N2 * MPA
    return st_, sb_, ct_, cb_'''))
rep.append(('''    st_, sb_, ct_ = eccentric_force(sec, N, -P1, k)
    ct_ += G.ES * ALPHA * DT * sign / N * MPA
    return st_, sb_, ct_''', '''    st_, sb_, ct_, cb_ = eccentric_force(sec, N, -P1, k)
    ct_ += G.ES * ALPHA * DT * sign / N * MPA; cb_ += G.ES * ALPHA * DT * sign / N * MPA
    return st_, sb_, ct_, cb_'''))
old = '''            def combo(cid, side):
                L = Lmax if side == "max" else Lmin
                v = [d1[i] + d2[i] for i in range(4)] if cid >= 2 else [d1[0], d1[1], 0.0, 0.0]
                if cid >= 2:
                    for i in range(4): v[i] += L[i] + (abs(cf[i]) if side == "max" else -abs(cf[i]))
                    lat = cf[5] * (1 if side == "max" else -1); v[0] += lat; v[1] += lat
                if cid >= 3:
                    for i in range(3): v[i] += cr[i]
                if cid >= 4:
                    for i in range(3): v[i] += sh[i]
                if cid in (5, 8):
                    for i in range(3): v[i] += td[i]
                    for i in range(4): v[i] += max(tp[i], tm[i]) if side == "max" else min(tp[i], tm[i])
                if cid in (6, 9):
                    for i in range(3): v[i] -= td[i]
                    for i in range(4): v[i] += max(tp[i], tm[i]) if side == "max" else min(tp[i], tm[i])
                if cid >= 7:
                    for i in range(4):
                        a = abs(w[i]) + abs(wl[i]) + abs(lf[i]); v[i] += a if side == "max" else -a
                    lat = w[5] + wl[5] + lf[5]; v[0] += lat if side == "max" else -lat; v[1] += lat if side == "max" else -lat
                if hog and side == "min": v[2] = 0.0        # 부모멘트부 콘크리트 무시
                if not hog: v[3] = 0.0
                return v'''
new = '''            IDX = [0, 1, 2, 3, 6]          # v = [강재상연, 강재하연, 콘크리트상연, 철근, 콘크리트하연]
            CI = {0: 0, 1: 1, 2: 2, 4: 3}  # 크리프·건조수축·온도차 반환 (st, sb, ct, cb) → v 인덱스
            def combo(cid, side):
                L = Lmax if side == "max" else Lmin
                v = [d1[i] + d2[i] for i in IDX] if cid >= 2 else [d1[0], d1[1], 0.0, 0.0, 0.0]
                sg = 1 if side == "max" else -1
                if cid >= 2:
                    for j, i in enumerate(IDX): v[j] += L[i] + sg * abs(cf[i])
                    v[0] += sg * cf[5]; v[1] += sg * cf[5]
                if cid >= 3:
                    for j, i in CI.items(): v[j] += cr[i]
                if cid >= 4:
                    for j, i in CI.items(): v[j] += sh[i]
                if cid in (5, 6, 8, 9):
                    tsg = 1 if cid in (5, 8) else -1
                    for j, i in CI.items(): v[j] += tsg * td[i]
                    for j, i in enumerate(IDX): v[j] += max(tp[i], tm[i]) if side == "max" else min(tp[i], tm[i])
                if cid >= 7:
                    for j, i in enumerate(IDX): v[j] += sg * (abs(w[i]) + abs(wl[i]) + abs(lf[i]))
                    lat = w[5] + wl[5] + lf[5]; v[0] += sg * lat; v[1] += sg * lat
                if hog and side == "min": v[2] = 0.0; v[4] = 0.0        # 부모멘트부 콘크리트 무시
                if not hog: v[3] = 0.0
                return v'''
rep.append((old, new))
rep.append(('''                rec["cases"][cid] = dict(max=[round(x, 2) for x in mx], min=[round(x, 2) for x in mn], fa=fa, fc=fc, sf=round(fa / peak, 3) if peak else 99.0,
                                         sf_c=round(fc / max(abs(min(mx[2], mn[2], 0.0)), 1e-9), 3) if min(mx[2], mn[2]) < 0 else 99.0)''',
'''                cmin = min(mx[2], mn[2], mx[4], mn[4], 0.0)
                rec["cases"][cid] = dict(max=[round(x, 2) for x in mx], min=[round(x, 2) for x in mn], fa=fa, fc=fc, sf=round(fa / peak, 3) if peak else 99.0,
                                         sf_c=round(fc / max(abs(cmin), 1e-9), 3) if cmin < 0 else 99.0)'''))
rep.append(('''                       parts=dict(D1=[round(x, 2) for x in d1[:4]], D2=[round(x, 2) for x in d2[:4]], LLmax=[round(x, 2) for x in Lmax[:4]], LLmin=[round(x, 2) for x in Lmin[:4]],
                                  CR=[round(x, 2) for x in cr], SH=[round(x, 2) for x in sh], TD=[round(x, 2) for x in td], W=[round(x, 2) for x in w[:4]]),''',
'''                       parts=dict(D1=[round(d1[i], 2) for i in IDX], D2=[round(d2[i], 2) for i in IDX], LLmax=[round(Lmax[i], 2) for i in IDX], LLmin=[round(Lmin[i], 2) for i in IDX],
                                  CR=[round(x, 2) for x in cr], SH=[round(x, 2) for x in sh], TD=[round(x, 2) for x in td], W=[round(w[i], 2) for i in IDX],
                                  CF=[round(cf[i], 2) for i in IDX], WL=[round(wl[i], 2) for i in IDX], LF=[round(lf[i], 2) for i in IDX], TP=[round(tp[i], 2) for i in IDX]),'''))
for o, n in rep:
    assert o in s, o[:60]
    s = s.replace(o, n)
open(p, "w", encoding="utf-8").write(s); print("patched", len(rep))

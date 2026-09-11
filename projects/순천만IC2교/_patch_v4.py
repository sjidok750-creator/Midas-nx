# -*- coding: utf-8 -*-
import sys; sys.stdout.reconfigure(encoding="utf-8")
p = 'build_ch5_v4.py'; s = open(p, encoding='utf-8').read()
def rep(old, new):
    global s
    assert old in s, old[:60]; s = s.replace(old, new)
rep('''from hwpx_table import new_table, new_para, insert_after, fix_layout, merge_cells''', '''from hwpx_table import new_table, new_para, insert_after, fix_layout, merge_cells
from derive import abutment_lines, pier_lines''')
rep('''    B.table("토압계수", [["구분", "안정검토 (가상배면)", "벽체·흉벽 단면검토 (구체배면)"]] + [[r[0], str(r[1]), str(r[2])] for r in cond["table"]], widths=[1.4, 1.5, 1.8])''',
    '''    B.table("토압계수", [["구분", "안정검토 (가상배면)", "벽체·흉벽 단면검토 (구체배면)"]] + [[r[0], str(r[1]), str(r[2])] for r in cond["table"]], widths=[1.4, 1.5, 1.8])
    LA = abutment_lines(A)
    for ln in LA["step4"]: B.body(ln)''')
rep('''    data = [["구분", "수직력 (kN)", "수평력 (kN)", "x (m)", "y (m)", "M저항 (kN·m)", "M전도 (kN·m)"]]
    for r in A["loads"]: data.append([r["name"], f2(r["V"]), f2(r["H"]), f3(r["x"]), f3(r["y"]), f2(r["Mr"]), f2(r["Mo"])])
    for k, v in c.items(): data.append([k, f2(v["V"]), f2(v["H"]), f"ξ = {v['xi']:.3f}", f"e = {v['e']:.3f}", f2(v["Mr"]), f2(v["Mo"])])
    B.table("교대(A1) 하중집계 (단위폭, 앞굽 연단 기준)", data, widths=[2.6, 1, 1, 0.9, 0.9, 1.1, 1.1])''',
    '''    data = [["구분", "수직력 (kN)", "수평력 (kN)", "x (m) [합계: ξ]", "y (m) [합계: e]", "M저항 (kN·m)", "M전도 (kN·m)"]]
    for r in A["loads"]: data.append([r["name"], f2(r["V"]), f2(r["H"]), f3(r["x"]), f3(r["y"]), f2(r["Mr"]), f2(r["Mo"])])
    for k, v in c.items(): data.append([k, f2(v["V"]), f2(v["H"]), f3(v["xi"]), f3(v["e"]), f2(v["Mr"]), f2(v["Mo"])])
    B.table("교대(A1) 하중집계 (단위폭, 앞굽 연단 기준)", data, widths=[2.6, 1, 1, 1, 1, 1.1, 1.1])
    for ln in LA["step5"]: B.body(ln)''')
rep('''    B.table("교대(A1) 말뚝 반력 (사용하중, kN/본)", data, widths=[2] + [0.9] * (len(data[0]) - 1))''',
    '''    B.table("교대(A1) 말뚝 반력 (사용하중, kN/본)", data, widths=[2] + [0.9] * (len(data[0]) - 1))
    for ln in LA["step6"]: B.body(ln)''')
rep('''    data.append(["흉벽", "계수 단면력", "", f2(pa["Vu"]), "", f2(pa["Mu"]), "Vu, Mu"])
    B.table("벽체·흉벽 단면력", data, widths=[0.8, 1.6, 2.2, 1, 0.9, 1.2, 0.9])''',
    '''    data.append(["흉벽", "계수 단면력 A (토압+상재)", "", f2(pa["VuA"]), "", f2(pa["MuA"]), "Vu, Mu"]); data.append(["흉벽", "계수 단면력 B (토압+윤하중)", "", f2(pa["Vu"]), "", f2(pa["Mu"]), "Vu, Mu"])
    B.table("벽체·흉벽 단면력", data, widths=[0.8, 1.9, 2.2, 1, 0.9, 1.2, 0.9])''')
rep('''            ["흉벽 기부", pa["bar"], f0(pa["As"]), f0(pa["d"]), f1(pa["Mu"]), f1(pa["phiMn"]), f3(pa["ratio_M"]), f1(pa["Vu"]), f1(pa["phiVc"]), f3(pa["ratio_V"]), ok(max(pa["ratio_M"], pa["ratio_V"]))],''',
    '''            ["흉벽 A (토압+상재)", pa["bar"], f0(pa["As"]), f0(pa["d"]), f1(pa["MuA"]), f1(pa["phiMn"]), f3(pa["ratio_MA"]), f1(pa["VuA"]), f1(pa["phiVc"]), f3(pa["ratio_VA"]), ok(max(pa["ratio_MA"], pa["ratio_VA"]))],
            ["흉벽 B (토압+윤하중)", pa["bar"], f0(pa["As"]), f0(pa["d"]), f1(pa["Mu"]), f1(pa["phiMn"]), f3(pa["ratio_M"]), f1(pa["Vu"]), f1(pa["phiVc"]), f3(pa["ratio_V"]), ok(max(pa["ratio_M"], pa["ratio_V"]))],''')
rep('''    B.body(f"수평철근 : {hz['bar']} 양면 As = {f0(hz['As'])} mm²/m ≥ 0.0015·b·h = {f0(hz['req'])} mm²/m [도로교설계기준 2010 4.3.9] → {'O.K' if hz['ok'] else 'N.G'}")
    B.body(f"흉벽 윤하중 : 합력 {f2(pa['wheel']['F'])} kN/m, 작용점 지표 아래 {f3(pa['wheel']['z'])} m. 흉벽 두께 {g['t_par']} m·배근 {pa['bar']}은 도면 판독값으로, 강도비 {f3(pa['ratio_M'])}{'(초과)' if pa['ratio_M'] > 1 else ''}는 두께·배근 재확인 후 확정한다.")''',
    '''    for ln in LA["step7"]: B.body(ln)
    B.text(f"흉벽은 준공 당시 설계 방식(토압 + 상재하중 10 kN/m², 경우 A)으로는 강도비 {f3(pa['ratio_MA'])}로 안전하나, 2020 도로설계요령 4.6의 윤하중(경우 B)을 고려하면 {f3(pa['ratio_M'])}로 설계강도를 초과한다. 흉벽 두께 {g['t_par']} m·배근 {pa['bar']}은 도면 판독값이므로 현장 확인 후 보수·보강 여부를 판단한다.")''')
rep('''    B.table("코핑 브래킷 검토 (기둥면, 강도 ①)", data, widths=[0.6, 0.7, 0.7, 0.9, 0.9, 1, 1, 0.9, 0.7, 0.9, 0.8, 1.3, 1.2])''',
    '''    B.table("코핑 브래킷 검토 (기둥면, 강도 ①)", data, widths=[0.6, 0.7, 0.7, 0.9, 0.9, 1, 1, 0.9, 0.7, 0.9, 0.8, 1.3, 1.2])
    LP = pier_lines(p3)
    for ln in LP["coping"]: B.body("P3: " + ln)''')
rep('''    B.table("기둥 검토 (P–M 강도비·전단)", data, widths=[0.6, 0.9, 0.6, 0.9, 2.2, 0.5, 0.8, 0.8, 0.6, 0.8, 0.7, 0.8, 0.6])''',
    '''    B.table("기둥 검토 (P–M 강도비·전단)", data, widths=[0.6, 0.9, 0.6, 0.9, 2.2, 0.5, 0.8, 0.8, 0.6, 0.8, 0.7, 0.8, 0.6])
    for ln in LP["column"]: B.body("P3: " + ln)''')
rep('''    B.table("기초·말뚝 검토 (P1~P5)", data, widths=[0.6, 1, 0.6, 0.6, 0.9, 1.6, 0.9, 0.8, 0.8, 0.6, 1, 0.9, 0.7, 0.7, 0.6])''',
    '''    B.table("기초·말뚝 검토 (P1~P5)", data, widths=[0.6, 1, 0.6, 0.6, 0.9, 1.6, 0.9, 0.8, 0.8, 0.6, 1, 0.9, 0.7, 0.7, 0.6])
    for ln in LP["footing"]: B.body("P3: " + ln)''')
rep('''    B.body("확인 필요 : P4·P5 말뚝 배치(도면 격자 판독), P5 코핑 상폭 8.0 m·PSC측 받침 반력. 말뚝 지반 지지력·침하·수평변위는 지반조사·시공기록 없음 → 미산정.")''',
    '''    B.body("확인 필요 : P4·P5 말뚝 배치(도면 격자 판독), P5 코핑 상폭 8.0 m·PSC측 받침 반력. 말뚝 지반 지지력·침하·수평변위는 지반조사·시공기록 없음 → 미산정.")
    B.text("교대·교각의 모든 하중별·조합별 단면력, 말뚝 반력, 부재검토 중간값과 풀이 문장은 부록 계산근거 엑셀(부록_계산근거_5장.xlsx)의 시트 '교대_*', '교각_*'에 수록하였다.")''')
rep('''    data = [["구분", "부재", "검토 항목", "발생값", "허용/설계값", "비 (발생/허용)", "판정", "등급"]]
    for nm, a, b, r in (("벽체 기부", st["Mu"], st["phiMn"], st["ratio_M"]), ("흉벽 기부", pa["Mu"], pa["phiMn"], pa["ratio_M"]), ("앞굽판", ft["toe"]["Mu"], ft["phiMn"], ft["toe"]["ratio_M"]), ("뒷굽판", ft["heel"]["Mu"], ft["phiMn"], ft["heel"]["ratio_M"])):
        data.append(["교대 A1", nm, "휨 Mu/φMn (kN·m/m)", f1(a), f1(b), f3(r), ok(r), grade(1 / r)])
    data.append(["교대 A1", "말뚝", "축응력 f/fa (MPa)", f1(pmax), "140.0", f3(pmax / 140), ok(pmax / 140), grade(140 / pmax)])
    data.append(["교대 A1", "받침", "반력/용량 (kN)", f0(A["bearing"]["R"]), f0(A["bearing"]["cap"]), f2(A["bearing"]["ratio"]), ok(A["bearing"]["ratio"]), grade(1 / A["bearing"]["ratio"])])
    for n, r in PR.items():''',
    '''    hdr = ["구분", "부재", "검토 항목", "발생값", "허용/설계값", "비 (발생/허용)", "판정", "등급"]; data = [hdr]
    for nm, a, b, r in (("벽체 기부", st["Mu"], st["phiMn"], st["ratio_M"]), ("흉벽 A(토압+상재)", pa["MuA"], pa["phiMn"], pa["ratio_MA"]), ("흉벽 B(토압+윤하중)", pa["Mu"], pa["phiMn"], pa["ratio_M"]), ("앞굽판", ft["toe"]["Mu"], ft["phiMn"], ft["toe"]["ratio_M"]), ("뒷굽판", ft["heel"]["Mu"], ft["phiMn"], ft["heel"]["ratio_M"])):
        data.append(["교대 A1", nm, "휨 Mu/φMn (kN·m/m)", f1(a), f1(b), f3(r), ok(r), grade(1 / r)])
    data.append(["교대 A1", "말뚝", "축응력 f/fa (MPa)", f1(pmax), "140.0", f3(pmax / 140), ok(pmax / 140), grade(140 / pmax)])
    data.append(["교대 A1", "받침", "반력/용량 (kN)", f0(A["bearing"]["R"]), f0(A["bearing"]["cap"]), f2(A["bearing"]["ratio"]), ok(A["bearing"]["ratio"]), grade(1 / A["bearing"]["ratio"])])
    t_ab = new_table(doc, B.T["tbl"], len(data), 8, data, widths=[1, 1.4, 1.8, 1, 1, 1, 0.7, 0.6], height=1900)
    cap_pr = new_para(B.T["tblcap"], "교각(P1~P5) 안전성평가 결과 (지진 제외)"); data = [hdr]
    for n, r in PR.items():''')
rep('''    t = new_table(doc, B.T["tbl"], len(data), 8, data, widths=[1, 1.1, 1.8, 1, 1, 1, 0.7, 0.6], height=2300); old = ps[658]; old.getparent().replace(old, t)
    doc.set_para_text(ps[657], "하부구조 안전성평가 결과 (교대 A1, 교각 P1~P5; 지진 제외)")''',
    '''    t = new_table(doc, B.T["tbl"], len(data), 8, data, widths=[1, 1.1, 1.8, 1, 1, 1, 0.7, 0.6], height=1900); old = ps[658]
    old.getparent().replace(old, t_ab); insert_after(t_ab, [new_para(B.T["spacer"], ""), cap_pr, t])
    doc.set_para_text(ps[657], "교대(A1) 안전성평가 결과")''')
open(p, 'w', encoding='utf-8').write(s); print('builder patched')

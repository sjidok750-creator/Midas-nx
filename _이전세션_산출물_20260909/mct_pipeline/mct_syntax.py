# -*- coding: utf-8 -*-
r"""
MCT 문법 상수 및 블록 생성기.

모든 형식은 실물 파일에서 검증함:
  D:\01_과업\2025년 과업\내진성능평가 보고서_용문교 등 4개소\
    02. 부록\3. 내진성능평가 결과자료\전산DATA\mct파일\01. 태봉2교\
    05_태봉2교 내진성능평가_보강전.mct   (CP949 인코딩)

[실제로 틀렸던 것 — 기억으로 쓰지 말 것]
  LOADCOMB  : 파라미터 10개, 하중줄은 "ST, 이름, 계수" (ST=해석타입)
              LCNAME= 형식은 파싱 에러 → 임포트 전체 실패
  DBUSER SB : 치수는 H, B 순서(높이 먼저). 'SB ' 뒤 공백 유지.
              뒤집어도 파싱은 통과하지만 Iy가 틀려 결과가 통째로 무의미해짐
  ELASTICLINK: 받침 모델링. SDx=연직, SDy=종, SDz=횡. 0이면 그 방향 가동
"""

UNIT_DEFAULT = "KN   , M, KCAL, C"
STRUCTYPE_DEFAULT = "     0, 1, 1, NO, YES, 9.806, 0, NO, NO, NO"


def header(title, notes=None):
    lines = [";" + "-" * 75,
             ";  MIDAS CIVIL NX Text(MCT) File.",
             ";  " + title]
    for n in (notes or []):
        lines.append(";  " + n)
    lines.append(";" + "-" * 75)
    return "\n".join(lines) + "\n"


def version(v="9.5.5"):
    return "\n*VERSION\n   {}\n".format(v)


def unit(u=UNIT_DEFAULT):
    return "\n*UNIT    ; Unit System\n   {}\n".format(u)


def structype(line=STRUCTYPE_DEFAULT):
    return "\n*STRUCTYPE    ; Structure Type\n{}\n".format(line)


def nodes(node_dict):
    """node_dict: {id: (x, y, z)}"""
    s = "\n*NODE    ; Nodes\n"
    for i in sorted(node_dict):
        x, y, z = node_dict[i]
        s += "{:6d}, {:.6g}, {:.6g}, {:.6g}\n".format(i, x, y, z)
    return s


def elements(elem_list):
    """elem_list: [(id, mat, sect, n1, n2)] — BEAM 전용"""
    s = "\n*ELEMENT    ; Elements\n"
    for (eid, mat, sect, n1, n2) in elem_list:
        s += "{:6d}, BEAM  , {:4d}, {:5d}, {:5d}, {:5d},     0,     0\n".format(
            eid, mat, sect, n1, n2)
    return s


def material_conc(mid, name, E_kN_m2, code="KSCE-LSD15(RC)"):
    return ("\n*MATERIAL    ; Material\n"
            "{:5d}, CONC , {:<18s}, 0, 0, , C, NO, 0.05, 1, {},            , "
            "{:<14s}, NO, {:.4e}\n".format(mid, name, code, name, E_kN_m2))


def section_rect(sid, name, H, B):
    """DBUSER Solid Rectangle. 실물 검증: 'SB ' 뒤 공백, 치수는 H,B 순서."""
    return ("\n*SECTION    ; Section\n"
            "{:5d}, DBUSER    , {:<18s}, CC, 0, 0, 0, 0, 0, 0, YES, NO, SB , 2, "
            "{:.6g}, {:.6g}, 0, 0, 0, 0, 0, 0, 0, 0\n".format(sid, name, H, B))


def stldcase(cases):
    """cases: [(name, type)] — type: D=고정, L=활하중 등"""
    s = "\n*STLDCASE    ; Static Load Cases\n"
    for n, t in cases:
        s += "   {:<10s}, {} , \n".format(n, t)
    return s


def selfweight(case, gz=-1):
    return "\n*USE-STLD, {}\n*SELFWEIGHT    ; Self Weight\n0, 0, {}, \n".format(case, gz)


def conload(case, loads):
    """loads: [(node, Fx, Fy, Fz, Mx, My, Mz)]"""
    s = "\n*USE-STLD, {}\n*CONLOAD    ; Nodal Loads\n".format(case)
    for (n, fx, fy, fz, mx, my, mz) in loads:
        s += "{:6d}, {:.6g}, {:.6g}, {:.6g}, {:.6g}, {:.6g}, {:.6g}, \n".format(
            n, fx, fy, fz, mx, my, mz)
    return s


def constraint(groups):
    """groups: [(node_list_str, dof)] — dof 예: '111111'"""
    s = "\n*CONSTRAINT    ; Supports\n"
    for nodes_str, dof in groups:
        s += "   {}, {}, \n".format(nodes_str, dof)
    return s


def elasticlink(links):
    """
    links: [(id, n1, n2, SDx, SDy, SDz)] — 받침 모델링.
    실물(태봉2교) 검증 패턴:
      1e9, 0,   0    → 연직만 (양방향 가동)
      1e9, 1e7, 0    → 연직+종 (횡방향 가동)
      1e9, 0,   1e7  → 연직+횡 (종방향 가동)
      1e9, 1e7, 1e7  → 고정단
    """
    s = "\n*ELASTICLINK    ; Elastic Link\n"
    for (lid, n1, n2, sx, sy, sz) in links:
        s += ("{:6d}, {:5d}, {:5d}, GEN  ,     0, NO, NO, NO, NO, NO, NO, "
              "{:g}, {:g}, {:g}, 0, 0, 0, NO, 0.5, 0.5, \n".format(
                  lid, n1, n2, sx, sy, sz))
    return s


def loadcomb(name, terms):
    """terms: [(case_name, factor)] — 실물 검증: 파라미터 10개 + 'ST, 이름, 계수'"""
    s = "\n*LOADCOMB    ; Combinations\n"
    s += "   NAME={}, GEN, ACTIVE, 0, 0, , 0, 0, 0, 1\n        ".format(name)
    s += ", ".join("ST, {}, {:g}".format(c, f) for c, f in terms) + "\n"
    return s


def enddata():
    return "\n*ENDDATA\n"

"""
검증 모듈 — 생성된 MCT마다 자동 실행.
"통과"가 아니라 "무엇을 확인했는지"를 출력한다.
"""
import re, math

class Check:
    def __init__(self):
        self.rows=[]
    def add(self, name, expected, actual, tol=1e-6, unit=""):
        if expected is None:
            ok=None; err=""
        else:
            denom = abs(expected) if abs(expected)>1e-12 else 1.0
            err = abs(actual-expected)/denom
            ok = err <= tol
        self.rows.append((name, expected, actual, ok, err, unit))
    def report(self):
        L=["","%-34s %14s %14s %8s"%("항목","기댓값","실제값","판정"),"-"*74]
        nfail=0
        for n,e,a,ok,err,u in self.rows:
            es = "-" if e is None else f"{e:.6g}"
            mark = "정보" if ok is None else ("OK" if ok else "불일치")
            if ok is False: nfail+=1
            L.append("%-34s %14s %14.6g %8s %s"%(n,es,a,mark,u))
        L.append("-"*74)
        L.append(f"불일치 {nfail}건" if nfail else "전 항목 일치")
        return "\n".join(L)
    @property
    def failed(self):
        return any(r[3] is False for r in self.rows)


def parse_mct(path):
    """생성된 MCT를 되읽어 구조를 확인한다(생성 로직과 독립적으로)."""
    txt = open(path, encoding="utf-8").read()
    blocks = {}
    cur=None
    for line in txt.splitlines():
        s=line.strip()
        if s.startswith("*"):
            cur = s.split(";")[0].strip().lstrip("*").split(",")[0].strip()
            blocks.setdefault(cur, [])
        elif cur and s and not s.startswith(";"):
            blocks[cur].append(s)
    return blocks


def rect_props(H, B):
    """직사각 단면 특성 — CIVIL NX와 대조용."""
    A = B*H
    Iy = B*H**3/12.0          # 강축(휨)
    Iz = H*B**3/12.0
    a, b = max(B,H), min(B,H)
    r = b/a
    beta = (1/3) - 0.21*r*(1-(r**4)/12)
    J = beta*a*b**3
    return dict(A=A, Iy=Iy, Iz=Iz, J=J)


def fixed_fixed_moments(P, w, L):
    """양단고정보 이론해 — 해석결과 대조용."""
    return dict(
        mid_P   = P*L/8.0,
        end_P   = -P*L/8.0,
        mid_w   = w*L*L/24.0,
        end_w   = -w*L*L/12.0,
        mid_tot = P*L/8.0 + w*L*L/24.0,
        end_tot = -P*L/8.0 - w*L*L/12.0,
    )


def check_equilibrium(reactions, applied_loads, tol=1e-3):
    """
    ΣF 평형 검증 — 반력 전달의 핵심 안전장치.
    reactions   : [(node, Fx,Fy,Fz,Mx,My,Mz)]  상부 해석 반력
    applied     : [(node, Fx,Fy,Fz,Mx,My,Mz)]  하부에 실은 하중
    부호 규약을 단정하지 않고, 두 방향 모두 시험해 어느 쪽이 맞는지 보고한다.
    """
    def total(rows):
        t=[0.0]*6
        for r in rows:
            for i in range(6): t[i]+=r[1+i]
        return t
    R = total(reactions); A = total(applied_loads)
    same = all(abs(R[i]-A[i]) <= tol*max(1.0,abs(R[i])) for i in range(6))
    flip = all(abs(R[i]+A[i]) <= tol*max(1.0,abs(R[i])) for i in range(6))
    return dict(
        sum_reaction=R, sum_applied=A,
        matches_same_sign=same, matches_flipped=flip,
        verdict=("동일부호" if same else "부호반전" if flip else "불일치")
    )

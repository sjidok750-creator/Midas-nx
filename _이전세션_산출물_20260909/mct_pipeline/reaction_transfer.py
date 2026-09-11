"""
반력 전달기 — 상부 해석 반력을 하부 모델 하중으로 변환.

입력 : CIVIL NX Results > Reactions 를 Export 한 CSV/텍스트
       + 절점 매핑표 (상부 받침절점 -> 하부 상단절점)   ※ 추론하지 않고 명시적으로 받는다
출력 : 하부 MCT 의 *CONLOAD 블록

부호 규약은 단정하지 않는다. sign_convention="auto" 로 두면
검증용 평형계산 결과를 보고 사람이 확정하도록 보고서를 낸다.
"""
import csv, io, re

def read_reactions(path, encoding=None):
    """
    CIVIL NX 반력 export 를 읽는다. 열 이름이 버전마다 달라
    Node/FX/FY/FZ/MX/MY/MZ 를 유연하게 찾는다.
    반환: {load_case: [(node,Fx,Fy,Fz,Mx,My,Mz)]}
    """
    encs = [encoding] if encoding else ["utf-8-sig","cp949","utf-16"]
    txt=None
    for e in encs:
        try:
            txt=open(path, encoding=e).read(); break
        except Exception:
            continue
    if txt is None:
        raise IOError(f"인코딩 판별 실패: {path}")

    delim = "\t" if txt.count("\t") > txt.count(",") else ","
    rows = list(csv.reader(io.StringIO(txt), delimiter=delim))

    hdr_i, hdr = None, None
    for i,r in enumerate(rows[:40]):
        low = [c.strip().lower() for c in r]
        if any(c.startswith("node") for c in low) and any(c in ("fz","fx") for c in low):
            hdr_i, hdr = i, low; break
    if hdr is None:
        raise ValueError("헤더(Node/FX..FZ)를 찾지 못했습니다. 파일을 확인하세요.")

    def col(*names):
        for n in names:
            if n in hdr: return hdr.index(n)
        return None
    ci = dict(node=col("node","nodeid","node id"),
              lc=col("load","load case","loadcase","lcname"),
              fx=col("fx"), fy=col("fy"), fz=col("fz"),
              mx=col("mx"), my=col("my"), mz=col("mz"))

    out={}
    for r in rows[hdr_i+1:]:
        if not r or ci["node"] is None or len(r)<=ci["node"]: continue
        try: node=int(float(r[ci["node"]]))
        except Exception: continue
        lc = r[ci["lc"]].strip() if ci["lc"] is not None and len(r)>ci["lc"] else "ALL"
        def g(k):
            j=ci[k]
            if j is None or len(r)<=j: return 0.0
            try: return float(r[j])
            except Exception: return 0.0
        out.setdefault(lc,[]).append((node,g("fx"),g("fy"),g("fz"),g("mx"),g("my"),g("mz")))
    return out


def transfer(reactions_by_case, node_map, sign=-1.0, cases=None):
    """
    node_map : {상부절점: 하부절점}   ※ 명시적으로 준다
    sign     : -1.0 이면 부호 반전(반력->하중). 검증 후 확정할 것.
    반환     : {load_case: [(하부절점, Fx..Mz)]}
    """
    out={}
    for lc, rows in reactions_by_case.items():
        if cases and lc not in cases: continue
        conv=[]
        missing=[]
        for (n,fx,fy,fz,mx,my,mz) in rows:
            if n not in node_map:
                missing.append(n); continue
            tgt=node_map[n]
            conv.append((tgt, sign*fx, sign*fy, sign*fz, sign*mx, sign*my, sign*mz))
        if missing:
            raise KeyError(f"[{lc}] 매핑 없는 상부절점: {sorted(set(missing))}")
        out[lc]=conv
    return out


def summarize(reactions_by_case, transferred):
    """전달 전후 합계를 나란히 출력 — 사람이 눈으로 확인할 표."""
    L=[]
    for lc in transferred:
        R=[0.0]*6; A=[0.0]*6
        for r in reactions_by_case[lc]:
            for i in range(6): R[i]+=r[1+i]
        for a in transferred[lc]:
            for i in range(6): A[i]+=a[1+i]
        L.append(f"[{lc}]")
        L.append(f"  상부 반력 합 : Fx={R[0]:12.4f} Fy={R[1]:12.4f} Fz={R[2]:12.4f}")
        L.append(f"  하부 재하 합 : Fx={A[0]:12.4f} Fy={A[1]:12.4f} Fz={A[2]:12.4f}")
        ok = all(abs(R[i]+A[i])<1e-6*max(1,abs(R[i])) for i in range(3))
        L.append(f"  → 연직 평형 {'성립(부호반전)' if ok else '재확인 필요'}")
    return "\n".join(L)

# -*- coding: utf-8 -*-
"""DXF 텍스트/치수 추출 공용 함수"""
import ezdxf, re, io, sys

def clean(t):
    t = re.sub(r'\[A-Za-z][^;]*;', '', t)
    t = t.replace('\P', ' ').replace('%%D', '°').replace('%%C', 'ⵁ').replace('%%c', 'ⵁ')
    t = t.replace('%%P', '±').replace('%%p', '±').replace('%%%', '%')
    return t.strip()

def texts(path):
    """[(x, y, text)] — 블록 내부 포함"""
    d = ezdxf.readfile(path); msp = d.modelspace()
    out = []
    def grab(e):
        t = e.dxftype()
        try:
            if t == "TEXT":  return (e.dxf.insert.x, e.dxf.insert.y, e.dxf.text)
            if t == "MTEXT": return (e.dxf.insert.x, e.dxf.insert.y, e.text)
        except Exception: pass
        return None
    for e in msp:
        r = grab(e)
        if r: out.append(r)
    for e in msp.query("INSERT"):
        try:
            for sub in e.virtual_entities():
                r = grab(sub)
                if r: out.append(r)
        except Exception: pass
    res = []
    for x, y, t in out:
        s = clean(t)
        if s: res.append((x, y, s))
    return res

def dims(path):
    """치수(DIMENSION) 실측값 — 도면의 진짜 숫자"""
    d = ezdxf.readfile(path); msp = d.modelspace()
    out = []
    for e in msp.query("DIMENSION"):
        try:
            m = e.get_measurement()
            p = e.dxf.defpoint
            txt = clean(e.dxf.text) if e.dxf.text not in ("", "<>") else ""
            out.append((p.x, p.y, float(m), txt))
        except Exception: pass
    return out

def rows(items, ytol=120):
    """y 근접끼리 묶어 표 복원"""
    items = sorted(items, key=lambda a: (-a[1], a[0]))
    R, cur, lasty = [], [], None
    for x, y, t in items:
        if lasty is None or abs(y - lasty) < ytol:
            cur.append(t); lasty = y if lasty is None else lasty
        else:
            R.append(" | ".join(cur)); cur = [t]; lasty = y
    if cur: R.append(" | ".join(cur))
    return R

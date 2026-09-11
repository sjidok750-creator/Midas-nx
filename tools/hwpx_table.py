# -*- coding: utf-8 -*-
"""
HWPX 표·문단 생성기 (원본 XML 복제 원칙: 새로 그리지 않고 문서 안의 표·문단을 복제해 크기와 내용만 바꾼다)
  new_table(doc, tmpl_para, nrows, ncols, data, widths=None, header_rows=1, height=None)
      tmpl_para: 표가 든 문단(첫 행 = 제목행 스타일, 둘째 행 = 본문 스타일). 반환: 새 문단(표 포함)
  new_para(tmpl_para, text)            : 문단 복제 후 텍스트 교체 (스타일 유지). 반환 새 문단
  insert_after(anchor, elems)          : anchor 문단 뒤에 순서대로 삽입
  fix_layout(doc, text_h_ratio=0.6)    : 표 나눔(짧은 표는 NONE, 긴 표는 CELL+제목행 반복), 빈 문단 연속 정리, 연속 쪽나눔 정리
검증: 2026-09-11 5장_v3.hwpx에서 3×8 표를 복제해 6×5 표 생성·저장·verify 통과
"""
import copy
from lxml import etree
from hwpx_edit import P, para_text

def _cells(tr): return tr.findall(P + "tc")

def _set_text(tc, text):
    """hwpx_edit.set_cell_text와 동일 (의존 최소화)"""
    sub = tc.find(P + "subList"); ps = sub.findall(P + "p"); p0 = ps[0]
    for p in ps[1:]: sub.remove(p)
    ts = p0.findall(".//" + P + "t")
    if ts:
        for ch in list(ts[0]): ts[0].remove(ch)
        ts[0].text = "" if text is None else str(text); ts[0].tail = None
        for t in ts[1:]: t.getparent().remove(t)
    else:
        run = p0.find(P + "run")
        if run is None: run = etree.SubElement(p0, P + "run"); run.set("charPrIDRef", "0")
        t = etree.SubElement(run, P + "t"); t.text = "" if text is None else str(text)
    for la in p0.findall(P + "linesegarray"): p0.remove(la)

def new_table(doc, tmpl_para, nrows, ncols, data, widths=None, header_rows=1, height=None, body_row=None):
    """data: 2차원 리스트(문자열). widths: 열 폭 비율 리스트(합 임의) 또는 None(균등). height: 행 높이(HWPUNIT, None이면 템플릿 값)"""
    para = copy.deepcopy(tmpl_para); tbl = para.find(".//" + P + "tbl"); assert tbl is not None, "템플릿 문단에 표가 없음"
    trs = tbl.findall(P + "tr"); hdr_tc = _cells(trs[0])[0]
    body_tc = _cells(trs[body_row if body_row is not None else min(1, len(trs) - 1)])[0]
    W = int(tbl.find(P + "sz").get("width")); hh = int(hdr_tc.find(P + "cellSz").get("height")); bh = int(body_tc.find(P + "cellSz").get("height"))
    if height: hh = bh = height
    ws = widths or [1] * ncols; tot = float(sum(ws)); cw = [int(W * w / tot) for w in ws]; cw[-1] = W - sum(cw[:-1])
    for tr in trs: tbl.remove(tr)
    for r in range(nrows):
        tr = etree.SubElement(tbl, P + "tr")
        for c in range(ncols):
            tc = copy.deepcopy(hdr_tc if r < header_rows else body_tc); tc.set("header", "1" if r < header_rows else "0")
            tc.find(P + "cellAddr").set("colAddr", str(c)); tc.find(P + "cellAddr").set("rowAddr", str(r))
            sp = tc.find(P + "cellSpan"); sp.set("colSpan", "1"); sp.set("rowSpan", "1")
            cs = tc.find(P + "cellSz"); cs.set("width", str(cw[c])); cs.set("height", str(hh if r < header_rows else bh))
            _set_text(tc, data[r][c] if r < len(data) and c < len(data[r]) else ""); tr.append(tc)
    tbl.set("rowCnt", str(nrows)); tbl.set("colCnt", str(ncols)); tbl.set("repeatHeader", "1" if header_rows else "0")
    tbl.find(P + "sz").set("height", str(hh * header_rows + bh * (nrows - header_rows)))
    for la in para.findall(P + "linesegarray"): para.remove(la)
    return para

def merge_cells(tbl, r0, c0, r1, c1):
    """(r0,c0)~(r1,c1) 병합: 첫 셀 span 확대, 나머지 셀 제거"""
    trs = tbl.findall(P + "tr"); first = None
    for r in range(r0, r1 + 1):
        for tc in list(_cells(trs[r])):
            ca = tc.find(P + "cellAddr"); c = int(ca.get("colAddr"))
            if c0 <= c <= c1:
                if r == r0 and c == c0:
                    first = tc; sp = tc.find(P + "cellSpan"); sp.set("colSpan", str(c1 - c0 + 1)); sp.set("rowSpan", str(r1 - r0 + 1))
                    w = sum(int(x.find(P + "cellSz").get("width")) for x in _cells(trs[r0]) if c0 <= int(x.find(P + "cellAddr").get("colAddr")) <= c1)
                    h = sum(int(_cells(trs[rr])[0].find(P + "cellSz").get("height")) for rr in range(r0, r1 + 1))
                    tc.find(P + "cellSz").set("width", str(w)); tc.find(P + "cellSz").set("height", str(h))
                else: trs[r].remove(tc)
    return first

def new_para(tmpl_para, text):
    p = copy.deepcopy(tmpl_para)
    for e in list(p):
        if e.tag == P + "linesegarray": p.remove(e)
    ts = p.findall(".//" + P + "t")
    if ts:
        for ch in list(ts[0]): ts[0].remove(ch)
        ts[0].text = str(text); ts[0].tail = None
        for t in ts[1:]: t.getparent().remove(t)
    else:
        run = p.find(P + "run")
        if run is None: run = etree.SubElement(p, P + "run"); run.set("charPrIDRef", "0")
        for ch in list(run):
            if ch.tag != P + "t": run.remove(ch)
        t = etree.SubElement(run, P + "t"); t.text = str(text)
    if p.get("pageBreak") == "1": p.set("pageBreak", "0")
    return p

def insert_after(anchor, elems):
    parent = anchor.getparent(); pos = parent.index(anchor) + 1
    for k, e in enumerate(elems): parent.insert(pos + k, e)
    return elems[-1] if elems else anchor

def fix_layout(doc, ratio=0.6):
    """표 쪽나눔: 표 높이 ≤ 본문높이×ratio → NONE(통째로 다음 쪽), 초과 → CELL + 제목행 반복. 빈 문단 3개 이상 연속 → 1개. 쪽나눔 문단 바로 앞의 빈 문단 제거"""
    root = doc.root; ns = {"hp": P[1:-1]}
    pg = root.find(".//hp:pagePr", ns); mg = pg.find("hp:margin", ns)
    th = int(pg.get("height")) - int(mg.get("top")) - int(mg.get("bottom")) - int(mg.get("header")) - int(mg.get("footer"))
    n_none = n_cell = 0
    for tbl in root.iter(P + "tbl"):
        h = int(tbl.find(P + "sz").get("height"))
        if h <= th * ratio: tbl.set("pageBreak", "NONE"); n_none += 1
        else: tbl.set("pageBreak", "CELL"); tbl.set("repeatHeader", "1"); n_cell += 1
    ps = doc.paragraphs(); removed = 0; run = []
    def empty(p): return not para_text(p).strip() and p.find(".//" + P + "tbl") is None and p.find(".//" + P + "pic") is None and p.get("pageBreak") != "1"
    for i, p in enumerate(ps):
        if i == 0: continue
        if empty(p): run.append(p)
        else:
            if p.get("pageBreak") == "1":
                for q in run: q.getparent().remove(q); removed += 1
            elif len(run) >= 3:
                for q in run[1:]: q.getparent().remove(q); removed += 1
            run = []
    return dict(none=n_none, cell=n_cell, removed_empty=removed, text_h=th)

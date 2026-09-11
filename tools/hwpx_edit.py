# -*- coding: utf-8 -*-
"""
HWPX 원본 서식 보존 편집 도구 (구글드라이브 「한글문서(HWPX) 편집 작업지침 v2~v3.3」 준수)
  - zip 항목 순서·압축방식 보존, mimetype 첫 항목·무압축
  - Contents/section0.xml 만 수정 (문자열 치환 + lxml), 루트 <hs:sec> 태그 원문 복원
  - 글자 바꾼 문단의 linesegarray 제거, 복제 개체 id/instid/zOrder 재부여
  - 표 셀 텍스트 교체, 행 복제/삭제, 표 찾기(캡션), 검증(§8 일부)
사용:
  doc = Hwpx(path); doc.load()
  tbl = doc.find_table_after("휨모멘트 산정결과")  # 캡션 문단 다음 표
  doc.set_cell(tbl, r, c, "123.4")
  doc.clone_row(tbl, src_row=3, count=2)
  doc.save(out_path); doc.verify(out_path)
"""
import zipfile, re, copy, io, os, sys
from lxml import etree

NS = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph", "hs": "http://www.hancom.co.kr/hwpml/2011/section",
      "hc": "http://www.hancom.co.kr/hwpml/2011/core", "hh": "http://www.hancom.co.kr/hwpml/2011/head"}
P = "{%s}" % NS["hp"]; HS = "{%s}" % NS["hs"]; HC = "{%s}" % NS["hc"]

def para_text(p):
    return "".join("".join(t.itertext()) for t in p.iter(P + "t"))   # fwSpace 등 자식의 tail 포함

class Hwpx:
    def __init__(self, path):
        self.path = path; self.entries = []; self.data = {}; self.sec_name = None; self.root = None; self.raw = None

    def load(self):
        with zipfile.ZipFile(self.path) as z:
            for i in z.infolist():
                self.entries.append(i); self.data[i.filename] = z.read(i.filename)
        secs = sorted(n for n in self.data if re.match(r"Contents/section\d+\.xml", n))
        self.sec_name = secs[0]
        self.raw = self.data[self.sec_name].decode("utf-8")
        self.root = etree.fromstring(self.data[self.sec_name])
        return self

    # ── 탐색 ──
    def paragraphs(self):
        return self.root.findall(P + "p")           # 최상위 문단만

    def dump(self, limit=None, contains=None):
        out = []
        for i, p in enumerate(self.paragraphs()):
            t = para_text(p).strip(); has = "T" if p.find(".//" + P + "tbl") is not None else ("G" if p.find(".//" + P + "pic") is not None else " ")
            if contains and contains not in t: continue
            out.append((i, has, p.get("styleIDRef"), t[:90]))
            if limit and len(out) >= limit: break
        return out

    def find_para(self, text, start=0):
        for i, p in enumerate(self.paragraphs()):
            if i >= start and text in para_text(p): return i, p
        return None, None

    def find_table_after(self, caption_text, start=0, max_ahead=3):
        """캡션 문단(캡션은 표 위) 다음 문단들에서 첫 표"""
        i, p = self.find_para(caption_text, start)
        if p is None: return None
        ps = self.paragraphs()
        for j in range(i, min(i + 1 + max_ahead, len(ps))):
            t = ps[j].find(".//" + P + "tbl")
            if t is not None: return t
        return None

    @staticmethod
    def rows(tbl): return tbl.findall(P + "tr")

    @staticmethod
    def grid(tbl):
        """[[텍스트,...],...] (병합 셀은 첫 위치만)"""
        return [[para_text(tc).strip() for tc in tr.findall(P + "tc")] for tr in tbl.findall(P + "tr")]

    # ── 편집 ──
    def set_cell(self, tbl, r, c, text):
        tc = self.rows(tbl)[r].findall(P + "tc")[c]
        self.set_cell_text(tc, text)

    @staticmethod
    def set_cell_text(tc, text):
        """셀의 첫 문단에 텍스트, 나머지 문단은 삭제. linesegarray 제거"""
        sub = tc.find(P + "subList"); ps = sub.findall(P + "p")
        p0 = ps[0]
        for p in ps[1:]: sub.remove(p)
        ts = p0.findall(".//" + P + "t")
        if ts:
            for ch in list(ts[0]): ts[0].remove(ch)      # <hp:fwSpace/> 등 자식과 그 tail 텍스트 제거
            ts[0].text = str(text); ts[0].tail = None
            for t in ts[1:]: t.getparent().remove(t)
        else:
            run = p0.find(P + "run")
            if run is None:
                run = etree.SubElement(p0, P + "run"); run.set("charPrIDRef", "0")
            t = etree.SubElement(run, P + "t"); t.text = str(text)
        for la in p0.findall(P + "linesegarray"): p0.remove(la)

    def set_para_text(self, p, text):
        ts = p.findall(".//" + P + "t")
        if ts:
            for ch in list(ts[0]): ts[0].remove(ch)
            ts[0].text = str(text); ts[0].tail = None
            for t in ts[1:]: t.getparent().remove(t)
        for la in p.findall(P + "linesegarray"): p.remove(la)

    def set_para_runs(self, p, texts):
        """문단의 <hp:t>를 순서대로 texts로 교체 (수식 run 사이의 텍스트 유지용). 남는 <hp:t>는 삭제"""
        ts = p.findall(".//" + P + "t")
        for t, s_ in zip(ts, texts):
            for ch in list(t): t.remove(ch)
            t.text = str(s_); t.tail = None
        for t in ts[len(texts):]: t.getparent().remove(t)
        for la in p.findall(P + "linesegarray"): p.remove(la)

    def set_cell_lines(self, tc, lines):
        """셀을 여러 문단으로 채움. 첫 문단(수식 run 제거)을 템플릿으로 복제 — 새로 그리지 않음"""
        sub = tc.find(P + "subList"); ps = sub.findall(P + "p"); tmpl = copy.deepcopy(ps[0])
        for run in tmpl.findall(P + "run"):
            if run.find(P + "equation") is not None or run.find(P + "ctrl") is not None: tmpl.remove(run)
        if tmpl.find(P + "run") is None:
            r = copy.deepcopy(ps[0].find(P + "run")); [r.remove(c) for c in list(r) if c.tag != P + "t"]; tmpl.append(r)
        for p in ps: sub.remove(p)
        for ln in lines:
            q = copy.deepcopy(tmpl); self.set_para_text(q, ln); sub.append(q)

    # ── 그림 (작업지침 v3.1 §17) ──
    def add_image(self, data, ext="png"):
        """BinData에 이미지 추가 + content.hpf <opf:item> 등록. 반환: binaryItemIDRef (imageN)"""
        ids = [int(re.search(r"image(\d+)", n).group(1)) for n in self.data if re.match(r"BinData/image\d+\.", n)]
        n = max(ids + [0]) + 1; ref = f"image{n}"; name = f"BinData/{ref}.{ext}"
        self.data[name] = data
        zi = zipfile.ZipInfo(name, date_time=self.entries[-1].date_time); zi.compress_type = zipfile.ZIP_DEFLATED; zi.external_attr = self.entries[-1].external_attr
        pos = max(i for i, e in enumerate(self.entries) if e.filename.startswith("BinData/")) + 1
        self.entries.insert(pos, zi)
        hpf = self.data["Contents/content.hpf"].decode("utf-8")
        item = f'<opf:item id="{ref}" href="{name}" media-type="image/{ "jpeg" if ext == "jpg" else ext}" isEmbeded="1"/>'
        hpf = hpf.replace("</opf:manifest>", item + "</opf:manifest>", 1); self.data["Contents/content.hpf"] = hpf.encode("utf-8")
        return ref

    def prune_images(self):
        """어느 XML(본문·머리글·바탕쪽)에서도 참조하지 않는 BinData 이미지를 zip과 content.hpf에서 제거. 반환: 제거 목록"""
        used = set()
        for n, b in self.data.items():
            if n.endswith(".xml") and n != self.sec_name: used |= set(re.findall(r'binaryItemIDRef="([^"]+)"', b.decode("utf-8", "replace")))
        sec = self.serialize(); sec = sec.decode("utf-8") if isinstance(sec, bytes) else sec
        used |= set(re.findall(r'binaryItemIDRef="([^"]+)"', sec))
        hpf = self.data["Contents/content.hpf"].decode("utf-8"); removed = []
        for m in re.finditer(r'<opf:item id="(image\d+)" href="([^"]+)"[^>]*/>', hpf):
            ref, href = m.group(1), m.group(2)
            if ref not in used:
                removed.append(href); hpf = hpf.replace(m.group(0), "", 1)
                self.data.pop(href, None); self.entries = [e for e in self.entries if e.filename != href]
        self.data["Contents/content.hpf"] = hpf.encode("utf-8"); return removed

    def swap_pic(self, pic, ref, w_px, h_px, width_hu=None, max_width_hu=None):
        """기존 <hp:pic>의 이미지를 교체(원본 그림틀 유지). orgSz·imgRect·imgClip·imgDim을 새 이미지 크기로, 표시 폭은 기존(또는 지정) 폭, 높이는 새 비율.
        HWPUNIT = px × 75 (96 dpi). §17-3: curSz 0인 그룹 구성원은 다루지 않음(단독 pic 전용)"""
        HC = "{http://www.hancom.co.kr/hwpml/2011/core}"
        org_w, org_h = w_px * 75, h_px * 75
        cur = pic.find(P + "curSz"); sz = pic.find(P + "sz")
        cw = int(width_hu or (cur.get("width") if cur is not None and int(cur.get("width")) > 0 else sz.get("width")))
        if max_width_hu: cw = min(cw, int(max_width_hu))
        ch = int(round(cw * h_px / w_px))
        pic.find(HC + "img").set("binaryItemIDRef", ref)
        pic.find(P + "orgSz").set("width", str(org_w)); pic.find(P + "orgSz").set("height", str(org_h))
        for el in (cur, sz):
            if el is not None: el.set("width", str(cw)); el.set("height", str(ch))
        for tag, val in (("pt0", (0, 0)), ("pt1", (org_w, 0)), ("pt2", (org_w, org_h)), ("pt3", (0, org_h))):
            e = pic.find(P + "imgRect/" + HC + tag); e.set("x", str(val[0])); e.set("y", str(val[1]))
        clip = pic.find(P + "imgClip"); clip.set("left", "0"); clip.set("top", "0"); clip.set("right", str(org_w)); clip.set("bottom", str(org_h))
        dim = pic.find(P + "imgDim"); dim.set("dimwidth", str(org_w)); dim.set("dimheight", str(org_h))
        rot = pic.find(P + "rotationInfo")
        if rot is not None: rot.set("centerX", str(cw // 2)); rot.set("centerY", str(ch // 2))
        ri = pic.find(P + "renderingInfo")
        if ri is not None:
            tm, sm = ri.find(HC + "transMatrix"), ri.find(HC + "scaMatrix")
            for e in (tm,):
                if e is not None: e.set("e3", "0"); e.set("e6", "0")
            if sm is not None: sm.set("e1", f"{cw / org_w:.6f}"); sm.set("e5", f"{ch / org_h:.6f}"); sm.set("e3", "0"); sm.set("e6", "0")
        off = pic.find(P + "offset")
        if off is not None: off.set("x", "0"); off.set("y", "0")
        return cw, ch

    def delete_paragraphs(self, i0, i1):
        """최상위 문단 [i0, i1) 삭제 (문단 0의 secPr 보호). 뒤에서 앞 순서로 호출할 것"""
        ps = self.paragraphs(); assert i0 >= 1 and i1 <= len(ps) and i0 < i1
        for p in ps[i0:i1]: p.getparent().remove(p)
        return i1 - i0

    def clone_row(self, tbl, src_row, count=1, after=None):
        """src_row 를 복제해 after(기본 src_row) 뒤에 count개 삽입. rowAddr·rowCnt 재부여"""
        trs = self.rows(tbl); src = trs[src_row]; pos = (after if after is not None else src_row) + 1
        new = []
        for k in range(count):
            tr = copy.deepcopy(src); tbl.insert(list(tbl).index(trs[pos - 1]) + 1 + k, tr); new.append(tr)
        self._renumber_rows(tbl); return new

    def delete_rows(self, tbl, rows):
        trs = self.rows(tbl)
        for r in sorted(rows, reverse=True): tbl.remove(trs[r])
        self._renumber_rows(tbl)

    def _renumber_rows(self, tbl):
        trs = self.rows(tbl); tbl.set("rowCnt", str(len(trs)))
        for ri, tr in enumerate(trs):
            for tc in tr.findall(P + "tc"):
                ca = tc.find(P + "cellAddr")
                if ca is not None: ca.set("rowAddr", str(ri))
        # 표 높이 = 행 높이 합 (병합 고려 없이 첫 셀 기준)
        sz = tbl.find(P + "sz")
        if sz is not None:
            h = 0
            for tr in trs:
                tc = tr.find(P + "tc"); cs = tc.find(P + "cellSz") if tc is not None else None
                if cs is not None: h += int(cs.get("height", 0))
            if h: sz.set("height", str(h))

    def mark_header(self, tbl, header_rows=1):
        tbl.set("pageBreak", "CELL"); tbl.set("repeatHeader", "1")
        for ri, tr in enumerate(self.rows(tbl)):
            for tc in tr.findall(P + "tc"): tc.set("header", "1" if ri < header_rows else "0")

    def renumber_objects(self):
        """zOrder 0..N-1, tbl/pic id·instid 고유화 (복제분 포함)"""
        objs = [e for e in self.root.iter() if e.tag in (P + "tbl", P + "pic", P + "container", P + "rect", P + "line", P + "ellipse")]
        seen = set(); nxt = max([int(e.get("id", "0")) for e in objs] + [0]) + 1
        for i, e in enumerate(objs):
            if e.tag in (P + "tbl", P + "pic"): e.set("zOrder", str(i)) if e.get("zOrder") is not None else None
            eid = e.get("id")
            if eid in seen:
                e.set("id", str(nxt)); nxt += 1
            seen.add(e.get("id"))
        # instid
        seen = set(); nxt = max([int(e.get("instid", "0")) for e in objs] + [0]) + 1
        for e in objs:
            iid = e.get("instid")
            if iid is None: continue
            if iid in seen: e.set("instid", str(nxt)); nxt += 1
            seen.add(e.get("instid"))

    # ── 저장 ──
    def serialize(self):
        out = etree.tostring(self.root, encoding="unicode")
        orig_root = re.search(r"<hs:sec\b[^>]*>", self.raw).group(0)
        out = re.sub(r"^<hs:sec\b[^>]*>", lambda m: orig_root, out, count=1)
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>' + out).encode("utf-8")

    def save(self, out_path, section_bytes=None):
        secb = section_bytes if section_bytes is not None else self.serialize()
        with zipfile.ZipFile(out_path, "w") as z:
            for i in self.entries:
                zi = zipfile.ZipInfo(i.filename, date_time=i.date_time); zi.compress_type = i.compress_type; zi.external_attr = i.external_attr
                if i.filename == "mimetype": zi.compress_type = zipfile.ZIP_STORED
                z.writestr(zi, secb if i.filename == self.sec_name else self.data[i.filename])
        return out_path

    def baseline(self, out_path):
        """무변경 재저장 → 원본과 바이트 비교(항목별)"""
        self.save(out_path, section_bytes=self.data[self.sec_name])
        with zipfile.ZipFile(self.path) as a, zipfile.ZipFile(out_path) as b:
            diff = [n for n in a.namelist() if a.read(n) != b.read(n)]
            order = a.namelist() == b.namelist()
        return dict(same_entries=not diff, diff=diff, same_order=order)

    # ── 검증 (§8 일부) ──
    def verify(self, out_path):
        rep = {}
        with zipfile.ZipFile(out_path) as z:
            names = z.namelist(); rep["mimetype_first_stored"] = names[0] == "mimetype" and z.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
            bad = []
            for n in names:
                if n.endswith((".xml", ".hpf", ".rdf")):
                    try: etree.fromstring(z.read(n))
                    except Exception as ex: bad.append((n, str(ex)[:80]))
            rep["xml_parse_errors"] = bad
            sec = z.read(self.sec_name).decode("utf-8")
            rep["ns_count_same"] = len(re.findall(r'xmlns:\w+=', re.search(r"<hs:sec\b[^>]*>", sec).group(0))) == len(re.findall(r'xmlns:\w+=', re.search(r"<hs:sec\b[^>]*>", self.raw).group(0)))
            root = etree.fromstring(z.read(self.sec_name))
            zo = [e.get("zOrder") for e in root.iter() if e.tag in (P + "tbl", P + "pic") and e.get("zOrder") is not None]
            rep["zorder_unique"] = len(zo) == len(set(zo))
            ids = [e.get("id") for e in root.iter() if e.tag in (P + "tbl", P + "pic")]
            rep["obj_id_unique"] = len(ids) == len(set(ids))
            # lineseg textpos ≤ 글자 수
            bad_ls = 0
            for p in root.iter(P + "p"):
                n = len(para_text(p))
                for ls in p.findall(P + "linesegarray/" + P + "lineseg"):
                    if int(ls.get("textpos", 0)) > n: bad_ls += 1
            rep["lineseg_overflow"] = bad_ls
            # 표 격자
            bad_t = []
            for t in root.iter(P + "tbl"):
                rc, cc = int(t.get("rowCnt")), int(t.get("colCnt")); cover = {}
                for tr in t.findall(P + "tr"):
                    for tc in tr.findall(P + "tc"):
                        ca = tc.find(P + "cellAddr"); sp = tc.find(P + "cellSpan")
                        r0, c0 = int(ca.get("rowAddr")), int(ca.get("colAddr")); rs, cs = (int(sp.get("rowSpan")), int(sp.get("colSpan"))) if sp is not None else (1, 1)
                        for r in range(r0, r0 + rs):
                            for c in range(c0, c0 + cs): cover[(r, c)] = cover.get((r, c), 0) + 1
                holes = [(r, c) for r in range(rc) for c in range(cc) if (r, c) not in cover]; overl = [k for k, v in cover.items() if v > 1]
                if holes or overl or len(t.findall(P + "tr")) != rc: bad_t.append((t.get("id"), len(holes), len(overl), len(t.findall(P + "tr")), rc))
            rep["table_grid_errors"] = bad_t
        rep["ok"] = rep["mimetype_first_stored"] and not rep["xml_parse_errors"] and rep["ns_count_same"] and rep["zorder_unique"] and rep["obj_id_unique"] and rep["lineseg_overflow"] == 0 and not rep["table_grid_errors"]
        return rep

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    d = Hwpx(sys.argv[1]).load()
    q = sys.argv[2] if len(sys.argv) > 2 else None
    for row in d.dump(contains=q): print(row)

# -*- coding: utf-8 -*-
"""
HWPX 쪽 배치 다듬기 (한글 렌더링 PDF로 확인한 문제의 원인별 처방, 2026-09-11)
  keep_with_next(doc, para_pr_ids)   : header.xml의 문단모양을 복제해 keepWithNext="1"(다음 문단과 함께)로 만들고, 해당 문단모양을 쓰는 문단에 배정
                                        → 표 캡션·소제목이 표를 남겨두고 홀로 쪽 끝에 남는 문제 해결
  drop_pagebreaks(doc, style_ids)    : 세부 항목 문단(본문 스타일)에 걸린 강제 쪽나눔 제거 → 반쯤 빈 쪽 해소
  compact_tables(doc, min_rows, h)   : 행 수가 많은 표의 셀 최소높이를 줄여 내용 높이대로 배치 → 표가 한 쪽에 들어가도록
"""
import re
from hwpx_edit import P

HH = "http://www.hancom.co.kr/hwpml/2011/head"

def keep_with_next(doc, para_pr_ids):
    """반환 {old_id: new_id}. doc.data['Contents/header.xml'] 갱신 + 본문 문단 paraPrIDRef 교체"""
    key = "Contents/header.xml"; h = doc.data[key].decode("utf-8")
    m = re.search(r'<hh:paraProperties itemCnt="(\d+)"', h); cnt = int(m.group(1)); mapping = {}; clones = []
    for pid in para_pr_ids:
        mm = re.search(r'<hh:paraPr id="%s"[^>]*>.*?</hh:paraPr>' % pid, h, re.S)
        if not mm: continue
        blk = mm.group(0); new_id = cnt; cnt += 1
        nb = blk.replace('<hh:paraPr id="%s"' % pid, '<hh:paraPr id="%d"' % new_id, 1).replace('keepWithNext="0"', 'keepWithNext="1"', 1)
        clones.append(nb); mapping[str(pid)] = str(new_id)
    # ★ 한글은 paraPrIDRef를 목록의 순서(index)로 찾는다 → 복제본은 반드시 목록 끝에 덧붙인다(중간 삽입 시 뒤쪽 id 전부 어긋남, 2026-09-11 실측)
    end = h.rfind('</hh:paraProperties>'); h = h[:end] + "".join(clones) + h[end:]
    h = h.replace('<hh:paraProperties itemCnt="%d"' % int(m.group(1)), '<hh:paraProperties itemCnt="%d"' % cnt, 1)
    doc.data[key] = h.encode("utf-8")
    n = 0
    for p in doc.paragraphs():
        pp = p.get("paraPrIDRef")
        if pp in mapping: p.set("paraPrIDRef", mapping[pp]); n += 1
    return dict(mapping=mapping, changed=n)

def drop_pagebreaks(doc, style_ids):
    n = 0
    for p in doc.paragraphs():
        if p.get("pageBreak") == "1" and p.get("styleIDRef") in set(map(str, style_ids)) and p.find(".//" + P + "pic") is None:
            p.set("pageBreak", "0"); n += 1
    return n

def compact_tables(doc, min_rows=12, h_body=1900, h_head=2100, skip_first_paras=5):
    """표지(간지)처럼 레이아웃용 표(문서 앞 문단, 그림 포함 표)는 건드리지 않는다 — 2026-09-11 표지 회색 띠가 조각난 원인"""
    n = 0; ps = doc.paragraphs(); head = set(id(p) for p in ps[:skip_first_paras])
    for tbl in doc.root.iter(P + "tbl"):
        if int(tbl.get("rowCnt", 0)) < min_rows: continue
        if tbl.find(".//" + P + "pic") is not None: continue
        top = tbl
        while top is not None and top.getparent() is not None and top.getparent().tag != "{http://www.hancom.co.kr/hwpml/2011/section}sec": top = top.getparent()
        if id(top) in head: continue
        for tr in tbl.findall(P + "tr"):
            for tc in tr.findall(P + "tc"):
                cs = tc.find(P + "cellSz")
                if cs is None: continue
                cs.set("height", str(h_head if tc.get("header") == "1" else h_body))
        sz = tbl.find(P + "sz")
        if sz is not None:
            tot = sum(int(tr.find(P + "tc").find(P + "cellSz").get("height")) for tr in tbl.findall(P + "tr") if tr.find(P + "tc") is not None)
            sz.set("height", str(tot))
        n += 1
    return n

def stranded_from_pdf(doc, pdf_path, min_fill=0.65, head_styles=("5", "6", "7", "8", "10", "15", "16"), skip_pages=2):
    """한글 렌더 PDF에서 '쪽 끝에 홀로 남은 캡션·제목'을 찾아 그 묶음(연속된 제목 문단)의 첫 문단에 강제 쪽나눔을 건다
    (표는 글자처럼 취급되어 keepWithNext가 안 먹는 문제의 우회). 묶음이 이미 쪽 머리에 있으면(앞 쪽나눔 때문에 표만 다음 쪽으로 밀린 경우)
    묶음 뒤 문단의 쪽나눔을 푼다. 반환: 조치 목록 (2026-09-11)"""
    import fitz, re
    from hwpx_edit import para_text
    pdf = fitz.open(pdf_path); ps = doc.paragraphs(); hit = []; cursor = -1   # 같은 제목(①고정하중 등)이 반복되므로 문서 순서로 전진하며 찾는다
    head_re = re.compile(r"^(【표|【그림|\d+(\.\d+)+\s|[가-힣]\.\s|\d+\)\s|\[단계|[①-⑳㉠-㉭])")
    norm = lambda t: re.sub(r"\s+", "", t)
    strip_no = lambda t: norm(re.sub(r"^(【(표|그림)\s*[\d.]+】|[①-⑳㉠-㉭]|[가-힣]\.|\d+\)|\d+(\.\d+)+|\[단계\s*\d+\])\s*", "", t))[:16]
    is_head = lambda p: (head_re.match(para_text(p).strip()) or p.get("styleIDRef") in head_styles) and para_text(p).strip() and p.find(".//" + P + "tbl") is None and p.find(".//" + P + "pic") is None and p.find(".//" + P + "equation") is None
    for i in range(skip_pages, len(pdf) - 1):   # 표지(목차 표)는 건너뛴다 — '5.5 …'가 제목으로 잡혀 cursor가 끝으로 튀는 사고
        pg = pdf[i]; H = pg.rect.height; blocks = [b for b in pg.get_text("blocks") if b[4].strip() and 0.06 * H < b[1] and b[3] < 0.92 * H]
        if not blocks: continue
        blocks.sort(key=lambda b: b[1]); last = blocks[-1]; fill = last[3] / H; ltxt = last[4].strip().split("\n")[-1].strip()
        ftxt = blocks[0][4].strip().split("\n")[0].strip()
        if not head_re.match(ltxt): continue
        if ltxt.startswith("【그림"): continue   # 그림 캡션은 그림 아래에 붙으므로 쪽 끝에 오는 것이 정상
        # 채움(fill)과 무관하게 판단한다: 뒤에 표·그림이 오는 제목·표 캡션이 쪽 끝에 홀로 남는 것 자체가 문제(2026-09-11 p16 ⑧, p20 ③ 실측)
        key = strip_no(ltxt)
        cands = [k for k, p in enumerate(ps) if k > cursor and key and p.find(".//" + P + "equation") is None and norm(para_text(p)).startswith(key)]
        if not cands: continue
        end = k = cands[0]; cursor = end
        while k - 1 > 0 and ps[k].get("pageBreak") != "1" and is_head(ps[k - 1]): k -= 1   # 이미 쪽나눔이 걸린 문단이 묶음의 머리
        nxt = end + 1
        while nxt < len(ps) and not para_text(ps[nxt]).strip() and ps[nxt].find(".//" + P + "tbl") is None and ps[nxt].find(".//" + P + "pic") is None: nxt += 1
        if nxt >= len(ps) or (ps[nxt].find(".//" + P + "tbl") is None and ps[nxt].find(".//" + P + "pic") is None): continue   # 뒤에 표·그림이 오는 제목만 대상(목록 항목 ⑥… 은 제외)
        at_top = ps[k].get("pageBreak") == "1" or (strip_no(ftxt) and norm(para_text(ps[k])).startswith(strip_no(ftxt)))
        if at_top:
            if nxt < len(ps) and ps[nxt].get("pageBreak") == "1": ps[nxt].set("pageBreak", "0"); hit.append(f"p{i+1}: unbreak " + para_text(ps[nxt]).strip()[:40])
            continue
        ps[k].set("pageBreak", "1"); hit.append(f"p{i+1}: break " + para_text(ps[k]).strip()[:40])
        j = k + 1   # 묶음 안·묶음 뒤(표/그림 전까지)의 기존 쪽나눔은 푼다 — 제목만 남은 쪽이 생기지 않도록
        while j < len(ps) and j < end + 8 and ps[j].find(".//" + P + "tbl") is None and ps[j].find(".//" + P + "pic") is None:
            if ps[j].get("pageBreak") == "1": ps[j].set("pageBreak", "0"); hit.append(f"p{i+1}:   unbreak " + para_text(ps[j]).strip()[:40])
            j += 1
    return hit

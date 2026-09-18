# -*- coding: utf-8 -*-
import sys, os, json; sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\Midas\core\tools"); sys.path.insert(0, r"D:\Midas\projects\순천만IC2교")
from hwpx_edit import Hwpx, para_text, P
import build_ch5 as B
doc = Hwpx(os.path.join(B.REP, "원본_5장_초안.hwpx")).load()
def chk(tag):
    ps = doc.paragraphs(); t = ps[276].find(".//" + P + "tbl")
    print(f"[{tag}] 문단 {len(ps)}, p276 표 {'있음' if t is not None else '없음'} '{para_text(ps[276]).strip()[:30]}'")
chk("load")
ps = doc.paragraphs(); idx = lambda text, start=0: doc.find_para(text, start)[0]
i = idx("교량연장 : L"); doc.set_para_text(ps[i], "X"); chk("step0a")
t = B.table_of(doc, 227); doc.clone_row(t, src_row=14, count=10); chk("clone227")
doc.mark_header(t, 3); chk("markhdr")
t = B.table_of(doc, 237); B.setc(doc, t, 1, 1, "2.2"); chk("setc237")
B.caption_units(doc, 266); chk("caption266")
t = B.table_of(doc, 267); B.setc(doc, t, 3, 2, "1"); doc.mark_header(t, 3); chk("267")

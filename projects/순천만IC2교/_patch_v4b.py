# -*- coding: utf-8 -*-
"""5장_v4.hwpx 빌드 후 서식 패치 (2026-09-11, 한글 렌더 PDF 점검에서 나온 문제) — 멱등
  1. 바닥판 고정하중 표(캔틸레버 좌·우)의 '검토단면' 범례 셀이 22 mm로 너무 좁아 글자가 한 자씩 꺾임
     → 그림 셀 13655→9800, 범례 셀 6366→10221(표 폭 유지), 그림 축소, 범례 문구를 행 번호(①~⑨)와 맞춰 짧게
  2. 교각 P3 NX 휨모멘트도 캡처가 세로로 길어 한 쪽을 통째로 차지 → 폭 14000 HWPUNIT(≈49 mm)으로 축소
  4. B.fig 캡션을 문서 표준 그림제목(자동번호)으로 통일  5. 좌측 캔틸레버 ④ 앞 쪽나눔 제거
  3. '나. 구조검토 조건', '5.2.4 … 결과 요약' 앞의 강제 쪽나눔 제거(앞 쪽이 1/4만 차고 넘어가던 원인)
사용: python _patch_v4b.py  (report/5장_v4.hwpx 를 제자리에서 갱신)"""
import sys, os
sys.path.insert(0, r"D:\Midas\tools")
from hwpx_edit import Hwpx, para_text, P

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report")
SRC = os.path.join(R, "5장_v4.hwpx")
HC = "{http://www.hancom.co.kr/hwpml/2011/core}"

LEGEND = ["① 방호벽 0.23×0.97", "② 경사부 0.07×0.97", "③ 기부 0.30×0.35", "④ 헌치 0.12×0.175", "⑤ 연석 0.12×0.175",
          "⑥ 바닥판 1.14×0.24", "⑦ 변단면 1.03×0.107", "⑧ 단부 0.11×0.107", "⑨ 포장 0.69×0.05", "윤하중 위치 X=0.39 m", "(단위 m, 슬래브 일반도)"]

def resize_pic(pic, cw):
    """표시 폭을 cw(HWPUNIT)로, 높이는 원본 비율. swap_pic과 같은 요소를 손본다."""
    org = pic.find(P + "orgSz"); ow, oh = int(org.get("width")), int(org.get("height"))
    ch = int(round(cw * oh / ow))
    for tag in ("curSz", "sz"):
        el = pic.find(P + tag)
        if el is not None: el.set("width", str(cw)); el.set("height", str(ch))
    rot = pic.find(P + "rotationInfo")
    if rot is not None: rot.set("centerX", str(cw // 2)); rot.set("centerY", str(ch // 2))
    ri = pic.find(P + "renderingInfo")
    if ri is not None:
        sm = ri.find(HC + "scaMatrix")
        if sm is not None: sm.set("e1", f"{cw / ow:.6f}"); sm.set("e5", f"{ch / oh:.6f}")
    return cw, ch

def main():
    doc = Hwpx(SRC); doc.load(); ps = doc.paragraphs(); log = []
    # 1. 범례 셀
    for k, p in enumerate(ps):
        tbl = p.find(".//" + P + "tbl")
        if tbl is None or tbl.find(".//" + P + "pic") is None: continue
        cells = {(tc.find(P + "cellAddr").get("colAddr"), tc.find(P + "cellAddr").get("rowAddr")): tc for tc in tbl.iter(P + "tc")}
        pic_tc, leg_tc = cells.get(("6", "1")), cells.get(("7", "1"))
        if pic_tc is None or leg_tc is None or pic_tc.find(".//" + P + "pic") is None: continue
        if "방호벽" not in "".join(para_text(q) for q in leg_tc.iter(P + "p")) and "①" not in "".join(para_text(q) for q in leg_tc.iter(P + "p")): continue
        pic_tc.find(P + "cellSz").set("width", "9800"); leg_tc.find(P + "cellSz").set("width", "10221")
        cw, ch = resize_pic(pic_tc.find(".//" + P + "pic"), 9500)
        paras = list(leg_tc.iter(P + "p"))
        for q, t in zip(paras, LEGEND): doc.set_para_text(q, t)
        for q in paras[len(LEGEND):]: doc.set_para_text(q, "")
        log.append(f"legend table @para {k}: pic {cw}x{ch}, {len(paras)} lines")
    # 2. NX 캡처 축소
    for k, p in enumerate(ps):
        if "MIDAS CIVIL NX 2026 프레임 모델" in para_text(p):
            for q in ps[k + 1:k + 3]:
                pic = q.find(".//" + P + "pic")
                if pic is not None: log.append("NX fig -> %dx%d" % resize_pic(pic, 14000)); break
            break
    # 3. 쪽나눔 제거
    for k, p in enumerate(ps):
        t = para_text(p).strip()
        if p.get("pageBreak") == "1" and (t == "구조검토 조건" or t.startswith("상부구조 안전성 검토 결과 요약")):
            p.set("pageBreak", "0"); log.append(f"unbreak {k}: {t[:20]}")
    # 4. B.fig 캡션(스타일 72 '<그림>', 자동번호 없음) → 문서 표준 '그림제목'(스타일 16, 문단모양 71: 【그림 5.x】 자동번호, 글자모양 2)
    for k, p in enumerate(ps):
        if p.get("styleIDRef") == "72":
            p.set("styleIDRef", "16"); p.set("paraPrIDRef", "71")
            for r in p.findall(P + "run"): r.set("charPrIDRef", "2")
            log.append(f"figcap numbered {k}: {para_text(p).strip()[:24]}")
    # 5. 바닥판 좌측 캔틸레버 '④ 단면검토' 앞 쪽나눔: ①②표가 한 쪽에 들어가면서 ③표만 남은 쪽(26 %) 뒤에 ④가 들어갈 자리가 생김
    for k, p in enumerate(ps):
        if p.get("pageBreak") == "1" and para_text(p).strip() == "단면검토" and 100 < k < 115: p.set("pageBreak", "0"); log.append(f"unbreak {k}: 단면검토")
    # 6. 그림 5.13 교대 배근 단면 A-A: 이전 크롭이 표제란 조각을 포함하고 기초 하단이 잘림 → dxf_render 재크롭(x 24200~36600, y 10900~26300) 이미지로 교체
    import glob
    from PIL import Image
    png = glob.glob(os.path.join(os.path.dirname(SRC), "..", "png", "report", "A1_배근_단면AA", "*.png"))
    if png:
        im = Image.open(png[0]); data = open(png[0], "rb").read()
        for k, p in enumerate(ps):
            if para_text(p).strip().startswith("교대 A1 배근 단면 A-A"):
                pic = ps[k - 1].find(".//" + P + "pic")
                if pic is not None:
                    ref = doc.add_image(data, "png"); doc.swap_pic(pic, ref, im.size[0], im.size[1], max_width_hu=30000); log.append(f"A-A fig swapped ({im.size[0]}x{im.size[1]})")
                break
    doc.renumber_objects(); doc.save(SRC); v = doc.verify(SRC)
    print("\n".join(log)); print("verify ok:", v["ok"])

if __name__ == "__main__":
    main()

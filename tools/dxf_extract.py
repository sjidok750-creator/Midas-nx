# -*- coding: utf-8 -*-
"""
DXF → 구조화 추출 (도면 판독기 1/3)
  python dxf_extract.py <dxf파일 또는 폴더> <출력폴더>
각 DXF마다 <이름>.json 을 만든다:
  texts : [{x,y,h,layer,text}]   (블록 내부 포함, MTEXT 서식코드 제거)
  dims  : [{x,y,value,text,layer}] (DIMENSION 실측값 — 도면의 진짜 숫자)
  rows  : y좌표로 묶은 표 복원 문자열 목록
  layers: 레이어명 → 엔티티 수
  bbox  : 모델공간 범위
그리고 폴더 단위 index.json (파일별 문자·치수 수, 제목 후보).
"""
import sys, os, re, json, glob
import ezdxf
from ezdxf import bbox as _bbox

def clean(t: str) -> str:
    t = re.sub(r"\\[A-Za-z][^;]*;", "", t)          # MTEXT 서식 \fXXX; \H1.2x; 등
    t = re.sub(r"[{}]", "", t)
    t = t.replace("\\P", " ").replace("%%D", "°").replace("%%d", "°")
    t = t.replace("%%C", "Ø").replace("%%c", "Ø").replace("%%P", "±").replace("%%p", "±").replace("%%%", "%")
    return re.sub(r"\s+", " ", t).strip()

def _grab(e):
    t = e.dxftype()
    try:
        if t == "TEXT":
            return dict(x=e.dxf.insert.x, y=e.dxf.insert.y, h=float(e.dxf.height), layer=e.dxf.layer, text=e.dxf.text)
        if t == "MTEXT":
            return dict(x=e.dxf.insert.x, y=e.dxf.insert.y, h=float(e.dxf.char_height), layer=e.dxf.layer, text=e.text)
        if t == "ATTRIB":
            return dict(x=e.dxf.insert.x, y=e.dxf.insert.y, h=float(e.dxf.height), layer=e.dxf.layer, text=e.dxf.text)
    except Exception:
        pass
    return None

def extract(path: str) -> dict:
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    texts, dims, layers = [], [], {}
    for e in msp:
        layers[e.dxf.layer] = layers.get(e.dxf.layer, 0) + 1
        r = _grab(e)
        if r:
            texts.append(r)
        if e.dxftype() == "INSERT":
            for a in e.attribs:
                r = _grab(a)
                if r: texts.append(r)
            try:
                for sub in e.virtual_entities():
                    r = _grab(sub)
                    if r: texts.append(r)
                    if sub.dxftype() == "DIMENSION":
                        dims.append(_dim(sub))
            except Exception:
                pass
        if e.dxftype() == "DIMENSION":
            dims.append(_dim(e))
    texts = [dict(t, text=clean(t["text"])) for t in texts]
    texts = [t for t in texts if t["text"]]
    dims = [d for d in dims if d]
    try:
        bb = _bbox.extents(msp, fast=True)
        bbox = [bb.extmin.x, bb.extmin.y, bb.extmax.x, bb.extmax.y]
    except Exception:
        bbox = None
    return dict(file=os.path.basename(path), texts=texts, dims=dims, rows=rows(texts), layers=layers, bbox=bbox)

def _dim(e):
    try:
        m = e.get_measurement()
        if not isinstance(m, (int, float)):
            m = float(getattr(m, "magnitude", 0))
        p = e.dxf.defpoint
        raw = e.dxf.text
        txt = clean(raw) if raw not in ("", "<>") else ""
        return dict(x=p.x, y=p.y, value=float(m), text=txt, layer=e.dxf.layer)
    except Exception:
        return None

def rows(texts, ytol=None):
    """y가 가까운 문자를 한 줄로 묶어 표를 복원. ytol 기본 = 중간 글자높이의 0.6배"""
    if not texts:
        return []
    hs = sorted(t["h"] for t in texts)
    ytol = ytol or max(hs[len(hs)//2] * 0.6, 1.0)
    items = sorted(texts, key=lambda a: (-a["y"], a["x"]))
    R, cur, y0 = [], [], None
    for t in items:
        if y0 is None or abs(t["y"] - y0) < ytol:
            cur.append(t["text"]); y0 = t["y"] if y0 is None else y0
        else:
            R.append(" | ".join(cur)); cur, y0 = [t["text"]], t["y"]
    if cur:
        R.append(" | ".join(cur))
    return R

def title_guess(texts):
    """가장 큰 글자 3개를 제목 후보로"""
    big = sorted(texts, key=lambda t: -t["h"])[:3]
    return [t["text"] for t in big]

def main(src, out):
    os.makedirs(out, exist_ok=True)
    files = sorted(glob.glob(os.path.join(src, "*.dxf"))) if os.path.isdir(src) else [src]
    index = []
    for f in files:
        try:
            d = extract(f)
        except Exception as ex:
            index.append(dict(file=os.path.basename(f), error=str(ex)[:200])); print("FAIL", f, ex); continue
        name = os.path.splitext(os.path.basename(f))[0]
        with open(os.path.join(out, name + ".json"), "w", encoding="utf-8") as fp:
            json.dump(d, fp, ensure_ascii=False, indent=1)
        index.append(dict(file=d["file"], n_text=len(d["texts"]), n_dim=len(d["dims"]), n_rows=len(d["rows"]),
                          title=title_guess(d["texts"]), bbox=d["bbox"]))
        print(f"{name[:60]:60s} 문자 {len(d['texts']):5d} 치수 {len(d['dims']):4d}")
    with open(os.path.join(out, "index.json"), "w", encoding="utf-8") as fp:
        json.dump(index, fp, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1], sys.argv[2])

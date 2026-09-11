# -*- coding: utf-8 -*-
"""
DXF 부분 확대 렌더 (도면 판독기 3/3)
  python dxf_crop.py <dxf> <출력png> --find "정규식" [--margin 3000] [--dpi 200] [--pick N]
  python dxf_crop.py <dxf> <출력png> --box x0,y0,x1,y1 [--dpi 200]
--find : 정규식에 맞는 문자를 찾아 그 주변(margin, 도면단위)을 잘라 렌더. 여러 개면 --pick 번째(0부터), 기본은 전부 감싸는 범위.
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))
from dxf_extract import extract
from dxf_render import render

def main():
    a = sys.argv[1:]
    dxf, out = a[0], a[1]
    opt = {"--margin": "3000", "--dpi": "200", "--pick": None, "--find": None, "--box": None}
    i = 2
    while i < len(a):
        opt[a[i]] = a[i + 1]; i += 2
    if opt["--box"]:
        box = [float(v) for v in opt["--box"].split(",")]
    else:
        d = extract(dxf)
        rx = re.compile(opt["--find"])
        hits = [t for t in d["texts"] if rx.search(t["text"])]
        print(f"'{opt['--find']}' 일치 {len(hits)}개")
        for k, t in enumerate(hits[:30]):
            print(f"  [{k}] x={t['x']:.0f} y={t['y']:.0f} h={t['h']:.0f} {t['text'][:40]}")
        if not hits:
            sys.exit(1)
        if opt["--pick"] is not None:
            hits = [hits[int(opt["--pick"])]]
        m = float(opt["--margin"])
        xs = [t["x"] for t in hits]; ys = [t["y"] for t in hits]
        box = [min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m]
    w = box[2] - box[0]; h = box[3] - box[1]
    print("crop box:", [round(v) for v in box], f"({w:.0f} x {h:.0f})")
    render(dxf, out, dpi=int(opt["--dpi"]), crop=box, width_in=16)
    print("saved", out, os.path.getsize(out) // 1024, "KB")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

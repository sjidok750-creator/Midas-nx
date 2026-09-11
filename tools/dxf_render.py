# -*- coding: utf-8 -*-
"""
DXF → PNG 렌더 (도면 판독기 2/3) — 내가 그림으로 읽기 위한 용도
  python dxf_render.py <dxf파일|폴더> <출력폴더> [--dpi 150] [--crop x0,y0,x1,y1]
"""
import sys, os, glob
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]   # 한글 글꼴
plt.rcParams["axes.unicode_minus"] = False
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy

def render(path, out_png, dpi=150, crop=None, width_in=24):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    fig = plt.figure(figsize=(width_in, width_in * 0.7))
    ax = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(doc)
    cfg = Configuration(color_policy=ColorPolicy.BLACK, background_policy=BackgroundPolicy.WHITE, min_lineweight=0.1)
    Frontend(ctx, MatplotlibBackend(ax), config=cfg).draw_layout(msp, finalize=True)
    if crop:
        ax.set_xlim(crop[0], crop[2]); ax.set_ylim(crop[1], crop[3])
    ax.set_aspect("equal")
    fig.savefig(out_png, dpi=dpi, facecolor="white")
    plt.close(fig)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    dpi, crop = 150, None
    if "--dpi" in a:
        i = a.index("--dpi"); dpi = int(a[i + 1]); del a[i:i + 2]
    if "--crop" in a:
        i = a.index("--crop"); crop = [float(v) for v in a[i + 1].split(",")]; del a[i:i + 2]
    src, out = a[0], a[1]
    os.makedirs(out, exist_ok=True)
    files = sorted(glob.glob(os.path.join(src, "*.dxf"))) if os.path.isdir(src) else [src]
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        png = os.path.join(out, name + ".png")
        try:
            render(f, png, dpi, crop)
            print("OK ", name[:70], f"{os.path.getsize(png)//1024} KB")
        except Exception as ex:
            print("FAIL", name[:70], str(ex)[:150])

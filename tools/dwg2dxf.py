# -*- coding: utf-8 -*-
"""
DWG → DXF 일괄 변환 (ODA File Converter CLI)
  python dwg2dxf.py <출력폴더> <dwg파일|폴더> [<dwg파일|폴더> ...] [--glob 패턴]
- 이미 있는 DXF는 건너뜀
- ODA는 폴더 단위로만 받으므로 선택 파일을 임시 폴더에 모아 변환
"""
import sys, os, glob, shutil, subprocess, tempfile, time

ODA = r"C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe"

def convert(out_dir, inputs, pattern="*.dwg", version="ACAD2018", timeout=600):
    os.makedirs(out_dir, exist_ok=True)
    files = []
    for p in inputs:
        if os.path.isdir(p):
            files += glob.glob(os.path.join(p, pattern))
        else:
            files += glob.glob(p)
    files = sorted(set(files))
    todo = [f for f in files if not os.path.exists(os.path.join(out_dir, os.path.splitext(os.path.basename(f))[0] + ".dxf"))]
    print(f"대상 {len(files)}개, 변환 필요 {len(todo)}개")
    if not todo:
        return []
    tmp = tempfile.mkdtemp(prefix="oda_", dir=out_dir)
    for f in todo:
        shutil.copy2(f, tmp)
    t = time.time()
    r = subprocess.run([ODA, tmp, out_dir, version, "DXF", "0", "1", "*.dwg"], timeout=timeout,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    shutil.rmtree(tmp, ignore_errors=True)
    done, fail = [], []
    for f in todo:
        dxf = os.path.join(out_dir, os.path.splitext(os.path.basename(f))[0] + ".dxf")
        (done if os.path.exists(dxf) else fail).append(os.path.basename(f))
    print(f"ODA exit={r.returncode}  성공 {len(done)}  실패 {len(fail)}  ({time.time()-t:.0f}s)")
    for f in fail:
        print("  실패:", f)
    return done

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    pattern = "*.dwg"
    if "--glob" in args:
        i = args.index("--glob"); pattern = args[i + 1]; del args[i:i + 2]
    convert(args[0], args[1:], pattern)

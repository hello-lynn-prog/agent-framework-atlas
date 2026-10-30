# -*- coding: utf-8 -*-
"""把 sdk-对比图谱.html 的每页 slide 拆成独立 html，用 Edge 无头截图，再按内容实际底边自动裁掉空白。
用法:  python _build_png.py
"""
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
SRC = HERE / "sdk-对比图谱.html"
PNG = HERE / "png"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BG = (11, 18, 32)   # body 背景 #0b1220
TOL = 8             # 背景色容差
MARGIN = 36         # 裁切后保留的底部余量

src = SRC.read_text(encoding="utf-8")
style = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
sections = re.findall(r'(<section class="slide" id="(s\d+)" data-h="(\d+)">.*?</section>)', src, re.S)

PNG.mkdir(exist_ok=True)


def crop_bottom(path: Path) -> int:
    """从底部向上找第一条非背景行，裁掉其下的纯背景区，返回裁后高度。"""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    px = img.load()
    bottom = h
    for y in range(h - 1, -1, -1):
        row_has_content = any(
            abs(px[x, y][0] - BG[0]) > TOL or abs(px[x, y][1] - BG[1]) > TOL or abs(px[x, y][2] - BG[2]) > TOL
            for x in range(0, w, 4)  # 步进 4 列加速
        )
        if row_has_content:
            bottom = min(h, y + 1 + MARGIN)
            break
    if bottom < h:
        img.crop((0, 0, w, bottom)).save(path)
    return bottom


ok = 0
for html, sid, height in sections:
    n = sid[1:]
    page = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<style>{style} body{{background:#0b1220;margin:0}}</style></head>"
        f"<body>{html}</body></html>"
    )
    tmp = PNG / f"slide-{n}.html"
    tmp.write_text(page, encoding="utf-8")
    out = PNG / f"slide-{n}.png"
    r = subprocess.run([
        EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=1", f"--window-size=1600,{height}",
        "--virtual-time-budget=4000", f"--screenshot={out}",
        tmp.as_uri(),
    ], capture_output=True, timeout=90)
    tmp.unlink()
    if out.exists():
        final_h = crop_bottom(out)
        ok += 1
        print(f"slide-{n}.png  OK  ({out.stat().st_size//1024} KB, 1600x{final_h})")
    else:
        print(f"slide-{n}.png  FAIL  {r.stderr.decode(errors='ignore')[:200]}")

print(f"done: {ok}/{len(sections)}")
sys.exit(0 if ok == len(sections) else 1)

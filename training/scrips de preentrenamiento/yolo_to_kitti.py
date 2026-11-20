#!/usr/bin/env python3
"""Convierte dataset YOLO (gen_tickets.py) a formato KITTI para TAO.
Uso: python3 yolo_to_kitti.py --src dataset --dst kitti
Crea kitti/{train,val,test}/{images,labels} y kitti/classes.txt
"""
import argparse, re, json, shutil
from pathlib import Path
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("--src", default="dataset")
ap.add_argument("--dst", default="kitti")
a = ap.parse_args()
src, dst = Path(a.src), Path(a.dst)

yaml_txt = (src / "data.yaml").read_text(encoding="utf-8")
names = json.loads(re.search(r"names:\s*(\[.*\])", yaml_txt).group(1))
(dst).mkdir(parents=True, exist_ok=True)
(dst / "classes.txt").write_text("\n".join(names) + "\n")

for split in ("train", "val", "test"):
    (dst / split / "images").mkdir(parents=True, exist_ok=True)
    (dst / split / "labels").mkdir(parents=True, exist_ok=True)
    n = 0
    for img in sorted((src / "images" / split).glob("*.jpg")):
        w, h = Image.open(img).size
        shutil.copy(img, dst / split / "images" / img.name)
        out = []
        lab = src / "labels" / split / (img.stem + ".txt")
        for ln in lab.read_text().split("\n"):
            if not ln.strip():
                continue
            c, cx, cy, bw, bh = ln.split()
            cx, cy, bw, bh = float(cx) * w, float(cy) * h, float(bw) * w, float(bh) * h
            x1, y1, x2, y2 = cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2
            out.append(f"{names[int(c)]} 0.00 0 0.00 {x1:.2f} {y1:.2f} {x2:.2f} {y2:.2f} 0.00 0.00 0.00 0.00 0.00 0.00 0.00")
        (dst / split / "labels" / (img.stem + ".txt")).write_text("\n".join(out) + "\n")
        n += 1
    print(split, n, "imágenes")

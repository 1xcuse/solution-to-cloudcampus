#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_visuals.py - make the three picture-style deliverables used in CloudCampus
assignments: a mind map, an academic poster, and a "photo" of edited work.

All three are driven by a JSON spec so the layout survives content changes.
Requires Pillow only.

  python3 gen_visuals.py mindmap   --spec mindmap.json --out mindmap.png
  python3 gen_visuals.py poster    --spec poster.json  --out poster.png
  python3 gen_visuals.py photo     --spec photo.json   --out edited.jpg

mindmap.json:
{"title": "...", "center": "...", "branches": [
   {"label": "...", "items": ["...", "..."]}, ... up to 4]}
poster.json:
{"title": "...", "subtitle": "...", "issue_title": "The issue", "issue": "...",
 "columns": [{"title": "...", "items": ["..."]}, ... up to 3],
 "plan_title": "...", "plan_items": ["..."], "takeaway": "...",
 "references": ["..."]}
photo.json:
{"title": "...", "subtitle": "...", "text": "paragraph ...",
 "annotations": [{"token": "word", "note": "...", "sub": "..."}],
 "checklist": "...", "next_step": "..."}
"""
from __future__ import annotations

import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np

SUPP = "/System/Library/Fonts/Supplemental"
HANDWRITING = os.path.join(SUPP, "Bradley Hand Bold.ttf")
MARKER = os.path.join(SUPP, "MarkerFelt.ttc")
ARIAL = os.path.join(SUPP, "Arial.ttf")
ARIAL_B = os.path.join(SUPP, "Arial Bold.ttf")


def font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def wrap(draw, text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_font(draw, text, path, size, maxw):
    f = font(path, size)
    while size > 8 and draw.textlength(text, font=f) > maxw:
        size -= 1
        f = font(path, size)
    return f


def mindmap(spec: dict, out: str) -> None:
    W, H = 1600, 1100
    img = Image.new("RGB", (W, H), (251, 250, 246))
    d = ImageDraw.Draw(img)
    f_title = fit_font(d, spec.get("title", ""), ARIAL_B, 34, W - 120)
    d.text((W / 2, 55), spec.get("title", ""), font=f_title, fill=(30, 45, 65), anchor="mm")
    f_center = font(ARIAL_B, 26)
    center = spec.get("center", "")
    cw, ch = 420, 140
    d.rounded_rectangle([(W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2], radius=18,
                        fill=(219, 233, 255), outline=(43, 95, 168), width=3)
    for i, ln in enumerate(wrap(d, center, f_center, cw - 40)):
        d.text((W / 2, H / 2 - 20 + i * 34), ln, font=f_center, fill=(31, 45, 61), anchor="mm")
    branches = spec.get("branches", [])[:4]
    spots = [(280, 250), (W - 280, 250), (280, H - 250), (W - 280, H - 250)]
    palette = [((230, 244, 234), (46, 125, 70)), ((255, 243, 214), (176, 122, 0)),
               ((253, 226, 226), (163, 58, 58)), ((234, 228, 251), (91, 63, 160))]
    for br, (bx, by), (fc, ec) in zip(branches, spots, palette):
        label = br.get("label", "")
        items = br.get("items", [])
        bw, bh = 340, 90
        d.rounded_rectangle([bx - bw / 2, by - bh / 2, bx + bw / 2, by + bh / 2], radius=16,
                            fill=fc, outline=ec, width=3)
        fl = font(ARIAL_B, 22)
        for i, ln in enumerate(wrap(d, label, fl, bw - 40)):
            d.text((bx, by - 12 + i * 28), ln, font=fl, fill=(31, 45, 61), anchor="mm")
        # connector
        edge = (bx - bw / 2 if bx < W / 2 else bx + bw / 2, by)
        d.line([(W / 2 + (-120 if bx < W / 2 else 120), H / 2 + (-40 if by < H / 2 else 40)), edge],
               fill=ec, width=3)
        # items
        fi = font(ARIAL, 17)
        for k, item in enumerate(items[:4]):
            yy = by + 72 + k * 30
            xx = bx + (170 if bx < W / 2 else -170)
            anchor = "lm" if bx < W / 2 else "rm"
            d.ellipse([xx - (0 if bx < W / 2 else 8), yy - 4, xx + (8 if bx < W / 2 else 0), yy + 4], fill=ec)
            d.text((xx + 14 if bx < W / 2 else xx - 14, yy), item, font=fi, fill=(45, 45, 45), anchor=anchor)
    img.save(out, optimize=True)
    print(f"saved {out} {img.size}")


def poster(spec: dict, out: str) -> None:
    W, H = 1200, 1697
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    green = (20, 83, 45)
    d.rectangle([0, 0, W, 160], fill=green)
    ft = fit_font(d, spec.get("title", ""), ARIAL_B, 40, W - 90)
    d.text((W / 2, 62), spec.get("title", ""), font=ft, fill="white", anchor="mm")
    d.text((W / 2, 118), spec.get("subtitle", ""), font=font(ARIAL, 21), fill=(209, 231, 214), anchor="mm")
    issue_title = spec.get("issue_title", "The issue")
    issue = spec.get("issue", "")
    d.rounded_rectangle([45, 190, W - 45, 330], radius=14, fill=(241, 247, 242), outline=green, width=2)
    d.text((70, 212), issue_title, font=font(ARIAL_B, 26), fill=green)
    fi = font(ARIAL, 19)
    for i, ln in enumerate(wrap(d, issue, fi, W - 140)):
        d.text((70, 252 + i * 26), ln, font=fi, fill=(30, 30, 30))
    cols = spec.get("columns", [])[:3]
    colw, gap, top, colh = 352, 24, 360, 640
    colors = [((180, 83, 9), (255, 244, 229)), ((185, 28, 28), (253, 236, 236)), ((29, 78, 216), (232, 240, 254))]
    for idx, col in enumerate(cols):
        (ec, bg) = colors[idx]
        x = 45 + idx * (colw + gap)
        d.rounded_rectangle([x, top, x + colw, top + colh], radius=14, fill=bg, outline=ec, width=2)
        d.text((x + 16, top + 18), col.get("title", ""), font=font(ARIAL_B, 24), fill=ec)
        yy = top + 68
        fb = font(ARIAL, 19)
        for it in col.get("items", []):
            lines = wrap(d, it, fb, colw - 58)
            d.text((x + 18, yy), "•", font=fb, fill=ec)
            for i, ln in enumerate(lines):
                d.text((x + 40, yy + i * 25), ln, font=fb, fill=(30, 30, 30))
            yy += len(lines) * 25 + 26
    py = 1030
    d.rounded_rectangle([45, py, W - 45, py + 250], radius=14, fill=(247, 247, 247), outline=(107, 114, 128), width=2)
    d.text((70, py + 18), spec.get("plan_title", "My plan for the next month"), font=font(ARIAL_B, 26), fill=(55, 65, 81))
    fb = font(ARIAL, 19)
    yy = py + 62
    for item in spec.get("plan_items", []):
        d.text((72, yy), "□", font=fb, fill=(55, 65, 81))
        d.text((100, yy), item, font=fb, fill=(30, 30, 30))
        yy += 42
    ty = py + 285
    d.rounded_rectangle([45, ty, W - 45, ty + 110], radius=14, fill=green)
    take = spec.get("takeaway", "")
    ftk = font(ARIAL_B, 21)
    tl = wrap(d, take, ftk, W - 190)
    for i, ln in enumerate(tl):
        d.text((W / 2, ty + 38 + i * 30), ln, font=ftk, fill="white", anchor="mm")
    ry = ty + 145
    d.text((70, ry), "References", font=font(ARIAL_B, 24), fill=(55, 65, 81))
    fs = font(ARIAL, 16)
    yy = ry + 38
    for ref in spec.get("references", []):
        for ln in wrap(d, ref, fs, W - 160):
            d.text((70, yy), ln, font=fs, fill=(40, 40, 40))
            yy += 24
    img.save(out, optimize=True)
    print(f"saved {out} {img.size}")


def photo(spec: dict, out: str) -> None:
    W, H = 1600, 2000
    paper = Image.new("RGB", (W, H), (253, 251, 245))
    d = ImageDraw.Draw(paper)
    for y in range(300, H - 100, 66):
        d.line([(110, y), (W - 110, y)], fill=(205, 220, 235), width=2)
    d.line([(170, 160), (170, H - 100)], fill=(235, 160, 160), width=2)
    f_title = font(HANDWRITING, 58)
    f_sub = font(MARKER, 30)
    f_body = font(HANDWRITING, 42)
    f_note = font(MARKER, 30)
    f_small = font(MARKER, 24)
    d.text((190, 150), spec.get("title", "Edited work"), font=f_title, fill=(28, 42, 68))
    d.text((190, 228), spec.get("subtitle", ""), font=f_sub, fill=(95, 95, 95))
    body = spec.get("text", "")
    maxw = W - 190 - 580
    lines = wrap(d, body, f_body, maxw)
    y0, lh = 300, 66
    for i, ln in enumerate(lines):
        d.text((190, y0 + i * lh), ln, font=f_body, fill=(24, 34, 88))
    red = (200, 30, 30)
    def locate(token):
        for i, ln in enumerate(lines):
            if token in ln:
                pos = ln.find(token)
                xs = 190 + d.textlength(ln[:pos], font=f_body)
                return i, xs, xs + d.textlength(token, font=f_body)
        return None
    used_rows = set()
    for ann in spec.get("annotations", []):
        token = ann.get("token", "")
        z = locate(token)
        if not z:
            continue
        li, xs, xe = z
        ty = y0 + li * lh
        used_rows.add(li)
        nx = W - 480
        d.text((nx, ty - 4), ann.get("note", ""), font=f_note, fill=red)
        if ann.get("sub"):
            d.text((nx, ty + 28), ann["sub"], font=f_small, fill=red)
        d.line([(min(nx, xs) - 8, ty + 20), (xe, ty + 34)], fill=red, width=2)
        d.polygon([(xe, ty + 34), (xe - 14, ty + 24), (xe - 14, ty + 44)], fill=red)
        d.line([(xs, ty + 52), (xe, ty + 52)], fill=red, width=3)
    cy = y0 + len(lines) * lh + 70
    if spec.get("checklist"):
        d.text((190, cy), spec["checklist"], font=f_note, fill=red)
    if spec.get("next_step"):
        d.text((190, cy + 42), spec["next_step"], font=f_sub, fill=red)
    arr = np.array(paper).astype(np.int16)
    arr = np.clip(arr + np.random.normal(0, 5, (H, W, 1)).astype(np.int16), 0, 255).astype(np.uint8)
    paper = Image.fromarray(arr)
    base = Image.new("RGB", (W + 300, H + 300), (58, 58, 63))
    shadow = Image.new("RGBA", (W + 140, H + 140), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rectangle([50, 50, W + 90, H + 90], fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(30))
    base.paste(shadow, (60, 80), shadow)
    rot = paper.rotate(2.0, expand=True, fillcolor=(253, 251, 245), resample=Image.BICUBIC)
    base.paste(rot, (130, 140))
    vig = Image.new("L", base.size, 0)
    ImageDraw.Draw(vig).ellipse([-350, -350, base.size[0] + 350, base.size[1] + 350], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(170))
    dark = ImageEnhance.Brightness(base).enhance(0.75)
    base = Image.composite(base, dark, vig)
    base = base.resize((1000, int(base.size[1] * 1000 / base.size[0])), Image.LANCZOS)
    base.save(out, quality=85, optimize=True)
    print(f"saved {out} {base.size}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Mind map / poster / edited-work photo generator")
    ap.add_argument("kind", choices=["mindmap", "poster", "photo"])
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    spec = json.load(open(args.spec, encoding="utf-8"))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    {"mindmap": mindmap, "poster": poster, "photo": photo}[args.kind](spec, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

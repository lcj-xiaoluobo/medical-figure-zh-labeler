#!/usr/bin/env python3
"""Render Chinese medical labels over image OCR boxes.

Inputs:
  --ocr TSV with columns: fig width height x y w h text
  --config JSON containing:
    {
      "image_pattern": "Fig. 6.{fig}-原图.png",
      "output_pattern": "Fig. 6.{fig}-中文版-翻译后.png",
      "font": "/System/Library/Fonts/STHeiti Medium.ttc",
      "translations": {"English": "中文"},
      "groups": [{"texts": ["A", "B"], "lines": ["中文AB"]}]
    }

This is a reusable template; patch per task for file naming or special grouping.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ORIENTATION_TEXTS = {
    "Superior",
    "Inferior",
    "Right",
    "Left",
    "Right +",
    "+",
    "+ Left",
    ".+ Left",
    "Right + Left",
    "posterior",
    "anterior",
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ocr", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--root", default=".", type=Path)
    return parser.parse_args()


def read_rows(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fig, width, height, x, y, w, h, text = line.split("\t", 7)
        rows.append(
            {
                "fig": fig,
                "width": int(float(width)),
                "height": int(float(height)),
                "x": float(x),
                "y": float(y),
                "w": float(w),
                "h": float(h),
                "text": text,
            }
        )
    return rows


def is_orientation(row):
    return row["text"] in ORIENTATION_TEXTS and row["x"] > row["width"] * 0.62 and row["y"] < 170


def font_for(font_path, h):
    size = round(h * 0.98)
    size = max(20, min(24, size))
    return ImageFont.truetype(font_path, size)


def orientation_font_for(font_path, h):
    size = round(h * 0.98)
    size = max(22, min(26, size))
    return ImageFont.truetype(font_path, size)


def local_background(arr, x0, y0, x1, y1):
    h, w = arr.shape[:2]
    sx0, sy0 = max(0, x0 - 18), max(0, y0 - 18)
    sx1, sy1 = min(w, x1 + 18), min(h, y1 + 18)
    sample = arr[sy0:sy1, sx0:sx1].reshape(-1, 3)
    dark = sample[sample.max(axis=1) < 85]
    if len(dark) < 20:
        dark = sample[sample.mean(axis=1) < 105]
    if len(dark) < 20:
        return (0, 0, 0)
    return tuple(int(c) for c in np.median(dark, axis=0))


def text_bbox(draw, text, font):
    return draw.textbbox((0, 0), text, font=font)


def draw_text_block(draw, box, lines, font, font_path, fill, image_width, align):
    x, y, w, h = box
    margin = 18
    if align == "right":
        available_width = x + w - margin
    elif align == "center":
        available_width = image_width - 2 * margin
    else:
        available_width = image_width - margin - x
    while font.size > 18:
        widths = [text_bbox(draw, line, font)[2] - text_bbox(draw, line, font)[0] for line in lines]
        if max(widths) <= available_width:
            break
        font = ImageFont.truetype(font_path, font.size - 1)
    bboxes = [text_bbox(draw, line, font) for line in lines]
    widths = [bbox[2] - bbox[0] for bbox in bboxes]
    heights = [bbox[3] - bbox[1] for bbox in bboxes]
    max_w = max(widths)
    gap = max(4, int(font.size * 0.16))
    total_h = sum(heights) + gap * (len(lines) - 1)
    if align == "right":
        dx = x + w - max_w
    elif align == "center":
        dx = x + w / 2 - max_w / 2
    else:
        dx = x
    dx = max(margin, min(dx, image_width - margin - max_w))
    dy = y + h / 2 - total_h / 2
    for line, bbox, tw, th in zip(lines, bboxes, widths, heights):
        tx = dx
        if align == "right":
            tx = dx + max_w - tw
        elif align == "center":
            tx = dx + (max_w - tw) / 2
        draw.text((tx, dy - bbox[1]), line, font=font, fill=fill)
        dy += th + gap


def make_box(rows):
    x0 = min(r["x"] for r in rows)
    y0 = min(r["y"] for r in rows)
    x1 = max(r["x"] + r["w"] for r in rows)
    y1 = max(r["y"] + r["h"] for r in rows)
    return (x0, y0, x1 - x0, y1 - y0)


def build_blocks(rows, config):
    used = set()
    blocks = []
    groups = [(tuple(g["texts"]), g["lines"]) for g in config.get("groups", [])]

    def center(row):
        return row["x"] + row["w"] / 2, row["y"] + row["h"] / 2

    def usable(i):
        return i not in used and not is_orientation(rows[i])

    for texts, lines in groups:
        for i, row in enumerate(rows):
            if not usable(i) or row["text"] != texts[0]:
                continue
            group = [i]
            prev = row
            for text in texts[1:]:
                px, py = center(prev)
                candidates = []
                for j, cand in enumerate(rows):
                    if not usable(j) or cand["text"] != text:
                        continue
                    cx, cy = center(cand)
                    if -8 <= cy - py <= 95 and abs(cx - px) <= 260:
                        candidates.append((abs(cy - py) + abs(cx - px) * 0.08, j))
                if not candidates:
                    group = []
                    break
                _, chosen = min(candidates)
                group.append(chosen)
                prev = rows[chosen]
            if group:
                used.update(group)
                selected = [rows[k] for k in group]
                blocks.append({"box": make_box(selected), "h": max(r["h"] for r in selected), "lines": lines})

    translations = config["translations"]
    missing = sorted({r["text"] for r in rows if not is_orientation(r) and r["text"] not in translations and rows.index(r) not in used})
    if missing:
        raise SystemExit("Missing translations: " + ", ".join(missing))
    for i, row in enumerate(rows):
        if usable(i):
            blocks.append({"box": make_box([row]), "h": row["h"], "lines": [translations[row["text"]]]})
    return blocks


def block_align(box, image_width):
    x, _y, w, _h = box
    center = x + w / 2
    if x + w < image_width * 0.47:
        return "right"
    if center > image_width * 0.55:
        return "left"
    return "center"


def draw_orientation(draw, rows, font_path, image_width):
    rows = [r for r in rows if is_orientation(r)]
    if not rows:
        return
    font = orientation_font_for(font_path, max(r["h"] for r in rows))
    color = (228, 217, 58)
    x0 = min(r["x"] for r in rows)
    y0 = min(r["y"] for r in rows)
    x1 = max(r["x"] + r["w"] for r in rows)
    y1 = max(r["y"] + r["h"] for r in rows)
    positions = [
        ((x0 + x1) / 2, y0 + font.size * 0.25, ["上"]),
        (x0 + min(40, (x1 - x0) * 0.28), (y0 + y1) / 2, ["右", "后"]),
        ((x0 + x1) / 2, (y0 + y1) / 2, ["+"]),
        (x1 - min(40, (x1 - x0) * 0.28), (y0 + y1) / 2, ["左", "前"]),
        ((x0 + x1) / 2, y1 - font.size * 0.15, ["下"]),
    ]
    for cx, cy, lines in positions:
        bboxes = [text_bbox(draw, line, font) for line in lines]
        heights = [b[3] - b[1] for b in bboxes]
        total_h = sum(heights) + 2 * (len(lines) - 1)
        y = cy - total_h / 2
        for line, bbox, th in zip(lines, bboxes, heights):
            tw = bbox[2] - bbox[0]
            draw.text((cx - tw / 2, y - bbox[1]), line, font=font, fill=color)
            y += th + 2


def render_one(root, fig, rows, config):
    image_path = root / config["image_pattern"].format(fig=fig)
    out_path = root / config["output_pattern"].format(fig=fig)
    original = Image.open(image_path).convert("RGB")
    arr = np.array(original)
    mask = np.zeros(arr.shape[:2], dtype=np.uint8)
    edge_rects = []

    for r in rows:
        x0 = int(max(0, r["x"] - 6))
        y0 = int(max(0, r["y"] - 5))
        x1 = int(min(original.width, r["x"] + r["w"] + 6))
        y1 = int(min(original.height, r["y"] + r["h"] + 5))
        near_edge = x0 <= 24 or y0 <= 24 or x1 >= original.width - 24 or y1 >= original.height - 24
        if near_edge:
            edge_rects.append((x0, y0, x1, y1))
        else:
            mask[y0:y1, x0:x1] = 255

    inpainted = cv2.inpaint(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR), mask, 3, cv2.INPAINT_TELEA)
    image = Image.fromarray(cv2.cvtColor(inpainted, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image)
    for rect in edge_rects:
        draw.rectangle(rect, fill=local_background(arr, *rect))

    label_heights = [r["h"] for r in rows if not is_orientation(r)]
    font = font_for(config["font"], float(np.median(label_heights)))
    for block in build_blocks(rows, config):
        draw_text_block(
            draw,
            block["box"],
            block["lines"],
            font,
            config["font"],
            (246, 246, 246),
            image.width,
            block_align(block["box"], image.width),
        )
    draw_orientation(draw, rows, config["font"], image.width)
    image.save(out_path)
    print(out_path)


def main():
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    rows = read_rows(args.ocr)
    for fig in sorted({r["fig"] for r in rows}, key=lambda x: (len(x), x)):
        render_one(args.root, fig, [r for r in rows if r["fig"] == fig], config)


if __name__ == "__main__":
    main()

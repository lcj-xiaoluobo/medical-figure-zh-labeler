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
from typing import Any

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


def load_image_dependencies():
    global cv2, np, Image, ImageDraw, ImageFont
    try:
        import cv2
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise SystemExit(
            "Missing image dependency. Install with: "
            "python -m pip install pillow numpy opencv-python"
        ) from exc


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ocr", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--root", default=".", type=Path)
    return parser.parse_args()


def read_rows(path):
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split("\t", 7)
        if len(fields) != 8:
            raise SystemExit(f"Invalid OCR TSV line {line_no}: expected 8 tab-separated fields")
        fig, width, height, x, y, w, h, text = fields
        if not text.strip():
            raise SystemExit(f"Invalid OCR TSV line {line_no}: empty label text")
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
                "line_no": line_no,
            }
        )
    if not rows:
        raise SystemExit("OCR TSV contains no label rows")
    return rows


def parse_color(value: Any, name: str):
    if not isinstance(value, list) or len(value) != 3:
        raise SystemExit(f"{name} must be an RGB array with three integers")
    if any(not isinstance(channel, int) or not 0 <= channel <= 255 for channel in value):
        raise SystemExit(f"{name} channels must be integers from 0 to 255")
    return tuple(value)


def validate_config(config, root):
    required = {"image_pattern", "output_pattern", "font", "translations"}
    missing = sorted(required - config.keys())
    if missing:
        raise SystemExit("Missing config keys: " + ", ".join(missing))
    if "{fig}" not in config["image_pattern"] or "{fig}" not in config["output_pattern"]:
        raise SystemExit("image_pattern and output_pattern must contain {fig}")
    if config["image_pattern"] == config["output_pattern"]:
        raise SystemExit("output_pattern must not overwrite the source image")
    font_path = Path(config["font"]).expanduser()
    if not font_path.is_absolute():
        font_path = root / font_path
    if not font_path.is_file():
        raise SystemExit(f"Font not found: {font_path}")
    config["font"] = str(font_path)
    if not isinstance(config["translations"], dict):
        raise SystemExit("translations must be a JSON object")
    for source, target in config["translations"].items():
        if not str(source).strip() or not isinstance(target, str) or not target.strip():
            raise SystemExit(f"Invalid translation entry: {source!r}")
    for group in config.get("groups", []):
        if not group.get("texts") or not group.get("lines"):
            raise SystemExit("Every group requires non-empty texts and lines arrays")
        if not all(isinstance(value, str) and value.strip() for value in group["texts"] + group["lines"]):
            raise SystemExit("Group texts and lines must contain non-empty strings")
    min_font_size = config.get("min_font_size", 18)
    max_font_size = config.get("max_font_size", 32)
    if not all(isinstance(value, int) and value > 0 for value in (min_font_size, max_font_size)):
        raise SystemExit("min_font_size and max_font_size must be positive integers")
    if min_font_size > max_font_size:
        raise SystemExit("min_font_size must not exceed max_font_size")
    config["label_color"] = parse_color(config.get("label_color", [246, 246, 246]), "label_color")
    config["orientation_color"] = parse_color(
        config.get("orientation_color", [228, 217, 58]), "orientation_color"
    )


def is_orientation(row):
    return row["text"] in ORIENTATION_TEXTS and row["x"] > row["width"] * 0.62 and row["y"] < 170


def font_for(font_path, h, min_size=18, max_size=32):
    size = round(h * 0.98)
    size = max(min_size, min(max_size, size))
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
    missing = sorted(
        {
            row["text"]
            for index, row in enumerate(rows)
            if index not in used and not is_orientation(row) and row["text"] not in translations
        }
    )
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


def draw_orientation(draw, rows, font_path, image_width, color):
    rows = [r for r in rows if is_orientation(r)]
    if not rows:
        return
    font = orientation_font_for(font_path, max(r["h"] for r in rows))
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
    if not image_path.is_file():
        raise SystemExit(f"Source image not found: {image_path}")
    if image_path.resolve() == out_path.resolve():
        raise SystemExit(f"Refusing to overwrite source image: {image_path}")
    original = Image.open(image_path).convert("RGB")
    declared_sizes = {(row["width"], row["height"]) for row in rows}
    if declared_sizes != {(original.width, original.height)}:
        raise SystemExit(
            f"OCR dimensions do not match {image_path.name}: "
            f"TSV={sorted(declared_sizes)}, image={(original.width, original.height)}"
        )
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
    if label_heights:
        font = font_for(
            config["font"],
            float(np.median(label_heights)),
            config.get("min_font_size", 18),
            config.get("max_font_size", 32),
        )
        for block in build_blocks(rows, config):
            draw_text_block(
                draw,
                block["box"],
                block["lines"],
                font,
                config["font"],
                config["label_color"],
                image.width,
                block_align(block["box"], image.width),
            )
    draw_orientation(draw, rows, config["font"], image.width, config["orientation_color"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path)
    with Image.open(out_path) as saved:
        if saved.size != original.size:
            out_path.unlink(missing_ok=True)
            raise SystemExit(f"Output dimensions changed unexpectedly: {out_path}")
    print(out_path)


def main():
    args = parse_args()
    load_image_dependencies()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    validate_config(config, args.root)
    rows = read_rows(args.ocr)
    for fig in sorted({r["fig"] for r in rows}, key=lambda x: (len(x), x)):
        render_one(args.root, fig, [r for r in rows if r["fig"] == fig], config)


if __name__ == "__main__":
    main()

---
name: medical-figure-zh-labeler
description: Translate English labels in medical/anatomical figure images into Chinese while preserving the original image, leader lines, label-to-structure correspondence, layout, dimensions, and figure style. Use for PNG/JPG/TIFF medical atlases, anatomy and cardiology diagrams, catheter ablation figures, or requests to output independent translated images. For cardiovascular figures, apply the user-designated 2025 National Committee terminology glossary as the highest-authority naming source before local figure-label conventions.
---

# Medical Figure Chinese Labeler

## Goal

Replace only the English label text in medical figure images with professional Chinese labels. Preserve the original anatomy/photo content, leader-line geometry, line endpoints, canvas size, and label correspondence.

## Core Workflow

1. **Preserve originals**
   - Never overwrite source `*-原图.png` files.
   - Output independent images, usually `Fig. x-中文版-翻译后.png`; optionally also write `Fig. x-中文版.png`.
   - Verify output dimensions match the source dimensions exactly.

2. **Read reference style**
   - If the folder contains a prior good result such as `Fig. 6.12-中文版-翻译后.png`, inspect it first.
   - Match its label style: white medical labels, yellow orientation marker, black background cleanup, concise Chinese, and same visual hierarchy as the original.

3. **Locate English labels**
   - Prefer OCR for coordinates, not for final terminology.
   - On macOS, use Vision OCR via Swift for accurate label boxes and save a TSV with: `fig width height x y w h text`.
   - Manually inspect OCR output for split labels, OCR mistakes, missing short labels, and punctuation.

4. **Translate medically**
   - For cardiovascular figures, first read the installed `translate-cardiovascular-literature-zh/references/cardiovascular-terminology.md` and search its `terminology/cnterm-2025/` A0 glossary.
   - Use local [references/terminology.md](references/terminology.md) only for figure-specific anatomy, eponyms, orientation markers, or concepts not covered by A0.
   - If A0 conflicts with a local example or an older project translation, A0 wins unless the user later gives a specific exception.
   - For eponyms or transliterated names, use the standard Chinese name plus English in parentheses when helpful: `巴赫曼束（Bachmann's bundle）`.
   - Do not keep English for ordinary anatomical terms.
   - Record each final label as `source English -> final Chinese -> authority` before rendering.

5. **Group label blocks**
   - Merge OCR fragments that are one logical label before drawing:
     - `Anterior pericardial` + `reflection` -> `前心包反折`
     - `Right atrioventricular` + `groove` -> `右房室沟`
     - `Anterior` + `mitral leaflet` -> `二尖瓣前瓣`
   - Keep short Chinese labels on one line whenever they fit.
   - Use two lines only for genuinely long explanatory labels or parenthetical terms.

6. **Remove English text**
   - Remove full English label boxes, not just visible glyph pixels, when following a finished-reference style.
   - Use inpainting for interior label boxes.
   - Use local dark-background fill near image edges to avoid white border artifacts.
   - Do not mask or redraw leader lines unless the user explicitly asks; keep line positions and lengths unchanged.

7. **Draw Chinese text**
   - Use a Chinese sans/hei font close to the original English style, such as `Heiti SC`, `PingFang SC`, or `Noto Sans CJK`.
   - Keep ordinary label font size visually close to the original English labels; compute a common size from OCR text height and use it consistently within a figure.
   - Keep the yellow orientation marker separate and visually close to the original marker.
   - Align labels by side:
     - Left-side labels: right-align to the original label box so they stay near their leader lines.
     - Right-side labels: left-align to the original label box.
     - Central/bottom labels: center only when that matches the original placement.

8. **Verify**
   - Generate a contact sheet for all outputs.
   - Inspect at least the densest figures at full resolution.
   - Check: no English residue, no missing labels, no wrong terminology, no unnecessary two-line short labels, no label overlap, no shifted leader lines, and identical dimensions.
   - Recheck every cardiovascular label against A0; do not let layout convenience silently change the official term.

## Reusable Script

Use `scripts/render_labels_from_ocr.py` as a starting point when a task has OCR TSV and a translation JSON. It implements the important mechanics from this workflow:

- full English box cleanup with hybrid inpaint/local background fill
- logical label grouping
- side-aware alignment
- consistent font sizing close to original text
- independent output files
- same-dimension verification

Patch the script per task instead of rewriting the whole rendering pipeline.

## OCR TSV Pattern

Use this TSV schema:

```text
fig<TAB>width<TAB>height<TAB>x<TAB>y<TAB>w<TAB>h<TAB>text
```

For a single image batch, `fig` can be a file stem instead of a number if the script is adjusted accordingly.

## Quality Bar

The final image should look like a native Chinese edition of the original atlas figure: the anatomy/photo and leader lines stay fixed, the Chinese labels read professionally, and the typography feels intentionally matched rather than pasted on.

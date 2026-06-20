---
name: medical-figure-zh-labeler
description: Translate English labels in medical, anatomical, cardiovascular, electrophysiology, and catheter-ablation figure images into authoritative Chinese while preserving source pixels outside text areas, canvas dimensions, leader-line geometry, label-to-structure correspondence, typography, and layout. Use for PNG, JPG, JPEG, or TIFF atlas figures; independent Chinese-edition image output; batch figure localization; or requests that cite Chinese medical textbook terminology, eponyms, transliterations, or the user-designated 2025 cardiovascular terminology standard.
---

# Medical Figure Chinese Labeler

Produce publication-ready Chinese figures by replacing text only. Treat anatomy, image content, leader lines, endpoints, symbols, scale bars, panel markers, and canvas geometry as locked.

## Non-Negotiable Constraints

- Never overwrite a source image. Write one independent output per source.
- Keep output width and height identical to the source.
- Do not move, shorten, extend, erase, or redraw leader lines.
- Preserve the one-to-one relationship between every label and its anatomical target.
- Translate every English label; do not omit short labels, abbreviations, orientation markers, or parenthetical text.
- Prefer one line for short Chinese labels. Use multiple lines only when required to avoid overlap or preserve an explanatory parenthesis.
- Stop and report ambiguity when the label target, source text, or authoritative term cannot be determined safely.

## Required Workflow

1. **Inventory and protect inputs**
   - Enumerate source images and expected outputs before editing.
   - Record source dimensions and hashes when the batch is publication-critical.
   - Inspect the user's approved reference result first, such as `Fig. 6.12-中文版-翻译后.png`.

2. **Extract and reconcile labels**
   - Use OCR to obtain candidate text and coordinates, never as final terminology authority.
   - Inspect each figure visually for OCR omissions, split lines, superscripts, punctuation, abbreviations, and labels crossing textured anatomy.
   - Merge OCR fragments into logical labels before translation.
   - Build a manifest with `figure | source English | final Chinese | authority | box/group | target check`.

3. **Resolve terminology**
   - Read [references/terminology.md](references/terminology.md) for the authority hierarchy and naming rules.
   - For cardiovascular labels, use the user-designated *Cardiovascular Terminology (2025)* source as the highest authority when available.
   - If `translate-cardiovascular-literature-zh/references/terminology/cnterm-2025/` is installed, search it before using local examples.
   - Use current Chinese national terminology, Chinese medical textbooks, consensus/guideline usage, then project consistency in that order.
   - For eponyms and transliterations, retain the English original only when the reference rules call for `中文标准名（English）`.
   - Never shorten an official term into a different concept merely to fit the label area.

4. **Plan typography and placement**
   - Match the approved reference's font family, weight, color, hierarchy, and spacing.
   - Use a Chinese sans/hei font close to the source, such as Heiti SC, PingFang SC, or Noto Sans CJK.
   - Estimate a common label size from OCR height and keep it consistent within each figure.
   - Right-align left-side labels, left-align right-side labels, and center only labels that were originally centered.
   - Keep orientation markers, panel letters, symbols, and color coding visually distinct.

5. **Render conservatively**
   - Remove the complete English glyph area with the smallest safe mask.
   - Use inpainting for textured interiors and sampled local fill near uniform edges.
   - Exclude leader-line pixels from cleanup masks. If a text box touches a line, use a custom mask rather than a full rectangle.
   - Draw Chinese inside the original label zone; adjust font size and line breaks before considering any positional change.
   - Use [scripts/render_labels_from_ocr.py](scripts/render_labels_from_ocr.py) when its rectangular-mask assumptions are safe. Patch it for irregular masks or figure-specific grouping.

6. **Verify every output**
   - Compare source and output dimensions programmatically.
   - Compare non-text regions and line endpoints at high zoom; any shifted line is a failure.
   - Check the manifest against the rendered figure label by label.
   - Confirm no English residue, missing labels, mistranslations, overlaps, clipping, unnecessary line breaks, or altered anatomy.
   - Generate a contact sheet for batch consistency, then inspect the densest figures at full resolution.
   - Re-run terminology review after layout changes so typography decisions never silently alter meaning.

## Script Inputs

Use an OCR TSV with exactly eight tab-separated fields:

```text
fig<TAB>width<TAB>height<TAB>x<TAB>y<TAB>w<TAB>h<TAB>text
```

Use a JSON config containing at least:

```json
{
  "image_pattern": "Fig. 6.{fig}-原图.png",
  "output_pattern": "Fig. 6.{fig}-中文版-翻译后.png",
  "font": "/System/Library/Fonts/STHeiti Medium.ttc",
  "translations": {"Aortic arch": "主动脉弓"},
  "groups": [{"texts": ["Anterior", "mitral leaflet"], "lines": ["二尖瓣前瓣"]}]
}
```

Optional keys include `min_font_size`, `max_font_size`, `label_color`, and `orientation_color`. The script rejects malformed rows, missing translations, missing files/fonts, source overwrite, OCR dimension mismatch, and changed output dimensions.

## Acceptance Standard

The result must look like a native Chinese edition of the same figure: authoritative terminology, complete label coverage, intentional typography, unchanged anatomy and leader lines, exact label correspondence, and identical dimensions. Automated checks support this judgment but never replace full-resolution medical and visual review.

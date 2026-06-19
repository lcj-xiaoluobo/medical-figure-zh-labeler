# Medical Figure Chinese Labeler

一个用于医学与解剖图谱中文本地化的 Codex Skill：将图中的英文标注翻译为规范中文，同时保持原始图像内容、画布尺寸、引线位置、标注对应关系、版式和字体风格。

## 适用场景

- 心血管、心脏电生理与导管消融图谱
- 解剖学教材和医学专著插图
- PNG、JPG、TIFF 等医学图片中的英文标注替换
- 需要批量输出独立中文版图片的出版流程

## 核心能力

- 以 OCR 获取坐标，但由人工医学术语规则决定最终译名
- 合并被 OCR 拆分的多行标签，短中文优先保持单行
- 使用中国医学教材常用术语；音译或人名术语可保留“中文名（英文）”
- 仅替换文字，不移动或缩短引线，不改变解剖结构和原图尺寸
- 根据标签左右位置自动对齐，尽量匹配原图字号与字体风格
- 支持批量渲染、同尺寸校验和成品总览检查

## 目录结构

```text
medical-figure-zh-labeler/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   └── terminology.md
└── scripts/
    └── render_labels_from_ocr.py
```

## 安装

```bash
git clone https://github.com/blueheartone-two-three/medical-figure-zh-labeler.git \
  ~/.codex/skills/medical-figure-zh-labeler
```

重新启动 Codex 或开启新会话后，即可使用 `medical-figure-zh-labeler` Skill。

## Python 依赖

```bash
pip install pillow numpy opencv-python
```

macOS 可优先使用系统中文黑体，例如：

```text
/System/Library/Fonts/STHeiti Medium.ttc
```

## 使用流程

1. 保留并备份原图，禁止覆盖 `*-原图.png`。
2. 参考同一项目中已完成的中文版图片，确定字号、颜色和布局风格。
3. OCR 提取英文标签及坐标，人工检查漏字、断行和错误识别。
4. 按中国医学教材规范翻译，并合并同一标签的 OCR 片段。
5. 清理英文文本区域，在原位置绘制中文，不修改任何标注引线。
6. 输出独立图片，并检查尺寸、术语、残留英文、遮挡和对应关系。

## 渲染脚本

```bash
python scripts/render_labels_from_ocr.py \
  --ocr ocr_labels.tsv \
  --config translations.json \
  --root /path/to/figures
```

OCR TSV 基本格式：

```text
fig<TAB>width<TAB>height<TAB>x<TAB>y<TAB>w<TAB>h<TAB>text
```

具体配置字段和运行方式可执行：

```bash
python scripts/render_labels_from_ocr.py --help
```

## 医学术语原则

- 普通解剖名词使用标准中文，不无故保留英文。
- 人名、音译名或临床常用英文名称可采用“中文标准名（英文原名）”。
- 标签应准确、简洁，并与原图指向结构一一对应。
- 心血管常用译名见 [`references/terminology.md`](references/terminology.md)。

## 成品质量标准

成品应像原版图谱的正式中文版：医学结构和引线保持不变，中文术语规范，无英文残留、漏标、错位、遮挡或不必要的断行，输出尺寸与原图完全一致。

## 使用说明

本仓库提供工作流程与辅助脚本。处理第三方医学图片时，请确认拥有相应的编辑、翻译与发布权限，并对最终医学术语进行专业复核。


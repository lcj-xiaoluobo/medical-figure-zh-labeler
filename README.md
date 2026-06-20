# Medical Figure Chinese Labeler

面向医学图谱出版与教学场景的 Codex Skill。它将图中英文标注翻译为权威、自然的中文，同时冻结解剖内容、画布尺寸、引线几何和标签对应关系。

## 核心特色

- **术语有裁决层级**：心血管标签优先采用用户指定的《心血管病学名词（2025）》；其后依次参考国家规范、权威教材、指南/共识和项目既有译法。
- **标签可追溯**：建议先建立“英文原文 -> 中文定稿 -> 权威来源 -> 坐标/分组 -> 指向核对”清单，再进入渲染。
- **几何冻结**：不移动、缩短、延长或重画引线，不改变端点和解剖结构。
- **版式本地化**：短中文尽量单行，统一字号、字重、颜色和左右对齐方式，保持原图视觉层级。
- **双重验收**：自动检查尺寸、输入、缺译和覆盖风险，再进行逐标签医学复核与全分辨率视觉检查。

## 适用场景

- 心血管解剖、心脏电生理、导管消融和影像学图谱
- 医学教材、专著、论文和继续教育材料中的图像本地化
- PNG、JPG、JPEG、TIFF 图像的单图或批量中文化
- 要求输出独立中文版图片且严格保持引线对应关系的任务

## 安装

```bash
git clone https://github.com/lcj-xiaoluobo/medical-figure-zh-labeler.git \
  ~/.codex/skills/medical-figure-zh-labeler
```

重新启动 Codex 或开启新会话后使用。Python 渲染脚本需要：

```bash
python -m pip install pillow numpy opencv-python
```

## 推荐流程

1. 枚举原图和预期输出，禁止覆盖 `*-原图.*`。
2. 检查用户认可的中文版参考图，确定字体、颜色、字号和布局基准。
3. OCR 提取文本与坐标，人工补齐漏标并合并被拆开的标签。
4. 按权威层级定稿术语，建立可追溯标签清单。
5. 在不触碰引线的前提下清除英文并于原位置绘制中文。
6. 自动核验尺寸和缺译，再逐图检查术语、残留、遮挡、断行及一一对应关系。
7. 批量生成总览图，并对标签最密集的图片进行全分辨率终审。

## 渲染脚本

```bash
python scripts/render_labels_from_ocr.py \
  --ocr ocr_labels.tsv \
  --config translations.json \
  --root /path/to/figures
```

OCR TSV 每行必须包含 8 个制表符分隔字段：

```text
fig<TAB>width<TAB>height<TAB>x<TAB>y<TAB>w<TAB>h<TAB>text
```

最小配置示例：

```json
{
  "image_pattern": "Fig. 6.{fig}-原图.png",
  "output_pattern": "Fig. 6.{fig}-中文版-翻译后.png",
  "font": "/System/Library/Fonts/STHeiti Medium.ttc",
  "translations": {"Aortic arch": "主动脉弓"},
  "groups": [{"texts": ["Anterior", "mitral leaflet"], "lines": ["二尖瓣前瓣"]}]
}
```

脚本会拒绝格式错误、缺少译文、字体或原图缺失、OCR 尺寸不符、覆盖原图和输出尺寸变化。矩形文字框与引线相交时，不应直接套用默认遮罩，应为该图定制不触线的掩膜。

## 仓库结构

```text
medical-figure-zh-labeler/
├── SKILL.md
├── agents/openai.yaml
├── references/terminology.md
└── scripts/render_labels_from_ocr.py
```

处理第三方医学图片前，请确认拥有相应的编辑、翻译和发布权限。自动化不能替代医学专业人员对最终术语和指向关系的复核。

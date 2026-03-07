# Mermaid to PptxGenJS Mapping Guide

This reference provides a systematic approach for converting Mermaid graphs into PptxGenJS scripts.

## 1. Syntax Mapping

### Node Shapes

Map Mermaid brackets to PptxGenJS shapes:

| Mermaid Syntax | Shape           | PptxGenJS Equivalent                                           |
| :------------- | :-------------- | :------------------------------------------------------------- |
| `id[Text]`     | Rectangle       | `pptx.ShapeType.rect`                                          |
| `id(Text)`     | Rounded Rect    | `pptx.ShapeType.roundRect`                                     |
| `id{Text}`     | Rhombus/Diamond | `pptx.ShapeType.diamond` or `pptx.ShapeType.flowChartDecision` |
| `id((Text))`   | Circle          | `pptx.ShapeType.oval`                                          |
| `id[[Text]]`   | Subroutine      | `pptx.ShapeType.flowChartPredefinedProcess`                    |
| `id[(Text)]`   | Database        | `pptx.ShapeType.flowChartMagneticDisk`                         |
| `id[/Text/]`   | Parallelogram   | `pptx.ShapeType.flowChartInputOutput`                          |

### Link Styles

Map arrow types to line properties:

| Mermaid Syntax    | Style        | PptxGenJS Properties                                     |
| :---------------- | :----------- | :------------------------------------------------------- |
| `A --> B`         | Solid Arrow  | `{ line: { dashType: 'solid', endArrowType: 'arrow' } }` |
| `A --- B`         | Solid Line   | `{ line: { dashType: 'solid', endArrowType: 'none' } }`  |
| `A -.-> B`        | Dotted Arrow | `{ line: { dashType: 'dash', endArrowType: 'arrow' } }`  |
| `A ==> B`         | Thick Arrow  | `{ line: { width: 3, endArrowType: 'arrow' } }`          |
| `A -- Text --> B` | Label        | Add text box at midpoint of line                         |

### Subgraphs

Map `subgraph` to visual containers:

- **Visual**: A large rectangle with `fill` (usually light/transparent) and `line` (border).
- **Label**: A text box inside the container, usually at top/bottom.
- **Zoning**: Use subgraphs to define "Zones" (columns or rows) in your grid layout.

## 2. Structured Script Pattern

To avoid errors like "treating ID as label" or "missing connections", use this **Data-Driven Pattern**:

### Step 1: Define Data Structures (Mental or Code)

Separate the _Logic_ (Mermaid) from the _rendering_ (PptxGenJS).

```javascript
// 1. Nodes (ID is Key, Label is Value)
const nodes = {
  R1: {
    label: "传感器检测环境\n(温度/胶水批次)",
    shape: pptx.ShapeType.rect,
    zone: "Real_World",
  },
  R2: { label: "获取物理特征", shape: pptx.ShapeType.rect, zone: "Real_World" },
  M2: {
    label: "Modulus\n物理监控模型",
    shape: pptx.ShapeType.diamond,
    zone: "Modulus_Brain",
  },
};

// 2. Links (Source ID -> Target ID)
const links = [
  { from: "R1", to: "R2" },
  { from: "R2", to: "M2", label: "同步当前参数" },
  { from: "M2", to: "M3", type: "dotted", label: "残差对比" },
];

// 3. Subgraphs (Zones)
const zones = {
  Real_World: { label: "现实世界：感应与回传", color: "E1E1E1" },
  Modulus_Brain: { label: "物理脑：设定宪法与验算", color: "D0E0E3" },
};
```

### Step 2: Define Grid System

Don't guess coordinates. Define a grid.

```javascript
const GRID = {
  startX: 0.5,
  startY: 1.0,
  colW: 2.5,
  rowH: 1.5,
  cols: {
    Real_World: 0,
    Modulus_Brain: 1,
    Simulation_Loop: 2,
  },
};
```

### Step 3: Render Loop

1.  **Draw Zones first** (so they are behind nodes).
2.  **Draw Nodes** (calculate X/Y based on Grid + Offset).
3.  **Draw Links** (lookup source/target coordinates).

## 3. Handling "M2" ID vs Label

**Common Mistake**: `addText("M2 Modulus...")`
**Correction**: Use the `label` property from your data structure, NOT the ID.

```javascript
// WRONG
slide.addText("M2 Modulus...", { ... });

// CORRECT
const node = nodes['M2']; // { label: "Modulus...", ... }
slide.addText(node.label, { ... });
```

## 4. Example Implementation

```javascript
// ... setup pptx ...

// DATA
const nodes = [
  { id: "M2", text: "Modulus Model", type: "diamond", x: 2, y: 2 },
  { id: "S1", text: "Isaac Sim", type: "rect", x: 4, y: 2 },
];

const links = [{ from: "M2", to: "S1", label: "Calibration" }];

// RENDER NODES & STORE COORDS
const renderedNodes = {}; // Map ID -> {x, y, w, h}

nodes.forEach((node) => {
  // Draw shape
  slide.addText(node.text, {
    shape:
      node.type === "diamond" ? pptx.ShapeType.diamond : pptx.ShapeType.rect,
    x: node.x,
    y: node.y,
    w: 1.5,
    h: 1.0,
    align: "center",
  });
  // Store actual position for links
  renderedNodes[node.id] = { x: node.x, y: node.y, w: 1.5, h: 1.0 };
});

// RENDER LINKS
links.forEach((link) => {
  const start = renderedNodes[link.from];
  const end = renderedNodes[link.to];

  // Draw line from center to center (simplified)
  // Or use edge-to-edge logic
  slide.addShape(pptx.ShapeType.line, {
    x: start.x + start.w,
    y: start.y + start.h / 2,
    w: end.x - (start.x + start.w),
    h: 0,
    line: { endArrowType: "arrow" },
  });
});
```

## 5. 最佳实践与常见坑

- subgraph 用浅色背景容器+虚线边框+顶部标签，便于分区识别
- 节点尽量居中于分区内部，避免贴紧边界线
- 跨分区连线使用折线（水平→垂直→水平），并根据 Mermaid 用实线/虚线
- 箭头方向统一：左→右用 `endArrowType: 'arrow'`；右→左改用 `beginArrowType: 'arrow'`
- 反馈回路标签用竖排文本 `vert: 'eaVert'`，避免旋转导致字序横向
- 拐点位置避开分区边界线，优先在源或目标分区内设置 turnX
- 垂直段建议自上而下绘制（保证 `h` 为正），避免负值触发修复提示
- 针对菱形（决策）节点，连线出口通常从左右两侧中心，入口从目标节点的进入侧
- 品牌配色与形状保持一致（如 real=灰、modulus=绿、sim=青、ai=紫），提升整体一致性

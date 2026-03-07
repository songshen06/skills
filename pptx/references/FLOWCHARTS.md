# Creating Flowcharts with Native Shapes

When you need to create editable flowcharts or diagrams in PowerPoint, prefer using the native PptxGenJS Shape API over HTML-to-Image conversion. This ensures:

1.  **Editability**: Users can move shapes and resize them in PowerPoint.
2.  **Vector Quality**: Shapes are sharp at any zoom level.
3.  **Native Look**: Uses PowerPoint's built-in shape library.

## Core API: `addShape`

Use `slide.addShape(shapeType, options)` to add shapes and lines.

```javascript
// Example: Add a rectangle
slide.addShape(pptx.ShapeType.rect, {
  x: 1.0,
  y: 1.0,
  w: 2.0,
  h: 1.0,
  fill: { color: "0078D7" },
  line: { color: "000000" },
});

// Example: Add text inside shape
slide.addText("Process Step", {
  shape: pptx.ShapeType.rect,
  x: 1.0,
  y: 1.0,
  w: 2.0,
  h: 1.0,
  fill: { color: "FFFFFF" },
  color: "000000",
  align: "center",
});
```

## Common Flowchart Shapes

| Mermaid Node     | PptxGenJS ShapeType                                        |
| :--------------- | :--------------------------------------------------------- |
| `[Process]`      | `pptx.ShapeType.rect` or `pptx.ShapeType.flowChartProcess` |
| `(Round)`        | `pptx.ShapeType.roundRect`                                 |
| `{Decision}`     | `pptx.ShapeType.flowChartDecision`                         |
| `[[Subroutine]]` | `pptx.ShapeType.flowChartPredefinedProcess`                |
| `[(Database)]`   | `pptx.ShapeType.flowChartMagneticDisk`                     |
| `[/Input/]`      | `pptx.ShapeType.flowChartInputOutput`                      |
| `((Circle))`     | `pptx.ShapeType.oval`                                      |

## Connectors (Lines)

PowerPoint connectors are essentially lines with arrowheads. While PptxGenJS doesn't currently support "anchoring" lines to shapes (where they move together automatically), you can draw lines between shape coordinates.

### Drawing an Arrow

Use `pptx.ShapeType.line` with `line` properties.

```javascript
// Draw an arrow from (3.0, 1.5) to (4.0, 1.5)
slide.addShape(pptx.ShapeType.line, {
  x: 3.0,
  y: 1.5,
  w: 1.0,
  h: 0.0, // w is horizontal length, h is vertical
  line: {
    color: "000000",
    width: 2,
    endArrowType: "arrow", // 'triangle', 'stealth', 'diamond', 'oval', 'arrow'
  },
});
```

### Connector Routing

You must calculate the start and end points manually based on your shapes' positions.

- **Right-to-Left**: `x` = startX, `y` = startY, `w` = length, `h` = 0
- **Top-to-Bottom**: `x` = startX, `y` = startY, `w` = 0, `h` = length
- **Elbow Connectors**: You may need to draw two lines (one horizontal, one vertical) to create an elbow.

## Example: Simple Flowchart Script

```javascript
const pptxgen = require("pptxgenjs");
const pptx = new pptxgen();
const slide = pptx.addSlide();

// 1. Define Layout Constants
const START_X = 1.0;
const START_Y = 1.0;
const BOX_W = 2.0;
const BOX_H = 1.0;
const GAP = 1.0;

// 2. Add Process Box A
slide.addText("Start Process", {
  shape: pptx.ShapeType.roundRect,
  x: START_X,
  y: START_Y,
  w: BOX_W,
  h: BOX_H,
  fill: { color: "0078D7" },
  color: "FFFFFF",
  align: "center",
});

// 3. Add Process Box B (Next to A)
const boxBx = START_X + BOX_W + GAP;
slide.addText("Next Step", {
  shape: pptx.ShapeType.rect,
  x: boxBx,
  y: START_Y,
  w: BOX_W,
  h: BOX_H,
  fill: { color: "FFC000" },
  color: "000000",
  align: "center",
});

// 4. Add Connector Arrow (A -> B)
slide.addShape(pptx.ShapeType.line, {
  x: START_X + BOX_W, // Right edge of A
  y: START_Y + BOX_H / 2, // Middle of A
  w: GAP,
  h: 0,
  line: { color: "666666", width: 2, endArrowType: "arrow" },
});

pptx.writeFile({ fileName: "Flowchart.pptx" });
```

## Best Practices

1.  **Calculate Coordinates First**: Define your grid or layout variables (width, height, gap) at the top of your script.
2.  **Center Text**: Always use `align: 'center'` for text inside flowchart shapes.
3.  **Use Theme Colors**: Refer to `pptx.SchemeColor` if possible for consistent branding.
4.  **Group Shapes**: PptxGenJS supports grouping, which can be useful for complex nodes, but single shapes with text are usually sufficient.

##  Advanced Tips
- Cross-zone connectors: prefer elbow routing (horizontal→vertical→horizontal) instead of diagonals
- Dotted vs solid lines: mirror Mermaid semantics using `dashType: 'dash' | 'solid'`
- Arrow direction: left→right use `endArrowType: 'arrow'`, right→left use `beginArrowType: 'arrow'`
- Vertical labels: use `vert: 'eaVert'` for upright stacked text; avoid `rotate` for East Asian scripts
- Boundary avoidance: place elbow turn inside source/target zone, not on zone borders
- Geometry: keep `w`/`h` non-negative; draw vertical segments top→bottom to avoid negative heights

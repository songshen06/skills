const pptxgen = require('pptxgenjs')
const pptx = new pptxgen()
pptx.layout = 'LAYOUT_WIDE'
const slide = pptx.addSlide()
function zone(slide, x, y, w, h, bg, line, label, color) {
  slide.addShape(pptx.ShapeType.rect, { x, y, w, h, fill: { color: bg }, line: { color: line, width: 1, dashType: 'dash' } })
  slide.addText(label, { x, y: y + 0.1, w, h: 0.3, align: 'center', fontSize: 10, color, bold: true })
}
function node(slide, text, shape, x, y, w, h, fill, color) {
  slide.addText(text, { shape, x, y, w, h, fill: { color: fill }, color, align: 'center', fontSize: 10 })
  return { x, y, w, h, cx: x + w / 2, cy: y + h / 2, left: x, right: x + w, top: y, bottom: y + h }
}
function elbow(slide, sx, sy, ex, ey, color, dash, arrowEnd) {
  const mx = sx + (ex - sx) / 2
  slide.addShape(pptx.ShapeType.line, { x: sx, y: sy, w: mx - sx, h: 0, line: { color, width: 1.5, dashType: dash } })
  slide.addShape(pptx.ShapeType.line, { x: mx, y: Math.min(sy, ey), w: 0, h: Math.abs(ey - sy), line: { color, width: 1.5, dashType: dash } })
  slide.addShape(pptx.ShapeType.line, { x: mx, y: ey, w: ex - mx, h: 0, line: { color, width: 1.5, dashType: dash, endArrowType: arrowEnd ? 'arrow' : 'none' } })
}
module.exports = { pptx, slide, zone, node, elbow }

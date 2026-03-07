
import copy
import json
import os
import sys
from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN
from pptx.enum.dml import MSO_LINE_DASH_STYLE

# --- Constants ---
# NVIDIA Colors
COLOR_GREEN = RGBColor(118, 185, 0) # 76B900
COLOR_DARK_GRAY = RGBColor(51, 51, 51) # 333333
COLOR_LIGHT_GRAY = RGBColor(240, 240, 240) # F0F0F0
COLOR_WHITE = RGBColor(255, 255, 255)
COLOR_LINE = RGBColor(94, 94, 94) # 5E5E5E
COLOR_TEXT_MAIN = RGBColor(0, 0, 0)

# LIVRPS Colors (Approx)
COLOR_L = RGBColor(255, 153, 255) # f9f
COLOR_I = RGBColor(187, 187, 255) # bbf
COLOR_V = RGBColor(221, 255, 221) # dfd
COLOR_R = RGBColor(255, 221, 221) # fdd
COLOR_P = RGBColor(221, 255, 255) # dff
COLOR_S = RGBColor(255, 255, 221) # ffd

def duplicate_slide(pres, index):
    """Duplicate a slide in the presentation."""
    source = pres.slides[index]
    new_slide = pres.slides.add_slide(source.slide_layout)
    
    # Remove existing placeholders from new slide to avoid duplication conflicts
    for shape in new_slide.placeholders:
        pass

    # Copy other shapes (like logos, background elements if they are shapes)
    for shape in source.shapes:
        if not shape.is_placeholder:
            el = shape.element
            new_el = copy.deepcopy(el)
            new_slide.shapes._spTree.insert_element_before(new_el, "p:extLst")
    
    return new_slide

def replace_text(slide, replacements):
    """Replace text in a slide based on a dictionary of placeholder_type -> text."""
    # First pass: Identify placeholders
    placeholders = {}
    for shape in slide.placeholders:
        if shape.is_placeholder:
            ph_type = shape.placeholder_format.type
            # 1=Title, 3=Center Title, 4=Subtitle, 7=Object, 2=Body
            placeholders[ph_type] = shape

    # Identify if we have both Body(2) and Object(7)
    has_object = 7 in placeholders
    has_body = 2 in placeholders

    # Keep track of used keys to prevent duplication
    used_keys = set()

    for shape in slide.placeholders:
        if shape.is_placeholder:
            ph_type = shape.placeholder_format.type
            key = None
            
            # Map types to keys
            if ph_type == 1: key = "TITLE"
            elif ph_type == 3: key = "CENTER_TITLE"
            elif ph_type == 4: key = "SUBTITLE"
            elif ph_type == 7: key = "BODY" # Object
            elif ph_type == 2: 
                # If we have both, Type 2 is usually subtitle or secondary body
                # But if we map both to BODY, we get duplicates.
                # Heuristic: If we have Object(7), map Body(2) to SUBTITLE
                if has_object:
                    key = "SUBTITLE"
                else:
                    key = "BODY"
            
            # If we found a key and have replacement text
            if key and key in replacements:
                # Check if we already filled this key to avoid duplicates
                # UNLESS it's BODY and we have a list that we want to distribute? 
                # For now, let's assume one placeholder per key.
                if key in used_keys:
                    # Duplicate placeholder for same key. Clear it to avoid repetition.
                    if shape.has_text_frame:
                        shape.text_frame.clear()
                    continue

                text = replacements[key]
                used_keys.add(key)
                
                if not shape.has_text_frame: continue
                
                text_frame = shape.text_frame
                text_frame.clear()
                
                if isinstance(text, list):
                    for i, line in enumerate(text):
                        p = text_frame.add_paragraph()
                        p.text = line
                        p.level = 0
                        p.font.name = "NVIDIA Sans"
                else:
                    p = text_frame.paragraphs[0]
                    p.text = text
                    p.font.name = "NVIDIA Sans"
            else:
                # No replacement for this placeholder, clear it (optional, but cleaner)
                if shape.has_text_frame:
                    shape.text_frame.clear()

def add_zone(slide, label, x, y, w, h):
    """Add a dashed zone with label."""
    # Use Inches for positioning
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(245, 245, 245) # Very light gray
    shape.line.color.rgb = RGBColor(200, 200, 200)
    shape.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    
    # Label - position slightly inside or on top
    # Adjust textbox height to be small
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(0.4))
    p = tb.text_frame.paragraphs[0]
    p.text = label
    p.alignment = PP_ALIGN.CENTER
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = RGBColor(100, 100, 100)

def add_node(slide, text, x, y, w, h, fill_color, shape_type=MSO_SHAPE.RECTANGLE):
    """Add a node shape."""
    shape = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    # Handle hex strings or RGBColor objects
    if isinstance(fill_color, str):
        # Remove # if present
        hex_color = fill_color.replace('#', '')
        shape.fill.fore_color.rgb = RGBColor.from_string(hex_color)
    else:
        shape.fill.fore_color.rgb = fill_color
        
    shape.line.color.rgb = COLOR_LINE
    shape.line.width = Pt(1)
    
    tf = shape.text_frame
    tf.text = text
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.font.size = Pt(10)
    p.font.color.rgb = COLOR_TEXT_MAIN
    p.font.name = "Arial"
    
    return shape

def add_link(slide, shape1, shape2, link_type='straight'):
    """Add a connector between shapes."""
    connector = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, 
                                           Inches(0), Inches(0), Inches(0), Inches(0))
    
    connector.line.color.rgb = COLOR_LINE
    connector.line.width = Pt(1.5)
    
    if link_type == 'vertical':
        connector.begin_connect(shape1, 2) # Bottom
        connector.end_connect(shape2, 0)   # Top
    else: # horizontal
        connector.begin_connect(shape1, 1) # Right
        connector.end_connect(shape2, 3)   # Left
        
    return connector

def draw_composition_diagram(slide, data):
    # Shifted down to avoid header overlap (Y + 1.0 inch)
    # Zones
    base_y = 3.0 # Started at 2.0 previously
    
    add_zone(slide, "USD Layers", 0.5, base_y, 3.0, 3.5)
    add_zone(slide, "Composition Engine", 4.0, base_y, 4.0, 3.5)
    add_zone(slide, "USD Stage", 8.5, base_y, 3.0, 3.5)
    
    # Nodes relative to base_y
    # Previous: L1 at 2.5 (base_y + 0.5)
    l1 = add_node(slide, "L1\nLayer A (Root)", 1.0, base_y + 0.5, 2.0, 0.6, COLOR_WHITE)
    l2 = add_node(slide, "L2\nLayer B (Ref)", 1.0, base_y + 1.5, 2.0, 0.6, COLOR_WHITE)
    l3 = add_node(slide, "L3\nLayer C (Sub)", 1.0, base_y + 2.5, 2.0, 0.6, COLOR_WHITE)
    
    ca = add_node(slide, "Composition\nArcs", 4.5, base_y + 1.0, 1.4, 1.5, COLOR_WHITE)
    vr = add_node(slide, "Value\nResolution", 6.3, base_y + 1.0, 1.4, 1.5, COLOR_WHITE)
    
    s = add_node(slide, "Final Stage", 9.0, base_y + 0.5, 2.0, 0.6, COLOR_WHITE)
    p = add_node(slide, "Prims &\nProperties", 9.0, base_y + 2.0, 2.0, 0.6, COLOR_WHITE)
    
    # Links
    add_link(slide, l1, ca, 'horizontal')
    add_link(slide, l2, ca, 'horizontal')
    add_link(slide, l3, ca, 'horizontal')
    add_link(slide, ca, vr, 'horizontal')
    add_link(slide, vr, s, 'horizontal')
    add_link(slide, s, p, 'vertical')

def draw_livrps_diagram(slide, data):
    # Nodes centered around X=6.6
    cx = 6.6
    w = 3.0
    h = 0.6
    # Shift start_y down from 1.5 to 2.5 to avoid header
    start_y = 2.5
    gap = 0.4
    
    nodes_data = [
        ("L", "**L**ocal (本地意见)", COLOR_L),
        ("I", "**I**nherits (继承)", COLOR_I),
        ("V", "**V**ariantSets (变体集)", COLOR_V),
        ("R", "**R**eferences (引用)", COLOR_R),
        ("P", "**P**ayloads (负载)", COLOR_P),
        ("S", "**S**pecializes (特化)", COLOR_S)
    ]
    
    shapes = []
    for i, (code, text, color) in enumerate(nodes_data):
        y = start_y + i * (h + gap)
        # Remove markdown ** for pptx
        clean_text = text.replace("**", "")
        shape = add_node(slide, clean_text, cx - w/2, y, w, h, color)
        shapes.append(shape)
        
    # Links
    for i in range(len(shapes)-1):
        add_link(slide, shapes[i], shapes[i+1], 'vertical')
        
    # Annotation arrow
    arrow_h = (len(nodes_data) * (h + gap)) - gap
    arrow = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(3.0), Inches(start_y), Inches(0.5), Inches(arrow_h))
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = RGBColor(240, 240, 240) # COLOR_LIGHT_GRAY
    arrow.line.color.rgb = COLOR_LINE
    
    tb1 = slide.shapes.add_textbox(Inches(1.5), Inches(start_y), Inches(1.5), Inches(0.5))
    tb1.text_frame.text = "Strongest (1)"
    tb1.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT
    
    tb2 = slide.shapes.add_textbox(Inches(1.5), Inches(start_y + arrow_h - 0.5), Inches(1.5), Inches(0.5))
    tb2.text_frame.text = "Weakest (6)"
    tb2.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT

def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_from_template.py <content_json> <output_pptx> [template_name]")
        sys.exit(1)
        
    content_file = sys.argv[1]
    output_path = sys.argv[2]
    template_name = sys.argv[3] if len(sys.argv) > 3 else "nvidia"
    
    # Resolve template path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Assuming templates are in ../templates relative to scripts/
    template_path = os.path.join(script_dir, "..", "templates", f"{template_name}.pptx")
    
    if not os.path.exists(template_path):
        print(f"Template not found: {template_path}")
        sys.exit(1)
        
    # Load content
    with open(content_file, 'r', encoding='utf-8') as f:
        slides_config = json.load(f)
        
    prs = Presentation(template_path)
    new_slides = []
    
    print(f"Generating presentation using template: {template_name}")
    
    for item in slides_config:
        idx = item.get("index", 0) # Default to 0 if not specified
        # Allow 'layout_index' alias
        if "layout_index" in item:
            idx = item["layout_index"]
            
        slide = duplicate_slide(prs, idx)
        new_slides.append(slide)
        
        if "data" in item:
            replace_text(slide, item["data"])
        
        # Handle specialized types if needed
        type_ = item.get("type", "")
        if type_ == "diagram_composition":
            draw_composition_diagram(slide, item.get("data", {}))
        elif type_ == "diagram_livrps":
            draw_livrps_diagram(slide, item.get("data", {}))
            
    # Remove original template slides
    num_old_slides = len(prs.slides) - len(new_slides)
    for _ in range(num_old_slides):
        rId = prs.slides._sldIdLst[0].rId
        prs.part.drop_rel(rId)
        del prs.slides._sldIdLst[0]
        
    prs.save(output_path)
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    main()

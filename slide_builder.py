import os
import uuid
import requests
from io import BytesIO
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from PIL import Image, ImageDraw

UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

# Simple themes that work
THEMES = {
    "classic": {"bg": RGBColor(255,255,255), "accent": RGBColor(31,57,100), "text": RGBColor(0,0,0), "heading": RGBColor(31,57,100)},
    "dark": {"bg": RGBColor(26,26,46), "accent": RGBColor(233,76,125), "text": RGBColor(255,255,255), "heading": RGBColor(233,76,125)},
    "corporate": {"bg": RGBColor(244,246,249), "accent": RGBColor(0,78,146), "text": RGBColor(51,51,51), "heading": RGBColor(0,78,146)},
}

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

def fetch_image(keyword):
    try:
        if not UNSPLASH_KEY:
            return None
        url = f"https://api.unsplash.com/photos/random?query={keyword}&orientation=landscape&client_id={UNSPLASH_KEY}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            img_url = resp.json()["urls"]["regular"]
            img_resp = requests.get(img_url, timeout=10)
            return BytesIO(img_resp.content)
    except:
        pass
    return None

def add_text(slide, text, left, top, width, height, size, color, bold=False, center=False):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    if center:
        p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    run.font.size = size
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.name = "Calibri"

def add_rounded_rect(slide, left, top, width, height, color, radius=0.2):
    from pptx.oxml.ns import qn
    from lxml import etree
    shape = slide.shapes.add_shape(1, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    if radius > 0:
        sp = shape._element
        spPr = sp.find(qn("p:spPr"))
        prstGeom = spPr.find(qn("a:prstGeom"))
        if prstGeom is not None:
            spPr.remove(prstGeom)
        prstGeom = etree.SubElement(spPr, qn("a:prstGeom"))
        prstGeom.set("prst", "roundRect")
        avLst = etree.SubElement(prstGeom, qn("a:avLst"))
        gd = etree.SubElement(avLst, qn("a:gd"))
        gd.set("name", "adj")
        gd.set("fmla", f"val {int(radius * 100000)}")

def build_title_slide(prs, title, theme):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    img = fetch_image("abstract")
    if img:
        slide.shapes.add_picture(img, 0, 0, SLIDE_W, SLIDE_H)
    add_rounded_rect(slide, 0, Inches(5), SLIDE_W, Inches(2.5), theme["accent"], 0)
    add_text(slide, title, Inches(0.5), Inches(2), Inches(12.33), Inches(2), Pt(48), RGBColor(255,255,255), bold=True, center=True)
    add_text(slide, "SlideBot", Inches(0.5), Inches(6.2), Inches(12.33), Inches(0.5), Pt(16), RGBColor(255,255,255), center=True)

def build_content_slide(prs, heading, bullets, theme, keyword, layout_num):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Simple alternating layouts
    if layout_num % 2 == 0:
        # Layout A: Image on left
        img = fetch_image(keyword)
        if img:
            slide.shapes.add_picture(img, Inches(0.3), Inches(0.3), Inches(5), Inches(6.9))
        add_text(slide, heading, Inches(5.8), Inches(0.5), Inches(7), Inches(1), Pt(32), theme["heading"], bold=True)
        y = Inches(1.8)
        for b in bullets[:5]:
            add_text(slide, f"• {b}", Inches(5.8), y, Inches(7), Inches(0.6), Pt(16), theme["text"], wrap=True)
            y += Inches(0.7)
    else:
        # Layout B: Image on right
        img = fetch_image(keyword)
        if img:
            slide.shapes.add_picture(img, Inches(8), Inches(0.5), Inches(5), Inches(6.5))
        add_text(slide, heading, Inches(0.5), Inches(0.5), Inches(7), Inches(1), Pt(32), theme["heading"], bold=True)
        y = Inches(1.8)
        for b in bullets[:5]:
            add_text(slide, f"• {b}", Inches(0.5), y, Inches(7), Inches(0.6), Pt(16), theme["text"], wrap=True)
            y += Inches(0.7)

def build_thankyou_slide(prs, theme):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_text(slide, "Thank You!", Inches(0.5), Inches(3), Inches(12.33), Inches(1.5), Pt(54), theme["heading"], bold=True, center=True)
    add_text(slide, "Created with SlideBot", Inches(0.5), Inches(5), Inches(12.33), Inches(0.5), Pt(18), theme["text"], center=True)

def build_presentation(slide_data, theme_name="classic", is_premium=False):
    theme = THEMES.get(theme_name, THEMES["classic"])
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    
    slides = slide_data.get("slides", [])
    title = slide_data.get("title", "Presentation")
    
    build_title_slide(prs, title, theme)
    
    for i, slide in enumerate(slides):
        heading = slide.get("heading", f"Slide {i+1}")
        bullets = slide.get("bullets", [])
        keyword = slide.get("image_keyword", "business")
        build_content_slide(prs, heading, bullets, theme, keyword, i)
    
    build_thankyou_slide(prs, theme)
    
    filename = f"slidebot_{uuid.uuid4().hex[:8]}.pptx"
    os.makedirs("outputs", exist_ok=True)
    filepath = os.path.join("outputs", filename)
    prs.save(filepath)
    return filepath

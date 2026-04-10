import os
import uuid
import requests
from io import BytesIO

from dotenv import load_dotenv
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

from PIL import Image, ImageDraw

load_dotenv()

UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

# ─── THEMES — Warm, premium, human-centric colors ────────────────
THEMES = {
    "classic": {
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
        "title_color": RGBColor(0x1F, 0x39, 0x64),
        "heading_color": RGBColor(0x1F, 0x39, 0x64),
        "bullet_color": RGBColor(0x2C, 0x3E, 0x50),
        "accent": RGBColor(0x34, 0x98, 0xDB),
        "accent2": RGBColor(0x2E, 0xCC, 0x71),
        "card_bg": RGBColor(0xF8, 0xF9, 0xFA),
        "light_accent": RGBColor(0xEB, 0xF5, 0xFB),
        "soft_accent": RGBColor(0xBD, 0xC3, 0xC7),
    },
    "dark": {
        "bg": RGBColor(0x1A, 0x1A, 0x2E),
        "title_color": RGBColor(0xE9, 0x4C, 0x7D),
        "heading_color": RGBColor(0xE9, 0x4C, 0x7D),
        "bullet_color": RGBColor(0xE0, 0xE0, 0xE0),
        "accent": RGBColor(0xE9, 0x4C, 0x7D),
        "accent2": RGBColor(0x9B, 0x59, 0xB6),
        "card_bg": RGBColor(0x2A, 0x2A, 0x3E),
        "light_accent": RGBColor(0x34, 0x34, 0x4E),
        "soft_accent": RGBColor(0x58, 0x58, 0x6E),
    },
    "corporate": {
        "bg": RGBColor(0xF4, 0xF6, 0xF9),
        "title_color": RGBColor(0x00, 0x4E, 0x92),
        "heading_color": RGBColor(0x00, 0x4E, 0x92),
        "bullet_color": RGBColor(0x33, 0x33, 0x33),
        "accent": RGBColor(0x00, 0x4E, 0x92),
        "accent2": RGBColor(0x00, 0x8B, 0xD2),
        "card_bg": RGBColor(0xE8, 0xF0, 0xFE),
        "light_accent": RGBColor(0xE8, 0xF0, 0xFE),
        "soft_accent": RGBColor(0x66, 0xAA, 0xDD),
    },
    "startup": {
        "bg": RGBColor(0xFF, 0xFA, 0xF5),
        "title_color": RGBColor(0xFF, 0x6B, 0x35),
        "heading_color": RGBColor(0xFF, 0x6B, 0x35),
        "bullet_color": RGBColor(0x4A, 0x4A, 0x4A),
        "accent": RGBColor(0xFF, 0x6B, 0x35),
        "accent2": RGBColor(0x4E, 0xC5, 0xC3),
        "card_bg": RGBColor(0xFF, 0xF5, 0xEE),
        "light_accent": RGBColor(0xFF, 0xE8, 0xDD),
        "soft_accent": RGBColor(0xFF, 0xAA, 0x7A),
    },
    "academic": {
        "bg": RGBColor(0xFA, 0xFB, 0xFC),
        "title_color": RGBColor(0x2C, 0x3E, 0x50),
        "heading_color": RGBColor(0x2C, 0x3E, 0x50),
        "bullet_color": RGBColor(0x5D, 0x6D, 0x7E),
        "accent": RGBColor(0x8E, 0x44, 0xAD),
        "accent2": RGBColor(0x34, 0x98, 0xDB),
        "card_bg": RGBColor(0xF0, 0xF4, 0xF8),
        "light_accent": RGBColor(0xE8, 0xEE, 0xF4),
        "soft_accent": RGBColor(0xB0, 0xC4, 0xDE),
    },
    "minimal": {
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
        "title_color": RGBColor(0x2C, 0x3E, 0x50),
        "heading_color": RGBColor(0x2C, 0x3E, 0x50),
        "bullet_color": RGBColor(0x5D, 0x6D, 0x7E),
        "accent": RGBColor(0x7F, 0x8C, 0x8D),
        "accent2": RGBColor(0xBD, 0xC3, 0xC7),
        "card_bg": RGBColor(0xF4, 0xF6, 0xF7),
        "light_accent": RGBColor(0xEC, 0xF0, 0xF1),
        "soft_accent": RGBColor(0xD5, 0xDB, 0xDB),
    },
}

FREE_THEMES = ["classic", "dark"]
PREMIUM_THEMES = ["corporate", "startup", "academic", "minimal"]

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)


# ─── UNSPLASH IMAGE FETCH ────────────────────────────────────────
def fetch_unsplash_image(keyword: str):
    try:
        if not UNSPLASH_KEY:
            print("❌ No Unsplash key found")
            return None

        query = keyword or "business"
        url = "https://api.unsplash.com/photos/random"
        params = {
            "query": query,
            "orientation": "landscape",
            "content_filter": "high",
            "client_id": UNSPLASH_KEY,
        }
        print(f"🖼 Fetching Unsplash image for: {query}")
        resp = requests.get(url, params=params, timeout=15)
        print(f"🖼 Unsplash status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            img_url = data["urls"]["regular"]
            img_resp = requests.get(img_url, timeout=15)
            if img_resp.status_code == 200:
                print("✅ Image fetched successfully")
                bio = BytesIO(img_resp.content)
                bio.seek(0)
                return bio
        elif resp.status_code == 401:
            print("❌ Unsplash 401 Unauthorized")
        elif resp.status_code == 403:
            print("❌ Unsplash 403 Forbidden")
        else:
            print(f"❌ Unsplash error {resp.status_code}")

    except Exception as e:
        print(f"❌ Unsplash failed: {e}")

    return None


# ─── HELPERS ──────────────────────────────────────────────────────
def set_bg(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(slide, left, top, width, height, color, radius=0, transparency=0):
    from pptx.oxml.ns import qn
    from lxml import etree

    shape = slide.shapes.add_shape(1, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color

    if transparency > 0:
        shape.fill.transparency = transparency

    shape.line.fill.background()

    if radius > 0:
        sp = shape._element
        spPr = sp.find(qn("p:spPr"))
        prstGeom = spPr.find(qn("a:prstGeom")) if spPr is not None else None
        if prstGeom is not None:
            spPr.remove(prstGeom)
        prstGeom = etree.SubElement(spPr, qn("a:prstGeom"))
        prstGeom.set("prst", "roundRect")
        avLst = etree.SubElement(prstGeom, qn("a:avLst"))
        gd = etree.SubElement(avLst, qn("a:gd"))
        gd.set("name", "adj")
        gd.set("fmla", f"val {radius}")

    return shape


def add_circle(slide, left, top, width, height, color, transparency=0):
    shape = slide.shapes.add_shape(MSO_SHAPE.OVAL, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    if transparency > 0:
        shape.fill.transparency = transparency
    shape.line.fill.background()
    return shape


def add_text(
    slide,
    text,
    left,
    top,
    width,
    height,
    size,
    color,
    bold=False,
    align=PP_ALIGN.LEFT,
    wrap=True,
    italic=False,
):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = size
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = "Segoe UI"
    return tb


def add_image_to_slide(slide, image_stream, left, top, width, height):
    try:
        if hasattr(image_stream, "seek"):
            image_stream.seek(0)
        slide.shapes.add_picture(image_stream, left, top, width, height)
        return True
    except Exception as e:
        print(f"Image insert failed: {e}")
        return False


def make_rounded_image(image_stream, radius=60):
    try:
        image_stream.seek(0)
        img = Image.open(image_stream).convert("RGBA")
        w, h = img.size

        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)

        img.putalpha(mask)
        out = BytesIO()
        img.save(out, format="PNG")
        out.seek(0)
        return out
    except Exception as e:
        print(f"Rounded image failed: {e}")
        return image_stream


# ─── TITLE SLIDE ─────────────────────────────────────────────────
def build_title_slide(prs, title, theme, keyword="abstract"):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    img = fetch_unsplash_image(keyword)
    if img:
        add_image_to_slide(slide, img, 0, 0, SLIDE_W, SLIDE_H)
        overlay = add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, RGBColor(0x00, 0x00, 0x00))
        overlay.fill.transparency = 0.35

    add_rect(slide, 0, Inches(5.2), SLIDE_W, Inches(2.3), theme["accent"], transparency=0.85)

    add_text(
        slide,
        title,
        Inches(0.8),
        Inches(2.3),
        Inches(11.73),
        Inches(2.5),
        Pt(48),
        RGBColor(0xFF, 0xFF, 0xFF),
        bold=True,
        align=PP_ALIGN.CENTER,
    )

    add_text(
        slide,
        "Created with SlideBot",
        Inches(0.8),
        Inches(6.0),
        Inches(11.73),
        Inches(0.6),
        Pt(14),
        RGBColor(0xFF, 0xFF, 0xFF),
        align=PP_ALIGN.CENTER,
        italic=True,
    )


# ─── LAYOUT 1 — Hero Image + Text Overlay ─────────────────────────
def build_layout_1(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    img = fetch_unsplash_image(keyword)
    if img:
        add_image_to_slide(slide, img, 0, 0, SLIDE_W, SLIDE_H)

    add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, RGBColor(0x00, 0x00, 0x00), transparency=0.5)
    add_rect(slide, 0, Inches(7.2), SLIDE_W, Inches(0.3), theme["accent"])

    add_text(
        slide,
        heading,
        Inches(0.8),
        Inches(1.5),
        Inches(11.73),
        Inches(1.5),
        Pt(40),
        RGBColor(0xFF, 0xFF, 0xFF),
        bold=True,
        align=PP_ALIGN.CENTER,
    )

    top = Inches(3.2)
    for bullet in bullets[:4]:
        add_text(
            slide,
            f"▸ {bullet}",
            Inches(1.5),
            top,
            Inches(10.33),
            Inches(0.65),
            Pt(18),
            RGBColor(0xFF, 0xFF, 0xFF),
            align=PP_ALIGN.LEFT,
            wrap=True,
        )
        top += Inches(0.7)


# ─── LAYOUT 2 — Left Text, Right Full Image ───────────────────────
def build_layout_2(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    img = fetch_unsplash_image(keyword)
    if img:
        add_image_to_slide(slide, img, Inches(6.5), 0, Inches(6.83), SLIDE_H)
        add_rect(slide, Inches(6.5), 0, Inches(6.83), SLIDE_H, theme["accent"], transparency=0.85)

    add_text(
        slide,
        heading,
        Inches(0.6),
        Inches(0.5),
        Inches(5.8),
        Inches(1.2),
        Pt(32),
        theme["heading_color"],
        bold=True,
        align=PP_ALIGN.LEFT,
    )

    add_rect(slide, Inches(0.6), Inches(1.8), Inches(2.5), Inches(0.05), theme["accent"], radius=30000)

    top = Inches(2.2)
    for bullet in bullets[:5]:
        add_circle(slide, Inches(0.6), top + Inches(0.08), Inches(0.08), Inches(0.08), theme["accent2"])
        add_text(
            slide,
            bullet,
            Inches(0.9),
            top,
            Inches(5.5),
            Inches(0.65),
            Pt(16),
            theme["bullet_color"],
            align=PP_ALIGN.LEFT,
            wrap=True,
        )
        top += Inches(0.8)


# ─── LAYOUT 3 — Card Grid ────────────────────────────────────────
def build_layout_3(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    add_circle(slide, Inches(11.0), Inches(0.5), Inches(3.5), Inches(3.5), theme["light_accent"], transparency=0.8)

    add_text(
        slide,
        heading,
        Inches(0.6),
        Inches(0.4),
        Inches(8.0),
        Inches(0.9),
        Pt(30),
        theme["heading_color"],
        bold=True,
        align=PP_ALIGN.LEFT,
    )

    add_rect(slide, Inches(0.6), Inches(1.3), Inches(2.2), Inches(0.04), theme["accent"], radius=30000)

    top = Inches(1.7)
    for i, bullet in enumerate(bullets[:5]):
        card_color = [theme["card_bg"], theme["light_accent"]][i % 2]
        add_rect(slide, Inches(0.5), top, Inches(8.5), Inches(0.78), card_color, radius=12000)
        add_text(
            slide,
            bullet,
            Inches(0.8),
            top + Inches(0.1),
            Inches(8.0),
            Inches(0.6),
            Pt(15),
            theme["bullet_color"],
            align=PP_ALIGN.LEFT,
            wrap=True,
        )
        top += Inches(0.88)

    img = fetch_unsplash_image(keyword)
    if img:
        rounded = make_rounded_image(img, radius=30)
        add_image_to_slide(slide, rounded, Inches(10.5), Inches(5.5), Inches(2.5), Inches(1.8))


# ─── LAYOUT 4 — Split with Left Full Image ────────────────────────
def build_layout_4(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    img = fetch_unsplash_image(keyword)
    if img:
        add_image_to_slide(slide, img, 0, 0, Inches(6.5), SLIDE_H)
        add_rect(slide, 0, 0, Inches(6.5), SLIDE_H, theme["accent"], transparency=0.85)

    add_text(
        slide,
        heading,
        Inches(6.8),
        Inches(0.8),
        Inches(6.0),
        Inches(1.2),
        Pt(32),
        theme["heading_color"],
        bold=True,
        align=PP_ALIGN.LEFT,
    )

    add_rect(slide, Inches(6.8), Inches(2.1), Inches(2.2), Inches(0.04), theme["accent"], radius=30000)

    top = Inches(2.5)
    for bullet in bullets[:5]:
        add_text(
            slide,
            f"• {bullet}",
            Inches(6.8),
            top,
            Inches(6.0),
            Inches(0.7),
            Pt(16),
            theme["bullet_color"],
            align=PP_ALIGN.LEFT,
            wrap=True,
        )
        top += Inches(0.8)


# ─── LAYOUT 5 — Quote Style ──────────────────────────────────────
def build_layout_5(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["accent"])

    add_text(
        slide,
        "“",
        Inches(0.8),
        Inches(0.3),
        Inches(1.5),
        Inches(1.5),
        Pt(72),
        RGBColor(0xFF, 0xFF, 0xFF),
        bold=True,
        align=PP_ALIGN.LEFT,
        italic=True,
    )

    add_text(
        slide,
        heading,
        Inches(1.5),
        Inches(1.0),
        Inches(10.33),
        Inches(2.0),
        Pt(34),
        RGBColor(0xFF, 0xFF, 0xFF),
        bold=True,
        align=PP_ALIGN.CENTER,
        wrap=True,
    )

    add_rect(slide, Inches(5.5), Inches(3.2), Inches(2.33), Inches(0.04), RGBColor(0xFF, 0xFF, 0xFF))

    top = Inches(3.6)
    for bullet in bullets[:3]:
        add_text(
            slide,
            f"✦ {bullet}",
            Inches(1.5),
            top,
            Inches(10.33),
            Inches(0.7),
            Pt(18),
            RGBColor(0xFF, 0xFF, 0xFF),
            align=PP_ALIGN.CENTER,
            wrap=True,
        )
        top += Inches(0.8)

    img = fetch_unsplash_image(keyword)
    if img:
        rounded = make_rounded_image(img, radius=25)
        add_image_to_slide(slide, rounded, Inches(10.8), Inches(5.8), Inches(2.2), Inches(1.5))


# ─── LAYOUT 6 — Minimal Two Column ────────────────────────────────
def build_layout_6(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    add_rect(slide, 0, 0, SLIDE_W, Inches(0.06), theme["accent"])

    add_text(
        slide,
        heading,
        Inches(0.7),
        Inches(0.5),
        Inches(11.73),
        Inches(1.2),
        Pt(36),
        theme["heading_color"],
        bold=True,
        align=PP_ALIGN.LEFT,
    )

    add_rect(slide, Inches(0.7), Inches(1.8), Inches(3.0), Inches(0.05), theme["accent2"], radius=30000)

    mid = (len(bullets) + 1) // 2
    col1 = bullets[:mid]
    col2 = bullets[mid:]

    left_top = Inches(2.2)
    for bullet in col1[:4]:
        add_circle(slide, Inches(0.7), left_top + Inches(0.08), Inches(0.08), Inches(0.08), theme["accent"])
        add_text(
            slide,
            bullet,
            Inches(1.0),
            left_top,
            Inches(5.5),
            Inches(0.65),
            Pt(16),
            theme["bullet_color"],
            align=PP_ALIGN.LEFT,
            wrap=True,
        )
        left_top += Inches(0.85)

    right_top = Inches(2.2)
    for bullet in col2[:4]:
        add_circle(slide, Inches(6.8), right_top + Inches(0.08), Inches(0.08), Inches(0.08), theme["accent2"])
        add_text(
            slide,
            bullet,
            Inches(7.1),
            right_top,
            Inches(5.8),
            Inches(0.65),
            Pt(16),
            theme["bullet_color"],
            align=PP_ALIGN.LEFT,
            wrap=True,
        )
        right_top += Inches(0.85)

    img = fetch_unsplash_image(keyword)
    if img:
        rounded = make_rounded_image(img, radius=20)
        add_image_to_slide(slide, rounded, Inches(11.0), Inches(6.0), Inches(2.0), Inches(1.3))


# ─── THANK YOU SLIDE ──────────────────────────────────────────────
def build_thankyou_slide(prs, theme, is_premium: bool = False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    add_rect(slide, 0, 0, SLIDE_W, Inches(0.05), theme["accent"])
    add_rect(slide, 0, SLIDE_H - Inches(0.05), SLIDE_W, Inches(0.05), theme["accent"])

    add_circle(slide, Inches(5.5), Inches(2.0), Inches(2.5), Inches(2.5), theme["light_accent"], transparency=0.7)

    add_text(
        slide,
        "Thank You",
        Inches(1.0),
        Inches(2.3),
        Inches(11.33),
        Inches(1.5),
        Pt(48),
        theme["title_color"],
        bold=True,
        align=PP_ALIGN.CENTER,
    )

    add_text(
        slide,
        "Created with SlideBot",
        Inches(1.0),
        Inches(4.5),
        Inches(11.33),
        Inches(0.6),
        Pt(16),
        theme["bullet_color"],
        align=PP_ALIGN.CENTER,
        italic=True,
    )


# ─── MAIN BUILD FUNCTION ──────────────────────────────────────────
LAYOUTS = [
    build_layout_1,
    build_layout_2,
    build_layout_3,
    build_layout_4,
    build_layout_5,
    build_layout_6,
]


def build_presentation(slide_data: dict, theme_name: str = "classic", is_premium: bool = False) -> str:
    """
    slide_data: {
        "title": str,
        "slides": [
            {
                "slide_number": int,
                "heading": str,
                "explanation": str,   # Can be used later, but for now use bullets
                "image_keyword": str,
                "bullets": [str, ...]
            }
        ]
    }
    """
    theme = THEMES.get(theme_name, THEMES["classic"])

    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    slides = slide_data.get("slides", [])
    title = slide_data.get("title", "My Presentation")

    if not slides:
        raise ValueError("No slides data provided")

    # Title slide
    first_keyword = slides[0].get("image_keyword", "business")
    build_title_slide(prs, title, theme, first_keyword)

    # Content slides (skip the first slide if it's intro? Actually use all except last for content)
    # The AI already includes intro as first slide, so we use all slides except last as content
    # Last slide will be handled as thank you? No, AI generates conclusion as last slide
    # So we use ALL slides from the AI, no skipping
    
    for idx, slide in enumerate(slides):
        heading = slide.get("heading", f"Slide {idx+1}")
        bullets = slide.get("bullets", [])
        keyword = slide.get("image_keyword", "business")
        
        # Use different layouts for variety
        layout_fn = LAYOUTS[idx % len(LAYOUTS)]
        layout_fn(prs, heading, bullets, theme, keyword)

    # Thank you slide (separate from AI slides)
    build_thankyou_slide(prs, theme, is_premium=is_premium)

    # Save the presentation
    filename = f"slidebot_{uuid.uuid4().hex[:8]}.pptx"
    os.makedirs("outputs", exist_ok=True)
    filepath = os.path.join("outputs", filename)
    prs.save(filepath)
    
    print(f"✅ Presentation saved: {filepath}")
    return filepath

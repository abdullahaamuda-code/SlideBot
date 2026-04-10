import os
import uuid
import requests
from io import BytesIO
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from PIL import Image, ImageDraw
from dotenv import load_dotenv

load_dotenv()

UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

# ─── THEMES ───────────────────────────────────────────────────────
THEMES = {
    "classic": {
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
        "title_color": RGBColor(0x1F, 0x39, 0x64),
        "heading_color": RGBColor(0x1F, 0x39, 0x64),
        "bullet_color": RGBColor(0x22, 0x22, 0x22),
        "accent": RGBColor(0x1F, 0x39, 0x64),
        "accent2": RGBColor(0x2E, 0x75, 0xB6),
        "card_bg": RGBColor(0xEF, 0xF4, 0xFF),
    },
    "dark": {
        "bg": RGBColor(0x1A, 0x1A, 0x2E),
        "title_color": RGBColor(0xE9, 0x4C, 0x7D),
        "heading_color": RGBColor(0xE9, 0x4C, 0x7D),
        "bullet_color": RGBColor(0xFF, 0xFF, 0xFF),
        "accent": RGBColor(0xE9, 0x4C, 0x7D),
        "accent2": RGBColor(0x16, 0x21, 0x3E),
        "card_bg": RGBColor(0x16, 0x21, 0x3E),
    },
    "corporate": {
        "bg": RGBColor(0xF4, 0xF6, 0xF9),
        "title_color": RGBColor(0x00, 0x4E, 0x92),
        "heading_color": RGBColor(0x00, 0x4E, 0x92),
        "bullet_color": RGBColor(0x33, 0x33, 0x33),
        "accent": RGBColor(0x00, 0x4E, 0x92),
        "accent2": RGBColor(0x00, 0x8B, 0xD2),
        "card_bg": RGBColor(0xDF, 0xEE, 0xFF),
    },
    "startup": {
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
        "title_color": RGBColor(0xFF, 0x6B, 0x35),
        "heading_color": RGBColor(0xFF, 0x6B, 0x35),
        "bullet_color": RGBColor(0x22, 0x22, 0x22),
        "accent": RGBColor(0xFF, 0x6B, 0x35),
        "accent2": RGBColor(0xFF, 0xA0, 0x6A),
        "card_bg": RGBColor(0xFF, 0xF0, 0xE8),
    },
    "academic": {
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
        "title_color": RGBColor(0x2E, 0x86, 0xAB),
        "heading_color": RGBColor(0x2E, 0x86, 0xAB),
        "bullet_color": RGBColor(0x22, 0x22, 0x22),
        "accent": RGBColor(0x2E, 0x86, 0xAB),
        "accent2": RGBColor(0xA2, 0x33, 0x2F),
        "card_bg": RGBColor(0xE8, 0xF6, 0xFF),
    },
    "minimal": {
        "bg": RGBColor(0xFA, 0xFA, 0xFA),
        "title_color": RGBColor(0x11, 0x11, 0x11),
        "heading_color": RGBColor(0x11, 0x11, 0x11),
        "bullet_color": RGBColor(0x44, 0x44, 0x44),
        "accent": RGBColor(0x11, 0x11, 0x11),
        "accent2": RGBColor(0x88, 0x88, 0x88),
        "card_bg": RGBColor(0xEE, 0xEE, 0xEE),
    },
}

FREE_THEMES = ["classic", "dark"]
PREMIUM_THEMES = ["corporate", "startup", "academic", "minimal"]

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)


# ─── UNSPLASH IMAGE FETCH ─────────────────────────────────────────
def fetch_unsplash_image(keyword: str):
    try:
        if not UNSPLASH_KEY:
            print("❌ No Unsplash key found")
            return None

        url = "https://api.unsplash.com/photos/random"
        params = {
            "query": keyword,
            "orientation": "landscape",
            "content_filter": "high",
            "client_id": UNSPLASH_KEY,
        }
        print(f"🖼 Fetching Unsplash image for: {keyword}")
        response = requests.get(url, params=params, timeout=15)
        print(f"🖼 Unsplash status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            img_url = data["urls"]["regular"]
            img_response = requests.get(img_url, timeout=15)
            if img_response.status_code == 200:
                print("✅ Image fetched successfully")
                return BytesIO(img_response.content)

    except Exception as e:
        print(f"❌ Unsplash failed: {e}")

    return None


# ─── HELPERS ──────────────────────────────────────────────────────
def set_bg(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(slide, left, top, width, height, color, radius=0):
    from pptx.oxml.ns import qn
    from lxml import etree

    shape = slide.shapes.add_shape(1, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
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
    run.font.name = "Calibri"
    return tb


def add_image_to_slide(slide, image_stream, left, top, width, height):
    try:
        slide.shapes.add_picture(image_stream, left, top, width, height)
        return True
    except Exception as e:
        print(f"Image insert failed: {e}")
        return False


# ─── TITLE SLIDE ──────────────────────────────────────────────────
def build_title_slide(prs, title, theme, keyword="abstract"):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    img = fetch_unsplash_image(keyword)
    if img:
        add_image_to_slide(slide, img, 0, 0, SLIDE_W, SLIDE_H)
        overlay = add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, RGBColor(0x00, 0x00, 0x00))
        overlay.fill.transparency = 0.4

    add_rect(slide, 0, Inches(5.8), SLIDE_W, Inches(1.7), theme["accent"])

    add_text(
        slide,
        title,
        Inches(0.8),
        Inches(1.8),
        Inches(11.5),
        Inches(3.0),
        Pt(48),
        RGBColor(0xFF, 0xFF, 0xFF),
        bold=True,
        align=PP_ALIGN.CENTER,
    )

    add_text(
        slide,
        "Generated by SlideBot 🚀",
        Inches(0.8),
        Inches(6.0),
        Inches(11.5),
        Inches(0.7),
        Pt(18),
        RGBColor(0xFF, 0xFF, 0xFF),
        align=PP_ALIGN.CENTER,
    )


# ─── LAYOUT A — Left image, right bullets ─────────────────────────
def build_layout_a(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    add_rect(slide, 0, 0, SLIDE_W, Inches(0.12), theme["accent"])

    img = fetch_unsplash_image(keyword)
    if img:
        add_image_to_slide(slide, img, 0, Inches(0.12), Inches(5.5), Inches(7.38))
    else:
        add_rect(slide, 0, Inches(0.12), Inches(5.5), Inches(7.38), theme["card_bg"])

    add_text(
        slide,
        heading,
        Inches(5.8),
        Inches(0.5),
        Inches(7.2),
        Inches(1.2),
        Pt(28),
        theme["heading_color"],
        bold=True,
        align=PP_ALIGN.LEFT,
    )

    add_rect(slide, Inches(5.8), Inches(1.8), Inches(6.8), Inches(0.05), theme["accent"])

    top = Inches(2.0)
    for bullet in bullets[:5]:
        add_rect(slide, Inches(5.8), top + Inches(0.15), Inches(0.08), Inches(0.4), theme["accent"])
        add_text(
            slide,
            bullet,
            Inches(6.1),
            top,
            Inches(6.9),
            Inches(0.7),
            Pt(18),
            theme["bullet_color"],
            align=PP_ALIGN.LEFT,
        )
        top += Inches(0.9)

    add_rect(slide, 0, Inches(7.3), SLIDE_W, Inches(0.2), theme["accent"])


# ─── LAYOUT B — Full image background ─────────────────────────────
def build_layout_b(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    img = fetch_unsplash_image(keyword)
    if img:
        add_image_to_slide(slide, img, 0, 0, SLIDE_W, SLIDE_H)

    add_rect(slide, 0, Inches(3.2), SLIDE_W, Inches(4.3), RGBColor(0x10, 0x10, 0x10))
    add_rect(slide, 0, 0, SLIDE_W, Inches(0.15), theme["accent"])

    add_text(
        slide,
        heading,
        Inches(0.8),
        Inches(3.3),
        Inches(11.5),
        Inches(1.0),
        Pt(30),
        RGBColor(0xFF, 0xFF, 0xFF),
        bold=True,
        align=PP_ALIGN.LEFT,
    )

    top = Inches(4.4)
    for bullet in bullets[:4]:
        add_text(
            slide,
            f"▸  {bullet}",
            Inches(1.0),
            top,
            Inches(11.0),
            Inches(0.65),
            Pt(18),
            RGBColor(0xEE, 0xEE, 0xEE),
            align=PP_ALIGN.LEFT,
        )
        top += Inches(0.72)


# ─── THANK YOU SLIDE ──────────────────────────────────────────────
def build_thankyou_slide(prs, theme):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    add_rect(slide, 0, 0, SLIDE_W, Inches(0.15), theme["accent"])
    add_rect(slide, 0, Inches(7.35), SLIDE_W, Inches(0.15), theme["accent"])
    add_rect(slide, Inches(5.16), Inches(1.5), Inches(3.0), Inches(3.0), theme["card_bg"], radius=50000)

    add_text(
        slide,
        "Thank You! 🙏",
        Inches(1.0),
        Inches(2.2),
        Inches(11.0),
        Inches(1.8),
        Pt(52),
        theme["title_color"],
        bold=True,
        align=PP_ALIGN.CENTER,
    )

    add_text(
        slide,
        "Generated by SlideBot",
        Inches(1.0),
        Inches(4.5),
        Inches(11.0),
        Inches(0.6),
        Pt(16),
        theme["bullet_color"],
        align=PP_ALIGN.CENTER,
    )


# ─── MAIN BUILD FUNCTION ──────────────────────────────────────────
LAYOUTS = [build_layout_a, build_layout_b]


def build_presentation(slide_data: dict, theme_name: str = "classic", is_premium: bool = False) -> str:
    theme = THEMES.get(theme_name, THEMES["classic"])

    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    slides = slide_data.get("slides", [])
    title = slide_data.get("title", "My Presentation")

    first_keyword = slides[0].get("image_keyword", "business") if slides else "business"
    build_title_slide(prs, title, theme, first_keyword)

    for idx, slide in enumerate(slides):
        heading = slide.get("heading", "")
        bullets = slide.get("bullets", [])
        keyword = slide.get("image_keyword", "business")
        layout_fn = LAYOUTS[idx % len(LAYOUTS)]
        layout_fn(prs, heading, bullets, theme, keyword)

    build_thankyou_slide(prs, theme)

    filename = f"slidebot_{uuid.uuid4().hex[:8]}.pptx"
    filepath = os.path.join("outputs", filename)
    os.makedirs("outputs", exist_ok=True)
    prs.save(filepath)

    return filepath

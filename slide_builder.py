import os
import uuid
import random
import requests
from io import BytesIO

from dotenv import load_dotenv
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, PP_PARAGRAPH_ALIGNMENT
from pptx.enum.shapes import MSO_SHAPE

from PIL import Image, ImageDraw

load_dotenv()

UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

# ─── THEMES — Premium corporate & Instagram-style color palettes ───
THEMES = {
    "classic": {
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
        "title_color": RGBColor(0x1F, 0x39, 0x64),
        "heading_color": RGBColor(0x1F, 0x39, 0x64),
        "bullet_color": RGBColor(0x22, 0x22, 0x22),
        "accent": RGBColor(0x1F, 0x39, 0x64),
        "accent2": RGBColor(0x2E, 0x75, 0xB6),
        "card_bg": RGBColor(0xEF, 0xF4, 0xFF),
        "light_accent": RGBColor(0xD6, 0xE6, 0xF5),
        "soft_accent": RGBColor(0x8B, 0xB3, 0xD9),
    },
    "dark": {
        "bg": RGBColor(0x1A, 0x1A, 0x2E),
        "title_color": RGBColor(0xE9, 0x4C, 0x7D),
        "heading_color": RGBColor(0xE9, 0x4C, 0x7D),
        "bullet_color": RGBColor(0xFF, 0xFF, 0xFF),
        "accent": RGBColor(0xE9, 0x4C, 0x7D),
        "accent2": RGBColor(0x16, 0x21, 0x3E),
        "card_bg": RGBColor(0x16, 0x21, 0x3E),
        "light_accent": RGBColor(0x2A, 0x2A, 0x4A),
        "soft_accent": RGBColor(0xE9, 0x4C, 0x7D),
    },
    "corporate": {
        "bg": RGBColor(0xF4, 0xF6, 0xF9),
        "title_color": RGBColor(0x00, 0x4E, 0x92),
        "heading_color": RGBColor(0x00, 0x4E, 0x92),
        "bullet_color": RGBColor(0x33, 0x33, 0x33),
        "accent": RGBColor(0x00, 0x4E, 0x92),
        "accent2": RGBColor(0x00, 0x8B, 0xD2),
        "card_bg": RGBColor(0xDF, 0xEE, 0xFF),
        "light_accent": RGBColor(0xE8, 0xF0, 0xFE),
        "soft_accent": RGBColor(0x66, 0xAA, 0xDD),
    },
    "startup": {
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
        "title_color": RGBColor(0xFF, 0x6B, 0x35),
        "heading_color": RGBColor(0xFF, 0x6B, 0x35),
        "bullet_color": RGBColor(0x22, 0x22, 0x22),
        "accent": RGBColor(0xFF, 0x6B, 0x35),
        "accent2": RGBColor(0xFF, 0xA0, 0x6A),
        "card_bg": RGBColor(0xFF, 0xF0, 0xE8),
        "light_accent": RGBColor(0xFF, 0xE0, 0xD0),
        "soft_accent": RGBColor(0xFF, 0x8C, 0x55),
    },
    "academic": {
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
        "title_color": RGBColor(0x2E, 0x86, 0xAB),
        "heading_color": RGBColor(0x2E, 0x86, 0xAB),
        "bullet_color": RGBColor(0x22, 0x22, 0x22),
        "accent": RGBColor(0x2E, 0x86, 0xAB),
        "accent2": RGBColor(0xA2, 0x33, 0x2F),
        "card_bg": RGBColor(0xE8, 0xF6, 0xFF),
        "light_accent": RGBColor(0xD4, 0xEA, 0xF7),
        "soft_accent": RGBColor(0x5B, 0xA9, 0xC9),
    },
    "minimal": {
        "bg": RGBColor(0xFA, 0xFA, 0xFA),
        "title_color": RGBColor(0x11, 0x11, 0x11),
        "heading_color": RGBColor(0x11, 0x11, 0x11),
        "bullet_color": RGBColor(0x44, 0x44, 0x44),
        "accent": RGBColor(0x11, 0x11, 0x11),
        "accent2": RGBColor(0x88, 0x88, 0x88),
        "card_bg": RGBColor(0xEE, 0xEE, 0xEE),
        "light_accent": RGBColor(0xE0, 0xE0, 0xE0),
        "soft_accent": RGBColor(0xAA, 0xAA, 0xAA),
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
            print(f"🖼 Got image URL: {img_url[:60]}")
            img_response = requests.get(img_url, timeout=15)
            print(f"🖼 Image download status: {img_response.status_code}")
            if img_response.status_code == 200:
                print("✅ Image fetched successfully")
                return BytesIO(img_response.content)

        elif response.status_code == 403:
            print("❌ Unsplash key invalid or rate limited")
        elif response.status_code == 401:
            print("❌ Unsplash unauthorized — check your key")
        else:
            print(f"❌ Unsplash error: {response.text[:200]}")

    except requests.Timeout:
        print(f"❌ Unsplash timeout for '{keyword}'")
    except Exception as e:
        print(f"❌ Unsplash failed for '{keyword}': {e}")

    return None


# ─── ENHANCED HELPERS WITH SHAPE VARIETY ──────────────────────────
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


def add_diagonal_line(slide, start_left, start_top, end_left, end_top, color, width_pt=2):
    from pptx.enum.shapes import MSO_SHAPE
    line = slide.shapes.add_shape(MSO_SHAPE.LINE_CALLOUT_1, start_left, start_top, 0, 0)
    # Alternative approach for diagonal
    connector = slide.shapes.add_connector(1, start_left, start_top, end_left, end_top)
    connector.line.color.rgb = color
    connector.line.width = Pt(width_pt)
    return connector


def add_corner_bracket(slide, x, y, size, color, corner="tl", thickness=3):
    """Add L-shaped corner bracket (top-left, top-right, bottom-left, bottom-right)"""
    from pptx.enum.shapes import MSO_SHAPE
    
    bracket_width = Inches(size)
    bracket_height = Inches(size)
    
    if corner == "tl":
        # Top-left corner - horizontal and vertical lines
        h_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, bracket_width, Pt(thickness))
        v_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, Pt(thickness), bracket_height)
    elif corner == "tr":
        # Top-right corner
        h_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x - bracket_width, y, bracket_width, Pt(thickness))
        v_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x - Pt(thickness), y, Pt(thickness), bracket_height)
    elif corner == "bl":
        # Bottom-left corner
        h_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y - Pt(thickness), bracket_width, Pt(thickness))
        v_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y - bracket_height, Pt(thickness), bracket_height)
    elif corner == "br":
        # Bottom-right corner
        h_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x - bracket_width, y - Pt(thickness), bracket_width, Pt(thickness))
        v_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x - Pt(thickness), y - bracket_height, Pt(thickness), bracket_height)
    else:
        return
    
    for shape in [h_line, v_line]:
        shape.fill.solid()
        shape.fill.fore_color.rgb = color
        shape.line.fill.background()


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
    run.font.name = "Calibri"
    return tb


def add_image_to_slide(slide, image_stream, left, top, width, height):
    try:
        slide.shapes.add_picture(image_stream, left, top, width, height)
        return True
    except Exception as e:
        print(f"Image insert failed: {e}")
        return False


def make_rounded_image(image_stream, radius=60):
    try:
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
        try:
            image_stream.seek(0)
        except Exception:
            pass
        return image_stream


# ─── TITLE SLIDE — Premium hero layout with corner accents ─────────
def build_title_slide(prs, title, theme, keyword="abstract"):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    img = fetch_unsplash_image(keyword)
    if img:
        add_image_to_slide(slide, img, 0, 0, SLIDE_W, SLIDE_H)
        overlay = add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, RGBColor(0x00, 0x00, 0x00))
        overlay.fill.transparency = 0.4

    # Corner brackets (all 4 corners)
    add_corner_bracket(slide, Inches(0.3), Inches(0.3), 0.5, theme["accent"], "tl")
    add_corner_bracket(slide, SLIDE_W - Inches(0.3), Inches(0.3), 0.5, theme["accent"], "tr")
    add_corner_bracket(slide, Inches(0.3), SLIDE_H - Inches(0.3), 0.5, theme["accent"], "bl")
    add_corner_bracket(slide, SLIDE_W - Inches(0.3), SLIDE_H - Inches(0.3), 0.5, theme["accent"], "br")

    # Large decorative circle behind title
    add_circle(slide, Inches(3.5), Inches(1.5), Inches(6.33), Inches(4.5), theme["accent"], transparency=0.85)
    
    # Side accent bars
    add_rect(slide, 0, 0, Inches(0.08), SLIDE_H, theme["accent"])
    add_rect(slide, SLIDE_W - Inches(0.08), 0, Inches(0.08), SLIDE_H, theme["accent"])

    # Gradient-like effect with multiple accent bars
    add_rect(slide, 0, Inches(5.5), SLIDE_W, Inches(2.0), theme["accent"], transparency=0.15)
    add_rect(slide, 0, Inches(6.2), SLIDE_W, Inches(1.3), theme["accent"], transparency=0.3)

    # Main title with premium spacing
    add_text(
        slide,
        title,
        Inches(0.8),
        Inches(2.2),
        Inches(11.73),
        Inches(2.5),
        Pt(52),
        RGBColor(0xFF, 0xFF, 0xFF),
        bold=True,
        align=PP_ALIGN.CENTER,
    )

    add_text(
        slide,
        "Generated by SlideBot",
        Inches(0.8),
        Inches(6.3),
        Inches(11.73),
        Inches(0.6),
        Pt(16),
        RGBColor(0xFF, 0xFF, 0xFF),
        align=PP_ALIGN.CENTER,
        italic=True,
    )


# ─── LAYOUT A — Split screen with side accents and corner brackets ─
def build_layout_a(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    # All 4 corner brackets
    add_corner_bracket(slide, Inches(0.2), Inches(0.2), 0.4, theme["soft_accent"], "tl")
    add_corner_bracket(slide, SLIDE_W - Inches(0.2), Inches(0.2), 0.4, theme["soft_accent"], "tr")
    add_corner_bracket(slide, Inches(0.2), SLIDE_H - Inches(0.2), 0.4, theme["soft_accent"], "bl")
    add_corner_bracket(slide, SLIDE_W - Inches(0.2), SLIDE_H - Inches(0.2), 0.4, theme["soft_accent"], "br")

    # Side vertical accent bars
    add_rect(slide, Inches(0.08), 0, Inches(0.06), SLIDE_H, theme["accent"], transparency=0.3)
    add_rect(slide, SLIDE_W - Inches(0.14), 0, Inches(0.06), SLIDE_H, theme["accent"], transparency=0.3)

    # Top accent bar
    add_rect(slide, 0, 0, SLIDE_W, Inches(0.08), theme["accent"])

    # Left image with rounded corners and decorative circle behind
    img = fetch_unsplash_image(keyword)
    if img:
        rounded = make_rounded_image(img, radius=60)
        add_image_to_slide(slide, rounded, Inches(0.4), Inches(0.4), Inches(5.0), Inches(6.7))
    else:
        add_rect(slide, Inches(0.4), Inches(0.4), Inches(5.0), Inches(6.7), theme["card_bg"], radius=60)

    # Decorative circle overlapping image
    add_circle(slide, Inches(5.0), Inches(6.5), Inches(1.0), Inches(1.0), theme["light_accent"], transparency=0.5)

    # Right content area with better spacing
    heading_box = add_text(
        slide,
        heading,
        Inches(5.7),
        Inches(0.5),
        Inches(7.3),
        Inches(1.3),
        Pt(32),
        theme["heading_color"],
        bold=True,
        align=PP_ALIGN.LEFT,
    )
    
    # Decorative line under heading
    add_rect(slide, Inches(5.7), Inches(1.9), Inches(2.5), Inches(0.06), theme["accent"], radius=30000)

    # Enhanced bullet points with custom icons
    top = Inches(2.3)
    for i, bullet in enumerate(bullets[:5]):
        # Colored bullet accent circle
        add_circle(slide, Inches(5.7), top + Inches(0.08), Inches(0.1), Inches(0.1), theme["accent"])
        
        add_text(
            slide,
            bullet,
            Inches(6.0),
            top,
            Inches(7.0),
            Inches(0.65),
            Pt(17),
            theme["bullet_color"],
            align=PP_ALIGN.LEFT,
            wrap=True,
        )
        top += Inches(0.85)

    # Bottom accent bar
    add_rect(slide, 0, Inches(7.42), SLIDE_W, Inches(0.08), theme["accent"])


# ─── LAYOUT B — Full bleed with diagonal accents and side bars ────
def build_layout_b(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    img = fetch_unsplash_image(keyword)
    if img:
        add_image_to_slide(slide, img, 0, 0, SLIDE_W, SLIDE_H)

    # Gradient-like overlay
    add_rect(slide, 0, Inches(2.8), SLIDE_W, Inches(4.7), theme["accent"], transparency=0.7)
    add_rect(slide, 0, Inches(3.0), SLIDE_W, Inches(4.5), RGBColor(0x00, 0x00, 0x00), transparency=0.3)

    # Side accent bars
    add_rect(slide, 0, 0, Inches(0.1), SLIDE_H, theme["accent"])
    add_rect(slide, SLIDE_W - Inches(0.1), 0, Inches(0.1), SLIDE_H, theme["accent"])
    
    # Corner brackets
    add_corner_bracket(slide, Inches(0.25), Inches(0.25), 0.45, RGBColor(0xFF, 0xFF, 0xFF), "tl")
    add_corner_bracket(slide, SLIDE_W - Inches(0.25), Inches(0.25), 0.45, RGBColor(0xFF, 0xFF, 0xFF), "tr")
    add_corner_bracket(slide, Inches(0.25), SLIDE_H - Inches(0.25), 0.45, RGBColor(0xFF, 0xFF, 0xFF), "bl")
    add_corner_bracket(slide, SLIDE_W - Inches(0.25), SLIDE_H - Inches(0.25), 0.45, RGBColor(0xFF, 0xFF, 0xFF), "br")

    # Top and bottom accent bars
    add_rect(slide, 0, 0, SLIDE_W, Inches(0.1), theme["accent"])
    add_rect(slide, 0, SLIDE_H - Inches(0.1), SLIDE_W, Inches(0.1), theme["accent"])

    # Large heading
    add_text(
        slide,
        heading,
        Inches(0.8),
        Inches(3.1),
        Inches(11.73),
        Inches(1.2),
        Pt(36),
        RGBColor(0xFF, 0xFF, 0xFF),
        bold=True,
        align=PP_ALIGN.LEFT,
    )

    # Decorative line under heading
    add_rect(slide, Inches(0.8), Inches(4.3), Inches(3.0), Inches(0.04), RGBColor(0xFF, 0xFF, 0xFF))

    # Bullets with chevron style
    top = Inches(4.6)
    for bullet in bullets[:4]:
        add_text(
            slide,
            f"◆  {bullet}",
            Inches(0.8),
            top,
            Inches(11.73),
            Inches(0.7),
            Pt(18),
            RGBColor(0xFF, 0xFF, 0xFF),
            align=PP_ALIGN.LEFT,
        )
        top += Inches(0.75)

    # Bottom indicator
    add_rect(slide, Inches(6.165), Inches(7.25), Inches(1.0), Inches(0.06), RGBColor(0xFF, 0xFF, 0xFF), radius=30000)


# ─── LAYOUT C — Card-style with overlapping circles and side accents ─
def build_layout_c(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    # Decorative large circle in background
    add_circle(slide, Inches(10.0), Inches(1.0), Inches(4.0), Inches(4.0), theme["light_accent"], transparency=0.7)
    add_circle(slide, Inches(0.5), Inches(5.5), Inches(2.5), Inches(2.5), theme["light_accent"], transparency=0.5)

    # Side accent bars
    add_rect(slide, Inches(0.06), 0, Inches(0.06), SLIDE_H, theme["accent"], transparency=0.4)
    add_rect(slide, SLIDE_W - Inches(0.12), 0, Inches(0.06), SLIDE_H, theme["accent"], transparency=0.4)
    
    # Corner brackets
    add_corner_bracket(slide, Inches(0.2), Inches(0.2), 0.4, theme["accent2"], "tl")
    add_corner_bracket(slide, SLIDE_W - Inches(0.2), SLIDE_H - Inches(0.2), 0.4, theme["accent2"], "br")

    # Top and bottom bars
    add_rect(slide, 0, 0, SLIDE_W, Inches(0.08), theme["accent"])
    add_rect(slide, 0, SLIDE_H - Inches(0.08), SLIDE_W, Inches(0.08), theme["accent"])

    # Heading
    add_text(
        slide,
        heading,
        Inches(0.7),
        Inches(0.35),
        Inches(9.0),
        Inches(1.0),
        Pt(30),
        theme["heading_color"],
        bold=True,
        align=PP_ALIGN.LEFT,
    )

    # Right side image with rounded corners and circle accent
    img = fetch_unsplash_image(keyword)
    if img:
        rounded = make_rounded_image(img, radius=50)
        add_image_to_slide(slide, rounded, Inches(9.3), Inches(0.25), Inches(3.8), Inches(3.8))
        add_circle(slide, Inches(12.5), Inches(3.8), Inches(0.8), Inches(0.8), theme["accent"], transparency=0.6)

    # Card-style bullets
    top = Inches(1.5)
    card_colors = [theme["accent"], theme["accent2"], theme["card_bg"], theme["light_accent"]]

    for i, bullet in enumerate(bullets[:5]):
        card_color = card_colors[i % len(card_colors)]
        is_dark = card_color in [theme["accent"], theme["accent2"]]
        
        add_rect(slide, Inches(0.5), top, Inches(8.5), Inches(0.82), card_color, radius=20000)
        
        txt_color = RGBColor(0xFF, 0xFF, 0xFF) if is_dark else theme["bullet_color"]
        
        add_text(
            slide,
            f"0{i+1}",
            Inches(0.7),
            top + Inches(0.12),
            Inches(0.8),
            Inches(0.6),
            Pt(14),
            txt_color,
            bold=True,
            align=PP_ALIGN.CENTER,
        )
        
        add_text(
            slide,
            bullet,
            Inches(1.6),
            top + Inches(0.08),
            Inches(7.2),
            Inches(0.65),
            Pt(16),
            txt_color,
            align=PP_ALIGN.LEFT,
        )
        top += Inches(0.96)


# ─── LAYOUT D — Impact quote with diagonal lines and geometric shapes ─
def build_layout_d(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["accent"])

    # Diagonal accent lines in corners
    add_rect(slide, 0, 0, Inches(1.5), Inches(0.06), RGBColor(0xFF, 0xFF, 0xFF), transparency=0.4)
    add_rect(slide, 0, 0, Inches(0.06), Inches(1.5), RGBColor(0xFF, 0xFF, 0xFF), transparency=0.4)
    add_rect(slide, SLIDE_W - Inches(1.5), 0, Inches(1.5), Inches(0.06), RGBColor(0xFF, 0xFF, 0xFF), transparency=0.4)
    add_rect(slide, SLIDE_W - Inches(0.06), 0, Inches(0.06), Inches(1.5), RGBColor(0xFF, 0xFF, 0xFF), transparency=0.4)
    
    # Bottom diagonal accents
    add_rect(slide, 0, SLIDE_H - Inches(0.06), Inches(1.5), Inches(0.06), RGBColor(0xFF, 0xFF, 0xFF), transparency=0.4)
    add_rect(slide, SLIDE_W - Inches(1.5), SLIDE_H - Inches(0.06), Inches(1.5), Inches(0.06), RGBColor(0xFF, 0xFF, 0xFF), transparency=0.4)

    # Side accent bars
    add_rect(slide, 0, 0, Inches(0.08), SLIDE_H, RGBColor(0xFF, 0xFF, 0xFF), transparency=0.3)
    add_rect(slide, SLIDE_W - Inches(0.08), 0, Inches(0.08), SLIDE_H, RGBColor(0xFF, 0xFF, 0xFF), transparency=0.3)

    # Decorative circles
    add_circle(slide, Inches(0.5), Inches(6.0), Inches(1.2), Inches(1.2), RGBColor(0xFF, 0xFF, 0xFF), transparency=0.85)
    add_circle(slide, Inches(11.5), Inches(0.5), Inches(1.0), Inches(1.0), RGBColor(0xFF, 0xFF, 0xFF), transparency=0.85)

    # Large quote/heading
    add_text(
        slide,
        heading,
        Inches(1.5),
        Inches(0.8),
        Inches(10.33),
        Inches(2.0),
        Pt(38),
        RGBColor(0xFF, 0xFF, 0xFF),
        bold=True,
        align=PP_ALIGN.CENTER,
    )

    # Divider line
    add_rect(slide, Inches(5.0), Inches(2.9), Inches(3.33), Inches(0.05), RGBColor(0xFF, 0xFF, 0xFF))

    # Key points
    top = Inches(3.2)
    for bullet in bullets[:4]:
        add_text(
            slide,
            f"✦  {bullet}",
            Inches(1.5),
            top,
            Inches(10.33),
            Inches(0.7),
            Pt(19),
            RGBColor(0xFF, 0xFF, 0xFF),
            align=PP_ALIGN.CENTER,
        )
        top += Inches(0.82)

    # Decorative image with circle frame
    img = fetch_unsplash_image(keyword)
    if img:
        rounded = make_rounded_image(img, radius=30)
        add_image_to_slide(slide, rounded, Inches(10.8), Inches(5.8), Inches(2.2), Inches(1.5))
        add_circle(slide, Inches(10.6), Inches(5.6), Inches(2.6), Inches(1.9), RGBColor(0xFF, 0xFF, 0xFF), transparency=0.8)


# ─── LAYOUT E — Timeline with vertical side bar and node circles ───
def build_layout_e(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    # Thick vertical side bar (modern corporate look)
    add_rect(slide, 0, 0, Inches(0.25), SLIDE_H, theme["accent"])
    
    # Corner brackets
    add_corner_bracket(slide, Inches(0.3), Inches(0.2), 0.4, theme["accent2"], "tl")
    add_corner_bracket(slide, SLIDE_W - Inches(0.2), SLIDE_H - Inches(0.2), 0.4, theme["accent2"], "br")
    
    # Top and bottom bars
    add_rect(slide, 0, 0, SLIDE_W, Inches(0.08), theme["accent"])
    add_rect(slide, 0, SLIDE_H - Inches(0.08), SLIDE_W, Inches(0.08), theme["accent"])

    # Heading with accent background
    add_rect(slide, Inches(0.4), Inches(0.4), Inches(9.0), Inches(0.9), theme["light_accent"], radius=20000)
    add_text(
        slide,
        heading,
        Inches(0.6),
        Inches(0.45),
        Inches(9.0),
        Inches(0.8),
        Pt(28),
        theme["heading_color"],
        bold=True,
        align=PP_ALIGN.LEFT,
    )

    # Timeline line
    add_rect(slide, Inches(1.3), Inches(1.6), Inches(0.08), Inches(5.5), theme["light_accent"], radius=30000)

    # Bullets as timeline nodes
    top = Inches(1.6)
    for i, bullet in enumerate(bullets[:5]):
        # Node circle with inner dot
        add_circle(slide, Inches(1.26), top + Inches(0.12), Inches(0.16), Inches(0.16), theme["accent"])
        add_circle(slide, Inches(1.3), top + Inches(0.16), Inches(0.08), Inches(0.08), RGBColor(0xFF, 0xFF, 0xFF))
        
        # Year/step indicator
        add_text(
            slide,
            f"STEP 0{i+1}",
            Inches(1.7),
            top,
            Inches(1.5),
            Inches(0.5),
            Pt(12),
            theme["accent2"],
            bold=True,
            align=PP_ALIGN.LEFT,
        )
        
        # Bullet text
        add_text(
            slide,
            bullet,
            Inches(3.3),
            top,
            Inches(9.5),
            Inches(0.7),
            Pt(16),
            theme["bullet_color"],
            align=PP_ALIGN.LEFT,
            wrap=True,
        )
        top += Inches(1.05)

    # Decorative image

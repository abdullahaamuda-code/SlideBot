import os
import uuid
import requests
from io import BytesIO
from PIL import Image, ImageDraw
from dotenv import load_dotenv
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from lxml import etree

load_dotenv()

UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

FREE_THEMES = ["classic", "dark"]
PREMIUM_THEMES = ["corporate", "startup", "academic", "minimal"]

THEMES = {
    "classic": {
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
        "title_color": RGBColor(0x1F, 0x39, 0x64),
        "heading_color": RGBColor(0x1F, 0x39, 0x64),
        "bullet_color": RGBColor(0x22, 0x22, 0x22),
        "accent": RGBColor(0x1F, 0x39, 0x64),
        "accent2": RGBColor(0x2E, 0x75, 0xB6),
        "card_bg": RGBColor(0xDF, 0xEC, 0xFF),
        "wave": RGBColor(0x2E, 0x75, 0xB6),
    },
    "dark": {
        "bg": RGBColor(0x1A, 0x1A, 0x2E),
        "title_color": RGBColor(0xE9, 0x4C, 0x7D),
        "heading_color": RGBColor(0xE9, 0x4C, 0x7D),
        "bullet_color": RGBColor(0xFF, 0xFF, 0xFF),
        "accent": RGBColor(0xE9, 0x4C, 0x7D),
        "accent2": RGBColor(0x16, 0x21, 0x3E),
        "card_bg": RGBColor(0x16, 0x21, 0x3E),
        "wave": RGBColor(0xE9, 0x4C, 0x7D),
    },
    "corporate": {
        "bg": RGBColor(0xF4, 0xF6, 0xF9),
        "title_color": RGBColor(0x00, 0x4E, 0x92),
        "heading_color": RGBColor(0x00, 0x4E, 0x92),
        "bullet_color": RGBColor(0x33, 0x33, 0x33),
        "accent": RGBColor(0x00, 0x4E, 0x92),
        "accent2": RGBColor(0x00, 0x8B, 0xD2),
        "card_bg": RGBColor(0xDF, 0xEE, 0xFF),
        "wave": RGBColor(0x00, 0x8B, 0xD2),
    },
    "startup": {
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
        "title_color": RGBColor(0xFF, 0x6B, 0x35),
        "heading_color": RGBColor(0xFF, 0x6B, 0x35),
        "bullet_color": RGBColor(0x22, 0x22, 0x22),
        "accent": RGBColor(0xFF, 0x6B, 0x35),
        "accent2": RGBColor(0xFF, 0xA0, 0x6A),
        "card_bg": RGBColor(0xFF, 0xF0, 0xE8),
        "wave": RGBColor(0xFF, 0x6B, 0x35),
    },
    "academic": {
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
        "title_color": RGBColor(0x2E, 0x86, 0xAB),
        "heading_color": RGBColor(0x2E, 0x86, 0xAB),
        "bullet_color": RGBColor(0x22, 0x22, 0x22),
        "accent": RGBColor(0x2E, 0x86, 0xAB),
        "accent2": RGBColor(0xA2, 0x33, 0x2F),
        "card_bg": RGBColor(0xE8, 0xF6, 0xFF),
        "wave": RGBColor(0x2E, 0x86, 0xAB),
    },
    "minimal": {
        "bg": RGBColor(0xFA, 0xFA, 0xFA),
        "title_color": RGBColor(0x11, 0x11, 0x11),
        "heading_color": RGBColor(0x11, 0x11, 0x11),
        "bullet_color": RGBColor(0x44, 0x44, 0x44),
        "accent": RGBColor(0x11, 0x11, 0x11),
        "accent2": RGBColor(0x88, 0x88, 0x88),
        "card_bg": RGBColor(0xEE, 0xEE, 0xEE),
        "wave": RGBColor(0x88, 0x88, 0x88),
    },
}


# ─── IMAGE HELPERS ────────────────────────────────────────────────

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
            "client_id": UNSPLASH_KEY
        }
        print(f"🖼 Fetching Unsplash image for: {keyword}")
        r = requests.get(url, params=params, timeout=15)
        print(f"🖼 Unsplash status: {r.status_code}")

        if r.status_code == 200:
            img_url = r.json()["urls"]["small"]
            print(f"🖼 Got image URL: {img_url[:50]}")
            img_r = requests.get(img_url, timeout=15)
            print(f"🖼 Image download status: {img_r.status_code}")
            if img_r.status_code == 200:
                print("✅ Image fetched successfully")
                return BytesIO(img_r.content)
        elif r.status_code == 403:
            print("❌ Unsplash key invalid or rate limited")
        elif r.status_code == 401:
            print("❌ Unsplash unauthorized — check your key")
        else:
            print(f"❌ Unsplash error: {r.text[:200]}")

    except requests.Timeout:
        print(f"❌ Unsplash timeout for '{keyword}'")
    except Exception as e:
        print(f"❌ Unsplash failed for '{keyword}': {e}")
    return None

def make_rounded_image(image_stream, radius=60):
    """Returns a BytesIO PNG with rounded corners using Pillow."""
    try:
        img = Image.open(image_stream).convert("RGBA")
        w, h = img.size
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
        img.putalpha(mask)
        output = BytesIO()
        img.save(output, format="PNG")
        output.seek(0)
        return output
    except Exception as e:
        print(f"Rounded image failed: {e}")
        if image_stream:
            image_stream.seek(0)
        return image_stream


def make_curved_side_image(image_stream, side="right"):
    """Returns image with one curved/diagonal side cut."""
    try:
        img = Image.open(image_stream).convert("RGBA")
        w, h = img.size
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        if side == "right":
            # Curve cuts into left side
            points = [
                (int(w * 0.12), 0),
                (w, 0),
                (w, h),
                (int(w * 0.12), h),
                (0, int(h * 0.5)),
            ]
        else:
            # Curve cuts into right side
            points = [
                (0, 0),
                (int(w * 0.88), 0),
                (w, int(h * 0.5)),
                (int(w * 0.88), h),
                (0, h),
            ]
        draw.polygon(points, fill=255)
        img.putalpha(mask)
        output = BytesIO()
        img.save(output, format="PNG")
        output.seek(0)
        return output
    except Exception as e:
        print(f"Curved image failed: {e}")
        if image_stream:
            image_stream.seek(0)
        return image_stream


# ─── SHAPE HELPERS ────────────────────────────────────────────────

def set_bg(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(slide, left, top, width, height, color, radius=0):
    shape = slide.shapes.add_shape(1, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    if radius > 0:
        sp = shape._element
        spPr = sp.find(qn('p:spPr'))
        prstGeom = spPr.find(qn('a:prstGeom'))
        if prstGeom is not None:
            spPr.remove(prstGeom)
        prstGeom = etree.SubElement(spPr, qn('a:prstGeom'))
        prstGeom.set('prst', 'roundRect')
        avLst = etree.SubElement(prstGeom, qn('a:avLst'))
        gd = etree.SubElement(avLst, qn('a:gd'))
        gd.set('name', 'adj')
        gd.set('fmla', f'val {radius}')
    return shape


def add_text(slide, text, left, top, width, height,
             size, color, bold=False, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = size
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.name = "Calibri"
    return tb


def add_image(slide, image_stream, left, top, width, height):
    try:
        slide.shapes.add_picture(image_stream, left, top, width, height)
        return True
    except Exception as e:
        print(f"Image insert failed: {e}")
        return False


def add_wave(slide, color, top_ratio=0.82, flip=False):
    """Add a wave shape at bottom or top of slide."""
    try:
        wave = slide.shapes.add_shape(
            97,  # Wave shape MSO_SHAPE
            Inches(0),
            Inches(top_ratio * 7.5),
            SLIDE_W,
            Inches((1 - top_ratio) * 7.5 + 0.1)
        )
        wave.fill.solid()
        wave.fill.fore_color.rgb = color
        wave.line.fill.background()
    except Exception:
        # Fallback to flat bar if wave shape not available
        add_rect(slide, Inches(0),
                 Inches(top_ratio * 7.5),
                 SLIDE_W,
                 Inches((1 - top_ratio) * 7.5 + 0.1),
                 color)


# ─── TITLE SLIDE ──────────────────────────────────────────────────

def build_title_slide(prs, title, theme, keyword="business", is_premium=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    if is_premium:
        # Full background image with overlay
        img = fetch_unsplash_image(keyword)
        if img:
            add_image(slide, img, 0, 0, SLIDE_W, SLIDE_H)
        # Dark gradient overlay
        overlay = add_rect(slide, 0, 0, SLIDE_W, SLIDE_H,
                           RGBColor(0x0A, 0x0A, 0x0A))
        title_text_color = RGBColor(0xFF, 0xFF, 0xFF)
        sub_color = RGBColor(0xDD, 0xDD, 0xDD)
    else:
        # Clean colored panel title slide
        add_rect(slide, 0, 0, SLIDE_W, Inches(4.5), theme["accent"])
        title_text_color = RGBColor(0xFF, 0xFF, 0xFF)
        sub_color = theme["bullet_color"]

    # Wave at bottom of header
    add_wave(slide, theme["bg"] if is_premium else theme["accent"],
             top_ratio=0.58)

    # Title
    add_text(slide, title,
             Inches(1.0), Inches(1.5), Inches(11.0), Inches(2.5),
             Pt(46), title_text_color,
             bold=True, align=PP_ALIGN.CENTER)

    # Subtitle
    add_text(slide, "Generated by SlideBot 🚀",
             Inches(1.0), Inches(5.8), Inches(11.0), Inches(0.7),
             Pt(16), sub_color,
             align=PP_ALIGN.CENTER)

    # Bottom accent bar
    add_rect(slide, 0, Inches(7.2), SLIDE_W, Inches(0.3), theme["accent"])


# ─── LAYOUT A — Left curved image + right bullets ─────────────────

def build_layout_a(prs, heading, bullets, theme, keyword, is_premium=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    # Top bar
    add_rect(slide, 0, 0, SLIDE_W, Inches(0.12), theme["accent"])

    if is_premium:
        img = fetch_unsplash_image(keyword)
        if img:
            curved = make_curved_side_image(img, side="right")
            add_image(slide, curved,
                      Inches(0), Inches(0.12),
                      Inches(5.8), Inches(7.38))
        else:
            add_rect(slide, 0, Inches(0.12),
                     Inches(5.8), Inches(7.38),
                     theme["card_bg"], radius=0)
    else:
        add_rect(slide, 0, Inches(0.12),
                 Inches(5.0), Inches(7.38),
                 theme["card_bg"])

    # Heading
    add_text(slide, heading,
             Inches(6.1), Inches(0.4), Inches(6.8), Inches(1.2),
             Pt(28), theme["heading_color"],
             bold=True, align=PP_ALIGN.LEFT)

    # Divider
    add_rect(slide, Inches(6.1), Inches(1.7),
             Inches(6.5), Inches(0.05), theme["accent"])

    # Bullets
    top = Inches(1.95)
    for bullet in bullets[:5]:
        add_rect(slide, Inches(6.1), top + Inches(0.18),
                 Inches(0.07), Inches(0.35),
                 theme["accent"], radius=20000)
        add_text(slide, bullet,
                 Inches(6.4), top, Inches(6.6), Inches(0.72),
                 Pt(18), theme["bullet_color"],
                 align=PP_ALIGN.LEFT)
        top += Inches(0.92)

    # Bottom wave
    add_wave(slide, theme["accent"], top_ratio=0.93)


# ─── LAYOUT B — Full image background + text overlay ──────────────

def build_layout_b(prs, heading, bullets, theme, keyword, is_premium=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    if is_premium:
        img = fetch_unsplash_image(keyword)
        if img:
            add_image(slide, img, 0, 0, SLIDE_W, SLIDE_H)

    # Bottom dark panel for text
    add_rect(slide, 0, Inches(3.0), SLIDE_W, Inches(4.5),
             RGBColor(0x10, 0x10, 0x10) if is_premium else theme["accent"])

    # Wave transition between image and text
    add_wave(slide, RGBColor(0x10, 0x10, 0x10)
             if is_premium else theme["accent"],
             top_ratio=0.38)

    # Top accent
    add_rect(slide, 0, 0, SLIDE_W, Inches(0.12), theme["accent"])

    # Heading
    add_text(slide, heading,
             Inches(0.8), Inches(3.2), Inches(11.5), Inches(1.0),
             Pt(30), RGBColor(0xFF, 0xFF, 0xFF),
             bold=True, align=PP_ALIGN.LEFT)

    # Bullets
    top = Inches(4.3)
    for bullet in bullets[:4]:
        add_text(slide, f"▸  {bullet}",
                 Inches(1.0), top, Inches(11.0), Inches(0.65),
                 Pt(18), RGBColor(0xEE, 0xEE, 0xEE),
                 align=PP_ALIGN.LEFT)
        top += Inches(0.72)


# ─── LAYOUT C — Rounded card bullets + side image ─────────────────

def build_layout_c(prs, heading, bullets, theme, keyword, is_premium=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    # Top bar
    add_rect(slide, 0, 0, SLIDE_W, Inches(0.12), theme["accent"])

    # Heading
    add_text(slide, heading,
             Inches(0.6), Inches(0.22), Inches(8.5), Inches(1.0),
             Pt(28), theme["heading_color"],
             bold=True, align=PP_ALIGN.LEFT)

    if is_premium:
        img = fetch_unsplash_image(keyword)
        if img:
            rounded = make_rounded_image(img, radius=80)
            add_image(slide, rounded,
                      Inches(9.6), Inches(0.3),
                      Inches(3.4), Inches(3.2))

    # Rounded bullet cards
    top = Inches(1.45)
    card_colors = [
        theme["accent"],
        theme["accent2"],
        theme["card_bg"],
        theme["accent"],
        theme["accent2"],
    ]
    for i, bullet in enumerate(bullets[:5]):
        c = card_colors[i % len(card_colors)]
        add_rect(slide, Inches(0.5), top,
                 Inches(8.8), Inches(0.82),
                 c, radius=35000)
        txt_color = (RGBColor(0xFF, 0xFF, 0xFF)
                     if c != theme["card_bg"]
                     else theme["bullet_color"])
        add_text(slide, f"   {bullet}",
                 Inches(0.6), top + Inches(0.1),
                 Inches(8.6), Inches(0.65),
                 Pt(17), txt_color,
                 align=PP_ALIGN.LEFT)
        top += Inches(1.0)

    # Bottom wave
    add_wave(slide, theme["accent"], top_ratio=0.93)


# ─── LAYOUT D — Bold accent color full slide ──────────────────────

def build_layout_d(prs, heading, bullets, theme, keyword, is_premium=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["accent"])

    # Top white bar
    add_rect(slide, 0, 0, SLIDE_W, Inches(0.1),
             RGBColor(0xFF, 0xFF, 0xFF))

    # Heading
    add_text(slide, heading,
             Inches(1.0), Inches(0.5), Inches(11.0), Inches(1.5),
             Pt(34), RGBColor(0xFF, 0xFF, 0xFF),
             bold=True, align=PP_ALIGN.CENTER)

    # White divider
    add_rect(slide, Inches(3.5), Inches(2.1),
             Inches(6.0), Inches(0.06),
             RGBColor(0xFF, 0xFF, 0xFF))

    # Bullets centered white
    top = Inches(2.4)
    for bullet in bullets[:4]:
        add_rect(slide, Inches(1.5), top,
                 Inches(10.0), Inches(0.78),
                 RGBColor(0xFF, 0xFF, 0xFF), radius=30000)
        add_text(slide, f"  {bullet}",
                 Inches(1.7), top + Inches(0.1),
                 Inches(9.6), Inches(0.62),
                 Pt(18), theme["accent"],
                 bold=True, align=PP_ALIGN.LEFT)
        top += Inches(0.98)

    if is_premium:
        img = fetch_unsplash_image(keyword)
        if img:
            rounded = make_rounded_image(img, radius=60)
            add_image(slide, rounded,
                      Inches(10.5), Inches(5.6),
                      Inches(2.5), Inches(1.7))

    # Bottom wave white
    add_wave(slide, RGBColor(0xFF, 0xFF, 0xFF), top_ratio=0.91)


# ─── LAYOUT E — Number cards (like image 1 you sent) ──────────────

def build_layout_e(prs, heading, bullets, theme, keyword, is_premium=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    # Top bar
    add_rect(slide, 0, 0, SLIDE_W, Inches(0.12), theme["accent"])

    # Heading centered
    add_text(slide, heading,
             Inches(0.5), Inches(0.2), Inches(12.0), Inches(0.9),
             Pt(28), theme["heading_color"],
             bold=True, align=PP_ALIGN.CENTER)

    # Number cards
    num_bullets = min(len(bullets), 4)
    card_width = Inches(11.8 / num_bullets) if num_bullets > 0 else Inches(3)
    card_colors = [
        theme["accent"],
        theme["accent2"],
        RGBColor(0x27, 0xAE, 0x60),
        RGBColor(0xE6, 0x7E, 0x22),
    ]

    for i, bullet in enumerate(bullets[:4]):
        left = Inches(0.6) + (card_width + Inches(0.2)) * i
        c = card_colors[i % len(card_colors)]

        # Card background rounded
        add_rect(slide, left, Inches(1.4),
                 card_width, Inches(5.6),
                 c, radius=25000)

        # Number circle
        add_rect(slide, left + Inches(0.3), Inches(1.7),
                 Inches(0.9), Inches(0.9),
                 RGBColor(0xFF, 0xFF, 0xFF), radius=50000)

        # Number text
        add_text(slide, str(i + 1),
                 left + Inches(0.32), Inches(1.72),
                 Inches(0.86), Inches(0.78),
                 Pt(22), c,
                 bold=True, align=PP_ALIGN.CENTER)

        # Bullet text
        add_text(slide, bullet,
                 left + Inches(0.15), Inches(2.9),
                 card_width - Inches(0.3), Inches(3.5),
                 Pt(16), RGBColor(0xFF, 0xFF, 0xFF),
                 align=PP_ALIGN.CENTER)

    # Bottom wave
    add_wave(slide, theme["accent"], top_ratio=0.93)


# ─── THANK YOU SLIDE ──────────────────────────────────────────────

def build_thankyou_slide(prs, theme, is_premium=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    # Top and bottom bars
    add_rect(slide, 0, 0, SLIDE_W, Inches(0.15), theme["accent"])
    add_rect(slide, 0, Inches(7.35), SLIDE_W, Inches(0.15), theme["accent"])

    # Wave decoration
    add_wave(slide, theme["card_bg"], top_ratio=0.55)

    # Soft rounded background circle
    add_rect(slide, Inches(4.8), Inches(1.2),
             Inches(3.5), Inches(3.5),
             theme["card_bg"], radius=50000)

    # Thank you text
    add_text(slide, "Thank You! 🙏",
             Inches(1.0), Inches(2.0), Inches(11.0), Inches(1.8),
             Pt(52), theme["title_color"],
             bold=True, align=PP_ALIGN.CENTER)

    add_text(slide, "Generated by SlideBot",
             Inches(1.0), Inches(4.3), Inches(11.0), Inches(0.6),
             Pt(16), theme["bullet_color"],
             align=PP_ALIGN.CENTER)


# ─── MAIN BUILD FUNCTION ──────────────────────────────────────────

PREMIUM_LAYOUTS = [
    build_layout_a,
    build_layout_b,
    build_layout_c,
    build_layout_d,
    build_layout_e,
]

FREE_LAYOUTS = [
    build_layout_c,
    build_layout_d,
    build_layout_e,
]

def build_presentation(slide_data: dict, theme_name: str = "classic",
                       premium: bool = False) -> str:
    theme = THEMES.get(theme_name, THEMES["classic"])

    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    slides = slide_data.get("slides", [])
    title = slide_data.get("title", "My Presentation")

    first_keyword = slides[0].get("image_keyword", "business") if slides else "business"
    build_title_slide(prs, title, theme, first_keyword, is_premium=premium)

    layouts = PREMIUM_LAYOUTS if premium else FREE_LAYOUTS
    content_slides = slides[1:-1] if len(slides) > 2 else slides

    for idx, slide in enumerate(content_slides):
        heading = slide.get("heading", "")
        bullets = slide.get("bullets", [])
        keyword = slide.get("image_keyword", "business")
        layout_fn = layouts[idx % len(layouts)]
        layout_fn(prs, heading, bullets, theme, keyword, is_premium=premium)

    build_thankyou_slide(prs, theme, is_premium=premium)

    filename = f"slidebot_{uuid.uuid4().hex[:8]}.pptx"
    filepath = os.path.join("outputs", filename)
    os.makedirs("outputs", exist_ok=True)
    prs.save(filepath)
    return filepath

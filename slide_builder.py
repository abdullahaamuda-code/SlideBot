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
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY")

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


def fetch_pixabay_image(keyword: str):
    try:
        if not PIXABAY_KEY:
            print("❌ No Pixabay key found")
            return None

        url = "https://pixabay.com/api/"
        params = {
            "key": PIXABAY_KEY,
            "q": keyword,
            "image_type": "photo",
            "orientation": "horizontal",
            "safesearch": "true",
            "per_page": 3,
        }

        print(f"🖼 Fetching Pixabay image for: {keyword}")
        response = requests.get(url, params=params, timeout=15)
        print(f"🖼 Pixabay status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            hits = data.get("hits", [])
            if not hits:
                print("❌ Pixabay returned no hits")
                return None

            hit = random.choice(hits)
            img_url = hit.get("largeImageURL") or hit.get("webformatURL")
            if not img_url:
                print("❌ Pixabay hit missing image URL")
                return None

            print(f"🖼 Got Pixabay image URL: {img_url[:60]}")
            img_response = requests.get(img_url, timeout=15)
            print(f"🖼 Pixabay image download status: {img_response.status_code}")
            if img_response.status_code == 200:
                print("✅ Pixabay image fetched successfully")
                return BytesIO(img_response.content)

        else:
            print(f"❌ Pixabay error: {response.text[:200]}")

    except requests.Timeout:
        print(f"❌ Pixabay timeout for '{keyword}'")
    except Exception as e:
        print(f"❌ Pixabay failed for '{keyword}': {e}")

    return None


def fetch_image(keyword: str):
    """
    Try Unsplash first, then fall back to Pixabay.
    """
    img = fetch_unsplash_image(keyword)
    if img:
        return img

    print("🔁 Falling back to Pixabay...")
    img = fetch_pixabay_image(keyword)
    if img:
        return img

    print("❌ All image providers failed")
    return None


# ─── ENHANCED HELPERS ─────────────────────────────────────────────
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


def add_corner_bars(slide, theme):
    # Short bar at top-left
    add_rect(
        slide,
        Inches(0.5),
        Inches(0.2),
        Inches(3.0),
        Inches(0.08),
        theme["accent"],
    )

    # Vertical bar on left
    add_rect(
        slide,
        Inches(0.5),
        Inches(0.6),
        Inches(0.08),
        Inches(2.5),
        theme["accent2"],
    )


# ─── TITLE SLIDE — Premium hero layout ────────────────────────────
def build_title_slide(prs, title, theme, keyword="abstract"):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    img = fetch_image(keyword)
    if img:
        add_image_to_slide(slide, img, 0, 0, SLIDE_W, SLIDE_H)
        overlay = add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, RGBColor(0x00, 0x00, 0x00))
        overlay.fill.transparency = 0.4

    # Gradient-like effect with multiple accent bars
    add_rect(slide, 0, Inches(5.5), SLIDE_W, Inches(2.0), theme["accent"], transparency=0.15)
    add_rect(slide, 0, Inches(6.2), SLIDE_W, Inches(1.3), theme["accent"], transparency=0.3)

    # Main title with premium spacing
    add_text(
        slide,
        title,
        Inches(0.8),
        Inches(2.0),
        Inches(11.73),
        Inches(2.5),
        Pt(52),
        theme["title_color"],
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


# ─── LAYOUT A — Split screen with rounded image and cards ─────────
def build_layout_a(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    # NEW: corner design instead of full-width top bar
    add_corner_bars(slide, theme)

    # Left image with rounded corners and subtle shadow effect
    img = fetch_image(keyword)
    if img:
        rounded = make_rounded_image(img, radius=60)
        add_image_to_slide(
            slide,
            rounded,
            Inches(0.3),
            Inches(0.3),
            Inches(5.2),
            Inches(6.9),
        )
    else:
        add_rect(
            slide,
            Inches(0.3),
            Inches(0.3),
            Inches(5.2),
            Inches(6.9),
            theme["card_bg"],
            radius=60,
        )

    # Right content area with better spacing
    heading_box = add_text(
        slide,
        heading,
        Inches(5.9),
        Inches(0.5),
        Inches(7.1),
        Inches(1.3),
        Pt(32),
        theme["heading_color"],
        bold=True,
        align=PP_ALIGN.LEFT,
    )

    # Decorative line under heading
    add_rect(
        slide,
        Inches(5.9),
        Inches(1.9),
        Inches(2.5),
        Inches(0.06),
        theme["accent"],
        radius=30000,
    )

    # Enhanced bullet points with custom icons
    top = Inches(2.3)
    for i, bullet in enumerate(bullets[:5]):
        add_rect(
            slide,
            Inches(5.9),
            top + Inches(0.12),
            Inches(0.12),
            Inches(0.12),
            theme["accent"],
            radius=30000,
        )

        add_text(
            slide,
            bullet,
            Inches(6.2),
            top,
            Inches(6.8),
            Inches(0.65),
            Pt(17),
            theme["bullet_color"],
            align=PP_ALIGN.LEFT,
            wrap=True,
        )
        top += Inches(0.85)

    # Bottom accent bar
    add_rect(slide, 0, Inches(7.4), SLIDE_W, Inches(0.1), theme["accent"])


# ─── LAYOUT B — Full bleed with modern overlay ────────────────────
def build_layout_b(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    img = fetch_image(keyword)
    if img:
        add_image_to_slide(slide, img, 0, 0, SLIDE_W, SLIDE_H)

    # Gradient-like overlay (semi-transparent)
    add_rect(slide, 0, Inches(2.8), SLIDE_W, Inches(4.7), theme["accent"], transparency=0.7)
    add_rect(slide, 0, Inches(3.0), SLIDE_W, Inches(4.5), RGBColor(0x00, 0x00, 0x00), transparency=0.3)

    # Top accent bar
    add_rect(slide, 0, 0, SLIDE_W, Inches(0.12), theme["accent"])

    # Large heading with letter spacing effect
    add_text(
        slide,
        heading,
        Inches(0.8),
        Inches(3.1),
        Inches(11.73),
        Inches(1.2),
        Pt(36),
        theme["heading_color"],
        bold=True,
        align=PP_ALIGN.LEFT,
    )

    # Subtitle/divider
    add_rect(slide, Inches(0.8), Inches(4.3), Inches(3.0), Inches(0.04), RGBColor(0xFF, 0xFF, 0xFF))

    # Bullets with modern chevron style
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
    add_rect(slide, Inches(6.165), Inches(7.25), Inches(1.0), Inches(0.08), RGBColor(0xFF, 0xFF, 0xFF), radius=30000)


# ─── LAYOUT C — Card-style grid layout ────────────────────────────
def build_layout_c(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    # Top decorative bar
    add_rect(slide, 0, 0, SLIDE_W, Inches(0.1), theme["accent"])

    # Heading with modern placement
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

    # Right side image with rounded corners
    img = fetch_image(keyword)
    if img:
        rounded = make_rounded_image(img, radius=50)
        add_image_to_slide(slide, rounded, Inches(9.3), Inches(0.25), Inches(3.8), Inches(3.8))

    # Card-style bullets with alternating colors
    top = Inches(1.5)
    card_colors = [theme["accent"], theme["accent2"], theme["card_bg"], theme["light_accent"]]

    for i, bullet in enumerate(bullets[:5]):
        card_color = card_colors[i % len(card_colors)]
        is_dark = card_color in [theme["accent"], theme["accent2"]]

        # Card background with rounded corners
        add_rect(slide, Inches(0.5), top, Inches(8.5), Inches(0.82), card_color, radius=20000)

        txt_color = RGBColor(0xFF, 0xFF, 0xFF) if is_dark else theme["bullet_color"]

        # Add bullet number/icon
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

    # Bottom bar
    add_rect(slide, 0, Inches(7.4), SLIDE_W, Inches(0.1), theme["accent"])


# ─── LAYOUT D — Impact quote / statistic style ────────────────────
def build_layout_d(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Use the normal background color so text is always readable
    set_bg(slide, theme["bg"])

    # Decorative elements (can stay white, they are just shapes)
    add_rect(
        slide,
        Inches(1.0),
        Inches(0.5),
        Inches(0.12),
        Inches(1.2),
        RGBColor(0xFF, 0xFF, 0xFF),
        transparency=0.3,
    )
    add_rect(
        slide,
        Inches(11.5),
        Inches(5.8),
        Inches(0.12),
        Inches(1.2),
        RGBColor(0xFF, 0xFF, 0xFF),
        transparency=0.3,
    )

    # Large quote/heading – use theme heading color
    add_text(
        slide,
        heading,
        Inches(1.5),
        Inches(0.8),
        Inches(10.33),
        Inches(2.0),
        Pt(38),
        theme["heading_color"],
        bold=True,
        align=PP_ALIGN.CENTER,
    )

    # Divider line (can stay white, it's decorative)
    add_rect(
        slide,
        Inches(5.0),
        Inches(2.9),
        Inches(3.33),
        Inches(0.05),
        RGBColor(0xFF, 0xFF, 0xFF),
    )

    # Key points as centered statements – use theme bullet color
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
            theme["bullet_color"],
            align=PP_ALIGN.CENTER,
        )
        top += Inches(0.82)

    # Small decorative image
    img = fetch_image(keyword)
    if img:
        rounded = make_rounded_image(img, radius=30)
        add_image_to_slide(slide, rounded, Inches(10.8), Inches(5.8), Inches(2.2), Inches(1.5))


# ─── LAYOUT E — Vertical timeline / process style ─────────────────
def build_layout_e(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    # Top bar
    add_rect(slide, 0, 0, SLIDE_W, Inches(0.1), theme["accent"])

    # Heading
    add_text(
        slide,
        heading,
        Inches(0.7),
        Inches(0.4),
        Inches(11.73),
        Inches(1.0),
        Pt(30),
        theme["heading_color"],
        bold=True,
        align=PP_ALIGN.LEFT,
    )

    # Timeline line
    add_rect(slide, Inches(1.2), Inches(1.6), Inches(0.08), Inches(5.5), theme["light_accent"], radius=30000)

    # Bullets as timeline nodes
    top = Inches(1.6)
    for i, bullet in enumerate(bullets[:5]):
        # Node circle
        add_rect(slide, Inches(1.16), top + Inches(0.15), Inches(0.16), Inches(0.16), theme["accent"], radius=30000)

        # Year/step indicator
        add_text(
            slide,
            f"STEP 0{i+1}",
            Inches(1.6),
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
            Inches(3.2),
            top,
            Inches(9.5),
            Inches(0.7),
            Pt(16),
            theme["bullet_color"],
            align=PP_ALIGN.LEFT,
            wrap=True,
        )
        top += Inches(1.05)

    # Bottom bar
    add_rect(slide, 0, Inches(7.4), SLIDE_W, Inches(0.1), theme["accent"])


# ─── LAYOUT F — Two-column comparison ─────────────────────────────
def build_layout_f(prs, heading, bullets, theme, keyword):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    # Top accent
    add_rect(slide, 0, 0, SLIDE_W, Inches(0.1), theme["accent"])

    # Main heading
    add_text(
        slide,
        heading,
        Inches(0.7),
        Inches(0.4),
        Inches(11.73),
        Inches(0.9),
        Pt(32),
        theme["heading_color"],
        bold=True,
        align=PP_ALIGN.LEFT,
    )

    # Split bullets into two columns
    mid = len(bullets) // 2
    col1 = bullets[:mid]
    col2 = bullets[mid:]

    # Left column
    left_top = Inches(1.6)
    for bullet in col1[:4]:
        add_rect(slide, Inches(0.7), left_top + Inches(0.12), Inches(0.1), Inches(0.1), theme["accent"], radius=30000)
        add_text(
            slide,
            bullet,
            Inches(1.0),
            left_top,
            Inches(5.0),
            Inches(0.65),
            Pt(16),
            theme["bullet_color"],
            align=PP_ALIGN.LEFT,
        )
        left_top += Inches(0.85)

    # Right column with image
    img = fetch_image(keyword)
    if img:
        rounded = make_rounded_image(img, radius=50)
        add_image_to_slide(slide, rounded, Inches(7.0), Inches(1.6), Inches(5.8), Inches(4.5))

    # Right column bullets if space
    right_top = Inches(1.6)
    for bullet in col2[:3]:
        add_rect(slide, Inches(7.0), right_top + Inches(0.12), Inches(0.1), Inches(0.1), theme["accent"], radius=30000)
        add_text(
            slide,
            bullet,
            Inches(7.3),
            right_top,
            Inches(5.5),
            Inches(0.65),
            Pt(16),
            theme["bullet_color"],
            align=PP_ALIGN.LEFT,
        )
        right_top += Inches(0.85)

    # Bottom bar
    add_rect(slide, 0, Inches(7.4), SLIDE_W, Inches(0.1), theme["accent"])


# ─── THANK YOU SLIDE — Premium closing ────────────────────────────
def build_thankyou_slide(prs, theme, is_premium=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, theme["bg"])

    # Top and bottom accent bars
    add_rect(slide, 0, 0, SLIDE_W, Inches(0.1), theme["accent"])
    add_rect(slide, 0, Inches(7.4), SLIDE_W, Inches(0.1), theme["accent"])

    # Decorative circle element
    add_rect(slide, Inches(5.0), Inches(1.8), Inches(3.33), Inches(3.33), theme["light_accent"], radius=50000)

    # Main thank you text
    add_text(
        slide,
        "Thank You",
        Inches(1.0),
        Inches(2.3),
        Inches(11.33),
        Inches(1.5),
        Pt(54),
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
        Pt(18),
        theme["bullet_color"],
        align=PP_ALIGN.CENTER,
        italic=True,
    )


# ─── MAIN BUILD FUNCTION ──────────────────────────────────────────
LAYOUTS = [
    build_layout_a,
    build_layout_b,
    build_layout_c,
    build_layout_d,
    build_layout_e,
    build_layout_f,
]


def build_presentation(slide_data: dict, theme_name: str = "classic", is_premium: bool = False) -> str:
    theme = THEMES.get(theme_name, THEMES["classic"])

    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    slides = slide_data.get("slides", [])
    title = slide_data.get("title", "My Presentation")

    first_keyword = slides[0].get("image_keyword", "business") if slides else "business"
    build_title_slide(prs, title, theme, first_keyword)

    content_slides = slides[1:-1] if len(slides) > 2 else slides
    for idx, slide in enumerate(content_slides):
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

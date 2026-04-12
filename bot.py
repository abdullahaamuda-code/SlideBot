import os
import io
import asyncio
import logging
import trafilatura
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from ai_engine import generate_slide_content, generate_from_text
from slide_builder import build_presentation
from slide_builder_magazine import build_magazine
from database import (
    get_or_create_user, can_generate, increment_usage,
    is_premium, activate_premium, revoke_premium,
    get_premium_users, get_total_stats,
    can_use_url, can_use_file,
    increment_url_usage, increment_file_usage,
    get_user_theme, save_user_theme,
    get_today_usage,
    get_user_pack, save_user_pack,
    get_user_accent, save_user_accent,
)

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID  = os.getenv("ADMIN_TELEGRAM_ID")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
#  COLOR SYSTEM
# ─────────────────────────────────────────────────────────────────
COLOR_PRESETS = {
    "navy":   "1E2761",
    "blue":   "1E2761",
    "red":    "C0392B",
    "crimson":"C0392B",
    "green":  "2C5F2D",
    "emerald":"2C5F2D",
    "purple": "6B2D8B",
    "violet": "6B2D8B",
    "orange": "FF6B35",
    "amber":  "FF6B35",
    "gold":   "B7790F",
    "yellow": "B7790F",
    "teal":   "028090",
    "cyan":   "028090",
    "pink":   "E94C7D",
    "rose":   "E94C7D",
    "black":  "212121",
    "white":  "F5F5F5",
}


def normalize_color(raw: str) -> str:
    """Turn 'purple' or '#6B2D8B' or '6B2D8B' into a clean 6-char hex string."""
    c = raw.strip().lower().lstrip("#")
    if c in COLOR_PRESETS:
        return COLOR_PRESETS[c]
    if len(c) == 6:
        try:
            int(c, 16)
            return c.upper()
        except ValueError:
            pass
    return "1E2761"  # default navy


def is_admin(uid: str) -> bool:
    return str(uid) == str(ADMIN_ID)


# ─────────────────────────────────────────────────────────────────
#  KEYBOARDS
# ─────────────────────────────────────────────────────────────────
def slide_count_keyboard(uid: str) -> InlineKeyboardMarkup:
    premium    = is_premium(uid)
    max_slides = 30 if premium else 8
    options    = [5, 8, 10, 12, 15, 20, 25, 30]
    keyboard, row = [], []
    for n in options:
        if n > max_slides:
            continue
        row.append(InlineKeyboardButton(str(n), callback_data=f"slides_{n}"))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)


def pack_keyboard() -> InlineKeyboardMarkup:
    """Pack picker — premium only."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏢 Executive", callback_data="pack_executive"),
            InlineKeyboardButton("📰 Magazine",  callback_data="pack_magazine"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ])


def color_keyboard() -> InlineKeyboardMarkup:
    """8 preset colors + skip — premium only."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔵 Navy",   callback_data="color_navy"),
            InlineKeyboardButton("🔴 Red",    callback_data="color_red"),
            InlineKeyboardButton("🟢 Green",  callback_data="color_green"),
            InlineKeyboardButton("🟣 Purple", callback_data="color_purple"),
        ],
        [
            InlineKeyboardButton("🟠 Orange", callback_data="color_orange"),
            InlineKeyboardButton("🟡 Gold",   callback_data="color_gold"),
            InlineKeyboardButton("🩵 Teal",   callback_data="color_teal"),
            InlineKeyboardButton("🩷 Pink",   callback_data="color_pink"),
        ],
        [InlineKeyboardButton("⏭️ Skip — use my saved color", callback_data="color_skip")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ])


def free_style_keyboard() -> InlineKeyboardMarkup:
    """
    Free users: Classic + Dark unlocked.
    Executive + Magazine shown but locked — tapping shows a teaser.
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Classic", callback_data="theme_classic"),
            InlineKeyboardButton("✅ Dark",    callback_data="theme_dark"),
        ],
        [
            InlineKeyboardButton("🔒 Executive Pack", callback_data="locked_executive"),
            InlineKeyboardButton("🔒 Magazine Pack",  callback_data="locked_magazine"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ])


# ─────────────────────────────────────────────────────────────────
#  /start
# ─────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid  = str(user.id)
    get_or_create_user(uid, str(user.username or user.first_name))
    premium = is_premium(uid)

    keyboard = [
        [InlineKeyboardButton("📖 How to use",         callback_data="show_help")],
        [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="show_upgrade")],
        [InlineKeyboardButton("📊 My Status",          callback_data="show_status")],
    ]
    await update.message.reply_text(
        f"✨ *Hey {user.first_name}!* ✨\n\n"
        "Welcome to *SlideBot* — your AI presentation designer.\n\n"
        "*Just type any topic* and I'll create a professional PowerPoint in seconds!\n\n"
        "📝 *Try:*\n"
        "• _Climate change in Africa_\n"
        "• _My business pitch_\n"
        "• _Digital marketing trends_\n\n"
        "📎 Or send me a *URL, PDF, or Word doc* to convert!\n\n"
        + ("💎 *Premium active* — Executive & Magazine packs unlocked!"
           if premium else
           "🎨 Free plan — Classic & Dark available. /upgrade for more!"),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
#  /color  — set custom accent (premium only)
# ─────────────────────────────────────────────────────────────────
async def color_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid  = str(user.id)
    get_or_create_user(uid, str(user.username or user.first_name))

    if not is_premium(uid):
        await update.message.reply_text(
            "🔒 *Custom colors are a Premium feature.*\n\n"
            "Type /upgrade to unlock all packs and colors! 💎",
            parse_mode="Markdown"
        )
        return

    if not context.args:
        saved = get_user_accent(uid) or "1E2761"
        await update.message.reply_text(
            "🎨 *Set your accent color*\n\n"
            f"Current saved color: `#{saved}`\n\n"
            "*Usage:*\n"
            "`/color purple` — use a color name\n"
            "`/color #6B2D8B` — use a hex code\n\n"
            "*Available names:*\n"
            "navy, red, green, purple, orange, gold, teal, pink, black",
            parse_mode="Markdown"
        )
        return

    raw     = " ".join(context.args)
    hex_val = normalize_color(raw)
    save_user_accent(uid, hex_val)

    await update.message.reply_text(
        f"✅ *Accent color saved!*\n\n"
        f"Color: `#{hex_val}`\n\n"
        "This will be used as your accent color in all future presentations.",
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
#  /help
# ─────────────────────────────────────────────────────────────────
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    get_or_create_user(uid, str(update.effective_user.username or update.effective_user.first_name))
    premium = is_premium(uid)

    text = (
        "📚 *How SlideBot Works*\n\n"
        "*1.* Type any topic or paste a URL\n"
        "*2.* Choose number of slides\n"
        "*3.* Pick your style & color\n"
        "*4.* Download your PPTX!\n\n"
        "*✨ Features:*\n"
        "• URL → Slides\n"
        "• PDF / Word → Slides\n"
        "• Executive & Magazine packs\n"
        "• Custom accent colors (/color)\n\n"
    )
    if premium:
        text += "💎 *Your plan: Premium*\n• Unlimited decks\n• Up to 30 slides\n• All packs & colors\n• Priority support"
    else:
        text += "📊 *Your plan: Free*\n• 2 decks/day\n• Up to 8 slides\n• Classic & Dark\n\nType /upgrade for Premium! 💎"

    await update.message.reply_text(text, parse_mode="Markdown")


# ─────────────────────────────────────────────────────────────────
#  /status
# ─────────────────────────────────────────────────────────────────
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    get_or_create_user(uid, str(update.effective_user.username or update.effective_user.first_name))
    premium   = is_premium(uid)
    used      = get_today_usage(uid)
    pack      = get_user_pack(uid)
    accent    = get_user_accent(uid) or "1E2761"
    remaining = "Unlimited" if premium else max(0, 2 - used)

    await update.message.reply_text(
        f"*Your SlideBot Status*\n\n"
        f"📌 *Plan:* {'💎 Premium' if premium else '📊 Free'}\n"
        f"📦 *Pack:* {pack.title()}\n"
        f"🎨 *Accent color:* `#{accent}`\n"
        f"✅ *Used today:* {'∞' if premium else used}\n"
        f"🎯 *Remaining today:* {remaining}\n\n"
        f"Type /upgrade to go Premium 💎",
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
#  /upgrade
# ─────────────────────────────────────────────────────────────────
async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💎 *SlideBot Premium — ₦500/month*\n\n"
        "*What you unlock:*\n"
        "✅ Unlimited presentations\n"
        "✅ Up to 30 slides per deck\n"
        "✅ 🏢 Executive Pack — dark panels, numbered cards, full-bleed images\n"
        "✅ 📰 Magazine Pack — editorial layouts, pull quotes, bold typography\n"
        "✅ Custom accent colors — type any color you want\n"
        "✅ Unlimited URL → Slides\n"
        "✅ Unlimited PDF/Word → Slides\n"
        "✅ No watermarks\n"
        "✅ Priority support\n\n"
        "*How to pay:*\n"
        "Bank: MONIEPOINT MFB\n"
        "Name: Abdullah Abdulgafar-Amuda\n"
        "Account: 8169936326\n\n"
        "After payment, send your receipt screenshot here, then type /paid 🙏",
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
#  /paid
# ─────────────────────────────────────────────────────────────────
async def paid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user     = update.effective_user
    uid      = str(user.id)
    username = user.username or user.first_name
    try:
        await context.bot.send_message(
            chat_id=int(ADMIN_ID),
            text=(
                f"💰 *Payment Claim*\n\n"
                f"👤 User: @{username}\n"
                f"🆔 ID: `{uid}`\n\n"
                f"To activate: `/activate {uid}`"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Admin notify error: {e}")

    await update.message.reply_text(
        "🙏 *Thank you for your payment!*\n\n"
        "We've received your claim and will verify shortly.\n"
        "You'll be activated within the hour — we'll notify you here. ✅",
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
#  ADMIN COMMANDS
# ─────────────────────────────────────────────────────────────────
async def activate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(str(update.effective_user.id)):
        await update.message.reply_text("❌ Not authorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /activate <telegram_id>")
        return
    target_id = context.args[0]
    if activate_premium(target_id, str(update.effective_user.id)):
        await update.message.reply_text(f"✅ *User {target_id} is now PREMIUM!*", parse_mode="Markdown")
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=(
                    "🎉 *CONGRATULATIONS!* 🎉\n\n"
                    "You've been upgraded to *Premium*!\n\n"
                    "✨ *You now have:*\n"
                    "• Unlimited presentations\n"
                    "• Up to 30 slides per deck\n"
                    "• 🏢 Executive Pack\n"
                    "• 📰 Magazine Pack\n"
                    "• Custom accent colors — try `/color purple`\n\n"
                    "Type any topic to create your first Premium deck! 🚀"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Could not notify user {target_id}: {e}")
    else:
        await update.message.reply_text(f"❌ Could not activate {target_id}. User may not exist.")


async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(str(update.effective_user.id)):
        await update.message.reply_text("❌ Not authorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /revoke <telegram_id>")
        return
    target_id = context.args[0]
    if revoke_premium(target_id):
        await update.message.reply_text(f"✅ Premium revoked for {target_id}")
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text="Your Premium access has been revoked. Contact support for more info."
            )
        except Exception:
            pass
    else:
        await update.message.reply_text(f"❌ User {target_id} not found")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(str(update.effective_user.id)):
        await update.message.reply_text("❌ Not authorized.")
        return
    s = get_total_stats()
    await update.message.reply_text(
        f"📊 *SlideBot Statistics*\n\n"
        f"👥 Total users: {s['total_users']}\n"
        f"💎 Premium users: {s['premium_users']}\n"
        f"📋 Free users: {s['free_users']}\n"
        f"🎨 Total presentations: {s['total_slides_generated']}",
        parse_mode="Markdown"
    )


async def premiumlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(str(update.effective_user.id)):
        await update.message.reply_text("❌ Not authorized.")
        return
    users = get_premium_users()
    if not users:
        await update.message.reply_text("No premium users yet.")
        return
    msg = "💎 *Premium Users:*\n\n"
    for uid, u in users.items():
        pack   = u.get("preferred_pack", "executive")
        msg   += f"• @{u['username']} — `{uid}` — {pack}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")


# ─────────────────────────────────────────────────────────────────
#  CALLBACK: slide count selected
# ─────────────────────────────────────────────────────────────────
async def slide_count_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid        = str(query.from_user.id)
    num_slides = int(query.data.replace("slides_", ""))
    context.user_data["pending_slides"] = num_slides

    if is_premium(uid):
        # Premium: pick pack first
        await query.edit_message_text(
            "📦 *Choose your presentation pack:*\n\n"
            "🏢 *Executive* — dark panels, numbered cards, full-bleed images, timeline layouts. "
            "Clean and professional.\n\n"
            "📰 *Magazine* — editorial pull quotes, hero image strips, bold serif headings. "
            "Modern and eye-catching.",
            reply_markup=pack_keyboard(),
            parse_mode="Markdown"
        )
    else:
        # Free: style picker (Classic/Dark + locked previews)
        await query.edit_message_text(
            "🎨 *Choose your slide style:*\n\n"
            "Tap a locked pack to see what it looks like 👇",
            reply_markup=free_style_keyboard(),
            parse_mode="Markdown"
        )


# ─────────────────────────────────────────────────────────────────
#  CALLBACK: pack selected (premium)
# ─────────────────────────────────────────────────────────────────
async def pack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid  = str(query.from_user.id)
    pack = query.data.replace("pack_", "")

    context.user_data["pending_pack"] = pack
    save_user_pack(uid, pack)

    saved_accent = get_user_accent(uid) or "1E2761"

    await query.edit_message_text(
        f"🎨 *Choose your accent color:*\n\n"
        f"Your saved color: `#{saved_accent}`\n\n"
        f"Pick one below, or tap *Skip* to use your saved color.\n\n"
        f"_You can also type_ `/color purple` _or_ `/color #FF5733` _anytime to change it._",
        reply_markup=color_keyboard(),
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
#  CALLBACK: color selected (premium)
# ─────────────────────────────────────────────────────────────────
async def color_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)

    if query.data == "color_skip":
        accent = get_user_accent(uid) or "1E2761"
        context.user_data["pending_color"] = accent
    else:
        color_name = query.data.replace("color_", "")
        hex_val    = normalize_color(color_name)
        context.user_data["pending_color"] = hex_val
        save_user_accent(uid, hex_val)

    # All info collected — generate
    if "pending_topic" in context.user_data and "pending_slides" in context.user_data:
        topic      = context.user_data.pop("pending_topic")
        num_slides = context.user_data.pop("pending_slides")
        pack       = context.user_data.pop("pending_pack", get_user_pack(uid))
        color      = context.user_data.pop("pending_color", "1E2761")
        raw_text   = context.user_data.pop("pending_raw_text", None)

        await query.edit_message_text(
            f"✅ *Pack: {pack.title()} · Color: #{color}*\n\n"
            f"🎯 Generating your {num_slides}-slide deck...",
            parse_mode="Markdown"
        )
        await start_generation(
            query, context, topic, num_slides,
            pack=pack, color=color, raw_text=raw_text
        )
    else:
        await query.edit_message_text(
            "✅ *Color saved!*\n\nSend me a topic to create your next presentation.",
            parse_mode="Markdown"
        )


# ─────────────────────────────────────────────────────────────────
#  CALLBACK: theme selected (free users — Classic / Dark)
# ─────────────────────────────────────────────────────────────────
async def theme_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid        = str(query.from_user.id)
    theme_name = query.data.replace("theme_", "")

    context.user_data["theme"] = theme_name
    save_user_theme(uid, theme_name)

    if "pending_topic" in context.user_data and "pending_slides" in context.user_data:
        topic      = context.user_data.pop("pending_topic")
        num_slides = context.user_data.pop("pending_slides")
        raw_text   = context.user_data.pop("pending_raw_text", None)

        await query.edit_message_text(
            f"✅ *Theme: {theme_name.title()}*\n\n"
            f"🎯 Generating your {num_slides}-slide deck...",
            parse_mode="Markdown"
        )
        await start_generation(
            query, context, topic, num_slides,
            pack="executive", color=None,
            theme=theme_name, raw_text=raw_text
        )
    else:
        await query.edit_message_text(
            f"✅ *Theme saved: {theme_name.title()}*\n\n"
            "📝 Send me a topic to create a presentation!",
            parse_mode="Markdown"
        )


# ─────────────────────────────────────────────────────────────────
#  CALLBACK: locked pack tapped by free user → teaser + upgrade
# ─────────────────────────────────────────────────────────────────
async def locked_pack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await query.answer()
    pack_name = query.data.replace("locked_", "")

    teasers = {
        "executive": (
            "🏢 *Executive Pack*\n\n"
            "Dark side panels anchor every slide. Numbered bullet circles. "
            "Full-bleed image layouts. Horizontal timeline slides. "
            "A professional dark-light sandwich structure that makes any deck "
            "look like it came from a top consulting firm.\n\n"
            "✦ 6 distinct layouts\n"
            "✦ Dark cover + conclusion\n"
            "✦ Light content slides\n"
            "✦ Numbered card grids\n\n"
            "🔒 *Premium only*"
        ),
        "magazine": (
            "📰 *Magazine Pack*\n\n"
            "Bold Georgia serif headings. Editorial pull quotes with large "
            "opening quotation marks. Hero image strips across the full slide. "
            "3-column editorial grids. Big numbered stat blocks. "
            "Looks like a high-end print magazine turned into a presentation.\n\n"
            "✦ 5 editorial layouts\n"
            "✦ Pull quote intro slide\n"
            "✦ Hero image layouts\n"
            "✦ 3-column content grids\n\n"
            "🔒 *Premium only*"
        ),
    }

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Upgrade — ₦500/month", callback_data="show_upgrade")],
        [InlineKeyboardButton("◀️ Back to styles",       callback_data="back_to_style")],
    ])

    await query.edit_message_text(
        teasers.get(pack_name, "Premium pack"),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
#  CALLBACK: misc nav
# ─────────────────────────────────────────────────────────────────
async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        "❌ *Cancelled.*\n\nSend me a topic anytime to start!",
        parse_mode="Markdown"
    )


async def back_to_style_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎨 *Choose your slide style:*\n\nTap a locked pack to see what it looks like 👇",
        reply_markup=free_style_keyboard(),
        parse_mode="Markdown"
    )


async def back_to_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid     = str(query.from_user.id)
    premium = is_premium(uid)
    context.user_data.clear()

    keyboard = [
        [InlineKeyboardButton("📖 How to use",         callback_data="show_help")],
        [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="show_upgrade")],
        [InlineKeyboardButton("📊 My Status",          callback_data="show_status")],
    ]
    await query.edit_message_text(
        "✨ *Welcome back!*\n\n"
        "Ready to create another presentation?\n\n"
        "📝 *Just type any topic* to get started!\n\n"
        + ("💎 *Premium active* — all packs & colors unlocked!"
           if premium else
           "🎨 Free plan active — /upgrade for more!"),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def show_upgrade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="back_to_start")]]
    await query.edit_message_text(
        "💎 *SlideBot Premium — ₦500/month*\n\n"
        "*What you unlock:*\n"
        "✅ Unlimited presentations\n"
        "✅ Up to 30 slides per deck\n"
        "✅ 🏢 Executive Pack\n"
        "✅ 📰 Magazine Pack\n"
        "✅ Custom accent colors\n"
        "✅ Unlimited URL/file → Slides\n"
        "✅ No watermarks\n"
        "✅ Priority support\n\n"
        "*How to pay:*\n"
        "Bank: MONIEPOINT MFB\n"
        "Name: Abdullah Abdulgafar-Amuda\n"
        "Account: 8169936326\n\n"
        "Send your receipt screenshot here, then type /paid 🙏",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid     = str(query.from_user.id)
    premium = is_premium(uid)
    text = (
        "📚 *How SlideBot Works*\n\n"
        "*1.* Type a topic or paste a URL\n"
        "*2.* Choose number of slides\n"
        "*3.* Pick your pack & color\n"
        "*4.* Download your PPTX!\n\n"
        "*✨ Features:*\n"
        "• URL → Slides\n"
        "• PDF / Word → Slides\n"
        "• Executive & Magazine packs\n"
        "• Custom accent colors (/color)\n\n"
    )
    text += ("💎 *Premium active* — all packs & colors unlocked!"
             if premium else
             "📊 *Free plan* — 2/day, Classic & Dark\n\nType /upgrade! 💎")
    keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="back_to_start")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def show_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await query.answer()
    uid       = str(query.from_user.id)
    premium   = is_premium(uid)
    used      = get_today_usage(uid)
    pack      = get_user_pack(uid)
    accent    = get_user_accent(uid) or "1E2761"
    remaining = "Unlimited" if premium else max(0, 2 - used)

    keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="back_to_start")]]
    await query.edit_message_text(
        f"*Your SlideBot Status*\n\n"
        f"📌 *Plan:* {'💎 Premium' if premium else '📊 Free'}\n"
        f"📦 *Pack:* {pack.title()}\n"
        f"🎨 *Accent color:* `#{accent}`\n"
        f"✅ *Used today:* {'∞' if premium else used}\n"
        f"🎯 *Remaining:* {remaining}\n\n"
        f"Type /upgrade to go Premium 💎",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
#  CORE GENERATION
# ─────────────────────────────────────────────────────────────────
async def start_generation(
    query, context, topic, num_slides,
    pack="executive", color=None, theme="classic", raw_text=None
):
    uid     = str(query.from_user.id)
    premium = is_premium(uid)

    await query.edit_message_text(
        "🎨 *Creating your presentation...*\n\n"
        "• Structuring content 📝\n"
        "• Designing layouts 🎨\n"
        "• Adding images 🖼️\n\n"
        "This may take 20-40 seconds...",
        parse_mode="Markdown"
    )

    try:
        loop = asyncio.get_event_loop()

        # ── Generate slide content
        if raw_text:
            slide_data = await asyncio.wait_for(
                loop.run_in_executor(None, generate_from_text, raw_text, num_slides),
                timeout=180
            )
        else:
            slide_data = await asyncio.wait_for(
                loop.run_in_executor(None, generate_slide_content, topic, num_slides),
                timeout=120
            )

        if not slide_data or "slides" not in slide_data:
            await query.edit_message_text(
                "❌ *The AI couldn't generate slides for this content.*\n\n"
                "Try uploading a shorter document or typing the topic directly.",
                parse_mode="Markdown"
            )
            return

        await query.edit_message_text(
            "📐 *Almost done!* Designing your slides...",
            parse_mode="Markdown"
        )

        # ── Build the file
                # ── Build the file
        if premium and pack == "magazine":
            accent_hex = color or get_user_accent(uid) or "1E2761"
            filepath   = await loop.run_in_executor(
                None, build_magazine, slide_data, accent_hex
            )
            pack_label = "Magazine 📰"
        else:
            # Executive pack uses slide_builder with theme + optional accent override
            # For premium executive, default theme is "classic" unless saved
            exec_theme = theme if not premium else (get_user_theme(uid) or "classic")

            # For premium, use chosen color (inline picker) or saved accent
            accent_hex = None
            if premium:
                accent_hex = color or get_user_accent(uid)

            filepath = await loop.run_in_executor(
                None, build_presentation, slide_data, exec_theme, premium, accent_hex
            )
            pack_label = "Executive 🏢"


        increment_usage(uid)

        await query.edit_message_text("✅ *Done! Sending your file now...*", parse_mode="Markdown")

        plan_note = (
            "💎 *Premium* — Unlimited generations!"
            if premium else
            "📊 *Free plan* — Type /upgrade for unlimited! 💎"
        )

        with open(filepath, "rb") as f:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=f,
                filename=f"{slide_data.get('title', 'Presentation')}.pptx",
                caption=(
                    f"🎉 *Here's your presentation!*\n\n"
                    f"📌 *Title:* {slide_data.get('title', '')}\n"
                    f"📦 *Pack:* {pack_label}\n"
                    f"📊 *Slides:* {num_slides}\n\n"
                    f"{plan_note}"
                ),
                parse_mode="Markdown"
            )

        os.remove(filepath)

    except asyncio.TimeoutError:
        await query.edit_message_text(
            "⏰ *This is taking too long.*\n\n"
            "Your document might be too large. Try:\n"
            "• Uploading a shorter document\n"
            "• Typing the topic directly instead",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Generation error: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ *Something went wrong generating your slides.*\n\n"
            "Please try again. If the issue persists, try typing the topic directly.",
            parse_mode="Markdown"
        )


# ─────────────────────────────────────────────────────────────────
#  MESSAGE HANDLER — text topics
# ─────────────────────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid  = str(user.id)
    text = update.message.text.strip()
    get_or_create_user(uid, str(user.username or user.first_name))

    # URL detection
    if text.startswith("http://") or text.startswith("https://"):
        if not can_use_url(uid):
            await update.message.reply_text(
                "🔒 *URL limit reached*\n\n"
                "You've used your free URL slot for this month.\n\n"
                "💎 Type /upgrade for unlimited URL → slides!",
                parse_mode="Markdown"
            )
            return
        await handle_url(update, context, text)
        return

    # Daily limit check
    if not can_generate(uid):
        await update.message.reply_text(
            "📊 *Daily limit reached*\n\n"
            "You've used your 2 free presentations for today.\n\n"
            "💎 Type /upgrade for unlimited access! 🚀",
            parse_mode="Markdown"
        )
        return

    context.user_data["pending_topic"] = text
    await update.message.reply_text(
        "📊 *How many slides do you need?*\n\n"
        f"{'✨ Premium: up to 30 slides' if is_premium(uid) else 'Free: up to 8 slides'}",
        reply_markup=slide_count_keyboard(uid),
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
#  URL HANDLER
# ─────────────────────────────────────────────────────────────────
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    uid = str(update.effective_user.id)
    await update.message.reply_text("🔍 *Extracting content from your link...*", parse_mode="Markdown")
    try:
        loop       = asyncio.get_event_loop()
        downloaded = await loop.run_in_executor(None, trafilatura.fetch_url, url)
        if not downloaded:
            await update.message.reply_text("❌ Couldn't fetch that URL. Try another link.")
            return
        text = trafilatura.extract(downloaded)
        if not text or len(text) < 100:
            await update.message.reply_text("❌ Couldn't extract enough content from that page.")
            return

        increment_url_usage(uid)
        context.user_data["pending_topic"]    = url
        context.user_data["pending_raw_text"] = text[:12000]

        await update.message.reply_text(
            f"✅ *Content extracted!* ({len(text)} characters)\n\n📊 *How many slides?*",
            reply_markup=slide_count_keyboard(uid),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"URL error: {e}")
        await update.message.reply_text("❌ Something went wrong fetching that URL. Try again.")


# ─────────────────────────────────────────────────────────────────
#  FILE HANDLER
# ─────────────────────────────────────────────────────────────────
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid  = str(user.id)
    get_or_create_user(uid, str(user.username or user.first_name))
    doc  = update.message.document
    if not doc:
        return

    if not can_use_file(uid):
        await update.message.reply_text(
            "🔒 *File upload limit reached*\n\n"
            "💎 Type /upgrade for unlimited file → slides!",
            parse_mode="Markdown"
        )
        return

    filename = doc.file_name or ""
    ext      = filename.lower().split(".")[-1] if "." in filename else ""

    if ext not in ["pdf", "docx", "doc"]:
        await update.message.reply_text(
            "📄 *Supported files:* PDF and Word (.docx)\n\n"
            "Please send one of these formats!",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        "📖 *Reading your file...*\n\nThis may take a moment for large documents.",
        parse_mode="Markdown"
    )

    try:
        file        = await context.bot.get_file(doc.file_id)
        file_bytes  = await file.download_as_bytearray()
        file_stream = io.BytesIO(bytes(file_bytes))
        loop        = asyncio.get_event_loop()

        if ext == "pdf":
            text = await loop.run_in_executor(None, extract_pdf_text, file_stream)
        else:
            text = await loop.run_in_executor(None, extract_docx_text, file_stream)

        if not text or len(text) < 100:
            await update.message.reply_text(
                "❌ *Couldn't extract enough text from that file.*\n\n"
                "Make sure the file contains readable text (not just images).",
                parse_mode="Markdown"
            )
            return

        increment_file_usage(uid)
        context.user_data["pending_topic"]    = filename
        context.user_data["pending_raw_text"] = text[:12000]

        await update.message.reply_text(
            f"✅ *File processed!* ({len(text)} characters extracted)\n\n"
            "📊 *How many slides do you want?*",
            reply_markup=slide_count_keyboard(uid),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"File processing error: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ *Something went wrong reading that file.*\n\n"
            "Please make sure it's a valid PDF or Word document and try again.",
            parse_mode="Markdown"
        )


def extract_pdf_text(file_stream) -> str:
    try:
        import fitz
        doc  = fitz.open(stream=file_stream.read(), filetype="pdf")
        text = "".join(page.get_text() for page in doc)
        return text.strip()
    except Exception as e:
        logger.error(f"PDF extract error: {e}")
        return ""


def extract_docx_text(file_stream) -> str:
    try:
        from docx import Document
        doc  = Document(file_stream)
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return text.strip()
    except Exception as e:
        logger.error(f"DOCX extract error: {e}")
        return ""


# ─────────────────────────────────────────────────────────────────
#  PHOTO HANDLER — payment screenshots
# ─────────────────────────────────────────────────────────────────
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user     = update.effective_user
    uid      = str(user.id)
    username = user.username or user.first_name
    try:
        await context.bot.send_message(
            chat_id=int(ADMIN_ID),
            text=(
                f"📸 *Payment Screenshot*\n\n"
                f"👤 User: @{username}\n"
                f"🆔 ID: `{uid}`\n\n"
                f"To activate: `/activate {uid}`"
            ),
            parse_mode="Markdown"
        )
        await context.bot.forward_message(
            chat_id=int(ADMIN_ID),
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
    except Exception as e:
        logger.error(f"Forward error: {e}")

    await update.message.reply_text(
        "📸 *Screenshot received!*\n\n"
        "Now type */paid* to complete your request — we'll activate you within the hour. 🙏",
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
#  PING SERVER (keeps Render.com alive)
# ─────────────────────────────────────────────────────────────────
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"SlideBot is alive!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass


def run_ping_server():
    port   = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), PingHandler)
    print(f"Ping server running on port {port}")
    server.serve_forever()


# ─────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────
async def main():
    Thread(target=run_ping_server, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start",       start))
    app.add_handler(CommandHandler("help",        help_command))
    app.add_handler(CommandHandler("status",      status_command))
    app.add_handler(CommandHandler("upgrade",     upgrade_command))
    app.add_handler(CommandHandler("paid",        paid_command))
    app.add_handler(CommandHandler("color",       color_command))
    app.add_handler(CommandHandler("activate",    activate_command))
    app.add_handler(CommandHandler("revoke",      revoke_command))
    app.add_handler(CommandHandler("stats",       stats_command))
    app.add_handler(CommandHandler("premiumlist", premiumlist_command))

    # Flow callbacks
    app.add_handler(CallbackQueryHandler(slide_count_callback,  pattern="^slides_"))
    app.add_handler(CallbackQueryHandler(pack_callback,         pattern="^pack_"))
    app.add_handler(CallbackQueryHandler(color_callback,        pattern="^color_"))
    app.add_handler(CallbackQueryHandler(theme_callback,        pattern="^theme_"))
    app.add_handler(CallbackQueryHandler(locked_pack_callback,  pattern="^locked_"))

    # Nav callbacks
    app.add_handler(CallbackQueryHandler(cancel_callback,       pattern="^cancel$"))
    app.add_handler(CallbackQueryHandler(back_to_style_callback,pattern="^back_to_style$"))
    app.add_handler(CallbackQueryHandler(back_to_start_callback,pattern="^back_to_start$"))
    app.add_handler(CallbackQueryHandler(show_upgrade_callback, pattern="^show_upgrade$"))
    app.add_handler(CallbackQueryHandler(help_callback,         pattern="^show_help$"))
    app.add_handler(CallbackQueryHandler(show_status_callback,  pattern="^show_status$"))

    # Message handlers
    app.add_handler(MessageHandler(filters.PHOTO,                            handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL,                     handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,          handle_message))

    print("🚀 SlideBot is running!")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

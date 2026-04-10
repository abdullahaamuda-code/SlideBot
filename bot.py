import os
import io
import asyncio
import logging
import requests
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
from slide_builder import build_presentation, FREE_THEMES, PREMIUM_THEMES
from database import (
    get_or_create_user, can_generate, increment_usage,
    is_premium, activate_premium, revoke_premium,
    get_premium_users, get_total_stats,
    can_use_url, can_use_file,
    increment_url_usage, increment_file_usage,
    get_user_theme, save_user_theme, get_today_usage  # ADD THIS LINE
)

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_TELEGRAM_ID")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─── HELPERS ──────────────────────────────────────────────────────
def is_admin(telegram_id: str) -> bool:
    return str(telegram_id) == str(ADMIN_ID)

def get_theme_keyboard(user_id: str, current_theme=None):
    premium = is_premium(user_id)
    keyboard = []
    
    # Free themes row
    row1 = []
    for t in FREE_THEMES:
        label = f"✅ {t.title()}" if current_theme == t else t.title()
        row1.append(InlineKeyboardButton(label, callback_data=f"theme_{t}"))
    keyboard.append(row1)
    
    # Premium themes rows
    row2 = []
    for theme in PREMIUM_THEMES[:2]:
        if premium:
            label = f"✅ {theme.title()}" if current_theme == theme else theme.title()
        else:
            label = f"🔒 {theme.title()}"
        row2.append(InlineKeyboardButton(label, callback_data=f"theme_{theme}"))
    keyboard.append(row2)
    
    row3 = []
    for theme in PREMIUM_THEMES[2:]:
        if premium:
            label = f"✅ {theme.title()}" if current_theme == theme else theme.title()
        else:
            label = f"🔒 {theme.title()}"
        row3.append(InlineKeyboardButton(label, callback_data=f"theme_{theme}"))
    keyboard.append(row3)
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

def get_slide_count_keyboard(user_id: str):
    premium = is_premium(user_id)
    max_slides = 30 if premium else 8
    options = [5, 8, 10, 12, 15, 20, 25, 30]
    keyboard = []
    row = []
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


# ─── GUIDED FLOW WITH BETTER UX ──────────────────────────────────
async def ask_for_slide_count(update: Update, context: ContextTypes.DEFAULT_TYPE, message=None):
    msg = message or update.message
    await msg.reply_text(
        "📊 **How many slides do you need?**\n\n"
        f"{'✨ Premium: up to 30 slides' if is_premium(str(update.effective_user.id)) else 'Free: up to 8 slides'}",
        reply_markup=get_slide_count_keyboard(str(update.effective_user.id)),
        parse_mode="Markdown"
    )

async def slide_count_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    num_slides = int(query.data.replace("slides_", ""))
    context.user_data["pending_slides"] = num_slides
    uid = str(query.from_user.id)
    
    # If theme already selected, generate immediately
    if "theme" in context.user_data:
        theme = context.user_data["theme"]
        await query.edit_message_text(f"🎯 **{num_slides} slides** — generating your deck now...")
        await start_generation(
            query, context,
            context.user_data.get("pending_topic", ""),
            num_slides, theme,
            raw_text=context.user_data.get("pending_raw_text")
        )
    else:
        await query.edit_message_text(
            "🎨 **Great! Now pick your slide style**\n\n"
            "Each theme has unique colors and layouts:",
            reply_markup=get_theme_keyboard(uid, context.user_data.get("theme")),
            parse_mode="Markdown"
        )

async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        "❌ **Cancelled**\n\n"
        "Send me a new topic anytime to create your presentation!",
        parse_mode="Markdown"
    )


# ─── COMMANDS ─────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    get_or_create_user(uid, str(user.username or user.first_name))
    
    # Load saved theme if exists
    from database import get_user_theme, save_user_theme
    saved_theme = get_user_theme(uid)
    if saved_theme:
        context.user_data["theme"] = saved_theme
    
    # ADDED: Status button in the keyboard
    keyboard = [
        [InlineKeyboardButton("📖 How to use", callback_data="show_help")],
        [InlineKeyboardButton("🎨 Change Theme", callback_data="change_theme")],
        [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="show_upgrade")],
        [InlineKeyboardButton("📊 My Status", callback_data="show_status")]  # NEW
    ]
    await update.message.reply_text(
        f"✨ **Hey {user.first_name}!** ✨\n\n"
        "Welcome to **SlideBot** — your AI presentation designer.\n\n"
        "**Just type any topic** and I'll create a professional PowerPoint in seconds!\n\n"
        "📝 **Try:**\n"
        "• *Climate change in Africa*\n"
        "• *My business pitch*\n"
        "• *Digital marketing trends*\n\n"
        "📎 Or send me a **URL, PDF, or Word doc** to convert!\n\n"
        f"{'🎨 Current theme: ' + saved_theme.title() if saved_theme else '🎨 Pick a theme below'}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def change_theme_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    from database import get_user_theme
    current = get_user_theme(uid)
    
    # Get the theme keyboard
    keyboard = get_theme_keyboard(uid, current)
    
    # ADDED: Convert to list and add Back button at the bottom
    keyboard_list = keyboard.inline_keyboard
    back_button = [[InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_start")]]
    new_keyboard = InlineKeyboardMarkup(keyboard_list + back_button)
    
    await query.edit_message_text(
        f"🎨 **Choose your slide style**\n\nCurrent: **{current.title()}**\n\n"
        f"{'🔓 All themes unlocked!' if is_premium(uid) else '🔒 Premium themes require upgrade'}",
        reply_markup=new_keyboard,
        parse_mode="Markdown"
    )
async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    premium = is_premium(uid)
    
    help_text = (
        "📚 **How SlideBot Works**\n\n"
        "**1.** Type a topic or paste a URL\n"
        "**2.** Choose number of slides\n"
        "**3.** Pick your theme\n"
        "**4.** Download your PPTX instantly!\n\n"
        "**✨ Features:**\n"
        "• URL → Slides (extract from articles)\n"
        "• PDF/Word → Slides\n"
        "• 6 premium themes\n"
        "• Professional layouts\n\n"
    )
    
    if premium:
        help_text += "💎 **Your plan: Premium**\n• Unlimited decks\n• Up to 30 slides\n• All themes\n• Priority support"
    else:
        help_text += "📊 **Your plan: Free**\n• 2 decks/day\n• Up to 8 slides\n• Classic & Dark themes\n\nType /upgrade for unlimited! 💎"
    
    # ADDED: Back button instead of Change Theme button
    keyboard = [[InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_start")]]
    await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def show_upgrade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # ADDED: Back button
    keyboard = [[InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_start")]]
    
    await query.edit_message_text(
        "💎 **SlideBot Premium — ₦500/month**\n\n"
        "**What you unlock:**\n"
        "✅ Unlimited presentations\n"
        "✅ Up to 30 slides per deck\n"
        "✅ All 6 premium themes\n"
        "✅ Unlimited URL → Slides\n"
        "✅ Unlimited PDF/Word → Slides\n"
        "✅ No watermarks\n"
        "✅ Priority support\n\n"
        "**How to pay:**\n"
        "Bank: MONIEPOINT MFB\n"
        "Name: Abdullah Abdulgafar-Amuda\n"
        "Account: 8169936326\n\n"
        "After payment, send your receipt screenshot here,\n"
        "then type /paid 🙏",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
async def back_to_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back button - returns to main menu"""
    query = update.callback_query
    await query.answer()
    
    uid = str(query.from_user.id)
    from database import get_user_theme
    saved_theme = get_user_theme(uid)
    
    # Clear any pending data
    context.user_data.clear()
    context.user_data["theme"] = saved_theme
    
    # Main welcome keyboard - same as /start
    keyboard = [
        [InlineKeyboardButton("📖 How to use", callback_data="show_help")],
        [InlineKeyboardButton("🎨 Change Theme", callback_data="change_theme")],
        [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="show_upgrade")],
        [InlineKeyboardButton("📊 My Status", callback_data="show_status")]
    ]
    
    await query.edit_message_text(
        f"✨ **Welcome back!** ✨\n\n"
        "Ready to create another presentation?\n\n"
        "📝 **Just type any topic** and I'll get started!\n\n"
        f"🎨 **Current theme:** {saved_theme.title()}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def show_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle status button callback"""
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    premium = is_premium(uid)
    from database import get_today_usage, get_user_theme
    used_today = get_today_usage(uid)
    theme = get_user_theme(uid)
    
    plan = "💎 Premium" if premium else "📊 Free"
    remaining = "Unlimited" if premium else max(0, 2 - used_today)
    
    keyboard = [[InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_start")]]
    
    await query.edit_message_text(
        f"**Your SlideBot Status**\n\n"
        f"📌 **Plan:** {plan}\n"
        f"🎨 **Theme:** {theme.title()}\n"
        f"✅ **Used today:** {used_today if not premium else '∞'}\n"
        f"🎯 **Remaining:** {remaining}\n\n"
        f"Type /upgrade to go Premium 💎",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    get_or_create_user(uid, str(user.username or user.first_name))
    premium = is_premium(uid)
    
    help_text = (
        "📚 **How SlideBot Works**\n\n"
        "**1.** Type a topic or paste a URL\n"
        "**2.** Choose number of slides\n"
        "**3.** Pick your theme\n"
        "**4.** Download your PPTX instantly!\n\n"
        "**✨ Features:**\n"
        "• URL → Slides\n"
        "• PDF/Word → Slides\n"
        "• 6 premium themes\n"
        "• Professional layouts\n\n"
    )
    
    if premium:
        help_text += "💎 **Premium:** Unlimited access • 30 slides • All themes"
    else:
        help_text += "📊 **Free:** 2 decks/day • 8 slides • Basic themes\n\nType /upgrade for unlimited! 💎"
    
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def theme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    get_or_create_user(uid, str(user.username or user.first_name))
    await update.message.reply_text(
        "🎨 **Choose your slide style**",
        reply_markup=get_theme_keyboard(uid, context.user_data.get("theme")),
        parse_mode="Markdown"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    get_or_create_user(uid, str(user.username or user.first_name))
    premium = is_premium(uid)
    can_gen = can_generate(uid)
    plan = "💎 Premium" if premium else "📊 Free"
    limit_text = "Unlimited" if premium else "2 per day"
    
    # Get today's usage
    from database import get_today_usage
    used_today = get_today_usage(uid)
    remaining = "Unlimited" if premium else max(0, 2 - used_today)
    
    await update.message.reply_text(
        f"**Your SlideBot Status**\n\n"
        f"📌 **Plan:** {plan}\n"
        f"📊 **Daily limit:** {limit_text}\n"
        f"✅ **Used today:** {used_today if not premium else '∞'}\n"
        f"🎯 **Remaining:** {remaining if not premium else 'Unlimited'}\n"
        f"🎨 **Can generate now:** {'Yes ✅' if can_gen else 'No — limit reached'}\n\n"
        f"Type /upgrade to go Premium 💎",
        parse_mode="Markdown"
    )

async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💎 **SlideBot Premium — ₦500/month**\n\n"
        "**What you unlock:**\n"
        "✅ Unlimited presentations\n"
        "✅ Up to 30 slides per deck\n"
        "✅ All 6 premium themes\n"
        "✅ Unlimited URL → Slides\n"
        "✅ Unlimited PDF/Word → Slides\n"
        "✅ No watermarks\n"
        "✅ Priority support\n\n"
        "**How to pay:**\n"
        "Bank: MONIEPOINT MFB\n"
        "Name: Abdullah Abdulgafar-Amuda\n"
        "Account: 8169936326\n\n"
        "After payment, send your receipt screenshot here,\n"
        "then type /paid 🙏",
        parse_mode="Markdown"
    )

async def paid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    username = user.username or user.first_name
    try:
        await context.bot.send_message(
            chat_id=int(ADMIN_ID),
            text=f"💰 **Payment Claim**\n\n"
                 f"👤 User: @{username}\n"
                 f"🆔 ID: `{uid}`\n\n"
                 f"To activate: `/activate {uid}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Admin notify error: {e}")
    await update.message.reply_text(
        "🙏 **Thank you for your payment!**\n\n"
        "We've received your claim and will verify shortly.\n"
        "You'll be activated within the hour — we'll notify you here. ✅\n\n"
        "Meanwhile, try the free themes while you wait! 🎨",
        parse_mode="Markdown"
    )


# ─── ADMIN COMMANDS (FIXED) ───────────────────────────────────────
async def activate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(str(user.id)):
        await update.message.reply_text("❌ Not authorized.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /activate <telegram_id>\n\n"
            "Example: /activate 123456789",
            parse_mode="Markdown"
        )
        return
    
    target_id = context.args[0]
    success = activate_premium(target_id, str(user.id))
    
    if success:
        await update.message.reply_text(f"✅ **User {target_id} is now PREMIUM!**", parse_mode="Markdown")
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text="🎉 **CONGRATULATIONS!** 🎉\n\n"
                     "You've been upgraded to **Premium**!\n\n"
                     "✨ **What you get now:**\n"
                     "• Unlimited presentations\n"
                     "• Up to 30 slides per deck\n"
                     "• All 6 premium themes\n"
                     "• Unlimited URL & file uploads\n\n"
                     "Type a topic to create your first Premium deck! 🚀",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Could not message user: {e}")
    else:
        await update.message.reply_text(f"❌ Could not activate {target_id}. User may not exist.")

async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(str(user.id)):
        await update.message.reply_text("❌ Not authorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /revoke <telegram_id>")
        return
    target_id = context.args[0]
    success = revoke_premium(target_id)
    if success:
        await update.message.reply_text(f"✅ Premium revoked for {target_id}")
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text="Your Premium access has been revoked. Contact support for more info."
            )
        except:
            pass
    else:
        await update.message.reply_text(f"❌ User {target_id} not found")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(str(user.id)):
        await update.message.reply_text("❌ Not authorized.")
        return
    stats = get_total_stats()
    await update.message.reply_text(
        f"📊 **SlideBot Statistics**\n\n"
        f"👥 Total users: {stats['total_users']}\n"
        f"💎 Premium users: {stats['premium_users']}\n"
        f"📋 Free users: {stats['free_users']}\n"
        f"🎨 Total slides made: {stats['total_slides_generated']}",
        parse_mode="Markdown"
    )

async def premiumlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(str(user.id)):
        await update.message.reply_text("❌ Not authorized.")
        return
    premium_users = get_premium_users()
    if not premium_users:
        await update.message.reply_text("No premium users yet.")
        return
    msg = "💎 **Premium Users:**\n\n"
    for uid, u in premium_users.items():
        msg += f"• @{u['username']} — `{uid}`\n"
    await update.message.reply_text(msg, parse_mode="Markdown")


# ─── THEME CALLBACK (FIXED - saves theme) ─────────────────────────
async def theme_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    theme_name = query.data.replace("theme_", "")
    
    # Check premium restriction
    if theme_name in PREMIUM_THEMES and not is_premium(uid):
        await query.edit_message_text(
            "🔒 **Premium Theme Locked**\n\n"
            f"*{theme_name.title()}* is for Premium users only.\n\n"
            "💎 **Upgrade to Premium** for:\n"
            "• All 6 themes\n"
            "• Unlimited presentations\n"
            "• Up to 30 slides\n"
            "• Unlimited URL/file uploads\n\n"
            "Type /upgrade to get started! 🚀",
            parse_mode="Markdown"
        )
        return
    
    # Save the selected theme
    context.user_data["theme"] = theme_name
    
    # Save to database for persistence
    from database import save_user_theme
    save_user_theme(uid, theme_name)
    
    # If user has pending topic and slides, generate immediately
    if "pending_topic" in context.user_data and "pending_slides" in context.user_data:
        topic = context.user_data.pop("pending_topic")
        num_slides = context.user_data.pop("pending_slides")
        raw_text = context.user_data.pop("pending_raw_text", None)
        await query.edit_message_text(f"✅ Theme: **{theme_name.title()}** applied!\n\n🎯 Generating your {num_slides}-slide deck...", parse_mode="Markdown")
        await start_generation(query, context, topic, num_slides, theme_name, raw_text=raw_text)
    else:
        await query.edit_message_text(
            f"✅ **Theme saved: {theme_name.title()}**\n\n"
            "This theme will be used for all your presentations.\n\n"
            "📝 **Now send me your topic** or paste a URL to begin!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📖 How to use", callback_data="show_help")
            ]]),
            parse_mode="Markdown"
        )


# ─── CORE GENERATION ──────────────────────────────────────────────
async def start_generation(query, context, topic, num_slides, theme, raw_text=None):
    uid = str(query.from_user.id)
    premium = is_premium(uid)
    
    await query.edit_message_text("🎨 **Creating your presentation...**\n\n"
                                  "• Structuring content 📝\n"
                                  "• Designing layouts 🎨\n"
                                  "• Adding images 🖼️\n\n"
                                  "This may take 20-30 seconds...",
                                  parse_mode="Markdown")
    try:
        loop = asyncio.get_event_loop()
        if raw_text:
            slide_data = await asyncio.wait_for(
                loop.run_in_executor(None, generate_from_text, raw_text, num_slides),
                timeout=120
            )
        else:
            slide_data = await asyncio.wait_for(
                loop.run_in_executor(None, generate_slide_content, topic, num_slides),
                timeout=120
            )
        if not slide_data:
            await query.edit_message_text("❌ Something went wrong with the AI. Please try again.")
            return
        
        await query.edit_message_text("📐 **Almost done!** Designing your slides with premium layouts...", parse_mode="Markdown")
        
        filepath = await loop.run_in_executor(
            None, build_presentation, slide_data, theme, premium
        )
        
        increment_usage(uid)
        
        await query.edit_message_text("✅ **Done! Sending your file now...**", parse_mode="Markdown")
        
        with open(filepath, "rb") as f:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=f,
                filename=f"{slide_data.get('title', 'Presentation')}.pptx",
                caption=(
                    f"🎉 **Here's your presentation!**\n\n"
                    f"📌 **Title:** {slide_data.get('title', '')}\n"
                    f"🎨 **Theme:** {theme.title()}\n"
                    f"📊 **Slides:** {num_slides}\n\n"
                    f"{'💎 **Premium** — Unlimited generations!' if premium else '📊 **Free plan** — 2/day remaining. Type /upgrade for unlimited! 💎'}"
                ),
                parse_mode="Markdown"
            )
        
        os.remove(filepath)
        
    except asyncio.TimeoutError:
        await query.edit_message_text("⏰ **Taking too long** — please try a simpler topic or fewer slides.", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Generation error: {e}")
        await query.edit_message_text("❌ **Something went wrong.** Please try again or contact support.", parse_mode="Markdown")


# ─── MESSAGE HANDLER ──────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    text = update.message.text.strip()
    get_or_create_user(uid, str(user.username or user.first_name))

    # URL detection
    if text.startswith("http://") or text.startswith("https://"):
        if not can_use_url(uid):
            await update.message.reply_text(
                "🔒 **URL limit reached**\n\n"
                "You've used your free URL slot for this month.\n\n"
                "💎 **Upgrade to Premium** for unlimited URL → slides!\n"
                "Type /upgrade to unlock 🚀",
                parse_mode="Markdown"
            )
            return
        await handle_url(update, context, text)
        return

    # Check daily limit
    if not can_generate(uid):
        await update.message.reply_text(
            "📊 **Daily limit reached**\n\n"
            "You've used your 2 free presentations for today.\n\n"
            "💎 **Upgrade to Premium** for:\n"
            "• Unlimited presentations\n"
            "• Up to 30 slides\n"
            "• All premium themes\n"
            "• Unlimited URL/file uploads\n\n"
            "Type /upgrade to get unlimited access! 🚀",
            parse_mode="Markdown"
        )
        return
    
    context.user_data["pending_topic"] = text
    await ask_for_slide_count(update, context)


# ─── URL HANDLER ──────────────────────────────────────────────────
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    uid = str(update.effective_user.id)
    await update.message.reply_text("🔍 **Extracting content from your link...**", parse_mode="Markdown")
    try:
        loop = asyncio.get_event_loop()
        downloaded = await loop.run_in_executor(
            None, trafilatura.fetch_url, url
        )
        if not downloaded:
            await update.message.reply_text("❌ Couldn't fetch that URL. Try another link.")
            return
        text = trafilatura.extract(downloaded)
        if not text or len(text) < 100:
            await update.message.reply_text("❌ Couldn't extract enough content from that page.")
            return
        increment_url_usage(uid)
        context.user_data["pending_topic"] = url
        context.user_data["pending_raw_text"] = text[:8000]
        await update.message.reply_text(
            f"✅ **Content extracted!** ({len(text)} characters)\n\n"
            "📊 **How many slides do you want?**",
            reply_markup=get_slide_count_keyboard(uid),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"URL error: {e}")
        await update.message.reply_text("❌ Something went wrong fetching that URL. Try again.")


# ─── FILE HANDLER ─────────────────────────────────────────────────
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    get_or_create_user(uid, str(user.username or user.first_name))
    doc = update.message.document
    if not doc:
        return

    if not can_use_file(uid):
        await update.message.reply_text(
            "🔒 **File upload limit reached**\n\n"
            "You've used your free file upload for this month.\n\n"
            "💎 **Upgrade to Premium** for unlimited file → slides!\n"
            "Type /upgrade to unlock 🚀",
            parse_mode="Markdown"
        )
        return

    filename = doc.file_name or ""
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if ext not in ["pdf", "docx", "doc"]:
        await update.message.reply_text(
            "📄 **Supported files:** PDF and Word (.docx)\n\n"
            "Please send one of these formats and I'll convert it to slides!",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text("📖 **Reading your file...**", parse_mode="Markdown")

    try:
        file = await context.bot.get_file(doc.file_id)
        file_bytes = await file.download_as_bytearray()
        file_stream = io.BytesIO(bytes(file_bytes))
        loop = asyncio.get_event_loop()

        if ext == "pdf":
            text = await loop.run_in_executor(None, extract_pdf_text, file_stream)
        else:
            text = await loop.run_in_executor(None, extract_docx_text, file_stream)

        if not text or len(text) < 100:
            await update.message.reply_text("❌ Couldn't extract enough text from that file.")
            return

        increment_file_usage(uid)
        context.user_data["pending_topic"] = filename
        context.user_data["pending_raw_text"] = text[:8000]

        await update.message.reply_text(
            f"✅ **File processed!** ({len(text)} characters extracted)\n\n"
            "📊 **How many slides do you want?**",
            reply_markup=get_slide_count_keyboard(uid),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"File error: {e}")
        await update.message.reply_text("❌ Something went wrong reading that file. Try again.")


def extract_pdf_text(file_stream) -> str:
    try:
        import fitz
        doc = fitz.open(stream=file_stream.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text.strip()
    except Exception as e:
        print(f"PDF extract error: {e}")
        return ""

def extract_docx_text(file_stream) -> str:
    try:
        from docx import Document
        doc = Document(file_stream)
        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        return text.strip()
    except Exception as e:
        print(f"DOCX extract error: {e}")
        return ""


# ─── PHOTO HANDLER ────────────────────────────────────────────────
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    username = user.username or user.first_name
    try:
        await context.bot.send_message(
            chat_id=int(ADMIN_ID),
            text=f"📸 **Payment Screenshot**\n\n👤 User: @{username}\n🆔 ID: `{uid}`\n\nTo activate: `/activate {uid}`",
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
        "📸 **Screenshot received!**\n\n"
        "Now type **/paid** to complete your request — we'll activate you within the hour. 🙏",
        parse_mode="Markdown"
    )


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
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), PingHandler)
    print(f"Ping server running on port {port}")
    server.serve_forever()


# ─── MAIN ─────────────────────────────────────────────────────────
async def main():
    Thread(target=run_ping_server, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("theme", theme_command))
    app.add_handler(CommandHandler("upgrade", upgrade_command))
    app.add_handler(CommandHandler("paid", paid_command))
    app.add_handler(CommandHandler("activate", activate_command))
    app.add_handler(CommandHandler("revoke", revoke_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("premiumlist", premiumlist_command))

    app.add_handler(CallbackQueryHandler(slide_count_callback, pattern="^slides_"))
    app.add_handler(CallbackQueryHandler(theme_callback, pattern="^theme_"))
    app.add_handler(CallbackQueryHandler(cancel_callback, pattern="^cancel$"))
    app.add_handler(CallbackQueryHandler(help_callback, pattern="^show_help$"))
    app.add_handler(CallbackQueryHandler(change_theme_callback, pattern="^change_theme$"))
    app.add_handler(CallbackQueryHandler(show_upgrade_callback, pattern="^show_upgrade$"))
    app.add_handler(CallbackQueryHandler(back_to_start_callback, pattern="^back_to_start$"))  # ADD THIS
    app.add_handler(CallbackQueryHandler(show_status_callback, pattern="^show_status$"))       # ADD THIS

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 SlideBot is running!")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()


if __name__ == "__main__":
    import asyncio
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

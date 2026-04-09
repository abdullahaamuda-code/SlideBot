import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from ai_engine import generate_slide_content
from slide_builder import build_presentation, FREE_THEMES, PREMIUM_THEMES
from database import (
    get_or_create_user, can_generate, increment_usage,
    is_premium, activate_premium, revoke_premium,
    get_all_users, get_premium_users, get_total_stats
)

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_TELEGRAM_ID")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_admin(telegram_id: str) -> bool:
    return str(telegram_id) == str(ADMIN_ID)

def get_theme_keyboard(user_id: str):
    premium = is_premium(user_id)
    keyboard = []
    row1 = [InlineKeyboardButton(f"✅ {t.title()}", callback_data=f"theme_{t}") for t in FREE_THEMES]
    keyboard.append(row1)
    row2 = []
    for theme in PREMIUM_THEMES[:2]:
        label = theme.title() if premium else f"🔒 {theme.title()}"
        row2.append(InlineKeyboardButton(label, callback_data=f"theme_{theme}"))
    keyboard.append(row2)
    row3 = []
    for theme in PREMIUM_THEMES[2:]:
        label = theme.title() if premium else f"🔒 {theme.title()}"
        row3.append(InlineKeyboardButton(label, callback_data=f"theme_{theme}"))
    keyboard.append(row3)
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


# ─── GUIDED FLOW ──────────────────────────────────────────────────
async def ask_for_slide_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Got it! How many slides do you want?",
        reply_markup=get_slide_count_keyboard(str(update.effective_user.id))
    )

async def slide_count_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    num_slides = int(query.data.replace("slides_", ""))
    context.user_data["pending_slides"] = num_slides
    uid = str(query.from_user.id)
    if "theme" in context.user_data:
        theme = context.user_data["theme"]
        await query.edit_message_text(f"{num_slides} slides — generating now...")
        await start_generation(query, context, context.user_data["pending_topic"], num_slides, theme)
    else:
        await query.edit_message_text(
            "Nice! Now pick your slide style 👇",
            reply_markup=get_theme_keyboard(uid)
        )

async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("Cancelled. Send a new topic anytime!")


# ─── COMMANDS ─────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_user(str(user.id), str(user.username or user.first_name))
    await update.message.reply_text(
        f"Hey {user.first_name}! 👋\n\n"
        "Welcome to SlideBot — just type any topic and I'll turn it into a clean, professional PowerPoint in seconds.\n\n"
        "Try something like:\n"
        "• Climate change in Africa\n"
        "• My business pitch\n"
        "• Solar energy benefits\n\n"
        "Go ahead, type your topic 👇"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Here's how SlideBot works:\n\n"
        "1. Type your topic\n"
        "2. Choose how many slides\n"
        "3. Pick a theme\n"
        "4. Download your PPTX\n\n"
        "Free plan: 2 decks a day, up to 8 slides\n"
        "Premium (₦2,500/month): unlimited decks, up to 30 slides, all themes\n\n"
        "/upgrade — go Premium\n"
        "/status — check your plan\n"
        "/theme — change your style"
    )

async def theme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    get_or_create_user(uid, str(user.username or user.first_name))
    await update.message.reply_text(
        "Pick your slide style 🎨",
        reply_markup=get_theme_keyboard(uid)
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    get_or_create_user(uid, str(user.username or user.first_name))
    premium = is_premium(uid)
    can_gen = can_generate(uid)
    plan = "💎 Premium" if premium else "Free"
    limit_text = "Unlimited" if premium else "2 per day"
    await update.message.reply_text(
        f"Your plan: {plan}\n"
        f"Daily limit: {limit_text}\n"
        f"Can generate now: {'Yes ✅' if can_gen else 'No — limit reached for today'}\n\n"
        f"Type /upgrade to go Premium 💎"
    )

async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💎 SlideBot Premium — ₦2,500/month\n\n"
        "What you get:\n"
        "• Unlimited presentations\n"
        "• Up to 30 slides per deck\n"
        "• All 6 premium themes\n"
        "• Faster generation\n\n"
        "To pay:\n"
        "Bank: MONIEPOINT MFB\n"
        "Name: Abdullah Abdulgafar-Amuda\n"
        "Account: 8169936326\n\n"
        "After payment, send your receipt screenshot here in this chat, then type /paid and we'll activate you within the hour. 🙏"
    )

async def paid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    username = user.username or user.first_name
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"💰 Payment claim from @{username}\nID: {uid}\n\nActivate with: /activate {uid}",
        )
    except Exception as e:
        logger.error(f"Admin notify error: {e}")
    await update.message.reply_text(
        "Thank you! 🙏\n\n"
        "We've received your payment claim and will verify it shortly. "
        "You'll be activated within the hour — feel free to do other things and we'll message you the moment it's done. ✅"
    )


# ─── ADMIN COMMANDS ───────────────────────────────────────────────
async def activate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(str(user.id)):
        await update.message.reply_text("Not authorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /activate <telegram_id>")
        return
    target_id = context.args[0]
    success = activate_premium(target_id, str(user.id))
    if success:
        await update.message.reply_text(f"✅ {target_id} is now Premium!")
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="You're now Premium! 🎉\n\n"
                     "Unlimited slides, all themes, no limits. "
                     "Go ahead and type a topic to get started 🚀"
            )
        except Exception as e:
            logger.error(f"Could not message user: {e}")
    else:
        await update.message.reply_text(f"Could not activate {target_id} — user may not exist yet.")

async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(str(user.id)):
        await update.message.reply_text("Not authorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /revoke <telegram_id>")
        return
    target_id = context.args[0]
    success = revoke_premium(target_id)
    if success:
        await update.message.reply_text(f"Premium revoked for {target_id}")
    else:
        await update.message.reply_text(f"User {target_id} not found")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(str(user.id)):
        await update.message.reply_text("Not authorized.")
        return
    stats = get_total_stats()
    await update.message.reply_text(
        f"SlideBot Stats 📊\n\n"
        f"Total users: {stats['total_users']}\n"
        f"Premium: {stats['premium_users']}\n"
        f"Free: {stats['free_users']}\n"
        f"Total slides made: {stats['total_slides_generated']}"
    )

async def premiumlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(str(user.id)):
        await update.message.reply_text("Not authorized.")
        return
    premium_users = get_premium_users()
    if not premium_users:
        await update.message.reply_text("No premium users yet.")
        return
    msg = "💎 Premium Users:\n\n"
    for uid, u in premium_users.items():
        msg += f"• @{u['username']} — {uid}\n"
    await update.message.reply_text(msg)


# ─── THEME & GENERATION ───────────────────────────────────────────
async def theme_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    theme_name = query.data.replace("theme_", "")
    if theme_name in PREMIUM_THEMES and not is_premium(uid):
        await query.edit_message_text(
            "That theme is for Premium users.\n"
            "Type /upgrade to unlock all themes 💎"
        )
        return
    context.user_data["theme"] = theme_name
    if "pending_topic" in context.user_data and "pending_slides" in context.user_data:
        topic = context.user_data.pop("pending_topic")
        num_slides = context.user_data.pop("pending_slides")
        await start_generation(query, context, topic, num_slides, theme_name)
    else:
        await query.edit_message_text(
            f"Theme set to {theme_name.title()} ✅\n\nNow send your topic!"
        )

async def start_generation(query, context: ContextTypes.DEFAULT_TYPE, topic: str, num_slides: int, theme: str):
    uid = str(query.from_user.id)
    await query.edit_message_text("Working on it... 🤖 Structuring your content")
    try:
        loop = asyncio.get_event_loop()
        slide_data = await asyncio.wait_for(
            loop.run_in_executor(None, generate_slide_content, topic, num_slides),
            timeout=120
        )
        if not slide_data:
            await query.edit_message_text(
                "Something went wrong with the AI. Try again with a shorter topic."
            )
            return
        await query.edit_message_text("Almost done... 📐 Designing your slides")
        filepath = await loop.run_in_executor(None, build_presentation, slide_data, theme)
        increment_usage(uid)
        await query.edit_message_text("Done! Sending your file now ✅")
        with open(filepath, "rb") as f:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=f,
                filename=f"{slide_data.get('title', 'Presentation')}.pptx",
                caption=(
                    f"Here's your presentation! 🎉\n\n"
                    f"Title: {slide_data.get('title', '')}\n"
                    f"Theme: {theme.title()}\n\n"
                    f"{'💎 Premium — unlimited generations!' if is_premium(uid) else 'Free plan — 2 per day. Type /upgrade for unlimited 💎'}"
                )
            )
        os.remove(filepath)
    except asyncio.TimeoutError:
        await query.edit_message_text(
            "Taking too long — please try again with a simpler topic."
        )
    except Exception as e:
        logger.error(f"Generation error: {e}")
        await query.edit_message_text("Something went wrong. Please try again.")

# ─── MESSAGE & PHOTO HANDLERS ─────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    text = update.message.text.strip()
    get_or_create_user(uid, str(user.username or user.first_name))
    if not can_generate(uid):
        await update.message.reply_text(
            "You've hit your free limit for today (2 presentations).\n\n"
            "Come back tomorrow or type /upgrade for unlimited access 💎"
        )
        return
    context.user_data["pending_topic"] = text
    await ask_for_slide_count(update, context)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    username = user.username or user.first_name

    try:
        await context.bot.send_message(
            chat_id=int(ADMIN_ID),
            text=f"📸 Payment screenshot from @{username}\nID: {uid}\n\nActivate: /activate {uid}",
        )
        await context.bot.forward_message(
            chat_id=int(ADMIN_ID),
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
    except Exception as e:
        logger.error(f"Forward error: {e}")

    await update.message.reply_text(
        "Got your screenshot! 📸\n\n"
        "Now type /paid so we know you're ready, and we'll activate your Premium within the hour. 🙏"
    )


# ─── MAIN ─────────────────────────────────────────────────────────
async def main():
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

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
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
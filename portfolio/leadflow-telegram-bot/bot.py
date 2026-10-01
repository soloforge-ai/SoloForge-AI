import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ConversationHandler,
    ContextTypes, MessageHandler, filters,
)

from db import init_db, create_lead, get_lead, update_status, recent_leads, stats
from scoring import score_lead

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID_RAW = os.getenv("ADMIN_CHAT_ID", "").strip()
ADMIN_CHAT_ID = int(ADMIN_CHAT_ID_RAW) if ADMIN_CHAT_ID_RAW.lstrip("-").isdigit() else None

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

NAME, CONTACT, NEED, BUDGET = range(4)
FOOTER = "\n\nPowered by SoloForge AI"

def is_admin(user_id: int) -> bool:
    return ADMIN_CHAT_ID is not None and user_id == ADMIN_CHAT_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚡ <b>LeadFlow by SoloForge AI</b>\n\n"
        "Smart lead intake, qualification, and approval automation.\n\n"
        "<b>Commands</b>\n"
        "/newlead — Submit a new lead\n"
        "/myid — Show your Telegram ID\n"
        "/help — How to use LeadFlow\n"
        "/about — About LeadFlow\n"
        "/cancel — Cancel the current form\n\n"
        "<b>Admin</b>\n"
        "/leads — View recent leads\n"
        "/stats — View pipeline statistics"
        + FOOTER
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🧭 <b>How LeadFlow works</b>\n\n"
        "1. Submit a lead with /newlead\n"
        "2. LeadFlow captures contact details and project requirements\n"
        "3. The lead is automatically qualified\n"
        "4. The admin receives an instant notification\n"
        "5. The admin approves or rejects the lead\n"
        "6. The lead receives an automatic status update\n\n"
        "Use /cancel at any time while submitting a lead."
        + FOOTER
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def about_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ <b>About LeadFlow</b>\n\n"
        "LeadFlow is a Telegram automation workflow that turns incoming inquiries "
        "into a structured lead pipeline.\n\n"
        "It demonstrates lead intake, qualification, persistent storage, admin routing, "
        "approval actions, status updates, and pipeline reporting."
        + FOOTER
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Your Telegram user ID is:\n<code>{update.effective_user.id}</code>" + FOOTER,
        parse_mode="HTML",
    )

async def newlead(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["lead"] = {}
    await update.message.reply_text("1/4 What is your name or company name?")
    return NAME

async def lead_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["lead"]["name"] = update.message.text.strip()
    await update.message.reply_text(
        "2/4 What is the best way to contact you?\n"
        "For example: email, @Telegram username, or another preferred contact method."
    )
    return CONTACT

async def lead_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["lead"]["contact"] = update.message.text.strip()
    await update.message.reply_text(
        "3/4 What would you like us to automate?\n\n"
        "Example: Build a Telegram bot that captures leads, notifies the sales team, "
        "and sends the data to our CRM."
    )
    return NEED

async def lead_need(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["lead"]["need"] = update.message.text.strip()
    await update.message.reply_text(
        "4/4 What is your estimated budget?\n"
        "You can include the currency, for example: $1,000 or 20,000 THB."
    )
    return BUDGET

async def lead_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lead = context.user_data["lead"]
    lead["budget"] = update.message.text.strip()
    score, label = score_lead(lead["budget"], lead["need"])

    user = update.effective_user
    lead_id = create_lead(
        user.id, user.username, lead["name"], lead["contact"],
        lead["need"], lead["budget"], score, label
    )

    await update.message.reply_text(
        "✅ <b>Lead submitted successfully</b>\n\n"
        f"Lead ID: #{lead_id}\n"
        f"Qualification: {label} ({score}/100)\n"
        "Status: PENDING\n\n"
        "Your request has been sent to the team."
        + FOOTER,
        parse_mode="HTML",
    )

    if ADMIN_CHAT_ID:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"approve:{lead_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject:{lead_id}"),
        ]])

        admin_text = (
            f"🔥 <b>NEW LEAD #{lead_id}</b>\n\n"
            f"<b>Name:</b> {lead['name']}\n"
            f"<b>Contact:</b> {lead['contact']}\n"
            f"<b>Need:</b> {lead['need']}\n"
            f"<b>Budget:</b> {lead['budget']}\n\n"
            f"<b>Score:</b> {score}/100 — {label}\n"
            f"<b>Status:</b> PENDING\n"
            f"<b>Telegram:</b> @{user.username or '-'}\n"
            f"<b>User ID:</b> <code>{user.id}</code>"
            + FOOTER
        )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=admin_text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except Exception:
            logger.exception("Could not send admin notification")

    context.user_data.pop("lead", None)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("lead", None)
    await update.message.reply_text("Submission cancelled." + FOOTER)
    return ConversationHandler.END

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.answer("Admin only", show_alert=True)
        return

    action, lead_id_raw = query.data.split(":", 1)
    lead_id = int(lead_id_raw)
    lead = get_lead(lead_id)

    if not lead:
        await query.edit_message_text("Lead not found.")
        return

    status = "APPROVED" if action == "approve" else "REJECTED"
    update_status(lead_id, status)

    symbol = "✅" if status == "APPROVED" else "❌"
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(
        f"{symbol} Lead #{lead_id} → {status}" + FOOTER
    )

    if status == "APPROVED":
        user_text = (
            f"✅ <b>Lead #{lead_id} approved</b>\n\n"
            "Your request has moved to the next stage. "
            "The team will contact you using the details you provided."
        )
    else:
        user_text = (
            f"❌ <b>Lead #{lead_id} not selected</b>\n\n"
            "Thank you for your submission. "
            "The team will not move forward with this request at this time."
        )

    try:
        await context.bot.send_message(
            chat_id=lead["telegram_user_id"],
            text=user_text + FOOTER,
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("Could not notify lead owner")

async def leads_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only.")
        return

    rows = recent_leads(10)
    if not rows:
        await update.message.reply_text("No leads yet." + FOOTER)
        return

    lines = ["📋 <b>Recent Leads</b>\n"]
    for r in rows:
        lines.append(
            f"#{r['id']} | {r['label']} {r['score']}/100 | {r['status']}\n"
            f"{r['name']} — {r['budget']}"
        )

    await update.message.reply_text(
        "\n\n".join(lines) + FOOTER,
        parse_mode="HTML",
    )

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only.")
        return

    s = stats()
    text = (
        "📊 <b>LeadFlow Pipeline</b>\n\n"
        f"Total leads: {s['total']}\n"
        f"Pending: {s['pending']}\n"
        f"Approved: {s['approved']}\n"
        f"Rejected: {s['rejected']}\n"
        f"Average score: {s['avg_score']}"
        + FOOTER
    )
    await update.message.reply_text(text, parse_mode="HTML")

def build_app():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing. Set it in .env.")

    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("newlead", newlead)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, lead_name)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, lead_contact)],
            NEED: [MessageHandler(filters.TEXT & ~filters.COMMAND, lead_need)],
            BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, lead_budget)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("about", about_cmd))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("leads", leads_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(admin_action, pattern=r"^(approve|reject):\d+$"))
    return app

if __name__ == "__main__":
    application = build_app()
    logger.info("LeadFlow by SoloForge AI started")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

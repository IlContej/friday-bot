from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, ChatMemberHandler, MessageHandler, filters, CallbackQueryHandler
from captcha import make_captcha
import asyncio

pending = {}  # user_id -> captcha info
whitelist = set()
blacklist = set()
captcha_time = 90  # secondi

# ---- Handlers ----

async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member.new_chat_member
    if member.user.is_bot or member.user.id in whitelist:
        return

    if member.user.id in blacklist:
        await context.bot.ban_chat_member(update.effective_chat.id, member.user.id)
        await context.bot.unban_chat_member(update.effective_chat.id, member.user.id)
        return

    user = member.user
    chat_id = update.effective_chat.id
    expr, answer = make_captcha()

    await context.bot.restrict_chat_member(chat_id, user.id, ChatPermissions(can_send_messages=False))

    msg = await context.bot.send_message(
        chat_id,
        f"FRIDAY • Verifica accesso\n\n"
        f"{user.first_name}, risolvi: {expr}\n"
        f"Rispondi in reply entro {captcha_time} secondi."
    )

    pending[user.id] = {"answer": answer, "msg_id": msg.message_id, "chat_id": chat_id}
    asyncio.create_task(timeout_kick(context, chat_id, user.id, captcha_time))

async def timeout_kick(context, chat_id, user_id, seconds):
    await asyncio.sleep(seconds)
    if user_id in pending:
        await context.bot.ban_chat_member(chat_id, user_id)
        await context.bot.unban_chat_member(chat_id, user_id)
        await context.bot.send_message(chat_id, "FRIDAY • Verifica fallita. Accesso negato.")
        pending.pop(user_id, None)

async def guard_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user
    if user.id in pending:
        if not update.message.reply_to_message or update.message.reply_to_message.message_id != pending[user.id]["msg_id"]:
            await update.message.delete()
            return
        if not update.message.text.lstrip("-").isdigit():
            await update.message.delete()
            return
        if int(update.message.text) == pending[user.id]["answer"]:
            await context.bot.restrict_chat_member(
                pending[user.id]["chat_id"], user.id,
                ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
            )
            await update.message.reply_text("FRIDAY • Verifica completata.")
            pending.pop(user.id, None)
        else:
            await context.bot.ban_chat_member(pending[user.id]["chat_id"], user.id)
            await context.bot.unban_chat_member(pending[user.id]["chat_id"], user.id)
            await update.message.reply_text("FRIDAY • Risposta errata. Rimosso.")
            pending.pop(user.id, None)

# ---- Admin Panel ----

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Mostra utenti pendenti", callback_data="show_pending")],
        [InlineKeyboardButton("Whitelist/Blacklist", callback_data="edit_lists")],
        [InlineKeyboardButton(f"Timeout captcha ({captcha_time}s)", callback_data="set_timeout")]
    ]
    await update.message.reply_text("FRIDAY • Pannello Admin", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    global captcha_time
    if query.data == "show_pending":
        if pending:
            text = "\n".join([f"{uid} -> {info['answer']}" for uid, info in pending.items()])
        else:
            text = "Nessun utente pendente"
        await query.edit_message_text(f"FRIDAY • Utenti pendenti:\n{text}")
    elif query.data == "edit_lists":
        await query.edit_message_text(
            f"Whitelist: {whitelist}\nBlacklist: {blacklist}\nModifica tramite comandi /addwhitelist /addblacklist /rmwhitelist /rmblacklist"
        )
    elif query.data == "set_timeout":
        await query.edit_message_text(f"Timeout captcha attuale: {captcha_time}s\nModifica via comando /settimeout <secondi>")

# ---- Comandi ----

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("FRIDAY • Protezione attiva.")

async def add_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        uid = int(context.args[0])
        whitelist.add(uid)
        await update.message.reply_text(f"Aggiunto {uid} in whitelist")

async def add_blacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        uid = int(context.args[0])
        blacklist.add(uid)
        await update.message.reply_text(f"Aggiunto {uid} in blacklist")

async def set_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global captcha_time
    if context.args:
        captcha_time = int(context.args[0])
        await update.message.reply_text(f"Timeout captcha impostato a {captcha_time}s")

# ---- Registrazione Handlers ----

def register_handlers(app):
    app.add_handler(ChatMemberHandler(new_member, ChatMemberHandler.ANY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT, guard_messages))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("addwhitelist", add_whitelist))
    app.add_handler(CommandHandler("addblacklist", add_blacklist))
    app.add_handler(CommandHandler("settimeout", set_timeout))
    app.add_handler(CallbackQueryHandler(button_handler))

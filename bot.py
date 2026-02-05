import os
import random
import asyncio
import logging

from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    ChatMemberHandler,
    MessageHandler,
    CommandHandler,
    filters,
)

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN non impostato")

logging.basicConfig(level=logging.INFO)

pending = {}


def make_captcha():
    a = random.randint(2, 15)
    b = random.randint(2, 15)
    op = random.choice(["+", "-", "*"])

    if op == "+":
        return f"{a} + {b}", a + b
    if op == "-":
        return f"{a} - {b}", a - b
    if op == "*":
        return f"{a} × {b}", a * b


async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member.new_chat_member
    if member.user.is_bot:
        return

    user = member.user
    chat_id = update.effective_chat.id

    expr, answer = make_captcha()

    await context.bot.restrict_chat_member(
        chat_id,
        user.id,
        permissions=ChatPermissions(can_send_messages=False)
    )

    msg = await context.bot.send_message(
        chat_id,
        f"FRIDAY • Verifica accesso\n\n"
        f"{user.first_name}, risolvi: {expr}\n"
        f"Rispondi in reply entro 90 secondi."
    )

    pending[user.id] = {"answer": answer, "msg_id": msg.message_id}

    asyncio.create_task(timeout_kick(context, chat_id, user.id, 90))


async def timeout_kick(context, chat_id, user_id, seconds):
    await asyncio.sleep(seconds)

    if user_id in pending:
        await context.bot.ban_chat_member(chat_id, user_id)
        await context.bot.unban_chat_member(chat_id, user_id)

        await context.bot.send_message(
            chat_id,
            "FRIDAY • Verifica fallita. Accesso negato."
        )

        pending.pop(user_id, None)


async def guard_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    text = update.message.text or ""

    if user.id in pending:

        if (
            not update.message.reply_to_message
            or update.message.reply_to_message.message_id
            != pending[user.id]["msg_id"]
        ):
            await update.message.delete()
            return

        if not text.lstrip("-").isdigit():
            await update.message.delete()
            return

        if int(text) == pending[user.id]["answer"]:
            await context.bot.restrict_chat_member(
                chat_id,
                user.id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                ),
            )

            pending.pop(user.id, None)

            await update.message.reply_text(
                "FRIDAY • Verifica completata."
            )

        else:
            await context.bot.ban_chat_member(chat_id, user.id)
            await context.bot.unban_chat_member(chat_id, user.id)
            pending.pop(user.id, None)

            await update.message.reply_text(
                "FRIDAY • Risposta errata. Rimosso."
            )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "FRIDAY • Protezione attiva."
    )


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(ChatMemberHandler(new_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT, guard_messages))
    app.add_handler(CommandHandler("status", status))

    app.run_polling()


if __name__ == "__main__":
    main()
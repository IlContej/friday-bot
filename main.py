import os
import logging
from telegram.ext import ApplicationBuilder
from handlers import register_handlers

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN non impostato")

logging.basicConfig(level=logging.INFO)

app = ApplicationBuilder().token(TOKEN).build()
register_handlers(app)

logging.info("FRIDAY 2.0 online")
app.run_polling()

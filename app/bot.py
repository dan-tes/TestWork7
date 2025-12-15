import asyncio
import logging
import os

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from app.agent import build_app, _checkpointer

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

app = build_app()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Здравствуйте. Опишите, какая услуга вас интересует."
    )

async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    thread_id = f"tg:{chat_id}"

    _checkpointer.delete_thread(thread_id)

    await update.message.reply_text(
        "История диалога очищена."
    )



# -------------------------
# MESSAGE HANDLER
# -------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    # КЛЮЧЕВОЕ МЕСТО
    result = app.invoke(
        {
            "messages": [
                {"role": "human", "content": text}
            ]
        },
        {
            "configurable": {
                "thread_id": f"tg:{chat_id}"
            }
        }
    )

    # Берём последний ответ ассистента
    messages = result.get("messages", [])
    answer = messages[-1]["content"] if messages else "Ошибка обработки запроса."

    await update.message.reply_text(answer)


# -------------------------
# MAIN
# -------------------------

def main():
    application = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("clean", clean))

    logging.info("Telegram bot started")
    application.run_polling()


if __name__ == "__main__":
    main()

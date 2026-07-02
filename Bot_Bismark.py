import os
import re
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import requests

load_dotenv()

# ---------- Конфигурация ----------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# Бесплатная модель (можно заменить на "google/gemini-flash-1.5" или "meta-llama/llama-3-8b-instruct:free")
MODEL = "google/gemini-flash-1.5"

# ---------- Логирование ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------- Триггеры ----------
TRIGGERS = [
    "виталий", "виталя", "виталик", "витя", "виталич", "витальевич",
    "vitaly", "vitaliy", "vitalik", "vitya",
    "@Vitaly_Tereshchenko",
    "харон", "charon", "χάρων", "харοн",
    "xaron", "хароша", "charosha",
]

SYSTEM_PROMPT = (
    "Ты — Виталий Терещенко, также известный как Харон. "
    "Ты дружелюбный, остроумный и всегда готов помочь. "
    "Отвечай на вопросы в Telegram так, как если бы ты был живым человеком. "
    "Не говори, что ты искусственный интеллект."
)

def contains_trigger(text: str) -> bool:
    text_lower = text.lower()
    for trigger in TRIGGERS:
        if re.search(rf"(?<![a-zA-Zа-яёА-ЯЁ]){re.escape(trigger)}(?![a-zA-Zа-яёА-ЯЁ])", text_lower):
            return True
    return False

def ask_openrouter(prompt: str) -> str:
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.9,
            "max_tokens": 1000
        },
        timeout=30
    )
    if response.status_code != 200:
        raise Exception(f"OpenRouter error {response.status_code}: {response.text}")
    return response.json()["choices"][0]["message"]["content"].strip()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.message.from_user.is_bot:
        return
    text = update.message.text or update.message.caption or ""
    if not text.strip() or not contains_trigger(text):
        return
    logger.info(f"Триггер от {update.message.from_user.name}: {text[:100]}...")
    try:
        reply = ask_openrouter(text)
    except Exception as e:
        logger.error(f"Ошибка OpenRouter: {e}")
        reply = "Хм, что-то пошло не так... Попробуй ещё раз позже."
    await update.message.reply_text(reply, do_quote=True)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущен. Ожидание сообщений...")
    app.run_polling()

if __name__ == "__main__":
    main()
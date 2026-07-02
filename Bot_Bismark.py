import os
import re
import time
import logging
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Загружаем переменные из .env (для локального теста) или из переменных окружения Render
load_dotenv()

# ---------- Настройки ----------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Список бесплатных моделей (проверены 02.07.2026)
MODELS = [
    "meta-llama/llama-3.2-3b-instruct:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "google/gemma-4-31b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "microsoft/phi-3-mini-128k-instruct:free",
]

# ---------- Логирование ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------- Триггерные слова ----------
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
    "Отвечай кратко, по делу, на русском языке. "
    "Не говори, что ты искусственный интеллект."
)

def contains_trigger(text: str) -> bool:
    """Проверяет, есть ли в тексте триггерное слово."""
    text_lower = text.lower()
    for trigger in TRIGGERS:
        if re.search(rf"(?<![a-zA-Zа-яёА-ЯЁ]){re.escape(trigger)}(?![a-zA-Zа-яёА-ЯЁ])", text_lower):
            return True
    return False

def ask_ai(prompt: str, max_retries: int = 10) -> str:
    """
    Отправляет запрос в OpenRouter, перебирая модели при ошибках.
    Возвращает текст ответа или запасное сообщение.
    """
    for attempt in range(max_retries):
        model = MODELS[attempt % len(MODELS)]
        try:
            logger.info(f"Попытка {attempt+1}, модель: {model}")
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.9,
                    "max_tokens": 300
                },
                timeout=45
            )

            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0].get("message", {}).get("content", "")
                    if content and content.strip():
                        logger.info(f"✅ Успех с моделью {model}")
                        return content.strip()
                    else:
                        logger.warning(f"Пустой ответ от {model}")
                else:
                    logger.warning(f"Нет choices в ответе от {model}")

            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                logger.warning(f"⏳ Модель {model} перегружена, жду {retry_after}с...")
                time.sleep(retry_after)
            else:
                logger.error(f"Ошибка {response.status_code} от {model}: {response.text[:200]}")
                time.sleep(2)

        except Exception as e:
            logger.error(f"Исключение с моделью {model}: {e}")
            time.sleep(2)

    return "Харон сейчас в царстве Аида, перевозит души. Попробуй позже."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает входящее сообщение, если есть триггер."""
    if update.message is None or update.message.from_user.is_bot:
        return

    text = update.message.text or update.message.caption or ""
    if not text.strip() or not contains_trigger(text):
        return

    logger.info(f"Запрос от {update.message.from_user.name}: {text[:100]}...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    reply = ask_ai(text)
    await update.message.reply_text(reply, do_quote=True)

def main():
    """Запускает бота."""
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("✅ Бот запущен и готов к работе!")
    app.run_polling()

if __name__ == "__main__":
    main()

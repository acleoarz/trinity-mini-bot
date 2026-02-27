import telebot
import requests
import time
import threading

TOKEN = "8540805626:AAFxyYeVsdAZvllGgkv7KUr07dMVUlikXtw"
OPENROUTER_KEY = "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"

bot = telebot.TeleBot(TOKEN)

# ---------------- АНИМАЦИЯ ----------------
def thinking_animation(chat_id, stop_event):
    dots = ["Думает.", "Думает..", "Думает..."]
    i = 0
    current_message = None

    while not stop_event.is_set():
        try:
            if current_message:
                bot.delete_message(chat_id, current_message.message_id)

            current_message = bot.send_message(chat_id, dots[i % 3] + " 🤔")
            i += 1
            time.sleep(1.2)

        except:
            pass

    if current_message:
        try:
            bot.delete_message(chat_id, current_message.message_id)
        except:
            pass


# ---------------- ЗАПРОС К МОДЕЛИ ----------------
def ask_model(user_text):

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "arcee-ai/trinity-mini:free",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты — AI-модель Trinity Mini. "
                        "Ты не OpenAI и не GPT. "
                        "Запрещено упоминать OpenAI или GPT. "
                        "Всегда отвечай на русском языке. "
                        "Сначала подробно проанализируй вопрос в нескольких предложениях. "
                        "Потом напиши строку ===FINAL=== "
                        "и после неё дай краткий финальный ответ."
                    )
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ],
            "max_tokens": 1500
        }
    )

    data = response.json()
    return data["choices"][0]["message"]["content"]


# ---------------- ОБРАБОТЧИК ----------------
@bot.message_handler(content_types=['text'])
def handle_message(message):

    if message.from_user.is_bot:
        return

    stop_event = threading.Event()

    animation_thread = threading.Thread(
        target=thinking_animation,
        args=(message.chat.id, stop_event)
    )
    animation_thread.start()

    full_text = ask_model(message.text)

    stop_event.set()
    animation_thread.join()

    # -------- РАЗДЕЛЕНИЕ THINKING И FINAL --------
    if "===FINAL===" in full_text:
        parts = full_text.split("===FINAL===")
        thinking = parts[0].strip()
        final_answer = parts[1].strip()
    else:
        # если модель не разделила
        split_index = int(len(full_text) * 0.6)
        thinking = full_text[:split_index].strip()
        final_answer = full_text[split_index:].strip()

    # -------- ГОТОВО --------
    done_msg = bot.send_message(message.chat.id, "Готово 🥶")
    time.sleep(2)
    bot.delete_message(message.chat.id, done_msg.message_id)

    # -------- СОХРАНЯЕМ THINKING --------
    with open("Thinking.txt", "w", encoding="utf-8") as f:
        f.write(thinking)

    # -------- ОТПРАВЛЯЕМ THINKING ФАЙЛ --------
    with open("Thinking.txt", "rb") as f:
        bot.send_document(message.chat.id, f)

    # -------- ОТПРАВЛЯЕМ ФИНАЛ --------
    bot.send_message(message.chat.id, final_answer)


print("Trinity Mini запущен...")
bot.infinity_polling()

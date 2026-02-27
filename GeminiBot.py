import os
import requests
import time
import threading
from flask import Flask, request

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

app = Flask(__name__)

# ---------------- TELEGRAM SEND ----------------
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    return requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    }).json()

def delete_message(chat_id, message_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "message_id": message_id
    })

def send_document(chat_id, file_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(file_path, "rb") as f:
        requests.post(url, files={"document": f}, data={"chat_id": chat_id})


# ---------------- АНИМАЦИЯ ----------------
def thinking_animation(chat_id, stop_event):
    dots = ["Думает.", "Думает..", "Думает..."]
    i = 0
    current_message_id = None

    while not stop_event.is_set():
        try:
            if current_message_id:
                delete_message(chat_id, current_message_id)

            response = send_message(chat_id, dots[i % 3] + " 🤔")
            current_message_id = response["result"]["message_id"]
            i += 1
            time.sleep(1.2)

        except:
            pass

    if current_message_id:
        try:
            delete_message(chat_id, current_message_id)
        except:
            pass


# ---------------- ЗАПРОС К МОДЕЛИ ----------------
def ask_model(user_text):
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "arcee-ai/trinity-mini:free",
                "messages": [
                    {"role": "user", "content": user_text}
                ],
                "max_tokens": 1000
            },
            timeout=30
        )

        data = response.json()

        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        else:
            return f"Ошибка API: {data}"

    except Exception as e:
        return f"Ошибка запроса: {str(e)}"


# ---------------- WEBHOOK ----------------
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)

if not data:
    return "ok"

    if "message" not in data:
        return "ok"

    message = data["message"]

    if "text" not in message:
        return "ok"

    if message.get("from", {}).get("is_bot"):
        return "ok"

    chat_id = message["chat"]["id"]
    user_text = message["text"]

    stop_event = threading.Event()

    animation_thread = threading.Thread(
        target=thinking_animation,
        args=(chat_id, stop_event)
    )
    animation_thread.start()

    full_text = ask_model(user_text)

    stop_event.set()
    animation_thread.join()

    # -------- РАЗДЕЛЕНИЕ --------
    if "===FINAL===" in full_text:
        parts = full_text.split("===FINAL===")
        thinking = parts[0].strip()
        final_answer = parts[1].strip()
    else:
        split_index = int(len(full_text) * 0.6)
        thinking = full_text[:split_index].strip()
        final_answer = full_text[split_index:].strip()

    done = send_message(chat_id, "Готово 🥶")
    time.sleep(2)
    delete_message(chat_id, done["result"]["message_id"])

    with open("Thinking.txt", "w", encoding="utf-8") as f:
        f.write(thinking)

    send_document(chat_id, "Thinking.txt")
    send_message(chat_id, final_answer)

    return "ok"


@app.route("/")
def home():
    return "Bot is running"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

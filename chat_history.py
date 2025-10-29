import json
import os
from datetime import datetime

HISTORY_FILE = "chat_history.json"


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []

def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Sohbet geçmişi kaydedilemedi: {e}")
def add_to_history(question: str, answer: str):
    history = load_history()

    new_entry = {
        "soru": question,
        "cevap": answer,
        "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    history.append(new_entry)
    save_history(history)
def get_history():
    return load_history()
def clear_history():
    save_history([])
def get_recent_history(limit: int = 10):
    history = load_history()
    return history[-limit:] if len(history) > limit else history

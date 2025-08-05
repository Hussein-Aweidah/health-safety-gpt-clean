import json
import os

BASE_DIR = "user_data"
CHAT_HISTORY_FILE = os.path.join(BASE_DIR, "chat_history.json")

def save_to_history(question, answer, source, pages, timestamp, confidence=None, session_name="default"):
    history = load_chat_history()

    entry = {
        "question": question,
        "answer": answer,
        "source": source,
        "pages": pages,
        "timestamp": timestamp,
        "session": session_name
    }

    if confidence is not None:
        entry["confidence"] = confidence

    history.append(entry)

    os.makedirs(BASE_DIR, exist_ok=True)
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def load_chat_history():
    if not os.path.exists(CHAT_HISTORY_FILE):
        return []
    with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_chat_history():
    return load_chat_history()

def get_sessions():
    """Returns a set of session names from saved history"""
    history = load_chat_history()
    return sorted(set(entry.get("session", "default") for entry in history))

def load_session(session_name="default"):
    """Loads only interactions from a specific session"""
    return [entry for entry in load_chat_history() if entry.get("session", "default") == session_name]

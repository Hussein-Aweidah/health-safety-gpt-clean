import os
import json
from datetime import datetime

BASE_DIR = os.path.join(os.path.dirname(__file__), "user_data")
os.makedirs(BASE_DIR, exist_ok=True)

# user_memory.py (only change the safe characters in _sessions_file)
def _sessions_file(username):
    if username:
        safe = "".join(c for c in username if c.isalnum() or c in ("-", "_", ".", "@")).lower() or "user"
        return os.path.join(BASE_DIR, f"sessions_{safe}.json")
    return os.path.join(BASE_DIR, "sessions_guest.json")


def _load_file(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_sessions(username=None):
    """Return a list of session names for the given user (or guest)."""
    path = _sessions_file(username)
    data = _load_file(path)
    # data schema: { session_name: { "meta": {...}, "history": [...] } }
    return sorted(list(data.keys()))

def load_session(session_name, username=None):
    """Return chat_history list for the session_name or [] if not found."""
    path = _sessions_file(username)
    data = _load_file(path)
    return data.get(session_name, {}).get("history", [])

def save_to_history(question, answer, source, pages, ts, session_name="default", username=None, chat_history=None):
    """
    Save a single QA or entire chat_history.
    - If chat_history is provided, it replaces the session history.
    - Otherwise, question/answer pair is appended.
    """
    path = _sessions_file(username)
    data = _load_file(path)

    now = datetime.utcnow().isoformat() + "Z"
    sess = data.get(session_name, {"meta": {"created": now, "last_updated": now}, "history": []})

    if chat_history is not None:
        # full replace (used by explicit "Save session" action)
        sess["history"] = chat_history
        sess["meta"]["last_updated"] = now
    else:
        # append single QA if provided
        if question is not None:
            entry = {
                "question": question,
                "answer": answer,
                "source": source,
                "pages": pages,
                "timestamp": ts or now
            }
            sess.setdefault("history", []).append(entry)
            sess["meta"]["last_updated"] = now

    data[session_name] = sess
    _save_file(path, data)
    return True

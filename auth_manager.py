# auth_manager.py
import os, json, hashlib, re
from datetime import datetime

USER_FILE = "user_data/users.json"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _load_users():
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_users(users):
    os.makedirs("user_data", exist_ok=True)
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def signup(username: str, email: str, password: str):
    username = (username or "").strip()
    email = (email or "").strip().lower()

    if not username or not email or not password:
        return False, "Please enter a username, email, and password."
    if not EMAIL_RE.match(email):
        return False, "Please enter a valid email address."

    users = _load_users()
    # Use email as the unique key
    if email in users:
        return False, "That email is already in use."

    users[email] = {
        "password": _hash_pw(password),
        "username": username,                 # display name
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    _save_users(users)
    return True, "Signup successful!"

def login(email: str, password: str):
    email = (email or "").strip().lower()
    users = _load_users()
    if email not in users:
        return False, "Account not found."
    if users[email]["password"] != _hash_pw(password):
        return False, "Incorrect password."
    return True, "Login successful."

def get_profile(email: str):
    """Optional helper to fetch username/display name after login."""
    email = (email or "").strip().lower()
    users = _load_users()
    return users.get(email, None)

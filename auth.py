"""Authentication helpers with hashed passwords."""

import os
import json
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config

USERS_FILE = os.path.join(Config.DATA_PATH, 'users.json')


def _load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)


def _save_users(users):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)


def ensure_default_user():
    """Create default admin account with hashed password if missing."""
    users = _load_users()
    if Config.ADMIN_USERNAME not in users:
        users[Config.ADMIN_USERNAME] = generate_password_hash(Config.ADMIN_PASSWORD)
        _save_users(users)


def verify_user(username, password):
    """Return True if credentials match a stored hash."""
    ensure_default_user()
    users = _load_users()
    stored_hash = users.get(username)
    if not stored_hash:
        return False
    return check_password_hash(stored_hash, password)

import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# We use a simple JSON file to start
# No Supabase needed yet — keeps it simple and free
import json

DB_FILE = "users.json"

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({}, f)
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ─── USER FUNCTIONS ───────────────────────────────────────────────

def get_user(telegram_id: str):
    db = load_db()
    return db.get(str(telegram_id), None)

def create_user(telegram_id: str, username: str):
    db = load_db()
    uid = str(telegram_id)
    if uid not in db:
        db[uid] = {
            "telegram_id": uid,
            "username": username,
            "is_premium": False,
            "slides_today": 0,
            "last_used_date": str(datetime.now().date()),
            "total_presentations": 0,
            "joined": str(datetime.now()),
            "premium_activated_by": None,
            "premium_date": None
        }
        save_db(db)
    return db[uid]

def get_or_create_user(telegram_id: str, username: str):
    user = get_user(telegram_id)
    if not user:
        user = create_user(telegram_id, username)
    return user

def reset_daily_count_if_needed(telegram_id: str):
    db = load_db()
    uid = str(telegram_id)
    user = db.get(uid)
    if not user:
        return
    today = str(datetime.now().date())
    if user["last_used_date"] != today:
        db[uid]["slides_today"] = 0
        db[uid]["last_used_date"] = today
        save_db(db)

def increment_usage(telegram_id: str):
    db = load_db()
    uid = str(telegram_id)
    db[uid]["slides_today"] += 1
    db[uid]["total_presentations"] += 1
    save_db(db)

def is_premium(telegram_id: str) -> bool:
    user = get_user(str(telegram_id))
    if not user:
        return False
    return user.get("is_premium", False)

def can_generate(telegram_id: str) -> bool:
    reset_daily_count_if_needed(telegram_id)
    user = get_user(str(telegram_id))
    if not user:
        return True
    if user["is_premium"]:
        return True
    return user["slides_today"] < 2

def activate_premium(telegram_id: str, activated_by: str):
    db = load_db()
    uid = str(telegram_id)
    if uid in db:
        db[uid]["is_premium"] = True
        db[uid]["premium_activated_by"] = activated_by
        db[uid]["premium_date"] = str(datetime.now())
        save_db(db)
        return True
    return False

def revoke_premium(telegram_id: str):
    db = load_db()
    uid = str(telegram_id)
    if uid in db:
        db[uid]["is_premium"] = False
        save_db(db)
        return True
    return False

# ─── ADMIN FUNCTIONS ──────────────────────────────────────────────

def get_all_users():
    db = load_db()
    return db

def get_premium_users():
    db = load_db()
    return {uid: u for uid, u in db.items() if u.get("is_premium")}

def get_total_stats():
    db = load_db()
    total = len(db)
    premium = sum(1 for u in db.values() if u.get("is_premium"))
    total_slides = sum(u.get("total_presentations", 0) for u in db.values())
    return {
        "total_users": total,
        "premium_users": premium,
        "free_users": total - premium,
        "total_slides_generated": total_slides
    }

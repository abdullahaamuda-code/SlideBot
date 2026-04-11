import os
from datetime import datetime
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

try:
    supabase = create_client(url, key)
    print("✅ Supabase connected successfully")
except Exception as e:
    print(f"❌ Supabase connection error: {e}")
    supabase = None


# ─── USER MANAGEMENT ─────────────────────────────────────────────
def get_user(telegram_id: str):
    if not supabase:
        return None
    try:
        result = supabase.table("users").select("*").eq("telegram_id", str(telegram_id)).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        print(f"get_user error: {e}")
        return None


def create_user(telegram_id: str, username: str):
    if not supabase:
        return None
    try:
        today = datetime.now()
        user_data = {
            "telegram_id": str(telegram_id),
            "username": str(username)[:100],
            "is_premium": False,
            "slides_today": 0,
            "last_used_date": today.strftime("%Y-%m-%d"),
            "total_presentations": 0,
            "joined": today.isoformat(),
            "premium_activated_by": None,
            "premium_date": None,
            "url_uses_this_month": 0,
            "file_uses_this_month": 0,
            "last_month_reset": today.strftime("%Y-%m"),
            "theme": "classic",
            # ── NEW COLUMNS ──
            "preferred_pack": "executive",   # 'executive' or 'magazine'
            "accent_color": None,            # hex string e.g. '#6B2D8B' or None
        }
        result = supabase.table("users").insert(user_data).execute()
        print(f"✅ User created: {telegram_id} ({username})")
        if result.data and len(result.data) > 0:
            return result.data[0]
        return user_data
    except Exception as e:
        print(f"create_user error: {e}")
        return None


def get_or_create_user(telegram_id: str, username: str):
    user = get_user(telegram_id)
    if not user:
        user = create_user(telegram_id, username)
        if not user:
            user = get_user(telegram_id)
    return user


# ─── DAILY / MONTHLY RESET ───────────────────────────────────────
def reset_daily_if_needed(telegram_id: str):
    if not supabase:
        return
    try:
        user = get_user(telegram_id)
        if not user:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        if user.get("last_used_date", "") != today:
            supabase.table("users").update({
                "slides_today": 0,
                "last_used_date": today
            }).eq("telegram_id", str(telegram_id)).execute()
    except Exception as e:
        print(f"reset_daily error: {e}")


def reset_monthly_if_needed(telegram_id: str):
    if not supabase:
        return
    try:
        user = get_user(telegram_id)
        if not user:
            return
        current_month = datetime.now().strftime("%Y-%m")
        if user.get("last_month_reset", "") != current_month:
            supabase.table("users").update({
                "url_uses_this_month": 0,
                "file_uses_this_month": 0,
                "last_month_reset": current_month
            }).eq("telegram_id", str(telegram_id)).execute()
    except Exception as e:
        print(f"reset_monthly error: {e}")


# ─── USAGE TRACKING ──────────────────────────────────────────────
def increment_usage(telegram_id: str):
    if not supabase:
        return
    try:
        user = get_user(telegram_id)
        if not user:
            return
        supabase.table("users").update({
            "slides_today": user.get("slides_today", 0) + 1,
            "total_presentations": user.get("total_presentations", 0) + 1
        }).eq("telegram_id", str(telegram_id)).execute()
    except Exception as e:
        print(f"increment_usage error: {e}")


def increment_url_usage(telegram_id: str):
    if not supabase:
        return
    try:
        reset_monthly_if_needed(telegram_id)
        user = get_user(telegram_id)
        if not user:
            return
        supabase.table("users").update({
            "url_uses_this_month": user.get("url_uses_this_month", 0) + 1
        }).eq("telegram_id", str(telegram_id)).execute()
    except Exception as e:
        print(f"increment_url error: {e}")


def increment_file_usage(telegram_id: str):
    if not supabase:
        return
    try:
        reset_monthly_if_needed(telegram_id)
        user = get_user(telegram_id)
        if not user:
            return
        supabase.table("users").update({
            "file_uses_this_month": user.get("file_uses_this_month", 0) + 1
        }).eq("telegram_id", str(telegram_id)).execute()
    except Exception as e:
        print(f"increment_file error: {e}")


# ─── CHECKS ──────────────────────────────────────────────────────
def can_generate(telegram_id: str) -> bool:
    try:
        reset_daily_if_needed(telegram_id)
        user = get_user(telegram_id)
        if not user:
            return True
        if user.get("is_premium", False):
            return True
        return user.get("slides_today", 0) < 2
    except Exception as e:
        print(f"can_generate error: {e}")
        return True


def can_use_url(telegram_id: str) -> bool:
    try:
        reset_monthly_if_needed(telegram_id)
        user = get_user(telegram_id)
        if not user:
            return True
        if user.get("is_premium", False):
            return True
        return user.get("url_uses_this_month", 0) < 1
    except Exception as e:
        print(f"can_use_url error: {e}")
        return True


def can_use_file(telegram_id: str) -> bool:
    try:
        reset_monthly_if_needed(telegram_id)
        user = get_user(telegram_id)
        if not user:
            return True
        if user.get("is_premium", False):
            return True
        return user.get("file_uses_this_month", 0) < 1
    except Exception as e:
        print(f"can_use_file error: {e}")
        return True


def is_premium(telegram_id: str) -> bool:
    try:
        user = get_user(str(telegram_id))
        if not user:
            return False
        return user.get("is_premium", False)
    except Exception as e:
        print(f"is_premium error: {e}")
        return False


# ─── PREMIUM MANAGEMENT ──────────────────────────────────────────
def activate_premium(telegram_id: str, activated_by: str):
    if not supabase:
        return False
    try:
        user = get_user(str(telegram_id))
        if not user:
            return False
        supabase.table("users").update({
            "is_premium": True,
            "premium_activated_by": activated_by,
            "premium_date": datetime.now().isoformat()
        }).eq("telegram_id", str(telegram_id)).execute()
        return True
    except Exception as e:
        print(f"activate_premium error: {e}")
        return False


def revoke_premium(telegram_id: str):
    if not supabase:
        return False
    try:
        supabase.table("users").update({
            "is_premium": False
        }).eq("telegram_id", str(telegram_id)).execute()
        return True
    except Exception as e:
        print(f"revoke_premium error: {e}")
        return False


# ─── STATISTICS ──────────────────────────────────────────────────
def get_all_users():
    if not supabase:
        return {}
    try:
        result = supabase.table("users").select("*").execute()
        return {u["telegram_id"]: u for u in result.data}
    except Exception as e:
        print(f"get_all_users error: {e}")
        return {}


def get_premium_users():
    if not supabase:
        return {}
    try:
        result = supabase.table("users").select("*").eq("is_premium", True).execute()
        return {u["telegram_id"]: u for u in result.data}
    except Exception as e:
        print(f"get_premium_users error: {e}")
        return {}


def get_total_stats():
    if not supabase:
        return {"total_users": 0, "premium_users": 0, "free_users": 0, "total_slides_generated": 0}
    try:
        result = supabase.table("users").select("*").execute()
        users = result.data
        total = len(users)
        premium = sum(1 for u in users if u.get("is_premium", False))
        total_slides = sum(u.get("total_presentations", 0) for u in users)
        return {
            "total_users": total,
            "premium_users": premium,
            "free_users": total - premium,
            "total_slides_generated": total_slides
        }
    except Exception as e:
        print(f"get_total_stats error: {e}")
        return {"total_users": 0, "premium_users": 0, "free_users": 0, "total_slides_generated": 0}


# ─── THEME ───────────────────────────────────────────────────────
def get_user_theme(telegram_id: str) -> str:
    try:
        user = get_user(str(telegram_id))
        if not user:
            return "classic"
        return user.get("theme", "classic")
    except Exception as e:
        print(f"get_user_theme error: {e}")
        return "classic"


def save_user_theme(telegram_id: str, theme: str):
    if not supabase:
        return False
    try:
        supabase.table("users").update({
            "theme": theme
        }).eq("telegram_id", str(telegram_id)).execute()
        return True
    except Exception as e:
        print(f"save_user_theme error: {e}")
        return False


# ─── PACK & COLOR (NEW) ──────────────────────────────────────────
def get_user_pack(telegram_id: str) -> str:
    """Get user's preferred pack: 'executive' or 'magazine'"""
    try:
        user = get_user(str(telegram_id))
        if not user:
            return "executive"
        return user.get("preferred_pack", "executive") or "executive"
    except Exception as e:
        print(f"get_user_pack error: {e}")
        return "executive"


def save_user_pack(telegram_id: str, pack: str):
    """Save user's preferred pack"""
    if not supabase:
        return False
    try:
        supabase.table("users").update({
            "preferred_pack": pack
        }).eq("telegram_id", str(telegram_id)).execute()
        print(f"📦 Saved pack {pack} for {telegram_id}")
        return True
    except Exception as e:
        print(f"save_user_pack error: {e}")
        return False


def get_user_accent(telegram_id: str):
    """Get user's saved accent color (hex string or None)"""
    try:
        user = get_user(str(telegram_id))
        if not user:
            return None
        return user.get("accent_color", None)
    except Exception as e:
        print(f"get_user_accent error: {e}")
        return None


def save_user_accent(telegram_id: str, color: str):
    """Save user's accent color. color = hex string like '#6B2D8B' or name like 'purple'"""
    if not supabase:
        return False
    try:
        supabase.table("users").update({
            "accent_color": color
        }).eq("telegram_id", str(telegram_id)).execute()
        print(f"🎨 Saved accent {color} for {telegram_id}")
        return True
    except Exception as e:
        print(f"save_user_accent error: {e}")
        return False


# ─── TODAY USAGE ─────────────────────────────────────────────────
def get_today_usage(telegram_id: str) -> int:
    try:
        user = get_user(str(telegram_id))
        if not user:
            return 0
        reset_daily_if_needed(telegram_id)
        user = get_user(str(telegram_id))
        return user.get("slides_today", 0) if user else 0
    except Exception as e:
        print(f"get_today_usage error: {e}")
        return 0


# ─── DEBUG ───────────────────────────────────────────────────────
def debug_print_users():
    if not supabase:
        print("Supabase not connected")
        return
    try:
        result = supabase.table("users").select("*").execute()
        print(f"\n📊 USERS IN DATABASE: {len(result.data)}")
        for user in result.data:
            print(f"  - {user.get('telegram_id')} | {user.get('username')} | "
                  f"Premium: {user.get('is_premium')} | "
                  f"Pack: {user.get('preferred_pack','executive')} | "
                  f"Color: {user.get('accent_color','default')}")
        print("")
    except Exception as e:
        print(f"debug error: {e}")

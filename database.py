import os
from datetime import datetime
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

def get_user(telegram_id: str):
    try:
        result = supabase.table("users").select("*").eq("telegram_id", str(telegram_id)).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        print(f"get_user error: {e}")
        return None

def create_user(telegram_id: str, username: str):
    try:
        user = {
            "telegram_id": str(telegram_id),
            "username": username,
            "is_premium": False,
            "slides_today": 0,
            "last_used_date": str(datetime.now().date()),
            "total_presentations": 0,
            "joined": str(datetime.now()),
            "premium_activated_by": None,
            "premium_date": None,
            "url_uses_this_month": 0,
            "file_uses_this_month": 0,
            "last_month_reset": datetime.now().strftime("%Y-%m"),
        }
        supabase.table("users").insert(user).execute()
        return user
    except Exception as e:
        print(f"create_user error: {e}")
        return None

def get_or_create_user(telegram_id: str, username: str):
    user = get_user(telegram_id)
    if not user:
        user = create_user(telegram_id, username)
    return user

def reset_daily_if_needed(telegram_id: str):
    try:
        user = get_user(telegram_id)
        if not user:
            return
        today = str(datetime.now().date())
        if user["last_used_date"] != today:
            supabase.table("users").update({
                "slides_today": 0,
                "last_used_date": today
            }).eq("telegram_id", str(telegram_id)).execute()
    except Exception as e:
        print(f"reset_daily error: {e}")

def reset_monthly_if_needed(telegram_id: str):
    try:
        user = get_user(telegram_id)
        if not user:
            return
        current_month = datetime.now().strftime("%Y-%m")
        if user.get("last_month_reset") != current_month:
            supabase.table("users").update({
                "url_uses_this_month": 0,
                "file_uses_this_month": 0,
                "last_month_reset": current_month
            }).eq("telegram_id", str(telegram_id)).execute()
    except Exception as e:
        print(f"reset_monthly error: {e}")

def increment_usage(telegram_id: str):
    try:
        user = get_user(telegram_id)
        if not user:
            return
        supabase.table("users").update({
            "slides_today": user["slides_today"] + 1,
            "total_presentations": user["total_presentations"] + 1
        }).eq("telegram_id", str(telegram_id)).execute()
    except Exception as e:
        print(f"increment_usage error: {e}")

def increment_url_usage(telegram_id: str):
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

def can_generate(telegram_id: str) -> bool:
    try:
        reset_daily_if_needed(telegram_id)
        user = get_user(telegram_id)
        if not user:
            return True
        if user["is_premium"]:
            return True
        return user["slides_today"] < 2
    except Exception as e:
        print(f"can_generate error: {e}")
        return True

def can_use_url(telegram_id: str) -> bool:
    try:
        reset_monthly_if_needed(telegram_id)
        user = get_user(telegram_id)
        if not user:
            return True
        if user["is_premium"]:
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
        if user["is_premium"]:
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

def activate_premium(telegram_id: str, activated_by: str):
    try:
        user = get_user(str(telegram_id))
        if not user:
            return False
        supabase.table("users").update({
            "is_premium": True,
            "premium_activated_by": activated_by,
            "premium_date": str(datetime.now())
        }).eq("telegram_id", str(telegram_id)).execute()
        return True
    except Exception as e:
        print(f"activate_premium error: {e}")
        return False

def revoke_premium(telegram_id: str):
    try:
        user = get_user(str(telegram_id))
        if not user:
            return False
        supabase.table("users").update({
            "is_premium": False
        }).eq("telegram_id", str(telegram_id)).execute()
        return True
    except Exception as e:
        print(f"revoke_premium error: {e}")
        return False

def get_all_users():
    try:
        result = supabase.table("users").select("*").execute()
        return {u["telegram_id"]: u for u in result.data}
    except Exception as e:
        print(f"get_all_users error: {e}")
        return {}

def get_premium_users():
    try:
        result = supabase.table("users").select("*").eq("is_premium", True).execute()
        return {u["telegram_id"]: u for u in result.data}
    except Exception as e:
        print(f"get_premium_users error: {e}")
        return {}

def get_total_stats():
    try:
        all_users = supabase.table("users").select("*").execute().data
        total = len(all_users)
        premium = sum(1 for u in all_users if u.get("is_premium"))
        total_slides = sum(u.get("total_presentations", 0) for u in all_users)
        return {
            "total_users": total,
            "premium_users": premium,
            "free_users": total - premium,
            "total_slides_generated": total_slides
        }
    except Exception as e:
        print(f"get_total_stats error: {e}")
        return {"total_users": 0, "premium_users": 0, "free_users": 0, "total_slides_generated": 0}

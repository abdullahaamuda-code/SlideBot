import os
from datetime import datetime
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# Initialize Supabase client with error handling
try:
    supabase = create_client(url, key)
    print("✅ Supabase connected successfully")
except Exception as e:
    print(f"❌ Supabase connection error: {e}")
    supabase = None

# ─── USER MANAGEMENT ──────────────────────────────────────────────
def get_user(telegram_id: str):
    """Get user by telegram_id"""
    if not supabase:
        print("Supabase not connected")
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
    """Create a new user"""
    if not supabase:
        print("Supabase not connected")
        return None
    
    try:
        today = datetime.now()
        user_data = {
            "telegram_id": str(telegram_id),
            "username": str(username)[:100],  # Limit username length
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
    """Get user or create if doesn't exist"""
    user = get_user(telegram_id)
    if not user:
        user = create_user(telegram_id, username)
        # Try to get again after creation
        if not user:
            user = get_user(telegram_id)
    return user

# ─── DAILY RESET ──────────────────────────────────────────────────
def reset_daily_if_needed(telegram_id: str):
    """Reset daily slide count if it's a new day"""
    if not supabase:
        return
    
    try:
        user = get_user(telegram_id)
        if not user:
            return
        
        today = datetime.now().strftime("%Y-%m-%d")
        last_used = user.get("last_used_date", "")
        
        if last_used != today:
            supabase.table("users").update({
                "slides_today": 0,
                "last_used_date": today
            }).eq("telegram_id", str(telegram_id)).execute()
            print(f"🔄 Reset daily count for {telegram_id}")
    except Exception as e:
        print(f"reset_daily error: {e}")

def reset_monthly_if_needed(telegram_id: str):
    """Reset monthly URL/file counts if it's a new month"""
    if not supabase:
        return
    
    try:
        user = get_user(telegram_id)
        if not user:
            return
        
        current_month = datetime.now().strftime("%Y-%m")
        last_reset = user.get("last_month_reset", "")
        
        if last_reset != current_month:
            supabase.table("users").update({
                "url_uses_this_month": 0,
                "file_uses_this_month": 0,
                "last_month_reset": current_month
            }).eq("telegram_id", str(telegram_id)).execute()
            print(f"🔄 Reset monthly counts for {telegram_id}")
    except Exception as e:
        print(f"reset_monthly error: {e}")

# ─── USAGE TRACKING ──────────────────────────────────────────────
def increment_usage(telegram_id: str):
    """Increment user's presentation count"""
    if not supabase:
        return
    
    try:
        user = get_user(telegram_id)
        if not user:
            return
        
        current_slides = user.get("slides_today", 0)
        current_total = user.get("total_presentations", 0)
        
        supabase.table("users").update({
            "slides_today": current_slides + 1,
            "total_presentations": current_total + 1
        }).eq("telegram_id", str(telegram_id)).execute()
        print(f"📊 Incremented usage for {telegram_id}")
    except Exception as e:
        print(f"increment_usage error: {e}")

def increment_url_usage(telegram_id: str):
    """Increment URL usage count"""
    if not supabase:
        return
    
    try:
        reset_monthly_if_needed(telegram_id)
        user = get_user(telegram_id)
        if not user:
            return
        
        current = user.get("url_uses_this_month", 0)
        supabase.table("users").update({
            "url_uses_this_month": current + 1
        }).eq("telegram_id", str(telegram_id)).execute()
        print(f"🔗 Incremented URL usage for {telegram_id}")
    except Exception as e:
        print(f"increment_url error: {e}")

def increment_file_usage(telegram_id: str):
    """Increment file usage count"""
    if not supabase:
        return
    
    try:
        reset_monthly_if_needed(telegram_id)
        user = get_user(telegram_id)
        if not user:
            return
        
        current = user.get("file_uses_this_month", 0)
        supabase.table("users").update({
            "file_uses_this_month": current + 1
        }).eq("telegram_id", str(telegram_id)).execute()
        print(f"📁 Incremented file usage for {telegram_id}")
    except Exception as e:
        print(f"increment_file error: {e}")

# ─── CHECKS ──────────────────────────────────────────────────────
def can_generate(telegram_id: str) -> bool:
    """Check if user can generate a presentation"""
    try:
        reset_daily_if_needed(telegram_id)
        user = get_user(telegram_id)
        
        if not user:
            return True
        
        if user.get("is_premium", False):
            return True
        
        slides_today = user.get("slides_today", 0)
        return slides_today < 2
    except Exception as e:
        print(f"can_generate error: {e}")
        return True

def can_use_url(telegram_id: str) -> bool:
    """Check if user can use URL feature"""
    try:
        reset_monthly_if_needed(telegram_id)
        user = get_user(telegram_id)
        
        if not user:
            return True
        
        if user.get("is_premium", False):
            return True
        
        uses = user.get("url_uses_this_month", 0)
        return uses < 1
    except Exception as e:
        print(f"can_use_url error: {e}")
        return True

def can_use_file(telegram_id: str) -> bool:
    """Check if user can use file feature"""
    try:
        reset_monthly_if_needed(telegram_id)
        user = get_user(telegram_id)
        
        if not user:
            return True
        
        if user.get("is_premium", False):
            return True
        
        uses = user.get("file_uses_this_month", 0)
        return uses < 1
    except Exception as e:
        print(f"can_use_file error: {e}")
        return True

def is_premium(telegram_id: str) -> bool:
    """Check if user is premium"""
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
    """Activate premium for a user"""
    if not supabase:
        return False
    
    try:
        user = get_user(str(telegram_id))
        if not user:
            print(f"❌ User {telegram_id} not found for activation")
            return False
        
        supabase.table("users").update({
            "is_premium": True,
            "premium_activated_by": activated_by,
            "premium_date": datetime.now().isoformat()
        }).eq("telegram_id", str(telegram_id)).execute()
        
        print(f"✅ Activated premium for {telegram_id}")
        return True
    except Exception as e:
        print(f"activate_premium error: {e}")
        return False

def revoke_premium(telegram_id: str):
    """Revoke premium from a user"""
    if not supabase:
        return False
    
    try:
        supabase.table("users").update({
            "is_premium": False
        }).eq("telegram_id", str(telegram_id)).execute()
        
        print(f"✅ Revoked premium for {telegram_id}")
        return True
    except Exception as e:
        print(f"revoke_premium error: {e}")
        return False

# ─── STATISTICS ──────────────────────────────────────────────────
def get_all_users():
    """Get all users"""
    if not supabase:
        return {}
    
    try:
        result = supabase.table("users").select("*").execute()
        return {u["telegram_id"]: u for u in result.data}
    except Exception as e:
        print(f"get_all_users error: {e}")
        return {}

def get_premium_users():
    """Get all premium users"""
    if not supabase:
        return {}
    
    try:
        result = supabase.table("users").select("*").eq("is_premium", True).execute()
        return {u["telegram_id"]: u for u in result.data}
    except Exception as e:
        print(f"get_premium_users error: {e}")
        return {}

def get_total_stats():
    """Get total statistics"""
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

# ─── THEME MANAGEMENT ────────────────────────────────────────────
def get_user_theme(telegram_id: str) -> str:
    """Get user's saved theme preference"""
    try:
        user = get_user(str(telegram_id))
        if not user:
            return "classic"
        return user.get("theme", "classic")
    except Exception as e:
        print(f"get_user_theme error: {e}")
        return "classic"

def save_user_theme(telegram_id: str, theme: str):
    """Save user's theme preference to database"""
    if not supabase:
        return False
    
    try:
        supabase.table("users").update({
            "theme": theme
        }).eq("telegram_id", str(telegram_id)).execute()
        print(f"🎨 Saved theme {theme} for {telegram_id}")
        return True
    except Exception as e:
        print(f"save_user_theme error: {e}")
        return False

def get_today_usage(telegram_id: str) -> int:
    """Get user's usage count for today"""
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

# ─── DEBUG FUNCTION ──────────────────────────────────────────────
def debug_print_users():
    """Debug function to print all users (for admin)"""
    if not supabase:
        print("Supabase not connected")
        return
    
    try:
        result = supabase.table("users").select("*").execute()
        print(f"\n📊 USERS IN DATABASE: {len(result.data)}")
        for user in result.data:
            print(f"  - {user.get('telegram_id')} | {user.get('username')} | Premium: {user.get('is_premium')} | Slides: {user.get('slides_today')}")
        print("")
    except Exception as e:
        print(f"debug error: {e}")

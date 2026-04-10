# Add these to your database.py file

def get_user_theme(telegram_id: str) -> str:
    """Get user's saved theme preference"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT theme FROM users WHERE telegram_id = ?", (telegram_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result and result[0] else "classic"

def save_user_theme(telegram_id: str, theme: str):
    """Save user's theme preference"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET theme = ? WHERE telegram_id = ?", (theme, telegram_id))
    conn.commit()
    conn.close()

def get_today_usage(telegram_id: str) -> int:
    """Get user's usage count for today"""
    conn = get_db_connection()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM usage WHERE telegram_id = ? AND date = ?", (telegram_id, today))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

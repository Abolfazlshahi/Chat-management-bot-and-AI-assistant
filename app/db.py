import json
import sqlite3
import threading
import time
from pathlib import Path

from app import config

_lock = threading.RLock()
_conn = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_seen_at INTEGER,
    credits INTEGER NOT NULL DEFAULT 0,
    is_banned INTEGER NOT NULL DEFAULT 0,
    msg_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    language TEXT NOT NULL DEFAULT 'fa',
    ai_enabled INTEGER NOT NULL DEFAULT 1,
    verify_enabled INTEGER NOT NULL DEFAULT 0,
    antispam_enabled INTEGER NOT NULL DEFAULT 0,
    lock_enabled INTEGER NOT NULL DEFAULT 0,
    link_policy TEXT NOT NULL DEFAULT 'allow_all',
    link_whitelist TEXT NOT NULL DEFAULT '[]',
    welcome_text TEXT,
    goodbye_text TEXT,
    rules TEXT,
    warn_limit INTEGER NOT NULL DEFAULT 3,
    warn_action TEXT NOT NULL DEFAULT 'kick'
);
CREATE TABLE IF NOT EXISTS warnings (
    chat_id INTEGER, user_id INTEGER,
    count INTEGER NOT NULL DEFAULT 0,
    last_reason TEXT, updated_at INTEGER,
    PRIMARY KEY (chat_id, user_id)
);
CREATE TABLE IF NOT EXISTS filters (
    chat_id INTEGER, word TEXT,
    PRIMARY KEY (chat_id, word)
);
CREATE TABLE IF NOT EXISTS faq (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,                 -- NULL یعنی سراسری
    pattern TEXT NOT NULL,
    answer TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ai_apis (
    name TEXT PRIMARY KEY,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL DEFAULT 'POST',
    headers TEXT NOT NULL DEFAULT '{}',
    body_template TEXT NOT NULL DEFAULT '{}',
    response_path TEXT NOT NULL,
    usage_path TEXT DEFAULT 'usage.total_tokens',
    enabled INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY, value TEXT
);
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER, actor_user_id INTEGER, action TEXT,
    target_user_id INTEGER, meta TEXT, created_at INTEGER
);
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER, chat_id INTEGER, due_at INTEGER,
    text TEXT, fired INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS wallets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coin TEXT NOT NULL,
    address TEXT NOT NULL,
    network TEXT
);
"""


def get_conn():
    global _conn
    if _conn is None:
        Path(config.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(config.DATABASE_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL;")
    return _conn


def init_db():
    with _lock:
        get_conn().executescript(SCHEMA)
        # مهاجرت ساده برای دیتابیس‌های قدیمی که ستون usage_path ندارند
        try:
            get_conn().execute("ALTER TABLE ai_apis ADD COLUMN usage_path TEXT DEFAULT 'usage.total_tokens'")
        except Exception:
            pass
        get_conn().commit()
    # ثبت و فعال‌سازی سرویس پیش‌فرض FreeModel (اگر هیچ APIای نباشد)
    seed_default_api()


def _exec(sql, params=()):
    with _lock:
        cur = get_conn().execute(sql, params)
        get_conn().commit()
        return cur


def _one(sql, params=()):
    with _lock:
        return get_conn().execute(sql, params).fetchone()


def _all(sql, params=()):
    with _lock:
        return get_conn().execute(sql, params).fetchall()


# ---------- کاربران و اعتبار ----------
def ensure_user(user_id, username=None):
    if _one("SELECT 1 FROM users WHERE user_id=?", (user_id,)) is None:
        _exec(
            "INSERT INTO users(user_id, username, first_seen_at, credits) VALUES(?,?,?,?)",
            (user_id, username, int(time.time()), get_default_credits()),
        )
    elif username:
        _exec("UPDATE users SET username=? WHERE user_id=?", (username, user_id))


def get_user(user_id):
    return _one("SELECT * FROM users WHERE user_id=?", (user_id,))


def get_credits(user_id):
    ensure_user(user_id)
    return get_user(user_id)["credits"]


def change_credits(user_id, delta):
    ensure_user(user_id)
    _exec("UPDATE users SET credits = MAX(0, credits + ?) WHERE user_id=?", (delta, user_id))
    return get_credits(user_id)


def inc_msg_count(user_id):
    ensure_user(user_id)
    _exec("UPDATE users SET msg_count = msg_count + 1 WHERE user_id=?", (user_id,))


def top_users(limit=10):
    return _all("SELECT user_id, username, msg_count FROM users ORDER BY msg_count DESC LIMIT ?", (limit,))


# ---------- تنظیمات گروه ----------
CHAT_FIELDS = {
    "language", "ai_enabled", "verify_enabled", "antispam_enabled",
    "lock_enabled", "link_policy", "link_whitelist", "welcome_text",
    "goodbye_text", "rules", "warn_limit", "warn_action",
}


def get_chat(chat_id):
    row = _one("SELECT * FROM chats WHERE chat_id=?", (chat_id,))
    if row is None:
        _exec(
            "INSERT INTO chats(chat_id, language, warn_limit, warn_action) VALUES(?,?,?,?)",
            (chat_id, config.DEFAULT_LANGUAGE, config.WARN_LIMIT, config.WARN_ACTION),
        )
        row = _one("SELECT * FROM chats WHERE chat_id=?", (chat_id,))
    return row


def update_chat(chat_id, **fields):
    get_chat(chat_id)
    sets, params = [], []
    for k, v in fields.items():
        if k in CHAT_FIELDS:
            sets.append(f"{k}=?")
            params.append(v)
    if sets:
        params.append(chat_id)
        _exec(f"UPDATE chats SET {', '.join(sets)} WHERE chat_id=?", params)


def get_whitelist(chat_id):
    return json.loads(get_chat(chat_id)["link_whitelist"] or "[]")


def set_whitelist(chat_id, domains):
    update_chat(chat_id, link_whitelist=json.dumps(sorted(set(domains))))


# ---------- وارن ----------
def add_warning(chat_id, user_id, reason=None):
    row = _one("SELECT count FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    count = (row["count"] if row else 0) + 1
    _exec(
        "INSERT INTO warnings(chat_id,user_id,count,last_reason,updated_at) VALUES(?,?,?,?,?) "
        "ON CONFLICT(chat_id,user_id) DO UPDATE SET count=?, last_reason=?, updated_at=?",
        (chat_id, user_id, count, reason, int(time.time()), count, reason, int(time.time())),
    )
    return count


def reset_warning(chat_id, user_id):
    _exec("DELETE FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id))


def get_warning(chat_id, user_id):
    row = _one("SELECT count FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    return row["count"] if row else 0


# ---------- فیلتر کلمات ----------
def add_filter(chat_id, word):
    _exec("INSERT OR IGNORE INTO filters(chat_id, word) VALUES(?,?)", (chat_id, word.lower()))


def remove_filter(chat_id, word):
    _exec("DELETE FROM filters WHERE chat_id=? AND word=?", (chat_id, word.lower()))


def list_filters(chat_id):
    return [r["word"] for r in _all("SELECT word FROM filters WHERE chat_id=?", (chat_id,))]


# ---------- FAQ ----------
def add_faq(chat_id, pattern, answer):
    _exec("INSERT INTO faq(chat_id, pattern, answer) VALUES(?,?,?)", (chat_id, pattern.lower(), answer))


def find_faq(chat_id, text):
    text = (text or "").lower()
    rows = _all("SELECT pattern, answer FROM faq WHERE chat_id IS NULL OR chat_id=?", (chat_id,))
    for r in rows:
        if r["pattern"] and r["pattern"] in text:
            return r["answer"]
    return None


# ---------- مدیریت API ----------
def set_api(cfg):
    _exec(
        "INSERT INTO ai_apis(name, endpoint, method, headers, body_template, response_path, usage_path) "
        "VALUES(?,?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET "
        "endpoint=excluded.endpoint, method=excluded.method, headers=excluded.headers, "
        "body_template=excluded.body_template, response_path=excluded.response_path, usage_path=excluded.usage_path",
        (
            cfg["name"], cfg["endpoint"], cfg.get("method", "POST"),
            json.dumps(cfg.get("headers", {})), json.dumps(cfg.get("body_template", {})),
            cfg["response_path"], cfg.get("usage_path", "usage.total_tokens"),
        ),
    )


def list_apis():
    return _all("SELECT name, enabled FROM ai_apis ORDER BY name")


def activate_api(name):
    if _one("SELECT 1 FROM ai_apis WHERE name=?", (name,)) is None:
        return False
    _exec("UPDATE ai_apis SET enabled=0")
    _exec("UPDATE ai_apis SET enabled=1 WHERE name=?", (name,))
    return True


def get_active_api():
    row = _one("SELECT * FROM ai_apis WHERE enabled=1 LIMIT 1")
    if not row:
        return None
    keys = row.keys()
    return {
        "name": row["name"], "endpoint": row["endpoint"], "method": row["method"],
        "headers": json.loads(row["headers"]), "body_template": json.loads(row["body_template"]),
        "response_path": row["response_path"],
        "usage_path": (row["usage_path"] if "usage_path" in keys else "usage.total_tokens") or "usage.total_tokens",
    }


# پیکربندی پیش‌فرض سرویس FreeModel (https://freemodel.dev) — OpenAI-compatible
DEFAULT_FREEMODEL_API = {
    "name": "freemodel",
    "endpoint": "https://api.freemodel.dev/v1/chat/completions",
    "method": "POST",
    "headers": {
        "Authorization": "Bearer {freemodel_key}",
        "Content-Type": "application/json",
    },
    "body_template": {
        "model": "gpt-4o-mini",
        "max_tokens": 150,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": "{system_prompt}"},
            {"role": "user", "content": "{user_message}"},
        ],
    },
    "response_path": "choices.0.message.content",
    "usage_path": "usage.total_tokens",
}


def seed_default_api():
    """اگر هیچ APIای ثبت نشده باشد، FreeModel را ثبت و فعال می‌کند؛ در غیر این صورت فقط کلید freemodel را به‌روزرسانی می‌کند."""
    api = dict(DEFAULT_FREEMODEL_API)
    headers = dict(api["headers"])
    headers["Authorization"] = f"Bearer {config.FREEMODEL_API_KEY}"
    api["headers"] = headers
    if _one("SELECT 1 FROM ai_apis", ()) is None:
        set_api(api)
        activate_api(api["name"])
    elif config.FREEMODEL_API_KEY and _one("SELECT 1 FROM ai_apis WHERE name='freemodel'", ()) is not None:
        set_api(api)  # فقط هدر/کلید را تازه می‌کند، API فعال را عوض نمی‌کند


# ---------- تنظیمات عمومی (key/value) ----------
def set_setting(key, value):
    _exec("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=?", (key, value, value))


def get_setting(key, default=None):
    row = _one("SELECT value FROM settings WHERE key=?", (key,))
    return row["value"] if row else default


# ---------- اعتبار اولیه و هزینه‌گذاری ----------
def get_default_credits():
    val = get_setting("default_credits")
    return int(val) if val is not None else config.DEFAULT_CREDITS


def set_default_credits(value):
    set_setting("default_credits", str(int(value)))


def get_cost_config():
    mode = get_setting("cost_mode", config.CREDIT_COST_MODE)
    per_message = int(get_setting("cost_per_message", str(config.CREDIT_COST_PER_MESSAGE)))
    tokens_per_credit = int(get_setting("tokens_per_credit", str(config.TOKENS_PER_CREDIT)))
    return mode, per_message, tokens_per_credit


def compute_cost(tokens):
    """هزینه امتیازِ یک پیام را بر اساس حالت تنظیم‌شده حساب می‌کند."""
    import math
    mode, per_message, tokens_per_credit = get_cost_config()
    if mode == "tokens" and tokens:
        return max(1, math.ceil(tokens / max(1, tokens_per_credit)))
    return max(0, per_message)


# ---------- کانال لاگ / ضداسپم / دونیت (همه قابل تنظیم در ربات، نه در کد) ----------
def get_log_channel():
    val = get_setting("log_channel_id")
    if val:
        try:
            return int(val)
        except Exception:
            return None
    return config.LOG_CHANNEL_ID


def set_log_channel(value):
    set_setting("log_channel_id", str(value))


def get_backup_channel():
    val = get_setting("backup_channel_id")
    if val:
        try:
            return int(val)
        except Exception:
            return None
    # اگر کانال بکاپ جدا تنظیم نشده باشد، از کانال لاگ استفاده می‌شود
    return get_log_channel()


def set_backup_channel(value):
    set_setting("backup_channel_id", str(value))


def get_personality():
    return get_setting("personality")


def set_personality(text):
    set_setting("personality", text)


def checkpoint():
    """WAL را در فایل اصلی دیتابیس ادغام می‌کند تا فایل بکاپ کامل و سالم باشد."""
    with _lock:
        try:
            get_conn().execute("PRAGMA wal_checkpoint(TRUNCATE)")
            get_conn().commit()
        except Exception:
            pass


def get_antispam_rate():
    mx = get_setting("antispam_max", str(config.ANTISPAM_MAX_MESSAGES))
    win = get_setting("antispam_window", str(config.ANTISPAM_WINDOW_SECONDS))
    return int(mx), int(win)


def set_antispam_rate(max_messages, window_seconds):
    set_setting("antispam_max", str(int(max_messages)))
    set_setting("antispam_window", str(int(window_seconds)))


def get_donation_mode():
    return get_setting("donation_mode", "off")  # off | crypto | rial | both


def set_donation_mode(mode):
    set_setting("donation_mode", mode)


def get_donation_text():
    return get_setting("donation_text")


def set_donation_text(text):
    set_setting("donation_text", text)


def get_rial_info():
    return get_setting("rial_info")


def set_rial_info(info):
    set_setting("rial_info", info)


def add_wallet(coin, address, network=None):
    _exec("INSERT INTO wallets(coin, address, network) VALUES(?,?,?)", (coin.upper(), address, network))


def remove_wallet(wallet_id):
    _exec("DELETE FROM wallets WHERE id=?", (wallet_id,))


def list_wallets():
    return _all("SELECT id, coin, address, network FROM wallets ORDER BY id")


# ---------- لاگ ----------
def log_action(chat_id, actor, action, target=None, meta=None):
    _exec(
        "INSERT INTO audit_logs(chat_id, actor_user_id, action, target_user_id, meta, created_at) "
        "VALUES(?,?,?,?,?,?)",
        (chat_id, actor, action, target, json.dumps(meta or {}), int(time.time())),
    )


# ---------- یادآور ----------
def add_reminder(user_id, chat_id, due_at, text):
    cur = _exec("INSERT INTO reminders(user_id, chat_id, due_at, text) VALUES(?,?,?,?)",
                (user_id, chat_id, due_at, text))
    return cur.lastrowid


def pending_reminders():
    return _all("SELECT * FROM reminders WHERE fired=0")


def mark_reminder_fired(rid):
    _exec("UPDATE reminders SET fired=1 WHERE id=?", (rid,))
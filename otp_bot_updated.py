import os
import sys
import sqlite3
import re
import asyncio
import threading
import time
import logging
import csv
import zipfile
import shutil
import html
import io
import random
import string
import json
import urllib.request
import urllib.error
import socket
import ssl
import http.client
import urllib.parse
from datetime import datetime, timedelta

try:
    import fcntl
except ImportError:  # pragma: no cover - Linux and Termux provide fcntl
    fcntl = None

from telethon import TelegramClient, events, Button
from telethon.errors import (
    SessionPasswordNeededError, 
    MessageNotModifiedError,
    UserNotParticipantError,
    AlreadyInConversationError,
    FloodWaitError,
)
from telethon.tl.types import ReplyKeyboardMarkup, KeyboardButtonRow, KeyboardButton
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.functions.account import GetPasswordRequest

# ========================= CREDENTIALS =========================
# OPTION A — Hardcode directly (fill in your values here):
_HARDCODED_API_ID    = "26899427"
_HARDCODED_API_HASH  = "345bde74037385c0da104dc18a9984d8"
_HARDCODED_BOT_TOKEN = '8816622445:AAGMSs-juqIY2nye49v8Cx4buO5FaJmYDb0'
_HARDCODED_ADMIN_ID  = "7093175010"

# OPTION B — Environment variables (Replit Secrets / export in shell).
# Environment variables are the source of truth. Hardcoding Telegram
# credentials in this file is unsafe because the file may be shared or backed up.
def _pick(hardcoded: str, env_key: str) -> str:
    return os.getenv(env_key, "").strip() or hardcoded.strip()

_raw_api_id    = _pick(_HARDCODED_API_ID,    "API_ID")
_raw_api_hash  = _pick(_HARDCODED_API_HASH,  "API_HASH")
_raw_bot_token = _pick(_HARDCODED_BOT_TOKEN, "BOT_TOKEN")
_raw_admin_id  = _pick(_HARDCODED_ADMIN_ID,  "ADMIN_ID")

_missing = [k for k, v in [("API_ID", _raw_api_id), ("API_HASH", _raw_api_hash),
                             ("BOT_TOKEN", _raw_bot_token), ("ADMIN_ID", _raw_admin_id)] if not v]
if _missing:
    print(f"❌  Missing required credentials: {', '.join(_missing)}")
    print("    Fill in the _HARDCODED_* strings above or set them as environment variables.")
    sys.exit(1)

API_ID    = int(_raw_api_id)
API_HASH  = _raw_api_hash
BOT_TOKEN = _raw_bot_token
ADMIN_ID  = int(_raw_admin_id)
# ===============================================================

# CHANNELS — separate defaults per log type
PURCHASE_LOG_CHANNEL_ID = -1002175693260   # 🛒 Purchase / order logs
PAYMENT_LOG_CHANNEL_ID  = -1002783520702   # 💳 Payment / deposit logs
USER_INFO_CHANNEL_ID    = -1002290728852   # 👤 User info / activity logs
LOG_CHANNEL_ID = PURCHASE_LOG_CHANNEL_ID  # legacy alias (kept for safety)
CHECK_CHANNELS = ["-1002496713109", "-1003185579355"]
JOIN_URLS = [
    "https://t.me/pfp_void",
    "https://t.me/pfp_void_2"
]

# LINKS & MEDIA
TERMS_URL = "https://tgtele.onrender.com/"

# CWALLET CONFIG
# IMPORTANT: Cwallet Payment Button is a web embed. The direct /payment API
# used by this Telegram auto-pay flow must be enabled/provided for your Cwallet
# account. Do NOT paste a Giveaway API key here.
# You can set CWALLET_API_KEY as an environment variable or via the admin panel
# only if your Cwallet payment/API product supplies that credential.
CWALLET_API_KEY = ""        # Fallback: set via admin panel
CWALLET_API_BASE = "https://gate.cwallet.com/v1"
CWALLET_COIN    = "USDT"   # Default coin
CWALLET_NETWORK = "trc20"  # Default network (TRC20)
_CWALLET_DEFAULT_NETWORKS = [
    ("trc20", "USDT — TRON (TRC20)"),
    ("bep20", "USDT — BNB Smart Chain (BEP20)"),
    ("erc20", "USDT — Ethereum (ERC20)"),
    ("polygon", "USDT — Polygon"),
    ("arbitrum", "USDT — Arbitrum"),
    ("optimism", "USDT — Optimism"),
    ("solana", "USDT — Solana"),
    ("ton", "USDT — TON"),
    ("avalanche", "USDT — Avalanche"),
]
def _cwallet_network_options():
    raw = os.getenv("CWALLET_NETWORKS", "").strip()
    if not raw:
        return _CWALLET_DEFAULT_NETWORKS
    labels = dict(_CWALLET_DEFAULT_NETWORKS)
    out = []
    for item in raw.split(","):
        key = item.strip().lower()
        if key:
            out.append((key, labels.get(key, f"USDT — {key.upper()}")))
    return out or _CWALLET_DEFAULT_NETWORKS

# UPI DETAILS (Manual)
UPI_ID = "8308845697.wallet@phonepe"

# Telegram login codes from sender 777000 are always exactly 5 digits.
# The old pattern \d{4,8} was too broad and matched timestamps, years (e.g. 2024),
# transaction IDs, and other incidental numbers in messages.
# 5-digit: Telegram standard login code
# 6-digit: some two-factor or third-party service codes
# We also exclude common false-positive patterns (4-digit years, 8-digit+ numbers)
# by anchoring to word boundaries and keeping the range tight.
OTP_REGEX = r"(?<!\d)(\d{5,6})(?!\d)"
AUTO_CANCEL_SECONDS = 600 

# ================= CRASH-FREE HD EMOJIS =================
# We use standard HD emojis to completely bypass Telegram's ENTITY_TEXT_INVALID Premium bans
P_YES = '✅'
P_NO = '❌'
P_PKG = '📦'
P_MONEY = '💰'
P_USDT = '💲'
P_INR = '₹'
P_TG = '✈️'
P_GIFT = '🎁'
P_STATS = '📊'
P_CARD = '💳'
P_USERS = '👥'
P_CAL = '📅'
P_PC = '💻'
P_EYE = '👁️'
P_UPI = '🏦'
P_HLK = '🔷'
P_ON = '🟢'
P_OFF = '🔴'
P_ID = '🆔'
P_KEY = '⌨️'
P_GLOBE = '🌎'
P_CART = '🛒'
P_STORE = '🏬'
P_OTP = '🔢'
P_2FA = '🔐'
P_FLAG = '🏳️'
P_PHONE = '📱'
P_WAIT = '⏳'
P_TIME = '⏰'
P_WARN = '⚠️'
P_DOC = '📃'
P_SOS = '🆘'
P_ASST = '🤖'
P_ACC = '👤'

# ================= INITIALIZATION =================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Dependency check ──────────────────────────────────────────────────────────
def _check_deps():
    """Warn about optional but important dependencies at startup."""
    missing = []
    warnings = []
    try:
        import telethon  # noqa: F401
    except ImportError:
        missing.append("telethon  →  pip install telethon")
    try:
        import dotenv    # noqa: F401
    except ImportError:
        warnings.append("python-dotenv (optional, env vars must be set manually)  →  pip install python-dotenv")
    try:
        import qrcode    # noqa: F401
    except ImportError:
        warnings.append("qrcode (UPI QR generation disabled)  →  pip install qrcode pillow")
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        warnings.append("pillow (UPI QR generation disabled)  →  pip install pillow")
    if missing:
        print("❌  MISSING REQUIRED DEPENDENCIES — bot cannot start:")
        for m in missing: print(f"    {m}")
        sys.exit(1)
    if warnings:
        print("⚠️   Optional dependencies missing (degraded functionality):")
        for w in warnings: print(f"    {w}")

_check_deps()
# ─────────────────────────────────────────────────────────────────────────────

# ================= CONCURRENCY-SAFE SQLITE =================
# A single sqlite3 connection is intentionally used by this bot, but it is shared
# by many asyncio handlers.  WAL alone does not prevent two handlers (or two
# accidentally-started bot processes) from briefly racing for the SQLite writer
# lock.  The connection below adds three layers of protection:
#   1. a process-local re-entrant lock for every write statement;
#   2. a generous SQLite busy timeout for another process holding the writer lock;
#   3. bounded retry/backoff for transient SQLITE_BUSY/SQLITE_LOCKED errors.
#
# The retry is deliberately at the connection/cursor boundary so legacy queries
# throughout this large bot receive the same protection without relying on every
# call site remembering a special helper.
_db_write_lock = threading.RLock()
_SQLITE_BUSY_TIMEOUT_MS = max(5_000, int(os.getenv("SQLITE_BUSY_TIMEOUT_MS", "60000")))
_SQLITE_RETRY_ATTEMPTS = max(1, int(os.getenv("SQLITE_RETRY_ATTEMPTS", "12")))


def _sqlite_is_read(sql: str) -> bool:
    """Return True only for statements that do not acquire a SQLite write lock."""
    first_word = sql.lstrip().split(None, 1)[0].upper() if sql.strip() else ""
    return first_word in {"SELECT", "EXPLAIN", "PRAGMA"}


def _sqlite_is_busy_error(error: BaseException) -> bool:
    if not isinstance(error, sqlite3.OperationalError):
        return False
    message = str(error).lower()
    return "database is locked" in message or "database table is locked" in message or "database is busy" in message


def _sqlite_retry(operation, operation_name: str):
    """Retry only transient SQLite lock errors, then preserve the real exception."""
    delay = 0.08
    for attempt in range(_SQLITE_RETRY_ATTEMPTS + 1):
        try:
            return operation()
        except sqlite3.OperationalError as error:
            if not _sqlite_is_busy_error(error) or attempt >= _SQLITE_RETRY_ATTEMPTS:
                raise
            # Exponential backoff with a cap avoids a thundering herd when many
            # Telegram callbacks arrive at once, while busy_timeout handles the
            # normal cross-process wait inside SQLite itself.
            time.sleep(min(delay, 1.5))
            delay *= 1.7


class _ResilientSQLiteCursor(sqlite3.Cursor):
    def execute(self, sql, parameters=()):
        def run():
            return sqlite3.Cursor.execute(self, sql, parameters)

        if _sqlite_is_read(sql):
            return _sqlite_retry(run, "cursor.execute")
        with _db_write_lock:
            return _sqlite_retry(run, "cursor.execute")

    def executemany(self, sql, parameters):
        def run():
            return sqlite3.Cursor.executemany(self, sql, parameters)

        with _db_write_lock:
            return _sqlite_retry(run, "cursor.executemany")

    def executescript(self, sql_script):
        with _db_write_lock:
            return _sqlite_retry(
                lambda: sqlite3.Cursor.executescript(self, sql_script),
                "cursor.executescript",
            )


class _ResilientSQLiteConnection(sqlite3.Connection):
    def cursor(self, factory=None):
        return sqlite3.Connection.cursor(
            self, factory or _ResilientSQLiteCursor
        )

    def execute(self, sql, parameters=()):
        # Connection.execute() otherwise creates a plain sqlite3.Cursor, which
        # would bypass the retry/lock behavior above.
        return self.cursor().execute(sql, parameters)

    def executemany(self, sql, parameters):
        return self.cursor().executemany(sql, parameters)

    def executescript(self, sql_script):
        return self.cursor().executescript(sql_script)

    def commit(self):
        with _db_write_lock:
            return _sqlite_retry(lambda: sqlite3.Connection.commit(self), "commit")

    def rollback(self):
        with _db_write_lock:
            return _sqlite_retry(lambda: sqlite3.Connection.rollback(self), "rollback")


def _prepare_database_path() -> str:
    """Return a writable absolute SQLite path and create its parent directory."""
    configured_path = os.getenv("OTP_DB_PATH", "").strip()
    if not configured_path:
        # Keep the default database in Termux's private, writable home
        # directory. The script may live under /storage/emulated/0, where
        # SQLite cannot write until Android storage access is granted.
        configured_path = os.path.join(
            os.path.expanduser("~"),
            "otp_bot_data",
            "otp_bot_final.db",
        )

    database_path = os.path.abspath(os.path.expanduser(configured_path))
    database_dir = os.path.dirname(database_path)

    try:
        os.makedirs(database_dir, exist_ok=True)
    except OSError as error:
        raise RuntimeError(
            f"Cannot create the SQLite directory '{database_dir}'. "
            "On Termux, run 'termux-setup-storage' and allow storage access, "
            "or set OTP_DB_PATH to a writable path under $HOME."
        ) from error

    if not os.access(database_dir, os.W_OK):
        raise RuntimeError(
            f"SQLite directory is not writable: '{database_dir}'. "
            "On Termux, run 'termux-setup-storage' and allow storage access, "
            "or set OTP_DB_PATH to a writable path under $HOME."
        )

    return database_path


_database_path = _prepare_database_path()
_data_dir = os.path.dirname(_database_path)
_sessions_dir = os.path.join(_data_dir, "sessions")
_backups_dir = os.path.join(_data_dir, "backups")
os.makedirs(_sessions_dir, exist_ok=True)
os.makedirs(_backups_dir, exist_ok=True)

_instance_lock_handle = None

def _acquire_instance_lock() -> None:
    """Prevent two copies from sending the same background notifications."""
    global _instance_lock_handle
    lock_path = os.path.join(_data_dir, "bot_instance.lock")
    _instance_lock_handle = open(lock_path, "a+", encoding="utf-8")
    if fcntl is None:
        return
    try:
        fcntl.flock(
            _instance_lock_handle.fileno(),
            fcntl.LOCK_EX | fcntl.LOCK_NB,
        )
    except BlockingIOError:
        print("❌ Another copy of this bot is already running. Stop it before starting a new copy.")
        _instance_lock_handle.close()
        _instance_lock_handle = None
        raise SystemExit(1)

_acquire_instance_lock()


def _resolve_session_base(session_path: str) -> str:
    """Resolve old relative stock paths and new absolute paths consistently."""
    raw_path = os.path.expanduser(str(session_path or "")).strip()
    if not raw_path:
        return ""

    candidates = [
        raw_path,
        os.path.join(_data_dir, raw_path),
        os.path.join(_sessions_dir, os.path.basename(raw_path)),
    ]
    for candidate in candidates:
        candidate_base = candidate[:-8] if candidate.endswith(".session") else candidate
        if os.path.exists(candidate_base + ".session"):
            return candidate_base

    # New records use the private data directory even before the file exists.
    if not os.path.isabs(raw_path):
        return os.path.join(_data_dir, raw_path)
    return raw_path[:-8] if raw_path.endswith(".session") else raw_path


def _safe_extract_zip(zip_ref: zipfile.ZipFile, destination: str) -> None:
    """Extract a ZIP without allowing entries to escape the destination."""
    destination_root = os.path.realpath(destination) + os.sep
    for member in zip_ref.infolist():
        target = os.path.realpath(os.path.join(destination, member.filename))
        if not target.startswith(destination_root):
            raise ValueError(f"Unsafe ZIP entry: {member.filename!r}")
    zip_ref.extractall(destination)


session_name = os.path.join(_sessions_dir, f"bot_session_{BOT_TOKEN.split(':')[0]}")
bot = TelegramClient(session_name, API_ID, API_HASH)
bot.parse_mode = 'html'

db = sqlite3.connect(
    _database_path,
    check_same_thread=False,
    timeout=_SQLITE_BUSY_TIMEOUT_MS / 1000,
    isolation_level=None,
    factory=_ResilientSQLiteConnection,
)
db.execute(f"PRAGMA busy_timeout={_SQLITE_BUSY_TIMEOUT_MS}")
db.execute("PRAGMA journal_mode=WAL")
db.execute("PRAGMA synchronous=NORMAL")  # safe with WAL; faster than FULL
db.execute("PRAGMA wal_autocheckpoint=1000")
db.execute("PRAGMA temp_store=MEMORY")
# cur is kept only for setup_db() executescript; all runtime queries use db.execute()
cur = db.cursor()

BOT_START_TIME: float = time.time()
active_orders = {}      
waiting_proof = {}      
deposit_input = {}          # uid → {step, val/method, ts}
_BOT_ID = None              # FIX Bug 7: cached once in main() — avoids a get_me() network call on every chat-action event
admin_dep_state = {}        # uid → {target_uid, dep_id, step, msg_id, ts}
user_spam_cooldown = {}     # uid → float timestamp
force_join_prompt_cooldown = {}  # uid → first force-join prompt timestamp
session_buy_state = {}      # uid → {country, year, price, stock, category, ts}
custom_dep_amt = {}         # dep_id → amount string  (admin custom keypad)
custom_dep_ts = {}          # dep_id → float timestamp (parallel age tracker)     
low_stock_alert_state = {}  # country → (threshold, count) for the current low-stock period
_active_admin_conv: dict[int, asyncio.Task] = {}    # uid → running admin event-handler task (cancelled by /cancel or new button)

# Per-user asyncio lock — prevents the same user from issuing concurrent purchases.
# Dict is intentionally kept small: only users with in-flight operations hold an entry.
# Old entries persist after the operation completes, but asyncio.Lock is tiny (~200 B),
# so the total footprint stays well under 1 MB for any realistic user base.
user_locks: dict[int, asyncio.Lock] = {}

def get_user_lock(uid: int) -> asyncio.Lock:
    # setdefault is atomic in CPython — avoids the check-then-set race where
    # two coroutines could each create a *different* Lock for the same uid and
    # then neither actually serialises the other.
    return user_locks.setdefault(uid, asyncio.Lock())


# ================= MEDIA CACHE (QR images persist across restarts) =================
# Root cause of the Termux restart / QR corruption bug:
#   The old code downloaded QR images to local files and stored the file PATH in the
#   DB.  On Termux restart the working directory can change, temp files are cleaned up,
#   or file-system state is simply gone — so os.path.exists() returns False and the
#   QR is silently skipped.
#
# Fix: store the raw image bytes as a BLOB in the media_cache table (same .db file
#   that already survives every restart).  No file-system dependency at all.
#   send_qr_blob() returns an io.BytesIO that Telethon's send_file() accepts directly.

class _NamedBytesIO(io.BytesIO):
    """io.BytesIO subclass with a .name attribute.
    Telethon reads .name to pick the correct MIME type; without it
    image blobs are uploaded as generic documents instead of photos.
    """
    def __init__(self, data: bytes, name: str = 'photo.jpg'):
        super().__init__(data)
        self.name = name


def _save_media_blob(key: str, data: bytes, mime: str = 'image/jpeg') -> None:
    """Store image bytes in the media_cache table, keyed by `key`."""
    with _db_write_lock:
        db.execute(
            "INSERT OR REPLACE INTO media_cache (key, data, mime) VALUES (?,?,?)",
            (key, data, mime)
        )
        db.commit()

def _load_media_blob(key: str):
    """Return _NamedBytesIO for the stored image, or None if not found.
    The .name attribute tells Telethon to upload it as a photo, not a document.
    """
    row = db.execute("SELECT data FROM media_cache WHERE key=?", (key,)).fetchone()
    if row and row[0]:
        return _NamedBytesIO(bytes(row[0]), name=f'{key}.jpg')
    return None

def _delete_media_blob(key: str) -> None:
    """Remove a stored image blob."""
    with _db_write_lock:
        db.execute("DELETE FROM media_cache WHERE key=?", (key,))
        db.commit()

async def _read_photo_bytes(msg) -> bytes | None:
    """Download a Telethon photo/document message into memory and return raw bytes."""
    try:
        buf = io.BytesIO()
        await bot.download_media(msg, file=buf)
        buf.seek(0)  # Reset position before reading
        data = buf.read()
        if not data:
            logger.warning("_read_photo_bytes: empty data after download")
            return None
        return data
    except Exception as _e:
        logger.warning(f"_read_photo_bytes failed: {_e}")
        return None

async def _send_with_blob_fallback(send_fn, blob_key: str, file_path_or_url: str | None, **kwargs):
    """Try to send a file, falling back to the DB blob if the local path is gone.

    send_fn  — coroutine factory: async callable that takes `file` as first positional arg
    blob_key — key in media_cache table
    file_path_or_url — legacy local path or http URL (may be None / stale)
    **kwargs — extra args forwarded to send_fn
    """
    # 1. Try local path / URL (backward compat for existing setups)
    if file_path_or_url:
        try:
            if file_path_or_url.startswith("http") or os.path.exists(file_path_or_url):
                return await send_fn(file_path_or_url, **kwargs)
        except Exception as _fp_e:
            logger.debug(f"File-path send failed for {blob_key}, trying DB blob: {_fp_e}")

    # 2. Try the DB blob (the reliable path post-restart)
    blob = _load_media_blob(blob_key)
    if blob:
        try:
            blob.seek(0)  # Ensure read position is at start
            return await send_fn(blob, **kwargs)
        except Exception as _bl_e:
            logger.warning(f"DB blob send failed for {blob_key}: {_bl_e}")

    return None  # Caller must handle the None case
# ==================================================================================


# ================= FLOOD-SAFE TELEGRAM CALL WRAPPER =================
# All outbound Telegram API calls that are not inside a polling loop should go
# through _tg_call() so that FloodWaitError is handled uniformly.
#
# Usage:  await _tg_call(bot.send_message, chat_id, text, buttons=btns)
#         await _tg_call(bot.edit_message, uid, msg_id, new_text)
#
# Parameters:
#   fn          — the bot/client method to call (NOT an already-awaited coroutine)
#   *args       — positional args forwarded to fn
#   _retries    — max attempts before re-raising (default 4)
#   _max_wait   — cap on how long we sleep for a single FloodWait (default 300 s)
#   **kwargs    — keyword args forwarded to fn
#
# Behaviour:
#   • On FloodWaitError: sleep the required time (capped at _max_wait), then retry.
#   • On MessageNotModifiedError: return None immediately (edit was a no-op).
#   • On any other exception after all retries: re-raise so callers can handle it.
async def _tg_call(fn, *args, _retries: int = 4, _max_wait: int = 300, **kwargs):
    last_err = None
    for attempt in range(_retries):
        try:
            return await fn(*args, **kwargs)
        except FloodWaitError as fw:
            wait = min(fw.seconds + 2, _max_wait)
            logger.warning(
                f"FloodWait {fw.seconds}s on {getattr(fn, '__name__', fn)!r} "
                f"(attempt {attempt + 1}/{_retries}) — sleeping {wait}s"
            )
            last_err = fw
            if attempt < _retries - 1:
                await asyncio.sleep(wait)
        except MessageNotModifiedError:
            return None   # edit was a no-op; caller does not need to handle this
        except Exception:
            raise
    raise last_err  # exhausted retries on FloodWait
# =====================================================================


# ================= DATABASE SCHEMA =================
def setup_db():
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 0,
        referred_by INTEGER,
        total_deposited INTEGER DEFAULT 0,
        joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        banned INTEGER DEFAULT 0,
        discount INTEGER DEFAULT 0,
        terms_accepted INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE IF NOT EXISTS stock (
        phone TEXT PRIMARY KEY,
        session_file TEXT,
        country_name TEXT,
        country_icon TEXT DEFAULT '🌍',
        account_year INTEGER,
        category TEXT DEFAULT 'Fresh',
        price INTEGER,
        available INTEGER DEFAULT 1,
        twofa TEXT DEFAULT 'None',
        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS auto_prices (
        country TEXT,
        year TEXT,
        price INTEGER,
        PRIMARY KEY (country, year)
    );
    CREATE TABLE IF NOT EXISTS deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        method_name TEXT,
        status TEXT, 
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS upi_orders (
        order_id TEXT PRIMARY KEY,
        user_id INTEGER,
        amount INTEGER,
        status TEXT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        country TEXT,
        year INTEGER,
        price INTEGER,
        phone TEXT,
        otp TEXT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS custom_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        caption TEXT,
        qr_file_id TEXT
    );
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        p_add_stock INTEGER DEFAULT 0,
        p_manage_stock INTEGER DEFAULT 0,
        p_stats INTEGER DEFAULT 0,
        p_bal INTEGER DEFAULT 0,
        p_settings INTEGER DEFAULT 0,
        p_broadcast INTEGER DEFAULT 0,
        p_userinfo INTEGER DEFAULT 0,
        p_ban INTEGER DEFAULT 0,
        p_payments INTEGER DEFAULT 0,
        p_faq INTEGER DEFAULT 0,
        p_forcejoin INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS custom_countries (
        code TEXT PRIMARY KEY,
        name TEXT,
        flag TEXT
    );
    CREATE TABLE IF NOT EXISTS faq_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS force_join_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT NOT NULL,
        join_url TEXT NOT NULL,
        type TEXT DEFAULT 'channel'
    );
    CREATE TABLE IF NOT EXISTS waiting_proof_db (
        user_id INTEGER PRIMARY KEY,
        amount INTEGER,
        method TEXT,
        expires_at REAL,
        msg_id INTEGER
    );
    CREATE TABLE IF NOT EXISTS active_orders_db (
        phone TEXT PRIMARY KEY,
        user_id INTEGER,
        price INTEGER,
        country TEXT,
        year INTEGER,
        c_icon TEXT,
        twofa TEXT,
        sess TEXT,
        start_time REAL,
        msg_id INTEGER
    );
    CREATE TABLE IF NOT EXISTS payment_proofs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        method TEXT,
        proof_type TEXT,
        proof_data TEXT,
        submitted_at REAL DEFAULT (strftime('%s','now')),
        dep_id INTEGER
    );
    CREATE TABLE IF NOT EXISTS cwallet_invoices (
        invoice_id TEXT PRIMARY KEY,
        user_id INTEGER,
        amount_inr INTEGER,
        amount_usdt TEXT,
        bonus_pct INTEGER DEFAULT 0,
        address TEXT,
        dep_id INTEGER,
        status TEXT DEFAULT 'pending',
        created_at REAL DEFAULT (strftime('%s','now')),
        expires_at REAL,
        msg_id INTEGER
    );
    CREATE TABLE IF NOT EXISTS media_cache (
        key TEXT PRIMARY KEY,
        data BLOB NOT NULL,
        mime TEXT DEFAULT 'image/jpeg'
    );
    """)
    db.commit()

setup_db()
# The ALTER TABLE calls below are idempotent schema migrations.  SQLite raises
# OperationalError: "duplicate column name" if the column already exists, which is
# expected on every run after the first.  We intentionally suppress that specific
# error and log everything else so real problems are still visible.
def _migrate(sql: str) -> None:
    try:
        db.execute(sql)
        db.commit()
    except Exception as _m_err:
        if "duplicate column" not in str(_m_err).lower():
            logger.warning(f"Schema migration warning ({sql!r:.60}): {_m_err}")

_migrate("ALTER TABLE force_join_channels ADD COLUMN type TEXT DEFAULT 'channel'")
_migrate("ALTER TABLE users ADD COLUMN fj_verified INTEGER DEFAULT 0")
# Performance index — large stock tables become slow without this
_migrate(
    "CREATE INDEX IF NOT EXISTS idx_stock_buy "
    "ON stock(country_name, price, category, available, account_year)"
)
# Rename legacy 'Good' category to 'Fresh' — one-time data migration
try:
    with _db_write_lock:
        db.execute("UPDATE stock SET category='Fresh' WHERE category='Good'")
        db.commit()
except Exception as _cat_migrate_err:
    logger.warning(f"Category rename migration warning: {_cat_migrate_err}")
# Grandfather existing users who already accepted T&C — runs ONCE on first deploy only.
# Guarded by a settings flag so it never fires again after admin resets fj_verified via the
# force-join panel; without the guard, every bot restart would re-grant fj_verified=1 to all
# terms-accepted users, silently bypassing any force-join channel the admin had just added.
try:
    _gf_done = db.execute("SELECT value FROM settings WHERE key='_fj_grandfather_done'").fetchone()
    if not _gf_done:
        with _db_write_lock:
            db.execute("UPDATE users SET fj_verified=1 WHERE terms_accepted=1 AND fj_verified=0")
            db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('_fj_grandfather_done', '1')")
            db.commit()
except Exception as _gf_err:
    logger.warning(f"Grandfather fj_verified update failed: {_gf_err}")
for _col in ['p_broadcast', 'p_userinfo', 'p_ban', 'p_payments', 'p_faq', 'p_forcejoin']:
    _migrate(f"ALTER TABLE admins ADD COLUMN {_col} INTEGER DEFAULT 0")

# ── New feature tables & columns ──────────────────────────────────────────────
_migrate("CREATE TABLE IF NOT EXISTS wishlist (user_id INTEGER, country_name TEXT, PRIMARY KEY(user_id, country_name))")
_migrate("CREATE TABLE IF NOT EXISTS scheduled_broadcasts (id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT, btn_name TEXT, btn_url TEXT, send_at TEXT, created_by INTEGER, sent INTEGER DEFAULT 0, claimed_at REAL DEFAULT 0)")
_migrate("ALTER TABLE scheduled_broadcasts ADD COLUMN claimed_at REAL DEFAULT 0")
_migrate("ALTER TABLE users ADD COLUMN reseller INTEGER DEFAULT 0")
_migrate("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'")
_migrate("""CREATE TABLE IF NOT EXISTS promo_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL COLLATE NOCASE,
    discount_pct INTEGER NOT NULL,
    max_uses INTEGER DEFAULT 1,
    uses_count INTEGER DEFAULT 0,
    expires_at TEXT,
    created_by INTEGER,
    category TEXT
)""")
_migrate("CREATE TABLE IF NOT EXISTS user_coupons (user_id INTEGER, code TEXT COLLATE NOCASE, used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user_id, code))")
_migrate("ALTER TABLE promo_codes ADD COLUMN coupon_type TEXT DEFAULT 'discount'")
_migrate("ALTER TABLE promo_codes ADD COLUMN balance_amount INTEGER DEFAULT 0")
_migrate("""CREATE TABLE IF NOT EXISTS bundle_deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    category TEXT NOT NULL,
    buy_qty INTEGER NOT NULL,
    free_qty INTEGER NOT NULL,
    active INTEGER DEFAULT 1
)""")
_migrate("CREATE TABLE IF NOT EXISTS fav_countries (user_id INTEGER, country_name TEXT, PRIMARY KEY (user_id, country_name))")
_migrate("""CREATE TABLE IF NOT EXISTS admin_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    target_uid INTEGER,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")

# ── Persistence helpers for in-memory state ────────────────────────────────────
def _save_waiting_proof(uid: int, data: dict) -> None:
    """Persist a waiting_proof entry to DB so it survives restarts."""
    try:
        with _db_write_lock:
            db.execute(
                "INSERT OR REPLACE INTO waiting_proof_db (user_id, amount, method, expires_at, msg_id) "
                "VALUES (?,?,?,?,?)",
                (uid, data.get('amount'), data.get('method'), data.get('expires_at', 0), data.get('msg_id'))
            )
            db.commit()
    except Exception as _e:
        logger.warning(f"_save_waiting_proof uid={uid}: {_e}")

def _clear_waiting_proof_db(uid: int) -> None:
    """Remove a waiting_proof entry from DB."""
    try:
        with _db_write_lock:
            db.execute("DELETE FROM waiting_proof_db WHERE user_id=?", (uid,))
            db.commit()
    except Exception as _e:
        logger.warning(f"_clear_waiting_proof_db uid={uid}: {_e}")

def _restore_waiting_proof() -> None:
    """On startup: load persisted (unexpired) waiting_proof rows back into memory."""
    now = time.time()
    try:
        rows = db.execute(
            "SELECT user_id, amount, method, expires_at, msg_id FROM waiting_proof_db"
        ).fetchall()
        expired_uids = []
        for uid, amount, method, expires_at, msg_id in rows:
            if expires_at and expires_at > now:
                waiting_proof[uid] = {
                    'amount': amount, 'method': method,
                    'expires_at': expires_at, 'msg_id': msg_id
                }
            else:
                expired_uids.append(uid)
        if expired_uids:
            with _db_write_lock:
                for uid in expired_uids:
                    db.execute("DELETE FROM waiting_proof_db WHERE user_id=?", (uid,))
                db.commit()
        logger.info(f"Restored {len(waiting_proof)} waiting_proof entries from DB (discarded {len(expired_uids)} expired)")
    except Exception as _e:
        logger.error(f"_restore_waiting_proof failed: {_e}")

def _save_active_order(phone: str, order_data: dict) -> None:
    """Persist active order metadata (without client) to DB."""
    try:
        with _db_write_lock:
            db.execute(
                "INSERT OR REPLACE INTO active_orders_db "
                "(phone, user_id, price, country, year, c_icon, twofa, sess, start_time, msg_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    phone, order_data['uid'], order_data['price'], order_data['country'],
                    order_data.get('year', 0), order_data.get('c_icon', ''),
                    order_data.get('twofa', 'None'), order_data['sess'],
                    order_data['start_time'], order_data.get('msg_id')
                )
            )
            db.commit()
    except Exception as _e:
        logger.warning(f"_save_active_order phone={phone}: {_e}")

def _clear_active_order_db(phone: str) -> None:
    """Remove active order from DB after completion/expiry."""
    try:
        with _db_write_lock:
            db.execute("DELETE FROM active_orders_db WHERE phone=?", (phone,))
            db.commit()
    except Exception as _e:
        logger.warning(f"_clear_active_order_db phone={phone}: {_e}")

def _save_payment_proof(uid: int, amount: int, method: str, proof_type: str,
                        proof_data: str, dep_id: int) -> None:
    """Permanently store a payment proof submission in DB."""
    try:
        with _db_write_lock:
            db.execute(
                "INSERT INTO payment_proofs (user_id, amount, method, proof_type, proof_data, dep_id) "
                "VALUES (?,?,?,?,?,?)",
                (uid, amount, method, proof_type, proof_data, dep_id)
            )
            db.commit()
    except Exception as _e:
        logger.warning(f"_save_payment_proof uid={uid}: {_e}")

# ================= HELPER FUNCTIONS =================
def is_bot_online():
    res = db.execute("SELECT value FROM settings WHERE key='bot_status'").fetchone()
    return res[0] == 'on' if res else True

def is_btn_enabled(key):
    res = db.execute("SELECT value FROM settings WHERE key=?", (f'btn_{key}',)).fetchone()
    return res[0] == 'on' if res else True

def sanitize_url(raw: str) -> str:
    """Strip HTML tags, decode common HTML entities, and clean up URLs received from Telegram messages."""
    clean = re.sub(r'<[^>]+>', '', raw)   # remove any HTML tags
    clean = html.unescape(clean)           # &amp; → & etc.
    clean = clean.strip()
    # If the result has a duplicated scheme (https://t.me/https://t.me/…), keep only the last URL
    match = re.search(r'(https?://\S+)$', clean)
    if match:
        clean = match.group(1)
    return clean

def get_force_join_entries():
    rows = db.execute("SELECT channel_id, join_url, type FROM force_join_channels").fetchall()
    if rows: return [{'cid': r[0], 'url': r[1], 'type': r[2] or 'channel'} for r in rows]
    return [{'cid': ch, 'url': url, 'type': 'channel'} for ch, url in zip(CHECK_CHANNELS, JOIN_URLS)]

def get_check_channels():
    return [e['cid'] for e in get_force_join_entries() if e['type'] != 'bot']

def get_join_urls():
    return [e['url'] for e in get_force_join_entries()]

def is_admin(uid):
    if uid == ADMIN_ID: return True
    row = db.execute("SELECT user_id FROM admins WHERE user_id=?", (uid,)).fetchone()
    return bool(row)

VALID_ADMIN_PERMS = {
    'p_add_stock', 'p_manage_stock', 'p_stats', 'p_broadcast', 'p_userinfo',
    'p_bal', 'p_ban', 'p_payments', 'p_faq', 'p_forcejoin', 'p_settings'
}

def has_perm(uid, *perms):
    """Return True if uid is main admin OR has ANY of the listed permissions."""
    if uid == ADMIN_ID: return True
    for perm in perms:
        if perm not in VALID_ADMIN_PERMS: continue
        row = db.execute(f"SELECT {perm} FROM admins WHERE user_id=?", (uid,)).fetchone()
        if row and row[0] == 1: return True
    return False

def ensure_user(uid):
    with _db_write_lock:
        db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
        db.commit()

def get_usdt_rate():
    res = db.execute("SELECT value FROM settings WHERE key='usdt_rate'").fetchone()
    try:
        rate = float(res[0]) if res else 94.0
        return rate if rate > 0 else 94.0  # BUG FIX: guard against 0 → ZeroDivisionError
    except Exception:
        return 94.0

def get_support_url():
    res = db.execute("SELECT value FROM settings WHERE key='support_url'").fetchone()
    url = res[0] if res and res[0] else "https://t.me/creperx4"
    if not url.startswith("http"): url = "https://" + url.replace("@", "t.me/")
    return url

# =================================================================
# NEW FEATURE HELPERS (language, coupons, flash sale, bundles, favs)
# =================================================================

# Feature 8: Language / Translation
TRANSLATIONS = {
  'en': {
      'deposit_approved': "✅ <b>Deposit Approved!</b>",
      'coupon_applied': "🎟 Coupon <b>{code}</b> applied — {pct}% off your next purchase!",
      'coupon_invalid': "❌ Invalid, expired, or already-used coupon code.",
      'coupon_already_used': "⚠️ You already used this coupon.",
      'flash_sale_banner': "🔥 <b>FLASH SALE!</b>  {pct}% OFF  ⏳ ends in {countdown}",
      'bundle_deal_banner': "🎁 Bundle: Buy {buy} get {free} FREE!",
  },
  'hi': {
      'deposit_approved': "✅ <b>डिपॉजिट स्वीकृत!</b>",
      'coupon_applied': "🎟 कूपन <b>{code}</b> लागू — अगली खरीد पर {pct}% छूट!",
      'coupon_invalid': "❌ अमान्य, समाप्त या पहले से उपयोग किया गया कूपन कोड।",
      'coupon_already_used': "⚠️ आप यह कूपन पहले ही उपयोग कर चुके हैं।",
      'flash_sale_banner': "🔥 <b>फ्लैश सेल!</b>  {pct}% छूट  ⏳ {countdown} बाकी",
      'bundle_deal_banner': "🎁 ऑफर: {buy} लें {free} मुफ्त पाएं!",
  },
  'ar': {
      'deposit_approved': "✅ <b>تمت الموافقة على الإيداع!</b>",
      'coupon_applied': "🎟 تم تفعيل الكوبون <b>{code}</b> — خصم {pct}% على مشترياتك!",
      'coupon_invalid': "❌ رمز كوبون غير صالح أو منتهي الصلاحية أو مستخدم.",
      'coupon_already_used': "⚠️ لقد استخدمت هذا الكوبون من قبل.",
      'flash_sale_banner': "🔥 <b>تخفيضات سريعة!</b>  خصم {pct}%  ⏳ ينتهي بعد {countdown}",
      'bundle_deal_banner': "🎁 عرض: اشترِ {buy} واحصل على {free} مجاناً!",
  },
}

def get_user_language(uid: int) -> str:
  row = db.execute("SELECT language FROM users WHERE user_id=?", (uid,)).fetchone()
  lang = row[0] if row and row[0] else 'en'
  return lang if lang in TRANSLATIONS else 'en'

def _t(uid: int, key: str, **kwargs) -> str:
  lang = get_user_language(uid)
  text = TRANSLATIONS[lang].get(key, TRANSLATIONS['en'].get(key, key))
  if kwargs:
      try: text = text.format(**kwargs)
      except Exception: pass
  return text

# Feature 1: Coupon helpers
def get_coupon_info(code: str):
  row = db.execute(
      "SELECT id, discount_pct, max_uses, uses_count, expires_at, category, "
      "COALESCE(coupon_type,'discount'), COALESCE(balance_amount,0) "
      "FROM promo_codes WHERE code=? COLLATE NOCASE",
      (code.upper().strip(),)
  ).fetchone()
  if not row: return None
  cid, disc, max_uses, uses, expires_at, category, coupon_type, balance_amount = row
  if max_uses > 0 and uses >= max_uses: return None
  if expires_at:
      try:
          if datetime.now() > datetime.strptime(expires_at, "%Y-%m-%d %H:%M"): return None
      except Exception: pass
  return {'id': cid, 'code': code.upper().strip(), 'discount_pct': disc,
          'max_uses': max_uses, 'uses_count': uses, 'expires_at': expires_at,
          'category': category, 'coupon_type': coupon_type,
          'balance_amount': balance_amount}

def user_has_used_coupon(uid: int, code: str) -> bool:
  return bool(db.execute(
      "SELECT 1 FROM user_coupons WHERE user_id=? AND code=? COLLATE NOCASE", (uid, code.upper())
  ).fetchone())

def apply_coupon_to_user(uid: int, code: str) -> bool:
  try:
      with _db_write_lock:
          if user_has_used_coupon(uid, code): return False
          db.execute("INSERT INTO user_coupons (user_id, code) VALUES (?,?)", (uid, code.upper()))
          db.execute("UPDATE promo_codes SET uses_count = uses_count + 1 WHERE code=? COLLATE NOCASE", (code.upper(),))
          db.commit()
      return True
  except Exception as _ce:
      logger.warning(f"apply_coupon_to_user: {_ce}")
      return False

def get_user_coupon_session(uid: int):
  row = db.execute("SELECT value FROM settings WHERE key=?", (f'cpn_sess_{uid}',)).fetchone()
  if not row or not row[0]: return None
  info = get_coupon_info(row[0])
  if info and not user_has_used_coupon(uid, row[0]): return info
  with _db_write_lock:
      db.execute("DELETE FROM settings WHERE key=?", (f'cpn_sess_{uid}',))
      db.commit()
  return None

def set_user_coupon_session(uid: int, code):
  with _db_write_lock:
      key = f'cpn_sess_{uid}'
      if code:
          db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, code.upper()))
      else:
          db.execute("DELETE FROM settings WHERE key=?", (key,))
      db.commit()

# Feature 2: Flash Sale helpers
def get_active_flash_sale():
  row = db.execute("SELECT value FROM settings WHERE key='flash_sale_ends_at'").fetchone()
  if not row or not row[0]: return None
  try:
      ends_dt = datetime.strptime(row[0], "%Y-%m-%d %H:%M")
      if datetime.now() > ends_dt: return None
  except Exception: return None
  dr = db.execute("SELECT value FROM settings WHERE key='flash_sale_discount'").fetchone()
  disc = int(dr[0]) if dr and dr[0] else 0
  if disc <= 0: return None
  return {'discount': disc, 'ends_at': row[0], 'ends_dt': ends_dt}

def get_flash_sale_countdown(ends_dt) -> str:
  remaining = ends_dt - datetime.now()
  if remaining.total_seconds() <= 0: return "Ended"
  h, rem = divmod(int(remaining.total_seconds()), 3600)
  m, s = divmod(rem, 60)
  if h > 0: return f"{h}h {m}m {s}s"
  elif m > 0: return f"{m}m {s}s"
  return f"{s}s"

# Feature 4: Bundle Deals helpers
def get_active_bundle(category: str):
  row = db.execute(
      "SELECT id, name, buy_qty, free_qty FROM bundle_deals WHERE category=? AND active=1 LIMIT 1", (category,)
  ).fetchone()
  if not row: return None
  return {'id': row[0], 'name': row[1], 'buy_qty': row[2], 'free_qty': row[3]}

# Feature 6: Favourite Countries helpers
def get_user_fav_countries(uid: int) -> list:
  rows = db.execute(
      "SELECT country_name FROM fav_countries WHERE user_id=? ORDER BY country_name", (uid,)
  ).fetchall()
  return [r[0] for r in rows]

def toggle_fav_country(uid: int, country_name: str) -> bool:
  existing = db.execute(
      "SELECT 1 FROM fav_countries WHERE user_id=? AND country_name=?", (uid, country_name)
  ).fetchone()
  with _db_write_lock:
      if existing:
          db.execute("DELETE FROM fav_countries WHERE user_id=? AND country_name=?", (uid, country_name))
          db.commit()
          return False
      db.execute("INSERT OR IGNORE INTO fav_countries (user_id, country_name) VALUES (?,?)", (uid, country_name))
      db.commit()
      return True

# Feature 12: Admin Audit Log
def log_admin_action_db(admin_id: int, action: str, target_uid: int = None, details: str = None):
  try:
      with _db_write_lock:
          db.execute(
              "INSERT INTO admin_audit_log (admin_id, action, target_uid, details) VALUES (?,?,?,?)",
              (admin_id, action, target_uid, details)
          )
          db.commit()
  except Exception as _ale:
      logger.debug(f"log_admin_action_db: {_ale}")

# Feature 7: PDF Receipt generator
def generate_receipt_pdf(uid: int, order_row: tuple):
  try:
      from reportlab.lib.pagesizes import A4
      from reportlab.lib import colors
      from reportlab.lib.units import cm
      from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                       Table, TableStyle, HRFlowable)
      from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
      from reportlab.lib.enums import TA_CENTER
      import io as _io
      order_id, phone, country, year, price, date_str = order_row
      buf = _io.BytesIO()
      doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                              topMargin=2*cm, bottomMargin=2*cm)
      styles = getSampleStyleSheet()
      h1  = ParagraphStyle('H1',  parent=styles['Heading1'], alignment=TA_CENTER, fontSize=22,
                            spaceAfter=4, textColor=colors.HexColor('#1a1a2e'))
      sub = ParagraphStyle('Sub', parent=styles['Normal'],   alignment=TA_CENTER, fontSize=11,
                            textColor=colors.grey)
      lbl = ParagraphStyle('Lbl', parent=styles['Normal'],   fontSize=11, textColor=colors.HexColor('#444444'))
      val = ParagraphStyle('Val', parent=styles['Normal'],   fontSize=11, fontName='Helvetica-Bold')
      story = [
          Paragraph("Fresh Tg Store", h1), Paragraph("Official Purchase Receipt", sub),
          Spacer(1, 0.5*cm), HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1a1a2e')),
          Spacer(1, 0.4*cm),
      ]
      yr_str = str(year) if year and str(year).isdigit() and int(year) > 2000 else "Unknown"
      data = [
          [Paragraph("Receipt No.", lbl), Paragraph(f"#{order_id}", val)],
          [Paragraph("User ID", lbl),     Paragraph(str(uid), val)],
          [Paragraph("Phone Number", lbl), Paragraph(f"+{phone}", val)],
          [Paragraph("Country", lbl),      Paragraph(str(country), val)],
          [Paragraph("Account Year", lbl), Paragraph(yr_str, val)],
          [Paragraph("Amount Paid", lbl),  Paragraph(f"Rs.{price}", val)],
          [Paragraph("Date", lbl),         Paragraph(str(date_str)[:16], val)],
      ]
      tbl = Table(data, colWidths=[5*cm, 11*cm])
      tbl.setStyle(TableStyle([
          ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, colors.HexColor('#f8f8f8')]),
          ('BOX', (0,0), (-1,-1), 0.5, colors.lightgrey),
          ('INNERGRID', (0,0), (-1,-1), 0.3, colors.lightgrey),
          ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
          ('TOPPADDING', (0,0), (-1,-1), 7), ('BOTTOMPADDING', (0,0), (-1,-1), 7),
      ]))
      story += [tbl, Spacer(1, 0.5*cm),
                HRFlowable(width="100%", thickness=0.8, color=colors.lightgrey), Spacer(1, 0.3*cm),
                Paragraph("Thank you for your purchase!", sub),
                Paragraph("Support: @Otp_shxp_bot", sub)]
      doc.build(story)
      buf.seek(0)
      return buf.read()
  except ImportError:
      logger.warning("reportlab not installed. pip install reportlab")
      return None
  except Exception as _pe:
      logger.warning(f"generate_receipt_pdf: {_pe}")
      return None

def get_activity_log_channel():
    res = db.execute("SELECT value FROM settings WHERE key='activity_log_channel'").fetchone()
    return int(res[0]) if res and res[0] else USER_INFO_CHANNEL_ID

def get_payment_log_channel():
    res = db.execute("SELECT value FROM settings WHERE key='payment_log_channel'").fetchone()
    return int(res[0]) if res and res[0] else PAYMENT_LOG_CHANNEL_ID

def get_purchase_log_channel():
    res = db.execute("SELECT value FROM settings WHERE key='purchase_log_channel'").fetchone()
    return int(res[0]) if res and res[0] else PURCHASE_LOG_CHANNEL_ID

def get_welcome_message():
    res = db.execute("SELECT value FROM settings WHERE key='welcome_message'").fetchone()
    return res[0] if res and res[0] else ""

def format_welcome(text: str, sender) -> str:
    """Replace user placeholders in the welcome message with real user data."""
    first = html.escape(getattr(sender, 'first_name', '') or '')
    last  = html.escape(getattr(sender, 'last_name',  '') or '')
    uname = getattr(sender, 'username', None)
    uid   = getattr(sender, 'id', '')
    full  = (first + (' ' + last if last else '')).strip()
    if uname:
        mention = f'<a href="https://t.me/{html.escape(uname)}">{html.escape(full or uname)}</a>'
    else:
        mention = f'<a href="tg://user?id={uid}">{html.escape(full or str(uid))}</a>'
    return (
        text
        .replace('{mention}',    mention)
        .replace('{first_name}', first)
        .replace('{last_name}',  last)
        .replace('{full_name}',  html.escape(full))
        .replace('{username}',   f'@{html.escape(uname)}' if uname else first)
        .replace('{user_id}',    str(uid))
    )

def get_welcome_button():
    """Returns (button_text, button_url) or (None, None) if not set."""
    txt = db.execute("SELECT value FROM settings WHERE key='welcome_btn_text'").fetchone()
    url = db.execute("SELECT value FROM settings WHERE key='welcome_btn_url'").fetchone()
    t = txt[0] if txt and txt[0] else None
    u = url[0] if url and url[0] else None
    if t and u:
        # Auto-repair double-prefixed URLs stored by old buggy code
        # e.g. "https://t.me/https://t.me/channel" → "https://t.me/channel"
        _first = re.match(r'https?://', u)
        if _first:
            _second = re.search(r'https?://', u[_first.end():])
            if _second:
                u = u[_first.end() + _second.start():]
                with _db_write_lock:
                    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('welcome_btn_url', ?)", (u,))
                    db.commit()
        return t, u
    return None, None

def to_usd(inr):
    return round(inr / get_usdt_rate(), 2)

def is_user_banned(uid):
    res = db.execute("SELECT banned FROM users WHERE user_id=?", (uid,)).fetchone()
    return res and res[0] == 1

def update_balance(uid, amount):
    """Add (or subtract, if amount is negative) from a user's balance and commit immediately.

    WARNING: do NOT call this inside a multi-statement transaction — it issues its own
    db.commit().  For multi-step transactions (e.g. deposit approval) use the raw SQL
    directly so everything is committed atomically in one go.
    """
    with _db_write_lock:
        if amount < 0:
            # Never let balance go below zero — clamp to max(0, balance + amount)
            db.execute("UPDATE users SET balance = MAX(0, balance + ?) WHERE user_id=?", (amount, uid))
        else:
            db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
        db.commit()

async def log_balance_change(admin_id, target_uid, amt, old_bal, new_bal):
    """Send a balance-change log to the purchase log channel only."""
    try:
        t = datetime.now().strftime('%d %b %Y  %I:%M %p')
        # resolve admin name
        try:
            adm = await bot.get_entity(int(admin_id))
            adm_name = html.escape(adm.first_name or str(admin_id))
            adm_uname = f"@{html.escape(adm.username)}" if adm.username else f"<code>{admin_id}</code>"
        except Exception as _e:
            logger.debug(f'Could not resolve admin entity {admin_id}: {_e}')
            adm_name, adm_uname = str(admin_id), f"<code>{admin_id}</code>"
        # resolve target user name
        try:
            usr = await bot.get_entity(int(target_uid))
            usr_name = html.escape(usr.first_name or str(target_uid))
            usr_uname = f"@{html.escape(usr.username)}" if usr.username else f"<code>{target_uid}</code>"
        except Exception as _e:
            logger.debug(f'Could not resolve user entity {target_uid}: {_e}')
            usr_name, usr_uname = str(target_uid), f"<code>{target_uid}</code>"
        direction = "➕ Added" if amt >= 0 else "➖ Deducted"
        msg = (
            f"💼 <b>ADMIN BALANCE CHANGE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔧 <b>Admin:</b>  {adm_name}  ({adm_uname})\n\n"
            f"👤 <b>User:</b>  {usr_name}  ({usr_uname})\n"
            f"   ID: <code>{target_uid}</code>\n\n"
            f"┄┄┄┄  💰 Balance Change  ┄┄┄┄\n"
            f"{direction}: <code>₹{abs(amt)}</code>\n"
            f"📊 <b>Old Balance:</b>  <code>₹{old_bal}</code>\n"
            f"📊 <b>New Balance:</b>  <code>₹{new_bal}</code>\n\n"
            f"🕐 <b>Time:</b>  {t}"
        )
        purchase_ch = get_purchase_log_channel()
        sent = False
        try:
            await _tg_call(bot.send_message, purchase_ch, msg)
            sent = True
        except Exception as e1:
            logger.error(f"Balance change log (purchase channel) error: {e1}")
        if not sent:
            try:
                await _tg_call(
                    bot.send_message,
                    int(admin_id),
                    f"⚠️ <b>Balance was changed but the log could NOT be sent to the purchase log channel.</b>\n"
                    f"Please check that the bot is an admin in your purchase log channel.\n\n"
                    f"Change details:\n{direction} <code>₹{abs(amt)}</code> to user <code>{target_uid}</code>\n"
                    f"Old: <code>₹{old_bal}</code> → New: <code>₹{new_bal}</code>"
                )
            except Exception as _e:
                logger.debug(f'Admin balance log fallback send failed: {_e}')
    except Exception as e:
        logger.error(f"Balance change log error: {e}")

def delete_session_files(session_path):
    base = _resolve_session_base(session_path)
    if not base:
        return
    for ext in ['.session', '.session-wal', '.session-shm', '.session-journal']:
        try:
            if os.path.exists(base + ext): os.remove(base + ext)
        except Exception as _e:
            logger.debug(f'Suppressed non-critical error: {_e}')

async def check_channel_joined(uid):
    if is_admin(uid): return True
    # If no force-join channels configured at all, skip check
    if not get_check_channels() and not any(e['type'] == 'bot' for e in get_force_join_entries()):
        return True
    # Use DB-verified flag as the source of truth.
    # Actual verification happens when the user clicks ✅ Verify.
    row = db.execute("SELECT fj_verified FROM users WHERE user_id=?", (uid,)).fetchone()
    return bool(row and row[0] == 1)

async def _send_fj_prompt(e, uid):
    """Show one force-join prompt per user until verification succeeds."""
    # Do not send a new panel for every incoming message.  A user can use the
    # Verify button on the first panel, so repeated panels only create outgoing
    # traffic and eventually trigger Telegram flood waits.
    now = time.time()
    last_prompt = force_join_prompt_cooldown.get(uid, 0.0)
    if last_prompt:
        return False  # FIX Bug 4: prompt already sent; False signals "no new action taken"
    force_join_prompt_cooldown[uid] = now

    _fj_entries = get_force_join_entries()
    _fj_btn_labels = {'channel': 'Join Channel', 'group': 'Join Group', 'bot': 'Start Bot'}
    _fj_btn_icons  = {'channel': '📢', 'group': '👥', 'bot': '🤖'}
    btns = [
        [Button.url(
            f"{_fj_btn_icons.get(en['type'], '📢')} {_fj_btn_labels.get(en['type'], 'Join')} {i+1}",
            sanitize_url(en['url'])
        )]
        for i, en in enumerate(_fj_entries)
        if sanitize_url(en['url']).startswith('http')
    ]
    btns.append([Button.inline("✅ Verify", "verify_join")])
    msg = (
        f"👋 <b>Welcome to OTP Shop!</b>\n\n"
        f"{P_WARN} <b>Before using the bot, you must join our official channel(s) / group(s).</b>\n\n"
        f"📌 <b>Steps:</b>\n"
        f"1️⃣ Click each button below and join / start.\n"
        f"2️⃣ Come back here and tap <b>✅ Verify</b>.\n"
        f"3️⃣ You're in — enjoy the bot! 🎉\n\n"
        f"<i>This is required to keep the community active and get important updates.</i>"
    )
    try:
        await e.respond(msg, buttons=btns)
    except Exception:
        try:
            await bot.send_message(uid, msg, buttons=btns)
        except Exception:
            # Allow a later /start or command to retry if the first send failed.
            force_join_prompt_cooldown.pop(uid, None)
    return True

COUNTRY_CODES = {
    # ── Americas ──────────────────────────────────────────────────────
    '1':    ('USA/Canada',       '🇺🇸'), '52':  ('Mexico',           '🇲🇽'),
    '53':   ('Cuba',             '🇨🇺'), '54':  ('Argentina',        '🇦🇷'),
    '55':   ('Brazil',           '🇧🇷'), '56':  ('Chile',            '🇨🇱'),
    '57':   ('Colombia',         '🇨🇴'), '58':  ('Venezuela',        '🇻🇪'),
    '51':   ('Peru',             '🇵🇪'), '591': ('Bolivia',          '🇧🇴'),
    '592':  ('Guyana',           '🇬🇾'), '593': ('Ecuador',          '🇪🇨'),
    '595':  ('Paraguay',         '🇵🇾'), '597': ('Suriname',         '🇸🇷'),
    '598':  ('Uruguay',          '🇺🇾'), '501': ('Belize',           '🇧🇿'),
    '502':  ('Guatemala',        '🇬🇹'), '503': ('El Salvador',      '🇸🇻'),
    '504':  ('Honduras',         '🇭🇳'), '505': ('Nicaragua',        '🇳🇮'),
    '506':  ('Costa Rica',       '🇨🇷'), '507': ('Panama',           '🇵🇦'),
    '509':  ('Haiti',            '🇭🇹'), '508': ('St. Pierre & M.',  '🇵🇲'),
    '500':  ('Falkland Islands', '🇫🇰'), '590': ('Guadeloupe',       '🇬🇵'),
    '594':  ('French Guiana',    '🇬🇫'), '596': ('Martinique',       '🇲🇶'),
    '599':  ('Curacao',          '🇨🇼'), '297': ('Aruba',            '🇦🇼'),
    # ── Europe ────────────────────────────────────────────────────────
    '7':    ('Russia',           '🇷🇺'), '30':  ('Greece',           '🇬🇷'),
    '31':   ('Netherlands',      '🇳🇱'), '32':  ('Belgium',          '🇧🇪'),
    '33':   ('France',           '🇫🇷'), '34':  ('Spain',            '🇪🇸'),
    '36':   ('Hungary',          '🇭🇺'), '39':  ('Italy',            '🇮🇹'),
    '40':   ('Romania',          '🇷🇴'), '41':  ('Switzerland',      '🇨🇭'),
    '43':   ('Austria',          '🇦🇹'), '44':  ('UK',               '🇬🇧'),
    '45':   ('Denmark',          '🇩🇰'), '46':  ('Sweden',           '🇸🇪'),
    '47':   ('Norway',           '🇳🇴'), '48':  ('Poland',           '🇵🇱'),
    '49':   ('Germany',          '🇩🇪'), '350': ('Gibraltar',        '🇬🇮'),
    '351':  ('Portugal',         '🇵🇹'), '352': ('Luxembourg',       '🇱🇺'),
    '353':  ('Ireland',          '🇮🇪'), '354': ('Iceland',          '🇮🇸'),
    '355':  ('Albania',          '🇦🇱'), '356': ('Malta',            '🇲🇹'),
    '357':  ('Cyprus',           '🇨🇾'), '358': ('Finland',          '🇫🇮'),
    '359':  ('Bulgaria',         '🇧🇬'), '370': ('Lithuania',        '🇱🇹'),
    '371':  ('Latvia',           '🇱🇻'), '372': ('Estonia',          '🇪🇪'),
    '373':  ('Moldova',          '🇲🇩'), '374': ('Armenia',          '🇦🇲'),
    '375':  ('Belarus',          '🇧🇾'), '376': ('Andorra',          '🇦🇩'),
    '377':  ('Monaco',           '🇲🇨'), '378': ('San Marino',       '🇸🇲'),
    '380':  ('Ukraine',          '🇺🇦'), '381': ('Serbia',           '🇷🇸'),
    '382':  ('Montenegro',       '🇲🇪'), '383': ('Kosovo',           '🇽🇰'),
    '385':  ('Croatia',          '🇭🇷'), '386': ('Slovenia',         '🇸🇮'),
    '387':  ('Bosnia',           '🇧🇦'), '389': ('N. Macedonia',     '🇲🇰'),
    '420':  ('Czech Republic',   '🇨🇿'), '421': ('Slovakia',         '🇸🇰'),
    '423':  ('Liechtenstein',    '🇱🇮'), '298': ('Faroe Islands',    '🇫🇴'),
    '299':  ('Greenland',        '🇬🇱'), '679': ('Fiji',             '🇫🇯'),
    # ── Middle East ───────────────────────────────────────────────────
    '90':   ('Turkey',           '🇹🇷'), '961': ('Lebanon',          '🇱🇧'),
    '962':  ('Jordan',           '🇯🇴'), '963': ('Syria',            '🇸🇾'),
    '964':  ('Iraq',             '🇮🇶'), '965': ('Kuwait',           '🇰🇼'),
    '966':  ('Saudi Arabia',     '🇸🇦'), '967': ('Yemen',            '🇾🇪'),
    '968':  ('Oman',             '🇴🇲'), '970': ('Palestine',        '🇵🇸'),
    '971':  ('UAE',              '🇦🇪'), '972': ('Israel',           '🇮🇱'),
    '973':  ('Bahrain',          '🇧🇭'), '974': ('Qatar',            '🇶🇦'),
    # ── South & Central Asia ──────────────────────────────────────────
    '91':   ('India',            '🇮🇳'), '92':  ('Pakistan',         '🇵🇰'),
    '93':   ('Afghanistan',      '🇦🇫'), '94':  ('Sri Lanka',        '🇱🇰'),
    '95':   ('Myanmar',          '🇲🇲'), '98':  ('Iran',             '🇮🇷'),
    '880':  ('Bangladesh',       '🇧🇩'), '975': ('Bhutan',           '🇧🇹'),
    '977':  ('Nepal',            '🇳🇵'), '960': ('Maldives',         '🇲🇻'),
    '992':  ('Tajikistan',       '🇹🇯'), '993': ('Turkmenistan',     '🇹🇲'),
    '994':  ('Azerbaijan',       '🇦🇿'), '995': ('Georgia',          '🇬🇪'),
    '996':  ('Kyrgyzstan',       '🇰🇬'), '998': ('Uzbekistan',       '🇺🇿'),
    '76':   ('Kazakhstan',       '🇰🇿'), '77':  ('Kazakhstan',       '🇰🇿'),
    # ── East & SE Asia / Pacific ──────────────────────────────────────
    '81':   ('Japan',            '🇯🇵'), '82':  ('South Korea',      '🇰🇷'),
    '84':   ('Vietnam',          '🇻🇳'), '86':  ('China',            '🇨🇳'),
    '60':   ('Malaysia',         '🇲🇾'), '61':  ('Australia',        '🇦🇺'),
    '62':   ('Indonesia',        '🇮🇩'), '63':  ('Philippines',      '🇵🇭'),
    '64':   ('New Zealand',      '🇳🇿'), '65':  ('Singapore',        '🇸🇬'),
    '66':   ('Thailand',         '🇹🇭'), '850': ('North Korea',      '🇰🇵'),
    '852':  ('Hong Kong',        '🇭🇰'), '853': ('Macau',            '🇲🇴'),
    '855':  ('Cambodia',         '🇰🇭'), '856': ('Laos',             '🇱🇦'),
    '886':  ('Taiwan',           '🇹🇼'), '673': ('Brunei',           '🇧🇳'),
    '670':  ('Timor-Leste',      '🇹🇱'), '675': ('Papua New Guinea', '🇵🇬'),
    '676':  ('Tonga',            '🇹🇴'), '677': ('Solomon Islands',  '🇸🇧'),
    '678':  ('Vanuatu',          '🇻🇺'), '680': ('Palau',            '🇵🇼'),
    '685':  ('Samoa',            '🇼🇸'), '686': ('Kiribati',         '🇰🇮'),
    '687':  ('New Caledonia',    '🇳🇨'), '688': ('Tuvalu',           '🇹🇻'),
    '689':  ('French Polynesia', '🇵🇫'), '691': ('Micronesia',       '🇫🇲'),
    '692':  ('Marshall Islands', '🇲🇭'), '674': ('Nauru',            '🇳🇷'),
    '682':  ('Cook Islands',     '🇨🇰'), '683': ('Niue',             '🇳🇺'),
    '690':  ('Tokelau',          '🇹🇰'),
    # ── Africa ────────────────────────────────────────────────────────
    '20':   ('Egypt',            '🇪🇬'), '27':  ('South Africa',     '🇿🇦'),
    '212':  ('Morocco',          '🇲🇦'), '213': ('Algeria',          '🇩🇿'),
    '216':  ('Tunisia',          '🇹🇳'), '218': ('Libya',            '🇱🇾'),
    '220':  ('Gambia',           '🇬🇲'), '221': ('Senegal',          '🇸🇳'),
    '222':  ('Mauritania',       '🇲🇷'), '223': ('Mali',             '🇲🇱'),
    '224':  ('Guinea',           '🇬🇳'), '225': ('Ivory Coast',      '🇨🇮'),
    '226':  ('Burkina Faso',     '🇧🇫'), '227': ('Niger',            '🇳🇪'),
    '228':  ('Togo',             '🇹🇬'), '229': ('Benin',            '🇧🇯'),
    '230':  ('Mauritius',        '🇲🇺'), '231': ('Liberia',          '🇱🇷'),
    '232':  ('Sierra Leone',     '🇸🇱'), '233': ('Ghana',            '🇬🇭'),
    '234':  ('Nigeria',          '🇳🇬'), '235': ('Chad',             '🇹🇩'),
    '236':  ('Cent. Afr. Rep.',  '🇨🇫'), '237': ('Cameroon',         '🇨🇲'),
    '238':  ('Cape Verde',       '🇨🇻'), '239': ('Sao Tome',         '🇸🇹'),
    '240':  ('Eq. Guinea',       '🇬🇶'), '241': ('Gabon',            '🇬🇦'),
    '242':  ('Republic of Congo','🇨🇬'), '243': ('DR Congo',         '🇨🇩'),
    '244':  ('Angola',           '🇦🇴'), '245': ('Guinea-Bissau',    '🇬🇼'),
    '248':  ('Seychelles',       '🇸🇨'), '249': ('Sudan',            '🇸🇩'),
    '250':  ('Rwanda',           '🇷🇼'), '251': ('Ethiopia',         '🇪🇹'),
    '252':  ('Somalia',          '🇸🇴'), '253': ('Djibouti',         '🇩🇯'),
    '254':  ('Kenya',            '🇰🇪'), '255': ('Tanzania',         '🇹🇿'),
    '256':  ('Uganda',           '🇺🇬'), '257': ('Burundi',          '🇧🇮'),
    '258':  ('Mozambique',       '🇲🇿'), '260': ('Zambia',           '🇿🇲'),
    '261':  ('Madagascar',       '🇲🇬'), '263': ('Zimbabwe',         '🇿🇼'),
    '264':  ('Namibia',          '🇳🇦'), '265': ('Malawi',           '🇲🇼'),
    '266':  ('Lesotho',          '🇱🇸'), '267': ('Botswana',         '🇧🇼'),
    '268':  ('Eswatini',         '🇸🇿'), '269': ('Comoros',          '🇰🇲'),
    '291':  ('Eritrea',          '🇪🇷'), '262': ('Reunion',          '🇷🇪'),
}

def get_cat_badge(category: str) -> str:
    """Return a short display badge for a category."""
    return {
        'Fresh': '🟢 Fresh',
        'Cheap': '💸 Cheap',
        'Old':   '🟡 Old',
        'Spam':  '🔴 Spam',
        'Rare':  '💎 Rare',
        'Number Change': '🔄 Number Change',
    }.get(category, f'📂 {category}')

# All supported stock categories (order matches the Buy Account menu)
STOCK_CATEGORIES = ['Fresh', 'Cheap', 'Old', 'Spam', 'Rare', 'Number Change']

def get_auto_price(c_name, year, category='Fresh'):
    """
    Price lookup with 4-level fallback:
      1. year_category  e.g. "2021_Old"
      2. year only      e.g. "2021"         (backward compat)
      3. Common_category e.g. "Common_Old"
      4. Common                              (catch-all fallback)
    """
    # Normalise legacy 'Good' references to 'Fresh'
    if category == 'Good':
        category = 'Fresh'
    for key in (f"{year}_{category}", str(year), f"Common_{category}", "Common"):
        row = db.execute("SELECT price FROM auto_prices WHERE country=? AND year=?", (c_name, key)).fetchone()
        if row:
            return row[0]
    return None


def is_auto_price_enabled():
    """Return True when auto-price detection is turned ON (default: ON)."""
    row = db.execute("SELECT value FROM settings WHERE key='auto_price_enabled'").fetchone()
    return (row is None) or (row[0] != '0')


# ══════════════════════════════════════════════════════════════════════════════
# ── NEW FEATURE HELPERS ───────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def apply_qty_discount(base_price, qty, user_discount=0):
    """Tiered qty discount stacked on top of user/reseller discount, capped at 60%."""
    if qty >= 20:
        row = db.execute("SELECT value FROM settings WHERE key='qty_tier_20_pct'").fetchone()
        tier_pct = int(row[0]) if row and row[0] else 15
    elif qty >= 10:
        row = db.execute("SELECT value FROM settings WHERE key='qty_tier_10_pct'").fetchone()
        tier_pct = int(row[0]) if row and row[0] else 10
    elif qty >= 5:
        row = db.execute("SELECT value FROM settings WHERE key='qty_tier_5_pct'").fetchone()
        tier_pct = int(row[0]) if row and row[0] else 5
    else:
        tier_pct = 0
    total_disc = min(user_discount + tier_pct, 60)
    return max(1, int(base_price * (100 - total_disc) / 100))

def get_reseller_discount():
    """Return the reseller discount % from settings (default 20%)."""
    row = db.execute("SELECT value FROM settings WHERE key='reseller_discount'").fetchone()
    return int(row[0]) if row and row[0] else 20

def is_reseller(uid):
    """Return True if user has reseller flag set."""
    row = db.execute("SELECT reseller FROM users WHERE user_id=?", (uid,)).fetchone()
    return bool(row and row[0])

def get_effective_discount(uid):
    """Return the effective discount % for a user (reseller or personal, whichever is higher)."""
    disc_row = db.execute("SELECT discount, reseller FROM users WHERE user_id=?", (uid,)).fetchone()
    if not disc_row:
        return 0
    user_disc = disc_row[0] or 0
    if disc_row[1]:  # reseller
        return max(user_disc, get_reseller_discount())
    return user_disc

async def check_low_stock_alert(c_name):
    """Notify ADMIN_ID if a country's stock falls at or below the threshold."""
    try:
        row = db.execute("SELECT value FROM settings WHERE key='low_stock_threshold'").fetchone()
        threshold = int(row[0]) if row and row[0] else 5
        cnt = db.execute("SELECT COUNT(*) FROM stock WHERE country_name=? AND available=1", (c_name,)).fetchone()[0]
        if cnt > threshold:
            # A future drop below the threshold should be eligible for one new
            # alert after stock has been replenished.
            low_stock_alert_state.pop(c_name, None)
            return

        # Purchases can launch this coroutine concurrently. Record the alert
        # state before the first await so only the first caller sends anything.
        previous = low_stock_alert_state.get(c_name)
        if previous and previous[0] == threshold:
            return
        low_stock_alert_state[c_name] = (threshold, cnt)

        flag = get_flag_by_country_name(c_name)
        _alert_msg = (
            f"⚠️ <b>LOW STOCK ALERT</b>\n\n"
            f"{flag} <b>{c_name}</b>\n"
            f"Only <b>{cnt}</b> account(s) left in stock!\n"
            f"<i>Threshold: ≤{threshold} — Please restock soon.</i>"
        )
        await bot.send_message(ADMIN_ID, _alert_msg)
        # Feature 10: notify sub-admins with stock permission
        _sa_rows = db.execute(
            "SELECT user_id FROM admins WHERE p_add_stock=1 OR p_manage_stock=1"
        ).fetchall()
        for (_sa_uid,) in _sa_rows:
            try:
                await bot.send_message(int(_sa_uid), _alert_msg)
            except Exception as _sa_err:
                logger.debug(f'Low stock notify sub-admin {_sa_uid}: {_sa_err}')
    except Exception as _lsa_err:
        logger.debug(f"check_low_stock_alert: {_lsa_err}")

async def notify_wishlist_users(c_name):
    """Ping users who wishlisted a country when new stock arrives."""
    try:
        rows = db.execute("SELECT user_id FROM wishlist WHERE country_name=?", (c_name,)).fetchall()
        if not rows:
            return
        flag = get_flag_by_country_name(c_name)
        cnt = db.execute("SELECT COUNT(*) FROM stock WHERE country_name=? AND available=1", (c_name,)).fetchone()[0]
        for (wl_uid,) in rows:
            try:
                await bot.send_message(wl_uid,
                    f"🔔 <b>Wishlist Alert!</b>\n\n"
                    f"{flag} <b>{c_name}</b> is back in stock!\n"
                    f"📦 Available: <b>{cnt}</b> account(s)\n\n"
                    f"<i>You added this country to your wishlist.</i>",
                    buttons=[[Button.inline(f"🛒 Buy Now", "cat_sel|single|Fresh")]]
                )
                await asyncio.sleep(0.05)
            except Exception as _e:
                logger.debug(f"notify_wishlist uid={wl_uid} c={c_name}: {_e}")
    except Exception as _nwl_err:
        logger.debug(f"notify_wishlist_users: {_nwl_err}")

def get_qty_tier_info():
    """Return (5pct, 10pct, 20pct) discount tiers from settings."""
    def _g(key, default):
        r = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return int(r[0]) if r and r[0] else default
    return _g('qty_tier_5_pct', 5), _g('qty_tier_10_pct', 10), _g('qty_tier_20_pct', 15)

def get_flag_by_country_name(name):
    for code, (c_name, c_flag) in COUNTRY_CODES.items():
        if c_name == name: return c_flag
    try:
        row = db.execute("SELECT flag FROM custom_countries WHERE name=?", (name,)).fetchone()
        if row: return row[0]
    except Exception as _e:
        logger.debug(f'Suppressed non-critical error: {_e}')
    return "🌍"

def get_country_info(phone):
    phone = str(phone).replace(' ', '').replace('+', '')
    if not phone: return "Unknown", "🌍"
    
    try:
        customs = db.execute("SELECT code, name, flag FROM custom_countries").fetchall()
        customs.sort(key=lambda x: len(x[0]), reverse=True)
        for code, name, flag in customs:
            if phone.startswith(code): return name, flag
    except Exception as _e:
        logger.debug(f'Suppressed non-critical error: {_e}')

    for length in (3, 2, 1):
        prefix = phone[:length]
        if prefix in COUNTRY_CODES: return COUNTRY_CODES[prefix]
    return "Unknown", "🌍"

async def detect_account_year(client):
    default_year = 0  # 0 means unknown; do NOT use current year — it corrupts DB year data
    current_year = datetime.now().year
    try:
        try: await client.delete_dialog('TGDNAbot')
        except Exception as _e:
            logger.debug(f'Suppressed non-critical error: {_e}')
        await client.send_message('TGDNAbot', '/start')
        me = await client.get_me()
        await asyncio.sleep(1.5)
        await client.send_message('TGDNAbot', str(me.id))
        for _ in range(10):
            await asyncio.sleep(2)
            msgs = await client.get_messages('TGDNAbot', limit=5)
            for m in msgs:
                if not m.text:
                    continue
                text = m.text
                # Strategy 1: keyword near a valid year — covers 2000-2029
                # Includes Age/Year/Reg keywords so "5 years (2021)" and "Year: 2021" both match
                match = re.search(
                    r'(?:Created|Registration|Registered|Age|Year|Reg)[^\n]*?(\b20[0-2][0-9]\b)',
                    text, re.IGNORECASE
                )
                if match:
                    y = int(match.group(1))
                    if 2013 <= y <= current_year:
                        return y
                # Strategy 2: any standalone 4-digit year 2000-2029 anywhere in the message
                for y_str in re.findall(r'\b(20[0-2][0-9])\b', text):
                    y = int(y_str)
                    if 2013 <= y <= current_year:
                        return y
    except Exception as _yr_err:
        logger.debug(f'detect_account_year error: {_yr_err}')
    return default_year

# ================= LOGGING LOGIC =================
async def process_referral_bonus(uid, amount):
    row = db.execute("SELECT referred_by FROM users WHERE user_id=?", (uid,)).fetchone()
    ref = row[0] if row else None
    if ref:
        pct_row = db.execute("SELECT value FROM settings WHERE key='ref_percent'").fetchone()
        pct = float(pct_row[0]) if pct_row else 3.0
        if pct > 0:
            bonus = int(amount * (pct / 100))
            if bonus > 0:
                update_balance(ref, bonus)
                try: await bot.send_message(ref, f"{P_GIFT} <b>Referral Bonus!</b>\nYour referral <code>{uid}</code> deposited {P_INR}{amount}.\n{P_YES} You earned <b>{P_INR}{bonus}</b>!")
                except Exception as _e:
                    logger.debug(f'Suppressed non-critical error: {_e}')

async def log_user_activity(uid, username, is_new: bool):
    ch = get_activity_log_channel()
    if not ch:
        return
    try:
        t = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        badge = "🆕 <b>NEW USER</b>" if is_new else "🔁 <b>RETURNING USER</b>"
        uname = f"@{html.escape(username)}" if username else "<i>no username</i>"
        msg = (
            f"{badge}\n\n"
            f"{P_ID} ID: <code>{uid}</code>\n"
            f"{P_ACC} Username: {uname}\n"
            f"{P_TIME} Time: {t}"
        )
        await _tg_call(bot.send_message, ch, msg)
    except Exception as e:
        logger.warning(f"Activity log failed: {e}")

async def log_primary_deposit(uid, amt, method):
    try:
        try:
            user = await bot.get_entity(int(uid))
            username = f"@{html.escape(user.username)}" if user.username else "<i>no username</i>"
        except Exception as _e:
            logger.debug(f'Could not resolve entity for uid: {_e}')
            username = "<i>unknown</i>"
        t = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # FIX Bug 8: query balance once, store in variable — was executing the same SELECT twice
        _bal_row = db.execute('SELECT balance FROM users WHERE user_id=?', (uid,)).fetchone()
        _new_bal = _bal_row[0] if _bal_row else '?'
        msg = (
            f"{P_YES} <b>DEPOSIT APPROVED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{P_ACC} <b>User ID:</b> <code>{uid}</code>\n"
            f"👤 <b>Username:</b> {username}\n"
            f"{P_MONEY} <b>Amount:</b> {P_INR}{amt}\n"
            f"{P_CARD} <b>Method:</b> {method}\n"
            f"{P_TIME} <b>Time:</b> {t}\n"
            f"📈 <b>New Balance:</b> {P_INR}{_new_bal}\n\n"
            f"<i>Balance has been credited to the user's account.</i>"
        )
        log_admin_action_db(uid, 'deposit_logged', uid, f'amt={amt} method={method}')
        try:
            await _tg_call(bot.send_message, get_payment_log_channel(), msg)
        except Exception as e:
            logger.error(f"Failed deposit log to channel: {e}")
            try:
                await _tg_call(bot.send_message, ADMIN_ID, f"⚠️ <b>Deposit log failed to send to channel!</b>\n\n{msg}")
            except Exception as _e:
                logger.debug(f'Deposit log admin fallback also failed: {_e}')
    except Exception as e: logger.error(f"Global Dep Log Err: {e}")

def _mask_uid(uid):
    """Partially hide a user ID for privacy in logs (e.g. 7093175010 -> 709***010)."""
    s = str(uid)
    if len(s) <= 5: return s
    return s[:3] + '***' + s[-3:]

def _mask_phone(phone):
    """Partially hide a phone number (e.g. 919812345678 -> 919****90)."""
    s = str(phone)
    if len(s) <= 6: return s
    return s[:3] + '****' + s[-2:]

def get_user_active_phone(uid: int):
    """Return the phone string for the user's current active OTP order, or None."""
    for phone, order in active_orders.items():
        if order.get('uid') == uid:
            return phone
    return None

async def log_primary_purchase(uid, country, price, amount, year, qty, phone=None, category=None):
    try:
        flag_icon = get_flag_by_country_name(country) or '🌍'
        cat_label = category if category else 'Standard'
        item_label = f"{flag_icon} {country} ({cat_label})"
        masked_uid   = _mask_uid(uid)
        masked_phone = _mask_phone(phone) if phone else '—'
        year_display = str(year) if year and int(year) > 2000 else 'Unknown'
        if qty > 1:
            qty_line = f"\n📦 <b>Qty:</b> <code>{qty}</code>  💰 <b>Total:</b> <code>₹{amount}</code>"
        else:
            qty_line = f"\n📅 <b>Acc Year:</b> <code>{year_display}</code>"
        msg = (
            f"🚀 <b>NEW ACCOUNT SOLD!</b>\n\n"
            f"👤 <b>User:</b> {masked_uid}\n"
            f"📦 <b>Item:</b> {item_label}\n"
            f"📍 <b>Region:</b> {item_label}\n"
            f"📱 <b>Number:</b> {masked_phone}"
            f"{qty_line}\n"
            f"⚡ <b>Status:</b> Verified &amp; Delivered\n\n"
            f"🤖 Always use @Otp_shxp_bot"
        )
        bot_btn = [[Button.url('🤖 Open Bot', 'https://t.me/Otp_shxp_bot')]]
        try: await _tg_call(bot.send_message, get_purchase_log_channel(), msg, buttons=bot_btn)
        except Exception as e: logger.error(f"Failed Purchase Log: {e}")
    except Exception as e: logger.error(f"Pur Log Err: {e}")

# ================= MENU HELPERS =================
def get_persistent_menu(uid):
    rows = []
    r1 = []
    if is_btn_enabled('buy_account'): r1.append(KeyboardButton("🛒 Buy Account"))
    if is_btn_enabled('my_profile'):  r1.append(KeyboardButton("👤 My Profile"))
    if r1: rows.append(r1)
    if is_btn_enabled('buy_sessions'): rows.append([KeyboardButton("📁 Buy Sessions")])
    r3 = []
    if is_btn_enabled('deposit'):    r3.append(KeyboardButton("💰 Deposit"))
    if is_btn_enabled('my_stats'):   r3.append(KeyboardButton("📊 My Stats"))
    if r3: rows.append(r3)
    r3b = []
    if is_btn_enabled('my_balance'): r3b.append(KeyboardButton("💳 My Balance"))
    if r3b: rows.append(r3b)
    r4 = []
    if is_btn_enabled('support'): r4.append(KeyboardButton("📞 Support"))
    if is_btn_enabled('help'):    r4.append(KeyboardButton("❓ Help"))
    if r4: rows.append(r4)
    if is_btn_enabled('stock_info'): rows.append([KeyboardButton("📦 Stock Info")])
    if is_admin(uid): rows.append([KeyboardButton("🔐 Admin Panel")])
    rows.append([KeyboardButton("🌐 Language"), KeyboardButton("⭐ My Favourites")])
    # Return None (no keyboard) instead of an empty ReplyKeyboardMarkup —
    # Telegram rejects keyboards with zero rows and raises BadRequest.
    if not rows:
        return None
    return ReplyKeyboardMarkup([KeyboardButtonRow(r) for r in rows], resize=True)

async def send_main_menu(event, uid, sender=None):
    # Resolve the user's first name for a personalised greeting
    try:
        _ent = sender or await bot.get_entity(uid)
        first_name = html.escape(getattr(_ent, 'first_name', '') or 'there')
    except Exception:
        first_name = 'there'

    msg = (
        f"👋 Hey <b>{first_name}!</b> Welcome to <b>Fresh Tg Store</b> 🏬\n\n"
        f"<blockquote>📱 Fresh TG Accounts | 📁 Sessions\n"
        f"⚡ Instant Delivery  |  🔒 Verified Stock</blockquote>\n\n"
        f"<blockquote>Best Prices  ·  24/7 Support  ·  Trusted Seller</blockquote>\n\n"
        f"👇 <b>Use the menu to get started!</b>"
    )

    _join_urls = JOIN_URLS
    support_url = get_support_url()
    channel_url = _join_urls[0] if _join_urls else "https://t.me/"
    inline_btns = [[
        Button.url("📩 Support Chat", support_url),
        Button.url("📢 Our Channel", channel_url),
    ]]

    # Optional start photo — set via admin panel (settings key = 'start_photo')
    _photo_row = db.execute("SELECT value FROM settings WHERE key='start_photo'").fetchone()
    _photo = _photo_row[0] if _photo_row and _photo_row[0] else None

    if isinstance(event, events.CallbackQuery.Event):
        try:
            await event.delete()
        except Exception as _e:
            logger.debug(f'Suppressed non-critical error: {_e}')
        # FIX: use blob fallback so photo works after Termux restart
        async def _menu_photo_send(file, **kw): return await bot.send_file(uid, file, **kw)
        _sent_photo = None
        if _photo:
            try:
                _sent_photo = await _send_with_blob_fallback(
                    _menu_photo_send, 'start_photo', _photo,
                    caption=msg, buttons=inline_btns, parse_mode='html'
                )
            except Exception as _e:
                logger.debug(f'Could not send start photo: {_e}')
        if not _sent_photo:
            await bot.send_message(uid, msg, buttons=inline_btns, link_preview=False)
    else:
        async def _menu_photo_send_ev(file, **kw): return await bot.send_file(uid, file, **kw)
        _sent_photo_ev = None
        if _photo:
            try:
                _sent_photo_ev = await _send_with_blob_fallback(
                    _menu_photo_send_ev, 'start_photo', _photo,
                    caption=msg, buttons=inline_btns, parse_mode='html'
                )
            except Exception as _e:
                logger.debug(f'Could not send start photo: {_e}')
        if not _sent_photo_ev:
            await event.respond(msg, buttons=inline_btns, link_preview=False)

    keyboard = get_persistent_menu(uid)
    if keyboard:
        await bot.send_message(uid, "👇 <b>Choose an option:</b>", buttons=keyboard)

# ================= STOCK INFO =================
async def show_stock_info(event):
    rows = db.execute(
        "SELECT MIN(country_icon), country_name, category, COUNT(*) as cnt "
        "FROM stock WHERE available=1 "
        "GROUP BY country_name, category "
        "ORDER BY country_name ASC"
    ).fetchall()

    total     = db.execute("SELECT COUNT(*) FROM stock WHERE available=1").fetchone()[0]
    if not rows:
        btns_empty = [
            [Button.inline("🛒 Buy Account", "cat|single"),
             Button.inline("📁 Buy Sessions", "cat|bulk")]
        ]
        return await event.reply(
            f"📦 <b>Stock Info</b>\n\n"
            f"❌ <b>No stock available right now.</b>\n"
            f"<i>Check back soon!</i>",
            buttons=btns_empty
        )

    # Build per-category counts
    cat_counts = {}
    for icon, cname, cat, cnt in rows:
        cat_counts[cat] = cat_counts.get(cat, 0) + cnt

    lines = [
        f"📦 <b>LIVE STOCK INFO</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🌐 <b>Total Available:</b> <code>{total}</code> accounts",
    ]
    for _cat in STOCK_CATEGORIES:
        _n = cat_counts.get(_cat, 0)
        if _n > 0:
            lines.append(f"{get_cat_badge(_cat)}: <code>{_n}</code>")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━")

    btns = []

    # Group rows by category in display order
    cat_rows: dict = {c: [] for c in STOCK_CATEGORIES}
    for icon, cname, cat, cnt in rows:
        if cat in cat_rows:
            cat_rows[cat].append((icon, cname, cnt))

    for cat in STOCK_CATEGORIES:
        group = cat_rows.get(cat, [])
        if not group:
            continue
        badge = get_cat_badge(cat)
        g_total = sum(c for _, _, c in group)
        lines.append(f"\n{badge}  (<code>{g_total}</code> available)")
        lines.append(f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄")
        for icon, cname, cnt in group:
            stock_dot = "🟢" if cnt >= 5 else ("🟡" if cnt >= 2 else "🔴")
            lines.append(f"  {icon} <b>{cname}</b>  ➤  {stock_dot} <b>{cnt}</b> in stock")
            btns.append([Button.inline(
                f"🛒 Buy {cname} — {badge}",
                f"bc|single|{cname}|{cat}"
            )])

    lines.append(f"\n━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"<i>Tap a country below to see prices & buy directly ↓</i>")

    msg = "\n".join(lines)
    if len(msg) > 4000:
        msg = msg[:3990] + "\n<i>…and more</i>"

    # Trim buttons if somehow over Telegram's 100-button limit
    if len(btns) > 50:
        btns = btns[:50]

    await event.reply(msg, buttons=btns if btns else None)

# ================= DEPOSIT HANDLERS =================
def format_payment_buttons(buttons):
    n = len(buttons)
    res = []
    for i in range(0, n, 2): res.append(buttons[i:i+2])
    return res

async def deposit_menu(event):
    msg = (
        f"💳 <b>Deposit Funds</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Choose your preferred payment method below.\n"
        f"📸 Submit proof after payment — balance is\n"
        f"credited once an admin approves your request.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    flat_buttons = []
    upi_enabled_row = db.execute("SELECT value FROM settings WHERE key='upi_enabled'").fetchone()
    upi_enabled = (upi_enabled_row[0] if upi_enabled_row else '1') != '0'
    if upi_enabled:
        flat_buttons.append(Button.inline("🏦 UPI (Manual)", "dep_upi"))
    hlk_enabled_row = db.execute("SELECT value FROM settings WHERE key='cwallet_enabled'").fetchone()
    hlk_enabled = (hlk_enabled_row[0] if hlk_enabled_row else '0') != '0'
    if hlk_enabled:
        hlk_bonus_row = db.execute("SELECT value FROM settings WHERE key='cwallet_bonus_pct'").fetchone()
        hlk_bonus_pct = int(hlk_bonus_row[0]) if hlk_bonus_row and hlk_bonus_row[0] else 0
        hlk_coin_row = db.execute("SELECT value FROM settings WHERE key='cwallet_coin'").fetchone()
        hlk_coin = (hlk_coin_row[0] if hlk_coin_row and hlk_coin_row[0] else CWALLET_COIN)
        _hlk_label = f"🔷 {hlk_coin} Auto-Pay"
        if hlk_bonus_pct > 0:
            _hlk_label += f" ( +{hlk_bonus_pct}% )"
        flat_buttons.append(Button.inline(_hlk_label, "dep_cwallet"))
    customs = db.execute("SELECT name FROM custom_payments").fetchall()
    for c in customs:
        flat_buttons.append(Button.inline(f"💳 {c[0]}", f"depm_{c[0]}"))
    btns = format_payment_buttons(flat_buttons)
    await bot.send_message(event.chat_id, msg, buttons=btns)

def get_keypad():
    return [
        [Button.inline("1", "kp_1"), Button.inline("2", "kp_2"), Button.inline("3", "kp_3")],
        [Button.inline("4", "kp_4"), Button.inline("5", "kp_5"), Button.inline("6", "kp_6")],
        [Button.inline("7", "kp_7"), Button.inline("8", "kp_8"), Button.inline("9", "kp_9")],
        [Button.inline("🔙 Del", "kp_del"), Button.inline("0", "kp_0"), Button.inline("✅ Confirm", "kp_done")],
        [Button.inline("❌ Cancel", "cancel_action")]
    ]

def get_admin_custom_keypad(dep_id):
    return [
        [Button.inline("1", f"dkp|{dep_id}|1"), Button.inline("2", f"dkp|{dep_id}|2"), Button.inline("3", f"dkp|{dep_id}|3")],
        [Button.inline("4", f"dkp|{dep_id}|4"), Button.inline("5", f"dkp|{dep_id}|5"), Button.inline("6", f"dkp|{dep_id}|6")],
        [Button.inline("7", f"dkp|{dep_id}|7"), Button.inline("8", f"dkp|{dep_id}|8"), Button.inline("9", f"dkp|{dep_id}|9")],
        [Button.inline("🔙 Del", f"dkp|{dep_id}|del"), Button.inline("0", f"dkp|{dep_id}|0"), Button.inline("✅ Confirm", f"dkp|{dep_id}|conf")],
        [Button.inline("❌ Cancel", f"dkp|{dep_id}|cancel")]
    ]

async def manual_deposit_init(event, method):
    uid = event.sender_id
    deposit_input[uid] = {'step': 'wait_amt', 'method': method, 'ts': time.time()}
    msg = (
        f"💳 <b>{method} Deposit</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💬 Send the <b>amount in ₹ (INR)</b> you wish to deposit."
    )
    btns = [[Button.inline("❌ Cancel", "cancel_action")]]
    try:
        await event.edit(msg, buttons=btns)
    except Exception:
        await bot.send_message(event.chat_id, msg, buttons=btns)

async def init_upi_keypad(event):
    uid = event.sender_id
    deposit_input[uid] = {'step': 'upi_keypad', 'val': '0', 'ts': time.time()}
    msg = (
        f"🏦 <b>UPI Deposit</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Enter the amount to deposit (Min ₹10):\n\n"
        f"{P_MONEY} <b>Amount:</b> <code>₹0</code>"
    )
    try:
        await event.edit(msg, buttons=get_keypad())
    except Exception:
        await bot.send_message(event.chat_id, msg, buttons=get_keypad())

async def keypad_logic(event):
    uid = event.sender_id
    action = event.data.decode().replace("kp_", "")
    curr = deposit_input.get(uid, {}).get('val', "0")

    if action.isdigit():
        if curr == "0": curr = action
        else: curr += action
        if len(curr) > 5: curr = curr[:5]
    elif action == "del": curr = curr[:-1] or "0"
    elif action == "done":
        try:
            amt = int(curr)
        except (ValueError, TypeError):
            return await event.answer("⚠️ Invalid amount.", alert=True)
        if amt < 10:  return await event.answer("⚠️ Minimum Deposit is ₹10", alert=True)
        if amt > 99999: return await event.answer("⚠️ Maximum Deposit is ₹99,999", alert=True)
        kp_step = deposit_input.get(uid, {}).get('step', 'upi_keypad')
        if kp_step == 'cwallet_keypad':
            return await show_cwallet_payment(event, amt)
        return await show_upi_manual_payment(event, amt)
    
    kp_step = deposit_input.get(uid, {}).get('step', 'upi_keypad')
    _prev_ts = deposit_input.get(uid, {}).get('ts', time.time())
    deposit_input[uid] = {'step': kp_step, 'val': curr, 'network': deposit_input.get(uid, {}).get('network'), 'ts': _prev_ts}
    if kp_step == 'cwallet_keypad':
        _hlk_cr = db.execute("SELECT value FROM settings WHERE key='cwallet_coin'").fetchone()
        _hlk_c = _hlk_cr[0] if _hlk_cr and _hlk_cr[0] else CWALLET_COIN
        _hlk_n = deposit_input.get(uid, {}).get('network') or _cwallet_network()
        label = f"🔷 <b>CWallet Crypto Deposit ({_hlk_c} / {_hlk_n.upper()})</b>"
    else:
        label = "🏦 <b>UPI Deposit</b>"
    kp_msg = (
        f"{label}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Enter the amount to deposit (Min ₹10):\n\n"
        f"{P_MONEY} <b>Amount:</b> <code>₹{curr}</code>"
    )
    try:
        await event.edit(kp_msg, buttons=get_keypad())
    except Exception:
        await bot.send_message(event.chat_id, kp_msg, buttons=get_keypad())

def get_active_upi_id():
    row = db.execute("SELECT value FROM settings WHERE key='upi_id'").fetchone()
    return row[0] if row and row[0] else UPI_ID

def generate_upi_qr(upi_id, amount):
    import qrcode
    upi_link = f"upi://pay?pa={upi_id}&pn=Store&am={amount}&cu=INR"
    path = f"upi_qr_tmp_{amount}_{int(time.time())}.png"

    # Primary: Pillow-based PNG (best quality, requires: pip install pillow)
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(upi_link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(path)
        return path
    except Exception as _qr_e:
        logger.debug(f'qrcode/pillow QR generation failed, trying pypng fallback: {_qr_e}')

    # Fallback: pure-Python pypng (works on Termux — no system libs needed)
    # Install with: pip install pypng
    try:
        import qrcode.image.pure
        qr = qrcode.QRCode(version=1, box_size=10, border=4,
                           image_factory=qrcode.image.pure.PyPNGImage)
        qr.add_data(upi_link)
        qr.make(fit=True)
        img = qr.make_image()
        img.save(path)
        return path
    except Exception:
        raise RuntimeError("QR generation failed: both Pillow and pypng methods failed. Install 'qrcode[pil]' or 'pypng'.")

async def show_upi_manual_payment(event, amount):
    uid = event.sender_id
    deposit_input.pop(uid, None)
    waiting_proof[uid] = {'amount': amount, 'method': 'UPI', 'expires_at': time.time() + 600}

    _active_upi_id = get_active_upi_id()

    msg_with_qr = (f"{P_UPI} <b>UPI Payment</b>\n\n"
                   f"{P_MONEY} <b>Amount:</b> <code>₹{amount}</code>\n\n"
                   f"📱 <b>Scan the QR above</b> — opens your UPI app with ₹{amount} pre-filled.\n\n"
                   f"📸 After paying, send a clear <b>Screenshot</b> here.\n"
                   f"<i>Balance will be credited after admin approval.</i>\n\n"
                   f"⏱ <b>This QR expires in 10 minutes.</b>")

    msg_no_qr = (f"{P_UPI} <b>UPI Payment</b>\n\n"
                 f"{P_MONEY} <b>Amount:</b> <code>₹{amount}</code>\n\n"
                 f"🔗 <b>Pay manually to this UPI ID:</b>\n<code>{_active_upi_id}</code>\n\n"
                 f"⚠️ <i>QR code could not be generated. Please copy the UPI ID above and pay ₹{amount} manually.</i>\n\n"
                 f"📸 After paying, send a clear <b>Screenshot</b> here.\n"
                 f"<i>Balance will be credited after admin approval.</i>\n\n"
                 f"⏱ <b>This session expires in 10 minutes.</b>")

    try:
        await event.delete()
    except Exception as _e:
        logger.debug(f'Suppressed non-critical error: {_e}')

    btns = [[Button.inline("❌ Cancel", "cancel_action")]]
    qr_path = None
    sent_msg = None
    qr_error = None

    # 1. Generate dynamic QR locally (amount pre-filled)
    try:
        qr_path = generate_upi_qr(get_active_upi_id(), amount)
        sent_msg = await bot.send_file(uid, qr_path, caption=msg_with_qr, buttons=btns)
    except Exception as qr_err:
        qr_error = qr_err
        logger.warning(f"Dynamic QR generation failed for uid={uid} amt={amount}: {qr_err}")
    finally:
        if qr_path and os.path.exists(qr_path):
            try: os.remove(qr_path)
            except Exception as _e:
                logger.debug(f'Suppressed non-critical error: {_e}')

    # 2. Fallback: admin-uploaded static QR (DB blob first, then legacy file path)
    if not sent_msg:
        qr_row = db.execute("SELECT value FROM settings WHERE key='upi_qr_file_id'").fetchone()
        _qr_val = qr_row[0] if qr_row and qr_row[0] else None
        async def _upi_send_fn(file, **kw): return await bot.send_file(uid, file, **kw)
        try:
            sent_msg = await _send_with_blob_fallback(
                _upi_send_fn, 'upi_qr', _qr_val, caption=msg_with_qr, buttons=btns
            )
        except Exception as static_err:
            logger.warning(f"Static QR send failed for uid={uid}: {static_err}")

    # 3. Fallback: text only — show clear manual payment instructions
    if not sent_msg:
        logger.warning(f"No QR available for uid={uid}, sending text-only UPI instructions. Root cause: {qr_error}")
        sent_msg = await bot.send_message(uid, msg_no_qr, buttons=btns)
        # Notify admin that QR is not working
        try:
            await bot.send_message(
                ADMIN_ID,
                f"{P_WARN} <b>UPI QR Not Working!</b>\n\n"
                f"User <code>{uid}</code> tried to deposit ₹{amount} via UPI but QR generation failed.\n\n"
                f"<b>Error:</b> <code>{html.escape(str(qr_error))}</code>\n\n"
                f"<i>Fix: Install <code>qrcode</code> and <code>pillow</code> libraries, or upload a static QR from Admin → Payments → UPI QR.</i>"
            )
        except Exception as _adm_e:
            logger.debug(f'Admin UPI notify failed: {_adm_e}')

    # Store message ID so the expiry task can edit it
    # BUG FIX: guard against race where another coroutine cleared waiting_proof[uid]
    if sent_msg and uid in waiting_proof:
        waiting_proof[uid]['msg_id'] = sent_msg.id
    if uid in waiting_proof:
        _save_waiting_proof(uid, waiting_proof[uid])
    asyncio.create_task(upi_qr_expiry_task(uid, amount))

async def upi_qr_expiry_task(uid, amount):
    await asyncio.sleep(600)
    proof = waiting_proof.get(uid)
    # If user already submitted proof or cancelled, do nothing
    if not proof or proof.get('method') != 'UPI':
        return
    waiting_proof.pop(uid, None)
    _clear_waiting_proof_db(uid)
    msg_id = proof.get('msg_id')
    if msg_id:
        try:
            await bot.edit_message(uid, msg_id,
                f"⌛ <b>UPI QR Expired</b>\n\n"
                f"Your payment session for <b>₹{amount}</b> has timed out (10 min limit).\n\n"
                f"If you already paid, contact support with your screenshot.\n"
                f"Otherwise, tap <b>Deposit</b> in the main menu to start again.")
        except Exception as _e:
            logger.debug(f'UPI expiry edit failed uid={uid}: {_e}')

# ─── CWallet API helpers ───────────────────────────────────────────────────────

def _cwallet_api_key() -> str:
    """Return active CWallet API key (DB override > hardcoded constant)."""
    row = db.execute("SELECT value FROM settings WHERE key='cwallet_api_key'").fetchone()
    return (row[0] if row and row[0] else CWALLET_API_KEY).strip()

def _cwallet_coin() -> str:
    row = db.execute("SELECT value FROM settings WHERE key='cwallet_coin'").fetchone()
    return row[0] if row and row[0] else CWALLET_COIN

def _cwallet_network() -> str:
    row = db.execute("SELECT value FROM settings WHERE key='cwallet_network'").fetchone()
    return row[0] if row and row[0] else CWALLET_NETWORK

def _doh_resolve_ipv4(hostname: str) -> str | None:
    """
    Resolve *hostname* to an IPv4 address using DNS-over-HTTPS.

    We connect directly to Google (8.8.8.8) and Cloudflare (1.1.1.1) by their
    IP addresses — so NO system DNS is needed at all.  This is the only reliable
    way to resolve hostnames on Termux / Android 13 when the Android resolver
    returns [Errno 7] No address associated with hostname.
    """
    doh_servers = [
        ("8.8.8.8",  443, "dns.google",        "/resolve"),
        ("1.1.1.1",  443, "cloudflare-dns.com", "/dns-query"),
    ]
    for ip, port, sni_host, doh_path in doh_servers:
        try:
            ctx = ssl.create_default_context()
            raw = socket.create_connection((ip, port), timeout=10)
            tls = ctx.wrap_socket(raw, server_hostname=sni_host)

            query   = urllib.parse.urlencode({"name": hostname, "type": "A"})
            request = (
                f"GET {doh_path}?{query} HTTP/1.1\r\n"
                f"Host: {sni_host}\r\n"
                f"Accept: application/dns-json\r\n"
                f"Connection: close\r\n\r\n"
            )
            tls.sendall(request.encode())

            data = b""
            while True:
                chunk = tls.recv(4096)
                if not chunk:
                    break
                data += chunk
            tls.close()

            # HTTP response: split off headers
            _, _, body = data.partition(b"\r\n\r\n")
            parsed = json.loads(body)
            for ans in parsed.get("Answer", []):
                if ans.get("type") == 1:          # A record → IPv4
                    ip_addr = ans["data"].strip()
                    logger.info(f"DoH resolved {hostname} → {ip_addr} via {sni_host}")
                    return ip_addr
        except Exception as _e:
            logger.debug(f"DoH resolve via {sni_host} ({ip}) failed: {_e}")
            continue
    return None


def _cwallet_raw_request(method: str, hostname: str, port: int, full_path: str,
                          headers: dict, body: bytes, resolved_ip: str, timeout: int) -> bytes:
    """
    Make an HTTPS request to *resolved_ip* while sending SNI / Host for *hostname*.
    This lets us completely bypass Android's DNS resolver.
    Returns the raw HTTP response body bytes.
    Raises http.client.HTTPException (or OSError) on network errors.
    """
    ctx = ssl.create_default_context()
    raw = socket.create_connection((resolved_ip, port), timeout=timeout)
    tls = ctx.wrap_socket(raw, server_hostname=hostname)   # SNI = real hostname

    # Build a minimal HTTP/1.1 request by hand
    hdr_lines = f"{method.upper()} {full_path} HTTP/1.1\r\nHost: {hostname}\r\n"
    for k, v in headers.items():
        hdr_lines += f"{k}: {v}\r\n"
    if body:
        hdr_lines += f"Content-Length: {len(body)}\r\n"
    hdr_lines += "Connection: close\r\n\r\n"

    tls.sendall(hdr_lines.encode() + body)

    resp_bytes = b""
    while True:
        chunk = tls.recv(8192)
        if not chunk:
            break
        resp_bytes += chunk
    tls.close()
    return resp_bytes


def _cwallet_request_sync(method: str, path: str, payload: dict = None) -> dict:
    """
    Synchronous CWallet API call (run via asyncio.to_thread for non-blocking use).

    Three-layer strategy for Termux / Android 13 where [Errno 7] No address
    associated with hostname is a common DNS failure:

      1. requests library  — if installed, handles everything automatically.
      2. System DNS + urllib — standard approach; works on desktops / VPS.
      3. DoH + raw SSL socket — resolves via Google/Cloudflare IPs directly
         (no Android resolver involved at all), then connects to the resolved IP
         with proper SNI so TLS certificates still validate correctly.
    """
    api_key  = _cwallet_api_key()
    full_url = CWALLET_API_BASE + path
    body     = json.dumps(payload).encode() if payload else b""
    req_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }
    _max_retries = 3
    _last_err    = None

    # ── Layer 1: requests library (best Android support) ──────────────────────
    try:
        import requests as _req
        for _attempt in range(_max_retries):
            try:
                r = _req.request(
                    method.upper(), full_url,
                    headers=req_headers,
                    data=body or None,
                    timeout=25,
                )
                if r.status_code >= 400:
                    logger.warning(f"CWallet {method} {path} HTTP {r.status_code}: {r.text}")
                    try:
                        return r.json()
                    except Exception:
                        return {"error": r.text, "code": r.status_code}
                return r.json()
            except Exception as _re:
                _last_err = _re
                logger.warning(f"CWallet (requests) attempt {_attempt+1}/{_max_retries}: {_re}")
                if _attempt < _max_retries - 1:
                    time.sleep(2 * (_attempt + 1))
        return {"error": f"Network error – could not reach CWallet: {_last_err}"}
    except ImportError:
        pass  # requests not installed — fall through to urllib / DoH

    # ── Layer 2 + 3: urllib with automatic DoH fallback ───────────────────────
    parsed   = urllib.parse.urlparse(full_url)
    hostname = parsed.hostname
    port     = parsed.port or 443
    api_path = parsed.path + (f"?{parsed.query}" if parsed.query else "")

    # Attempt normal IPv4 resolution first; if it fails, resolve via DoH
    resolved_ip = None
    try:
        info        = socket.getaddrinfo(hostname, port, socket.AF_INET, socket.SOCK_STREAM)
        resolved_ip = info[0][4][0]
        logger.debug(f"System DNS resolved {hostname} → {resolved_ip}")
    except socket.gaierror as _dns_err:
        logger.warning(f"System DNS failed for {hostname}: {_dns_err}. Trying DoH…")
        resolved_ip = _doh_resolve_ipv4(hostname)
        if not resolved_ip:
            logger.error(f"DoH also failed for {hostname}")

    for _attempt in range(_max_retries):
        try:
            if resolved_ip:
                # Layer 3: raw SSL socket → no Android DNS involved at all
                resp_bytes = _cwallet_raw_request(
                    method, hostname, port, api_path,
                    req_headers, body, resolved_ip, timeout=25,
                )
                # Parse HTTP status from response line
                first_line = resp_bytes.split(b"\r\n", 1)[0]
                status_code = int(first_line.split(b" ", 2)[1])
                _, _, resp_body = resp_bytes.partition(b"\r\n\r\n")
                if status_code >= 400:
                    logger.warning(f"CWallet {method} {path} HTTP {status_code}: {resp_body[:200]}")
                    try:
                        return json.loads(resp_body)
                    except Exception:
                        return {"error": resp_body.decode(errors="replace"), "code": status_code}
                return json.loads(resp_body)
            else:
                # Layer 2: urllib (system DNS must work)
                req = urllib.request.Request(full_url, data=body or None,
                                             headers=req_headers, method=method.upper())
                with urllib.request.urlopen(req, timeout=25) as resp:
                    return json.loads(resp.read().decode())

        except urllib.error.HTTPError as e:
            rb = e.read().decode(errors="replace")
            logger.warning(f"CWallet {method} {path} HTTP {e.code}: {rb}")
            try:
                return json.loads(rb)
            except Exception:
                return {"error": str(e), "code": e.code}
        except (urllib.error.URLError, OSError, ValueError) as e:
            _last_err = e
            logger.warning(f"CWallet attempt {_attempt+1}/{_max_retries}: {e}")
            if _attempt < _max_retries - 1:
                time.sleep(2 * (_attempt + 1))
        except Exception as e:
            logger.warning(f"CWallet unexpected error: {e}")
            return {"error": str(e)}

    logger.error(f"CWallet {method} {path} failed after {_max_retries} attempts: {_last_err}")
    return {
        "error": (
            f"Network error – could not reach CWallet after {_max_retries} attempts.\n"
            f"Fix: run  pip install requests  in Termux, then restart the bot.\n"
            f"Detail: {_last_err}"
        )
    }

async def _cwallet_create_invoice(amount_inr: int, order_id: str, network: str = None, coin: str = None) -> dict:
    """Create a CWallet invoice; returns the API response dict."""
    rate = get_usdt_rate()
    usdt_amt = round(amount_inr / rate, 4)
    coin = coin or _cwallet_coin()
    network = (network or _cwallet_network()).lower()
    payload = {
        "currency": coin,
        "network": network,
        "orderId": order_id,
        "amount": str(usdt_amt),
        "lifetime": 1800,
    }
    return await asyncio.to_thread(_cwallet_request_sync, "POST", "/payment", payload)

async def _cwallet_get_invoice(invoice_id: str) -> dict:
    """Fetch current status of a CWallet invoice."""
    return await asyncio.to_thread(_cwallet_request_sync, "GET", f"/payment/{invoice_id}")

async def show_cwallet_payment(event, amount):
    uid = event.sender_id
    deposit_input.pop(uid, None)
    api_key = _cwallet_api_key()
    if not api_key:
        try:
            await event.edit(
                f"{P_NO} <b>CWallet is not configured yet.</b>\n\n"
                f"Please ask the admin to set the CWallet API key in the Admin Panel.",
                buttons=[[Button.inline("🔙 Back", "cancel_action")]]
            )
        except Exception:
            await bot.send_message(uid,
                f"{P_NO} <b>CWallet is not configured yet.</b> Contact admin.",
                buttons=[[Button.inline("🔙 Back", "cancel_action")]]
            )
        return
    bonus_row = db.execute("SELECT value FROM settings WHERE key='cwallet_bonus_pct'").fetchone()
    bonus_pct = int(bonus_row[0]) if bonus_row and bonus_row[0] else 0
    bonus_amt = int(amount * bonus_pct / 100)
    rate = get_usdt_rate()
    usdt_amt = round(amount / rate, 4)
    coin = _cwallet_coin()
    network = (deposit_input.get(uid, {}).get('network') or _cwallet_network()).lower()
    # Create invoice
    order_id = f"uid{uid}_{int(time.time())}"
    # Create invoice BEFORE deleting the keypad message, so user can retry if API fails
    resp = None
    try:
        resp = await _cwallet_create_invoice(amount, order_id, network=network, coin=coin)
    except Exception as api_err:
        logger.error(f"show_cwallet_payment: create invoice failed uid={uid}: {api_err}")
        try:
            await event.edit(
                f"{P_NO} <b>Failed to create CWallet invoice.</b>\n"
                f"Please try again or contact support.\n<i>Error: {html.escape(str(api_err))}</i>",
                buttons=[[Button.inline("🔙 Back to Deposit", "show_deposit"), Button.inline("❌ Close", "cancel_action")]]
            )
        except Exception:
            await bot.send_message(uid,
                f"{P_NO} <b>Failed to create CWallet invoice.</b> Please try again or contact support.",
                buttons=[[Button.inline("❌ Close", "cancel_action")]]
            )
        return
    if resp.get("error") or (not resp.get("address") and not resp.get("payAddress") and not resp.get("id")):
        err_msg = resp.get("message") or resp.get("error") or "Unknown API error"
        logger.warning(f"show_cwallet_payment: API error uid={uid}: {resp}")
        try:
            await event.edit(
                f"{P_NO} <b>CWallet API Error:</b> {html.escape(str(err_msg))}\n\n"
                f"Please contact support or try another payment method.",
                buttons=[[Button.inline("🔙 Back to Deposit", "show_deposit"), Button.inline("❌ Close", "cancel_action")]]
            )
        except Exception:
            await bot.send_message(uid,
                f"{P_NO} <b>CWallet API Error:</b> {html.escape(str(err_msg))}",
                buttons=[[Button.inline("❌ Close", "cancel_action")]]
            )
        return
    # Extract fields — CWallet may use different key names
    invoice_id = resp.get("id") or resp.get("invoiceId") or resp.get("uuid") or order_id
    pay_address = (resp.get("address") or resp.get("payAddress") or
                   resp.get("paymentAddress") or resp.get("wallet") or "")
    actual_usdt = resp.get("amount") or str(usdt_amt)
    # Save invoice to DB
    dep_id = None
    with _db_write_lock:
        ins = db.execute(
            "INSERT INTO deposits (user_id, amount, method_name, status) VALUES (?,?,?,?)",
            (uid, amount + bonus_amt, f"CWallet ({coin})", "pending")
        )
        dep_id = ins.lastrowid
        db.execute(
            "INSERT OR REPLACE INTO cwallet_invoices "
            "(invoice_id, user_id, amount_inr, amount_usdt, bonus_pct, address, dep_id, "
            "status, created_at, expires_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (invoice_id, uid, amount, str(actual_usdt), bonus_pct,
             pay_address, dep_id, "pending", time.time(), time.time() + 1800)
        )
        db.commit()
    msg = (
        f"🔷 <b>CWallet Crypto Deposit</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{P_MONEY} <b>INR Amount:</b> <code>₹{amount}</code>\n"
        f"💲 <b>{coin} Amount:</b> <code>{actual_usdt}</code>\n"
        f"🌐 <b>Network:</b> <code>{network.upper()}</code>\n"
    )
    if bonus_pct > 0:
        msg += (f"{P_GIFT} <b>Bonus ({bonus_pct}%):</b> <code>+₹{bonus_amt}</code>\n"
                f"{P_YES} <b>You receive:</b> <code>₹{amount + bonus_amt}</code>\n")
    msg += (
        f"\n📬 <b>Send exactly <code>{actual_usdt} {coin}</code> to:</b>\n"
        f"<code>{pay_address or 'See your CWallet wallet'}</code>\n\n"
        f"⚡ <b>Auto-approved</b> within seconds of payment detection!\n"
        f"⏱ <b>This invoice expires in 30 minutes.</b>\n\n"
        f"🔑 <b>Invoice ID:</b> <code>{invoice_id}</code>"
    )
    try:
        await event.delete()
    except Exception as _e:
        logger.debug(f'Suppressed non-critical error: {_e}')
    btns = [[Button.inline("❌ Cancel", "cancel_action")]]
    sent_msg = await bot.send_message(uid, msg, buttons=btns)
    msg_id = sent_msg.id if sent_msg else None
    if msg_id:
        with _db_write_lock:
            db.execute("UPDATE cwallet_invoices SET msg_id=? WHERE invoice_id=?", (msg_id, invoice_id))
            db.commit()
    # Notify payment log channel
    try:
        await bot.send_message(
            get_payment_log_channel(),
            f"🔷 <b>NEW CWALLET REQUEST</b>\n"
            f"{P_ACC} User: <code>{uid}</code>\n"
            f"{P_MONEY} INR: {P_INR}{amount}"
            + (f" → ₹{amount + bonus_amt} with bonus" if bonus_pct else "") + "\n"
            f"💲 {coin}: <code>{actual_usdt}</code>\n"
            f"📬 Address: <code>{pay_address}</code>\n"
            f"🔑 Invoice: <code>{invoice_id}</code>\n"
            f"⏳ Monitoring for 30 min — will auto-approve on payment."
        )
    except Exception as _e:
        logger.debug(f"cwallet log channel notify failed: {_e}")
    # Launch background monitor
    asyncio.create_task(cwallet_payment_monitor(invoice_id, uid, amount, bonus_pct, dep_id, msg_id))


# ================= CWALLET PAYMENT MONITOR =================
def _cw_pick(obj, *keys):
    """Pick a value from a dict using case-insensitive key matching."""
    if not isinstance(obj, dict):
        return None
    lower = {str(k).lower(): v for k, v in obj.items()}
    for key in keys:
        if key.lower() in lower:
            return lower[key.lower()]
    return None


def _cw_find_value(obj, keys, max_depth=4):
    """Find a value in common nested Cwallet response shapes."""
    if max_depth < 0:
        return None
    if isinstance(obj, dict):
        val = _cw_pick(obj, *keys)
        if val is not None:
            return val
        for v in obj.values():
            found = _cw_find_value(v, keys, max_depth - 1)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _cw_find_value(v, keys, max_depth - 1)
            if found is not None:
                return found
    return None


def _cw_payment_state(resp):
    """Return (state, paid_amount) from flexible API response shapes."""
    state = _cw_find_value(resp, (
        'status', 'paymentStatus', 'payment_status', 'invoiceStatus',
        'invoice_status', 'state'
    ))
    paid_flag = _cw_find_value(resp, ('paid', 'isPaid', 'is_paid', 'success'))
    if isinstance(paid_flag, bool) and paid_flag:
        state = 'paid'
    if state is None:
        state = ''
    state = str(state).strip().lower()
    paid_amount = _cw_find_value(resp, (
        'paidAmount', 'paid_amount', 'receivedAmount', 'received_amount',
        'actualAmount', 'actual_amount', 'amount'
    ))
    return state, paid_amount


def _cw_amount_ok(paid_amount, expected_amount):
    """Require the reported crypto amount to cover the invoice when available."""
    if paid_amount in (None, ''):
        # A confirmed paid/completed state is still usable when the API does not
        # return an amount on the status endpoint.
        return True
    try:
        return float(paid_amount) + 1e-8 >= float(expected_amount)
    except (TypeError, ValueError):
        return False


async def cwallet_payment_monitor(invoice_id, uid, amount, bonus_pct, dep_id, msg_id=None):
    """Poll the configured Cwallet invoice endpoint and atomically credit a paid deposit.

    This is intentionally conservative: only an explicit paid/success/completed state
    can approve the deposit. Pending/unknown/error responses never credit balance.
    """
    deadline = time.time() + 1800
    paid_states = {
        'paid', 'success', 'successful', 'completed', 'complete',
        'confirmed', 'finished', 'done', 'settled'
    }
    failed_states = {'expired', 'cancelled', 'canceled', 'failed', 'rejected', 'refunded'}
    expected_crypto = None
    try:
        row = db.execute(
            "SELECT amount_usdt FROM cwallet_invoices WHERE invoice_id=?", (invoice_id,)
        ).fetchone()
        if row:
            expected_crypto = row[0]
    except Exception:
        pass

    while time.time() < deadline:
        try:
            resp = await _cwallet_get_invoice(invoice_id)
            if not isinstance(resp, dict):
                resp = {}
            if resp.get('error'):
                await asyncio.sleep(15)
                continue

            state, paid_amount = _cw_payment_state(resp)
            if state in failed_states:
                with _db_write_lock:
                    db.execute(
                        "UPDATE cwallet_invoices SET status=? WHERE invoice_id=? AND status='pending'",
                        (state, invoice_id)
                    )
                    db.execute(
                        "UPDATE deposits SET status='rejected' WHERE id=? AND status='pending'",
                        (dep_id,)
                    )
                    db.commit()
                try:
                    await bot.send_message(uid,
                        f"{P_NO} <b>Cwallet payment {html.escape(state)}.</b>\n"
                        f"No balance was added. You can start a new deposit.")
                except Exception:
                    pass
                return

            if state in paid_states and _cw_amount_ok(paid_amount, expected_crypto):
                credit = int(amount + (amount * int(bonus_pct or 0) / 100))
                method = f"CWallet ({_cwallet_coin()})"
                async with get_user_lock(uid):
                    with _db_write_lock:
                        # One atomic state transition prevents duplicate credits.
                        changed = db.execute(
                            "UPDATE deposits SET status='approved', amount=? "
                            "WHERE id=? AND status='pending'",
                            (credit, dep_id)
                        ).rowcount
                        if changed == 0:
                            return
                        prev_row = db.execute(
                            "SELECT balance FROM users WHERE user_id=?", (uid,)
                        ).fetchone()
                        prev_bal = prev_row[0] if prev_row else 0
                        db.execute(
                            "UPDATE users SET balance=balance+?, total_deposited=total_deposited+? "
                            "WHERE user_id=?", (credit, credit, uid)
                        )
                        db.execute(
                            "UPDATE cwallet_invoices SET status='paid' WHERE invoice_id=?",
                            (invoice_id,)
                        )
                        db.commit()
                try:
                    await process_referral_bonus(uid, credit)
                except Exception as _e:
                    logger.debug(f"Cwallet referral bonus failed: {_e}")
                try:
                    await log_primary_deposit(uid, credit, method)
                except Exception as _e:
                    logger.debug(f"Cwallet deposit log failed: {_e}")
                try:
                    await bot.send_message(
                        uid,
                        f"{P_YES} <b>Cwallet Payment Confirmed!</b>\n\n"
                        f"{P_MONEY} Added: <code>₹{credit}</code>\n"
                        f"📉 Old Balance: <code>₹{prev_bal}</code>\n"
                        f"📈 New Balance: <code>₹{prev_bal + credit}</code>\n\n"
                        f"🔑 Invoice: <code>{html.escape(str(invoice_id))}</code>"
                    )
                except Exception:
                    pass
                return
        except asyncio.CancelledError:
            raise
        except Exception as _e:
            logger.warning(f"Cwallet monitor error invoice={invoice_id}: {_e}")
        await asyncio.sleep(15)

    # Expire only if it is still pending; never overwrite a completed payment.
    with _db_write_lock:
        db.execute(
            "UPDATE cwallet_invoices SET status='expired' WHERE invoice_id=? AND status='pending'",
            (invoice_id,)
        )
        db.execute(
            "UPDATE deposits SET status='rejected' WHERE id=? AND status='pending'",
            (dep_id,)
        )
        db.commit()
    try:
        await bot.send_message(uid,
            f"{P_NO} <b>Cwallet invoice expired.</b>\nNo balance was added. Please create a new deposit.")
    except Exception:
        pass

# ================= CWALLET MANUAL DEPOSIT =================
CWALLET_ADDRESS = os.getenv("CWALLET_ADDRESS", "")
CWALLET_QR = os.getenv("CWALLET_QR", "")

def get_cwallet_config():
    addr_row = db.execute("SELECT value FROM settings WHERE key='cwallet_address'").fetchone()
    qr_row = db.execute("SELECT value FROM settings WHERE key='cwallet_qr'").fetchone()
    return (
        addr_row[0] if addr_row and addr_row[0] else CWALLET_ADDRESS,
        qr_row[0] if qr_row and qr_row[0] else CWALLET_QR,
    )

async def init_cwallet_keypad(event, network=None):
    uid = event.sender_id
    if not network:
        return await show_cwallet_networks(event)
    network = network.lower().strip()
    allowed = {n for n, _ in _cwallet_network_options()}
    if network not in allowed:
        return await event.answer("⚠️ Unsupported network option.", alert=True)
    deposit_input[uid] = {'step': 'cwallet_keypad', 'val': '0', 'network': network, 'ts': time.time()}
    label = next((label for n, label in _cwallet_network_options() if n == network), network.upper())
    msg = (
        f"💠 <b>CWallet Deposit</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💲 <b>Coin:</b> USDT\n"
        f"🌐 <b>Network:</b> {html.escape(label)}\n\n"
        f"Enter the amount to deposit (Min ₹10):\n\n"
        f"{P_MONEY} <b>Amount:</b> <code>₹0</code>"
    )
    try:
        await event.edit(msg, buttons=get_keypad())
    except Exception:
        await bot.send_message(event.chat_id, msg, buttons=get_keypad())

async def show_cwallet_networks(event):
    btns = [[Button.inline(label, f"cw_net|{network}")] for network, label in _cwallet_network_options()]
    btns.append([Button.inline("❌ Cancel", "cancel_action")])
    msg = (
        "💠 <b>CWallet Deposit</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💲 <b>Coin:</b> USDT\n"
        "🌐 <b>Select the network you will pay on:</b>\n\n"
        "<i>Send only USDT on the selected network. Sending on another network can cause loss of funds.</i>"
    )
    try:
        await event.edit(msg, buttons=btns)
    except Exception:
        await bot.send_message(event.chat_id, msg, buttons=btns)

# ==========================================================

# ================= BUYING FLOW =================
async def show_category_select(event, flow):
    """Step 1: Category selection — shows all 6 categories with live stock counts."""
    title = f"{P_STORE} <b>Bulk Sessions</b>" if flow == 'bulk' else f"{P_CART} <b>Buy Account</b>"

    # Fetch per-category counts in one query
    cat_rows = db.execute(
        "SELECT category, COUNT(*) FROM stock WHERE available=1 GROUP BY category"
    ).fetchall()
    counts = {cat: cnt for cat, cnt in cat_rows}
    total  = sum(counts.values())

    if total == 0:
        err_msg = f"{P_NO} <b>Stock is Empty right now. Check back later!</b>"
        if isinstance(event, events.CallbackQuery.Event):
            try: return await event.edit(err_msg)
            except Exception as _e:
                logger.debug(f'Suppressed non-critical error: {_e}')
        return await event.respond(err_msg)

    # Category descriptions shown before the user picks
    _CAT_DESC = {
        'Fresh':         '🟢 <b>Fresh</b> — New accounts, never used, low risk of bans.',
        'Cheap':         '💸 <b>Cheap</b> — Budget-friendly accounts at reduced prices.',
        'Old':           '🟡 <b>Old</b> — Aged accounts with activity history.',
        'Spam':          '🔴 <b>Spam</b> — Accounts flagged by Telegram; use at own risk.',
        'Rare':          '💎 <b>Rare</b> — Hard-to-find numbers from limited regions.',
        'Number Change': '🔄 <b>Number Change</b> — Accounts ready for phone-number transfer.',
    }
    _desc_lines = "\n".join(
        _CAT_DESC.get(cat, f"📂 <b>{cat}</b>")
        for cat in STOCK_CATEGORIES
        if counts.get(cat, 0) > 0 or True   # show all so user knows what exists
    )

    msg = (
        f"🟢 <b>Select Category</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{_desc_lines}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 <b>Tap a category to browse:</b>"
    )

    # One button per category in defined order, always shown (0 left if empty)
    btns = []
    for cat in STOCK_CATEGORIES:
        n = counts.get(cat, 0)
        btns.append([Button.inline(f"{get_cat_badge(cat)} | {n} left", f"cat_sel|{flow}|{cat}")])

    btns.append([Button.inline("❌ Cancel", "cancel_action")])

    if isinstance(event, events.CallbackQuery.Event):
        try: await event.edit(msg, buttons=btns)
        except Exception as _e:
            logger.debug(f"show_category_select edit failed, falling back to send: {_e}")
            await bot.send_message(event.sender_id, msg, buttons=btns)
    else:
        await event.respond(msg, buttons=btns)

async def show_countries(event, flow, page=1, category='Fresh'):
    """Step 2: Flat product list for the chosen category (country + year + price + stock)."""
    cat_badge = get_cat_badge(category)
    title = f"{P_STORE} <b>Bulk Sessions</b>" if flow == 'bulk' else f"{P_CART} <b>Buy Account</b>"

    rows = db.execute(
        "SELECT MIN(country_icon), country_name, account_year, price, COUNT(*) as stock "
        "FROM stock WHERE available=1 AND category=? "
        "GROUP BY country_name, account_year, price "
        "ORDER BY country_name ASC, account_year DESC, price ASC",
        (category,)
    ).fetchall()

    if not rows:
        err_msg = f"{P_NO} <b>No {cat_badge} accounts in stock right now!</b>\n<i>Try another category or check back later.</i>"
        if isinstance(event, events.CallbackQuery.Event):
            try: return await event.edit(err_msg, buttons=[[Button.inline("◀️ Back", f"back_cat|{flow}")]])
            except Exception as _e:
                logger.debug(f'Suppressed non-critical error: {_e}')
        return await event.respond(err_msg)

    rate = get_usdt_rate()

    def fmt_usd(inr_price):
        try: return f"${round(inr_price / rate, 2)}"
        except Exception: return "—"

    lines = [
        f"{title}  ·  {cat_badge}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚡ <b>Rate:</b> 1 USDT = {P_INR}{rate}\n"
    ]
    btns = []

    # Feature 6: fav countries starred and sorted to top
    try:
        _fav_set = set(get_user_fav_countries(event.sender_id))
    except Exception:
        _fav_set = set()
    rows_sorted = sorted(rows, key=lambda r: (0 if r[1] in _fav_set else 1, r[1]))
    for (icon, name, year, price, stock) in rows_sorted:
        yr = str(year) if year and year > 2000 else "?"
        avail_icon = "🟢" if stock >= 5 else ("🟡" if stock >= 2 else "🔴")
        fav_star = "⭐ " if name in _fav_set else ""
        lines.append(f"• {fav_star}{icon} {name} {yr}: {fmt_usd(price)} ({P_INR}{price}) — Stock: {avail_icon} {stock}")
        btn_label = f"{fav_star}{icon} {name} {yr}  ·  {P_INR}{price}  ·  {stock} avail"
        btns.append([Button.inline(btn_label, f"by|{flow}|{name}|{year}|{price}|{category}")])

    lines.append("\n<i>Select an item to view details and confirm purchase:</i>")
    btns.append([Button.inline("◀️ Back", f"back_cat|{flow}")])
    btns.append([Button.inline("❌ Cancel", "cancel_action")])

    msg = "\n".join(lines)

    if isinstance(event, events.CallbackQuery.Event):
        try: await event.edit(msg, buttons=btns)
        except Exception as _e:
            logger.debug(f"show_countries edit failed, falling back to send: {_e}")
            await bot.send_message(event.sender_id, msg, buttons=btns)
    else:
        await event.respond(msg, buttons=btns)

async def show_years(event, flow, country, category='Fresh'):
    """Step 3: Show available price+year options for the chosen country + category.
    FIX: Now groups by (price, account_year) and shows the actual year per plan.
    """
    # FIX: include account_year in GROUP BY so each plan shows its real year
    rows = db.execute(
        "SELECT price, account_year, COUNT(*) FROM stock "
        "WHERE available=1 AND country_name=? AND category=? "
        "GROUP BY price, account_year ORDER BY price ASC, account_year DESC",
        (country, category)
    ).fetchall()
    uid = event.sender_id
    if not rows:
        try: await event.answer()
        except Exception: pass
        flag_oos = get_flag_by_country_name(country)
        already_wl = db.execute("SELECT 1 FROM wishlist WHERE user_id=? AND country_name=?", (uid, country)).fetchone()
        wl_btn_label = "🔔 Already in Wishlist ✅" if already_wl else "🔔 Notify Me When In Stock"
        wl_btn_data  = f"wishlist_add|{country}" if not already_wl else "noop_wl"
        try:
            await event.edit(
                f"❌ <b>Out of Stock!</b>\n\n{flag_oos} <b>{country}</b> has no available accounts for the selected category.\n\n<i>Add to your wishlist to get a DM the moment new stock arrives!</i>",
                buttons=[[Button.inline(wl_btn_label, wl_btn_data)], [Button.inline("◀️ Back", f"back_cat|{flow}")]]
            )
        except Exception:
            await bot.send_message(uid,
                f"❌ <b>Out of Stock!</b>\n\n{flag_oos} <b>{country}</b> — no accounts available right now.",
                buttons=[[Button.inline(wl_btn_label, wl_btn_data)]]
            )
        return

    discount = get_effective_discount(uid)

    cat_badge  = get_cat_badge(category)
    flag = get_flag_by_country_name(country) or "🌍"

    msg = (
        f"💰 <b>Select Price Plan</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{flag}  <b>{country}</b>\n"
        f"📂  Type: {cat_badge}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 <i>Choose a plan below (year shown per plan):</i>\n"
    )
    btns = []

    for (p, y, c) in rows:
        disp_p    = p if discount == 0 else int(p * (100 - discount) / 100)
        disc_text = f"  (-{discount}%)" if discount > 0 else ""
        avail_icon = "🟢" if c >= 5 else ("🟡" if c >= 2 else "🔴")
        # FIX: show actual account year in button label; pass year in callback data
        year_label = str(y) if y and y > 2000 else "Unknown"
        btns.append([Button.inline(
            f"₹{disp_p}{disc_text}   ·   📅 {year_label}   ·   {avail_icon} {c} avail",
            f"by|{flow}|{country}|{y}|{p}|{category}"
        )])

    btns.append([Button.inline("◀️ Back", f"back_cat|{flow}")])
    try:
        await event.edit(msg, buttons=btns)
    except Exception:
        await bot.send_message(event.sender_id, msg, buttons=btns)

async def confirm_purchase(event, country, year, price_str, category='Fresh'):
    uid = event.sender_id
    base_price = int(price_str)

    bal_row = db.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
    bal = bal_row[0] if bal_row else 0
    discount   = get_effective_discount(uid)
    final_price = base_price if discount == 0 else int(base_price * (100 - discount) / 100)
    # Reseller badge
    _res_note   = "\n🌟 <i>Reseller price applied</i>" if is_reseller(uid) and discount > 0 else ""

    cat_badge  = get_cat_badge(category)
    disc_line  = f"\n🏷️  <b>Discount:</b> <code>{discount}% OFF</code>" if discount > 0 else ""
    enough     = "✅" if bal >= final_price else "❌  Insufficient"
    flag       = get_flag_by_country_name(country) or "🌍"
    # FIX: show the actual account year passed from show_years (not a generic age range)
    # FIX: safe int conversion — bare int(year) raises ValueError if year is a non-numeric string
    try:
        year_display = str(int(year)) if year and int(year) > 2000 else "Unknown"
    except (ValueError, TypeError):
        year_display = "Unknown"

    msg = (
        f"🛒 <b>Order Summary</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{flag}  <b>Country:</b>  {country}\n"
        f"📂  <b>Type:</b>  {cat_badge}\n"
        f"📅  <b>Acc Year:</b>  <code>{year_display}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰  <b>Price:</b>  ₹{final_price}{disc_line}\n"
        f"💳  <b>Your Balance:</b>  ₹{bal}  {enough}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{_res_note}\n"
        f"Confirm your purchase?"
    )

    # Feature 2: Flash sale banner
    _flash = get_active_flash_sale()
    if _flash:
        _cd = get_flash_sale_countdown(_flash['ends_dt'])
        msg += f"\n🔥 <b>FLASH SALE {_flash['discount']}% OFF!</b>  ⏳ {_cd} left"
    # Feature 1: Coupon
    _cpn = get_user_coupon_session(uid)
    if _cpn:
        msg += f"\n🎟 <b>Coupon {_cpn['code']}:</b> {_cpn['discount_pct']}% OFF applied!"
    # Feature 4: Bundle deal
    _bundle = get_active_bundle(category)
    if _bundle:
        msg += f"\n🎁 Bundle: Buy {_bundle['buy_qty']} get {_bundle['free_qty']} FREE!"
    # Feature 6: fav toggle + wishlist
    _is_fav = bool(db.execute(
        "SELECT 1 FROM fav_countries WHERE user_id=? AND country_name=?", (uid, country)
    ).fetchone())
    _fav_lbl = "⭐ Unfav" if _is_fav else "☆ Fav"
    # Wishlist button — works for in-stock countries too
    _already_wl = db.execute(
        "SELECT 1 FROM wishlist WHERE user_id=? AND country_name=?", (uid, country)
    ).fetchone()
    _wl_lbl  = "🔔 In Wishlist ✅" if _already_wl else "🔔 Add to Wishlist"
    _wl_data = "noop_wl" if _already_wl else f"wishlist_add|{country}"
    btns = [
        [Button.inline("✅  Confirm & Buy", f"buy_cf|{country}|{year}|{base_price}|{category}")],
        [Button.inline(_fav_lbl, f"fav_toggle|{country}"),
         Button.inline(_wl_lbl, _wl_data)],
        [Button.inline("❌  Cancel", "cancel_action")]
    ]
    await event.edit(msg, buttons=btns)

async def process_purchase(event, country, year_str, price_str, category='Fresh'):
    uid, base_price = event.sender_id, int(price_str)

    # FIX Bug 2: use get_effective_discount() so reseller-tier discounts are applied,
    # matching the behaviour of confirm_purchase() which the user saw in the preview.
    discount = get_effective_discount(uid)
    # Feature 2: Flash sale — override only if higher than effective discount
    _flash_now = get_active_flash_sale()
    if _flash_now and _flash_now['discount'] > discount:
        discount = _flash_now['discount']
    # Feature 1: Coupon — override only if higher than effective discount
    _cpn_now = get_user_coupon_session(uid)
    if _cpn_now and _cpn_now['discount_pct'] > discount:
        discount = _cpn_now['discount_pct']
    final_price = base_price if discount == 0 else int(base_price * (100 - discount) / 100)

    async with get_user_lock(uid):
        with _db_write_lock:
            year_filter = int(year_str) if year_str and str(year_str).isdigit() and int(year_str) > 2000 else None
            if year_filter:
                row = db.execute(
                    "SELECT phone, session_file, country_icon, account_year, twofa FROM stock "
                    "WHERE country_name=? AND price=? AND category=? AND account_year=? AND available=1 "
                    "ORDER BY added_date ASC LIMIT 1",
                    (country, base_price, category, year_filter)
                ).fetchone()
            else:
                row = db.execute(
                    "SELECT phone, session_file, country_icon, account_year, twofa FROM stock "
                    "WHERE country_name=? AND price=? AND category=? AND available=1 "
                    "ORDER BY added_date ASC LIMIT 1",
                    (country, base_price, category)
                ).fetchone()

            if not row:
                return await event.answer("❌ Sold out! Another user just bought this account.", alert=True)

            phone, sess, c_icon, actual_year, twofa_pass = row

            # Atomic balance deduction — fails safely if insufficient.
            # isolation_level=None = autocommit; WHERE balance>=price prevents the write
            # entirely if balance is too low, so rowcount==0 means nothing was written.
            _wrc = db.execute("UPDATE users SET balance = balance - ? WHERE user_id=? AND balance >= ?", (final_price, uid, final_price))
            if _wrc.rowcount == 0:
                # No write happened — WHERE clause blocked it. Nothing to roll back.
                return await event.answer(f"❌ Insufficient Balance! Need ₹{final_price}", alert=True)

            # Feature 1: consume coupon on purchase
            if _cpn_now and not user_has_used_coupon(uid, _cpn_now['code']):
                apply_coupon_to_user(uid, _cpn_now['code'])
                set_user_coupon_session(uid, None)
            # Atomic stock claim — AND available=1 prevents double-sell if two users
            # selected the same phone between the SELECT above and this UPDATE
            _stock_rc = db.execute("UPDATE stock SET available=0 WHERE phone=? AND available=1", (phone,))
            if _stock_rc.rowcount == 0:
                # Another user grabbed this item first — refund and abort
                db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (final_price, uid))
                db.commit()
                return await event.answer("❌ Just sold out! Balance refunded. Please try again.", alert=True)

            # FIX: persist a placeholder active_orders_db row NOW, inside the same lock
            # block that committed the balance deduction and stock claim. This ensures
            # _restore_and_refund_stale_orders can issue a refund if the bot crashes
            # before the real _save_active_order call later in the flow (e.g. during
            # session validation or Telegram message send).
            db.execute(
                "INSERT OR REPLACE INTO active_orders_db "
                "(phone, user_id, price, country, year, c_icon, twofa, sess, start_time, msg_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (phone, uid, final_price, country, 0, '', '', sess, time.time(), 0)
            )
            db.commit()

    try:
        await event.edit(f"🔄 <b>Fetching Number (+{phone})...</b>")
    except Exception:
        try: await bot.send_message(uid, f"🔄 <b>Fetching Number (+{phone})...</b>")
        except Exception as _e:
            logger.debug(f'Suppressed non-critical error: {_e}')

    clean_sess = _resolve_session_base(sess)
    # FIX: validate the session file exists before attempting to connect;
    # avoids a TelegramClient crash on invalid or deleted stock entries
    if not clean_sess or not os.path.exists(clean_sess + ".session"):
        async with get_user_lock(uid):
            with _db_write_lock:
                db.execute("DELETE FROM stock WHERE phone=?", (phone,))
                db.execute("DELETE FROM active_orders_db WHERE phone=?", (phone,))
                db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (final_price, uid))
                db.commit()
        user_locks.pop(uid, None)
        logger.warning(f"process_purchase: session file missing phone={phone}, removed from stock and refunded uid={uid}")
        try: await event.edit(f"{P_NO} <b>Account Invalid (missing session).</b> Money refunded. Try another.")
        except Exception as _e:
            logger.debug(f"process_purchase invalid session notify failed: {_e}")
            await bot.send_message(uid, f"{P_NO} <b>Account Invalid.</b> Money refunded.")
        return
    client = TelegramClient(clean_sess, API_ID, API_HASH)

    try:
        await client.connect()
        if not await client.is_user_authorized(): raise Exception("Session dead")
    except Exception as _conn_err:
        logger.warning(f"process_purchase: dead session phone={phone} uid={uid}: {_conn_err}")
        async with get_user_lock(uid):
            with _db_write_lock:
                db.execute("DELETE FROM stock WHERE phone=?", (phone,))
                db.execute("DELETE FROM active_orders_db WHERE phone=?", (phone,))
                db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (final_price, uid))
                db.commit()
        user_locks.pop(uid, None)
        try: await client.disconnect()
        except Exception as _e:
            logger.debug(f'Suppressed non-critical error: {_e}')
        delete_session_files(sess)
        try: await event.edit(f"{P_NO} <b>Account Invalid.</b> Money refunded. Try buying another.")
        except Exception as _e:
            logger.debug(f"process_purchase dead session notify failed: {_e}")
            await bot.send_message(uid, f"{P_NO} <b>Account Invalid.</b> Money refunded. Try buying another.")
        return

    # FIX: show actual year in "Order Active" message
    year_active = actual_year if actual_year and actual_year > 2000 else None
    year_active_line = f"📅 <b>Acc Year:</b>  <code>{year_active}</code>\n\n" if year_active else "\n"
    msg = (
        f"{P_YES} <b>Order Active!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{P_PHONE} <b>Phone:</b>  <code>{phone}</code>\n"
        f"{P_FLAG} <b>Country:</b>  {c_icon} {country}\n"
        f"{year_active_line}"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>Steps:</b>\n"
        f"1️⃣  Open Telegram → Add Account\n"
        f"2️⃣  Enter the phone number above\n"
        f"3️⃣  {P_WAIT} The bot is listening — OTP will arrive automatically\n\n"
        f"<i>⏱ If no OTP in 10 min, order is auto-cancelled & balance refunded.</i>"
    )

    try:
        try:
            sent_msg = await event.edit(msg)
        except Exception:
            sent_msg = await bot.send_message(uid, msg)
    except Exception as _msg_err:
        logger.warning(f"process_purchase: message delivery failed uid={uid}: {_msg_err}")
        # Both sends failed (e.g. user blocked bot) — refund and restore stock
        async with get_user_lock(uid):
            with _db_write_lock:
                db.execute("DELETE FROM active_orders_db WHERE phone=?", (phone,))
                db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (final_price, uid))
                db.execute("UPDATE stock SET available=1 WHERE phone=?", (phone,))
                db.commit()
        user_locks.pop(uid, None)
        try: await client.disconnect()
        except Exception as _e:
            logger.debug(f'Suppressed non-critical error: {_e}')
        return

    active_orders[phone] = {
        'uid': uid,
        'client': client, 'sess': sess, 'start_time': time.time(),
        'paid': False, 'price': final_price, 'country': country, 'year': actual_year,
        'c_icon': c_icon, 'twofa': twofa_pass, 'msg_id': sent_msg.id,
        'category': category,
    }
    _save_active_order(phone, active_orders[phone])
    asyncio.create_task(auto_otp_task(phone))

async def auto_otp_task(phone):
    if phone not in active_orders: return
    
    order = active_orders[phone]
    client = order['client']
    start_time = order['start_time']
    uid = order['uid']
    msg_id = order['msg_id']
    
    while time.time() - start_time < AUTO_CANCEL_SECONDS:
        if phone not in active_orders: return 
        try:
            msgs = await client.get_messages(777000, limit=5)
            code = None
            for m in msgs:
                if m.date.timestamp() > start_time - 10:
                    if m.message and "Login detected" not in m.message:
                        m_match = re.search(OTP_REGEX, m.message)
                        if m_match:
                            code = m_match.group(1)  # group(1) = the captured digits
                            break

            if code:
                # ── Duplicate-delivery guard ──────────────────────────────────────
                # Acquire the user lock BEFORE touching order['paid'] so that a
                # second polling iteration (or a retry) cannot slip past the check
                # and write a duplicate order/refund to the database.
                already_recorded = False
                async with get_user_lock(uid):
                    if order['paid']:
                        already_recorded = True  # another iteration already handled it
                    else:
                        order['paid'] = True
                        with _db_write_lock:
                            db.execute(
                                "INSERT INTO orders (user_id, country, year, price, phone, otp) "
                                "VALUES (?,?,?,?,?,?)",
                                (uid, order['country'], order['year'], order['price'], phone, code)
                            )
                            # DELETE the stock row entirely — it has been sold and delivered.
                            # This ensures the number never re-appears in stock, even after restarts.
                            db.execute("DELETE FROM stock WHERE phone=?", (phone,))
                            # FIX: delete from active_orders_db atomically in the same
                            # transaction so a crash between commit() and the old
                            # _clear_active_order_db() call can no longer cause
                            # _restore_and_refund_stale_orders to double-refund a
                            # user whose OTP was already delivered and recorded.
                            db.execute("DELETE FROM active_orders_db WHERE phone=?", (phone,))
                            db.commit()

                if not already_recorded:
                    await log_primary_purchase(
                        uid, order['country'], order['price'], order['price'], order['year'], 1,
                        phone=phone, category=order.get('category')
                    )
                    asyncio.create_task(check_low_stock_alert(order['country']))

                twofa_text = (
                    f"{P_2FA} <b>2FA Password:</b>  <code>{order['twofa']}</code>"
                    if order['twofa'] != "None"
                    else "🔓 <b>2FA:</b>  <code>None (No Password)</code>"
                )
                # FIX: include actual account year so buyer knows what they purchased
                year_val = order.get('year', 0)
                year_line = f"📅 <b>Acc Year:</b>  <code>{year_val}</code>\n" if year_val and year_val > 2000 else ""
                msg_text = (
                    f"{P_YES} <b>OTP Ready!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{P_PHONE} <b>Phone:</b>  <code>{phone}</code>\n"
                    f"{P_FLAG} <b>Country:</b>  {order['c_icon']} {order['country']}\n"
                    f"{year_line}"
                    f"{P_OTP} <b>OTP:</b>  <code>{code}</code>\n"
                    f"{twofa_text}\n\n"
                    f"<i>Enter the OTP on Telegram to complete login.</i>"
                )

                try:
                    # _tg_call handles FloodWait with retries and swallows
                    # MessageNotModifiedError so we don't need a separate catch.
                    await _tg_call(
                        bot.edit_message, uid, msg_id, msg_text,
                        buttons=[[Button.inline("🔄 Get OTP Again", f"get_otp_again|{phone}")],
                                 [Button.inline("🚪 Finish & Logout", f"logout_bot|{phone}")],
                                 [Button.url("🤖 Open @Otp_shxp_bot", "https://t.me/Otp_shxp_bot")]]
                    )
                except Exception as _send_err:
                    logger.warning(f"auto_otp_task: edit failed, falling back to send — {_send_err}")
                    try:
                        await _tg_call(
                            bot.send_message, uid, msg_text,
                            buttons=[[Button.inline("🔄 Get OTP Again", f"get_otp_again|{phone}")],
                                     [Button.inline("🚪 Finish & Logout", f"logout_bot|{phone}")],
                                     [Button.url("🤖 Open @Otp_shxp_bot", "https://t.me/Otp_shxp_bot")]]
                        )
                    except Exception as _send_err2:
                        logger.error(f"auto_otp_task: send also failed uid={uid}: {_send_err2}")
                user_locks.pop(uid, None)
                return
        except FloodWaitError as _fw:
            _fw_wait = _fw.seconds + 2
            logger.warning(f"auto_otp_task: FloodWait {_fw.seconds}s for phone={phone} — sleeping {_fw_wait}s")
            await asyncio.sleep(min(_fw_wait, AUTO_CANCEL_SECONDS))
        except Exception as _poll_err:
            # Log polling errors (network issues, etc.) so they are
            # visible in logs rather than silently disappearing.
            logger.warning(f"auto_otp_task: poll error phone={phone}: {_poll_err}")
        await asyncio.sleep(6)

    if phone in active_orders and not active_orders[phone]['paid']:
        order = active_orders.pop(phone, None)
        _clear_active_order_db(phone)
        if not order or order.get('paid'):   # double-refund guard
            return
        # FIX Bug 5: re-read uid and msg_id from the freshly-popped order dict rather
        # than relying on the closure variables captured at task-start, which could
        # be stale if the order was replaced by another coroutine in between.
        uid = order['uid']
        msg_id = order['msg_id']
        try:
            await order['client'].disconnect()
        except Exception as _dc_err:
            logger.debug(f"auto_otp_task: disconnect error phone={phone}: {_dc_err}")

        async with get_user_lock(uid):
            with _db_write_lock:
                db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (order['price'], uid))
                db.execute("UPDATE stock SET available=1 WHERE phone=?", (phone,))
                db.commit()
        user_locks.pop(uid, None)

        try:
            await bot.edit_message(uid, msg_id,
                f"⌛ <b>Order Expired</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"No OTP was received for <code>{phone}</code> within 10 minutes.\n\n"
                f"{P_MONEY} <b>Refund:</b>  <code>₹{order['price']}</code> has been returned to your balance.\n\n"
                f"<i>You can try buying another account from the menu.</i>"
            )
        except Exception as _exp_err:
            logger.warning(f"auto_otp_task: expiry notify failed uid={uid}: {_exp_err}")

async def init_session_purchase(event, country, year, price_str, category='Fresh'):
    uid, price = event.sender_id, int(price_str)
    year_int = int(year) if year and str(year).isdigit() and int(year) > 2000 else None
    if year_int:
        stock_row = db.execute(
            "SELECT COUNT(*) FROM stock WHERE country_name=? AND price=? AND category=? AND account_year=? AND available=1",
            (country, price, category, year_int)
        ).fetchone()
    else:
        stock_row = db.execute(
            "SELECT COUNT(*) FROM stock WHERE country_name=? AND price=? AND category=? AND available=1",
            (country, price, category)
        ).fetchone()
    stock = stock_row[0] if stock_row else 0
    if stock == 0: return await event.answer("❌ Out of stock!", alert=True)

    session_buy_state[uid] = {'country': country, 'year': year, 'price': price, 'stock': stock, 'category': category, 'ts': time.time()}
    discount = get_effective_discount(uid)
    t5, t10, t20 = get_qty_tier_info()
    p_disp = price if discount == 0 else int(price * (100 - discount) / 100)
    cat_badge = get_cat_badge(category)
    flag = get_flag_by_country_name(country) or "🌍"

    _tier_note = (
        f"\n🎁 <b>Qty Discounts:</b>  5+→{t5}% | 10+→{t10}% | 20+→{t20}% off"
        if any([t5, t10, t20]) else ""
    )
    msg = (
        f"📁 <b>Bulk Sessions</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{flag}  <b>Country:</b>  {country}\n"
        f"📂  <b>Quality:</b>  {cat_badge}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰  <b>Price per session:</b>  ₹{p_disp}\n"
        f"📦  <b>Available:</b>  {stock} sessions\n"
        f"{_tier_note}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 How many sessions do you want?\n"
        f"<i>Just reply with a number (e.g. 5)</i>"
    )
    await event.edit(msg, buttons=[[Button.inline("❌ Cancel", "cancel_action")]])

async def process_bulk_sessions(event, uid, qty, state, final_cost):
    country, price = state['country'], int(state['price'])
    category = state.get('category', 'Fresh')
    year_filter = state.get('year')
    year_int = int(year_filter) if year_filter and str(year_filter).isdigit() and int(year_filter) > 2000 else None
    await event.respond(f"{P_WAIT} <b>Processing your sessions...</b>")

    async with get_user_lock(uid):
        with _db_write_lock:
            # FIX: SELECT and UPDATE now happen under the same _db_write_lock so
            # there is zero gap during which another user could claim the same
            # phones between our read and our availability update.
            if year_int:
                rows = db.execute(
                    "SELECT phone, session_file, twofa, account_year FROM stock "
                    "WHERE country_name=? AND price=? AND category=? AND account_year=? AND available=1 LIMIT ?",
                    (country, price, category, year_int, qty)
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT phone, session_file, twofa, account_year FROM stock "
                    "WHERE country_name=? AND price=? AND category=? AND available=1 LIMIT ?",
                    (country, price, category, qty)
                ).fetchall()
            if len(rows) < qty:
                return await event.respond(f"{P_NO} Stock changed during processing. Purchase Cancelled.")

            _wrc = db.execute("UPDATE users SET balance = balance - ? WHERE user_id=? AND balance >= ?", (final_cost, uid, final_cost))
            if _wrc.rowcount == 0:
                # No write happened — WHERE clause blocked it. Nothing to roll back.
                return await event.respond(f"{P_NO} Insufficient Balance! Purchase Cancelled.")

            phones = [r[0] for r in rows]
            year_map = {r[0]: r[3] for r in rows}
            placeholders = ",".join("?" for _ in phones)
            # AND available=1 is a final safety net; with the SELECT now inside
            # the same lock this guard should never trigger, but we keep it for
            # defence-in-depth against any future refactoring.
            _stock_rc = db.execute(f"UPDATE stock SET available=0 WHERE phone IN ({placeholders}) AND available=1", phones)
            if _stock_rc.rowcount < qty:
                # Shouldn't happen now, but refund cleanly if it ever does
                db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (final_cost, uid))
                db.commit()
                return await event.respond(f"{P_NO} Some accounts just sold out. Balance refunded. Please try again.")
            price_per_acc = final_cost // qty
            for p in phones:
                db.execute("INSERT INTO orders (user_id, country, year, price, phone, otp) VALUES (?,?,?,?,?,?)", (uid, country, year_map.get(p, 0), price_per_acc, p, "SESSION_FILES"))
            db.commit()

    zip_name = os.path.join(_data_dir, f"sessions_{uid}_{int(time.time())}.zip")
    numbers_txt = ""

    try:
        resolved_rows = []
        for phone, sess_file, twofa_pass, y in rows:
            resolved_base = _resolve_session_base(sess_file)
            if not resolved_base or not os.path.exists(resolved_base + ".session"):
                raise FileNotFoundError(
                    f"Session file missing for +{phone}: {sess_file}"
                )
            resolved_rows.append((phone, resolved_base, twofa_pass, y))

        with zipfile.ZipFile(zip_name, 'w') as zf:
            for phone, base_s, twofa_pass, y in resolved_rows:
                for ext in ['.session', '.session-wal', '.session-shm', '.session-journal']:
                    src = base_s + ext
                    if os.path.exists(src): zf.write(src, os.path.basename(src))
                
                pass_text = twofa_pass if twofa_pass != "None" else "No_Password"
                year_text = str(y) if y and y > 2000 else "Unknown"
                numbers_txt += f"+{phone} | year:{year_text} | pass:{pass_text}\n"
            
            numbers_txt += "\n\nPurchased from @Otp_shxp_bot\n"
            zf.writestr("numbers.txt", numbers_txt)
            
        caption = (
            f"{P_YES} <b>Bulk Purchase Complete!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{P_FLAG} <b>Country:</b>  {country}\n"
            f"{P_PKG} <b>Quantity:</b>  {qty} sessions\n"
            f"{P_CARD} <b>Total Paid:</b>  {P_INR}{final_cost}\n\n"
            f"📂 Your ZIP contains <code>.session</code> files + <code>numbers.txt</code>\n\n"
            f"<i>Sessions are delivered as-is. Keep them secure!</i>\n\n"
            f"🤖 Always use @Otp_shxp_bot"
        )
        await bot.send_file(uid, zip_name, caption=caption)
        # Delivery succeeded — permanently DELETE the sold stock rows so they
        # never appear in the bot's database again.
        _del_ph = ",".join("?" for _ in phones)
        with _db_write_lock:
            db.execute(f"DELETE FROM stock WHERE phone IN ({_del_ph})", phones)
            db.commit()
        # FIX: pass actual year and category from purchase state
        await log_primary_purchase(
            uid, country, price, final_cost, state.get("year", 0), qty,
            category=state.get("category")
        )
        asyncio.create_task(check_low_stock_alert(country))
    except Exception as ex:
        logger.error(f"Bulk session delivery failed for uid={uid}: {ex}")
        async with get_user_lock(uid):
            placeholders = ",".join("?" for _ in phones)
            with _db_write_lock:
                db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (final_cost, uid))
                db.execute(f"UPDATE stock SET available=1 WHERE phone IN ({placeholders})", phones)
                db.execute(f"DELETE FROM orders WHERE user_id=? AND otp='SESSION_FILES' AND phone IN ({placeholders})", [uid] + phones)
                db.commit()
        await event.respond(f"{P_NO} <b>Delivery failed.</b> Your ₹{final_cost} has been <b>fully refunded</b>. Please try again.")
    finally:
        if os.path.exists(zip_name): os.remove(zip_name)

# ================= STATS & PROFILE FUNCTIONS =================
async def profile_handler(event):
    uid = event.sender_id
    row = db.execute("SELECT balance, total_deposited, joined_date, discount FROM users WHERE user_id=?", (uid,)).fetchone()
    if not row: return await bot.send_message(event.chat_id, "⚠️ Error: Please type /start to initialize your account.")
    
    bal, dep, date, discount = row
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{uid}"
    disc_msg = f"\n{P_GIFT} Active Discount: <b>{discount}% OFF</b>" if discount > 0 else ""
    
    msg = (
        f"👤 <b>My Profile</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{P_ID} <b>User ID:</b>  <code>{uid}</code>\n"
        f"{P_MONEY} <b>Balance:</b>  <code>₹{bal}</code>  <i>(${to_usd(bal):.2f})</i>\n"
        f"{P_CARD} <b>Deposited:</b>  <code>₹{dep}</code>  <i>(${to_usd(dep):.2f})</i>{disc_msg}\n"
        f"{P_CAL} <b>Joined:</b>  {date[:10]}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{P_GIFT} <b>Your Referral Link:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"<i>Share this link to earn bonus on every friend's deposit!</i>"
    )
    await bot.send_message(event.chat_id, msg)

async def stats_handler(event, is_callback=False):
    uid = event.sender_id
    row = db.execute("SELECT total_deposited FROM users WHERE user_id=?", (uid,)).fetchone()
    if not row: return
    dep = row[0]
    o_row = db.execute("SELECT COUNT(*), SUM(price) FROM orders WHERE user_id=?", (uid,)).fetchone()
    total_orders = o_row[0] if o_row else 0
    spent = o_row[1] if o_row and o_row[1] else 0
    
    msg = (
        f"📊 <b>My Statistics</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{P_CART} <b>Accounts Bought:</b>  {total_orders}\n"
        f"{P_MONEY} <b>Total Spent:</b>  <code>₹{spent}</code>  <i>(${to_usd(spent):.2f})</i>\n"
        f"{P_CARD} <b>Total Deposited:</b>  <code>₹{dep}</code>  <i>(${to_usd(dep):.2f})</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{uid}"
    is_res = is_reseller(uid)
    res_badge = "\n🌟 <b>Reseller Status:</b> Active" if is_res else ""
    wl_count = db.execute("SELECT COUNT(*) FROM wishlist WHERE user_id=?", (uid,)).fetchone()[0]
    wl_note = f"\n🔔 <b>Wishlist Items:</b>  {wl_count}" if wl_count > 0 else ""
    msg += res_badge + wl_note
    btns = [
        [Button.inline("📋 Purchase History", "page_purchases_1"), Button.inline("📋 My Wishlist", "my_wishlist")],
        [Button.inline("👥 Referral Logs", "view_referrals"), Button.url("🔗 My Referral Link", ref_link)]
    ]
    if is_callback:
        try: await event.edit(msg, buttons=btns)
        except MessageNotModifiedError: pass
    else: await bot.send_message(event.chat_id, msg, buttons=btns)

async def send_purchase_page(event, uid, page):
    limit = 5
    offset = (page - 1) * limit
    t_row = db.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (uid,)).fetchone()
    total = t_row[0] if t_row else 0
    rows = db.execute("SELECT phone, date FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (uid, limit, offset)).fetchall()
    
    msg = (
        f"📋 <b>Purchase History</b>  —  Page {page} of {max(1, -(-total//limit))}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    if not rows:
        msg += "<i>No purchases found yet.</i>"
    else:
        for ph, d in rows:
            try:
                dt = datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
                d_str = dt.strftime("%d %b %Y  %H:%M")
            except (ValueError, TypeError):
                d_str = d
            msg += f"{P_PHONE} <code>{ph}</code>\n{P_CAL} <i>{d_str}</i>\n\n"

    nav = []
    if page > 1: nav.append(Button.inline("◀️ Prev", f"page_purchases_{page-1}"))
    nav.append(Button.inline("🔙 Back", "back_to_stats"))
    if offset + limit < total: nav.append(Button.inline("Next ▶️", f"page_purchases_{page+1}"))
    try:
        await event.edit(msg, buttons=[nav])
    except Exception:
        await bot.send_message(event.chat_id, msg, buttons=[nav])

async def view_referrals(event):
    uid = event.sender_id
    refs = db.execute(
        "SELECT user_id, total_deposited FROM users WHERE referred_by=? ORDER BY user_id DESC",
        (uid,)
    ).fetchall()
    # Build the referral link
    try:
        _bot_info = await bot.get_me()
        _ref_link = f"https://t.me/{_bot_info.username}?start=ref_{uid}"
    except Exception:
        _ref_link = f"https://t.me/YourBot?start=ref_{uid}"
    # Fetch referral bonus % from settings
    _ref_pct_row = db.execute("SELECT value FROM settings WHERE key='referral_pct'").fetchone()
    _ref_pct = _ref_pct_row[0] if _ref_pct_row else "?"
    total_refs = len(refs)
    msg_r = (
        f"👥 <b>My Referrals</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 <b>Your Referral Link:</b>\n"
        f"<code>{_ref_link}</code>\n\n"
        f"💡 <i>Share this link. Every user who joins via it is linked to you permanently.</i>\n"
        f"💰 <i>You earn {_ref_pct}% bonus when they deposit.</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Total Referred:</b>  {total_refs} user(s)\n\n"
    )
    if refs:
        msg_r += "<b>Recent Referrals:</b>\n"
        for (_ruid, _rdep) in refs[:15]:   # cap at 15 entries
            _dep_str = f"  |  ₹{_rdep} deposited" if _rdep and _rdep > 0 else ""
            msg_r += f"  • <code>{_ruid}</code>{_dep_str}\n"
        if total_refs > 15:
            msg_r += f"  <i>…and {total_refs - 15} more</i>\n"
    else:
        msg_r += "<i>No referrals yet. Share your link to start earning!</i>\n"
    _ref_btns = [
        [Button.url("🔗 Share Referral Link", _ref_link)],
        [Button.inline("🔙 Back to Stats", "back_to_stats")]
    ]
    try:
        await event.edit(msg_r, buttons=_ref_btns)
    except Exception:
        await bot.send_message(uid, msg_r, buttons=_ref_btns)

# ================= HELP SYSTEM =================
HELP_TOPICS = {
    "getting_started": {
        "title": "🚀 Getting Started",
        "text": (
            "🚀 <b>Getting Started</b>\n\n"
            "Welcome to <b>OTP Shop!</b>\n\n"
            "<b>Step 1 — Join our channels</b>\n"
            "You must join our official channels before using the bot.\n\n"
            "<b>Step 2 — Accept Terms & Conditions</b>\n"
            "Read and accept our T&C to unlock all features.\n\n"
            "<b>Step 3 — Add Balance</b>\n"
            "Tap 💰 <b>Deposit</b> in the menu and choose a payment method.\n\n"
            "<b>Step 4 — Buy Accounts or Sessions</b>\n"
            "Use 🛒 <b>Buy Account</b> for single OTP accounts or\n"
            "📁 <b>Buy Sessions</b> for bulk session files.\n\n"
            "Need more help? Tap a topic below or contact Support. 👇"
        )
    },
    "buy_account": {
        "title": "🛒 Buying an Account (OTP)",
        "text": (
            "🛒 <b>How to Buy an Account (OTP Method)</b>\n\n"
            "1️⃣ Tap <b>🛒 Buy Account</b> in the main menu.\n"
            "2️⃣ Select a category: 🟢 Fresh · 💸 Cheap · 🟡 Old · 🔴 Spam · 💎 Rare · 🔄 Number Change.\n"
            "3️⃣ Choose a <b>Country</b> from the list.\n"
            "4️⃣ Select a <b>Price Plan</b> and review the cost.\n"
            "5️⃣ Tap <b>✅ Confirm &amp; Buy</b> to confirm.\n\n"
            "⏳ <b>After confirming:</b>\n"
            "• Open Telegram on your phone or PC.\n"
            "• Tap <b>Add Account</b> and enter the phone number shown.\n"
            "• The bot <b>automatically listens</b> for the OTP and sends it the moment Telegram delivers it.\n\n"
            "🔐 <b>2FA Passwords:</b>\n"
            "If the account has Two-Factor Authentication enabled, the password is shown alongside the OTP.\n\n"
            "⏰ <b>Auto-Cancel:</b>\n"
            "If no OTP arrives within <b>10 minutes</b>, the order is cancelled and your balance is fully refunded."
        )
    },
    "buy_sessions": {
        "title": "📁 Buying Sessions (Bulk)",
        "text": (
            "📁 <b>How to Buy Sessions (Bulk)</b>\n\n"
            "1️⃣ Tap <b>📁 Buy Sessions</b> in the main menu.\n"
            "2️⃣ Select a <b>Country</b>.\n"
            "3️⃣ Choose the <b>Account Year</b>.\n"
            "4️⃣ Reply with the <b>quantity</b> of sessions you want.\n"
            "5️⃣ The bot will send a <b>ZIP file</b> containing all <code>.session</code> files plus a <code>numbers.txt</code> with phone numbers and 2FA passwords.\n\n"
            "📦 <b>What's inside the ZIP?</b>\n"
            "• <code>+PhoneNumber.session</code> — the Telethon session file\n"
            "• <code>numbers.txt</code> — phone list with passwords\n\n"
            "⚠️ <b>Note:</b> Sessions are sold as-is. The bot logs out after delivery so accounts remain safe for you to use."
        )
    },
    "deposit": {
        "title": "💰 How to Deposit",
        "text": (
            "💰 <b>How to Deposit</b>\n\n"
            "Tap <b>💰 Deposit</b> from the main menu and choose a payment method:\n\n"
            "🏦 <b>UPI (Manual)</b>\n"
            "• A QR code and UPI ID are shown.\n"
            "• Pay the exact amount, then send a <b>screenshot</b> to the bot.\n"
            "• Balance is credited after admin approval.\n\n"
            "🔷 <b>CWallet (Crypto – Auto Approved)</b>\n"
            "• Choose amount, get a unique USDT/TRC20 address.\n"
            "• Send the exact crypto amount — balance is credited <b>automatically!</b>\n"
            "• Optional bonus % on CWallet deposits.\n\n"
            "💳 <b>Other Methods</b>\n"
            "• Additional payment methods may be available.\n"
            "• Each shows its own QR/ID and instructions.\n\n"
            "⏳ <b>Approval Time:</b>\n"
            "Deposits are reviewed and approved by admins. This usually takes a few minutes during active hours."
        )
    },
    "referral": {
        "title": "🎁 Referral Program",
        "text": (
            "🎁 <b>Referral Program</b>\n\n"
            "Earn <b>passive income</b> by inviting friends!\n\n"
            "📌 <b>How it works:</b>\n"
            "1. Find your personal referral link in 👤 <b>My Profile</b>.\n"
            "2. Share it with your friends.\n"
            "3. When they deposit money, you automatically earn a <b>percentage bonus</b> added to your balance.\n\n"
            "💸 <b>Bonus Rate:</b>\n"
            "The referral % is set by the admin and shown on the main menu.\n\n"
            "📊 <b>Track Your Referrals:</b>\n"
            "Go to 📊 <b>My Stats → Referral Logs</b> to see how many users you've referred.\n\n"
            "🔗 Your referral link is unique to your account — every user who joins via your link is permanently linked to you."
        )
    },
    "faq": {
        "title": "❓ FAQ",
        "text": (
            "❓ <b>Frequently Asked Questions</b>\n\n"
            "<b>Q: My OTP never arrived — what do I do?</b>\n"
            "A: The bot waits up to 10 minutes. If no OTP arrives, the order is auto-cancelled and your balance is refunded. Try buying the same account again.\n\n"
            "<b>Q: My deposit was submitted but not approved yet.</b>\n"
            "A: Deposits are manually reviewed by admins. If it has been more than a few hours, please contact Support with your screenshot.\n\n"
            "<b>Q: Can I get a refund for a purchased account?</b>\n"
            "A: Refunds are only issued if the account is dead/invalid at the time of purchase (the bot checks this automatically). Contact Support for disputes.\n\n"
            "<b>Q: What does the account year mean?</b>\n"
            "A: It's the year the Telegram account was originally registered. Older accounts (e.g. 2018–2020) are generally more trusted by Telegram.\n\n"
            "<b>Q: My session file isn't working.</b>\n"
            "A: Make sure you're using the correct Telethon version. Each session requires the same API_ID/API_HASH used to create it.\n\n"
            "<b>Q: How do I check my balance?</b>\n"
            "A: Tap 👤 <b>My Profile</b> to see your current balance and deposit history."
        )
    },
    "otp_tips": {
        "title": "🔢 OTP & Login Tips",
        "text": (
            "🔢 <b>OTP & Login Tips</b>\n\n"
            "✅ <b>For best results:</b>\n"
            "• Start the login process on Telegram <i>immediately</i> after the bot confirms your purchase.\n"
            "• Use <b>Telegram desktop</b> or the official Telegram app — third-party apps may block the OTP.\n"
            "• Enter the phone number <b>exactly</b> as shown (with country code, no spaces).\n\n"
            "⚠️ <b>Common issues:</b>\n"
            "• <b>OTP not showing?</b> The bot polls every 6 seconds — wait at least 30–60 seconds after entering the number on Telegram.\n"
            "• <b>Flood wait?</b> Telegram may ask you to wait if too many login attempts were made. Try a different account.\n"
            "• <b>Number not accepted?</b> Make sure the number is entered exactly as shown, with the + prefix.\n\n"
            "🔐 <b>2FA Accounts:</b>\n"
            "If a 2FA password is shown, enter it in the <b>Two-Step Verification</b> field on Telegram after entering the OTP.\n\n"
            "💡 <b>Tip:</b> Tap <b>🔄 Get OTP Again</b> at any time during an active order to refresh the latest OTP."
        )
    },
}

def get_help_main_buttons():
    return [
        [Button.inline("🚀 Getting Started", "help_getting_started"),
         Button.inline("🛒 Buy Account (OTP)", "help_buy_account")],
        [Button.inline("📁 Buy Sessions", "help_buy_sessions"),
         Button.inline("💰 Deposits", "help_deposit")],
        [Button.inline("🎁 Referral Program", "help_referral"),
         Button.inline("🔢 OTP & Login Tips", "help_otp_tips")],
        [Button.inline("❓ FAQ", "help_faq")],
    ]

async def send_help_main(event, edit=False):
    msg = (
        "❓ <b>Help Center</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select a topic below to learn how the bot works:\n\n"
        "🛒 <b>Buy Account</b>  —  OTP-based single accounts\n"
        "📁 <b>Buy Sessions</b>  —  Bulk session ZIP downloads\n"
        "💰 <b>Deposits</b>  —  How to add balance\n"
        "🎁 <b>Referrals</b>  —  Earn bonuses by inviting friends\n"
        "🔢 <b>OTP Tips</b>  —  Troubleshoot login issues\n"
        "❓ <b>FAQ</b>  —  Common questions answered\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 Still stuck? Tap 📞 <b>Support</b> in the main menu."
    )
    btns = get_help_main_buttons()
    if edit:
        try:
            await event.edit(msg, buttons=btns)
        except Exception:
            await bot.send_message(event.chat_id, msg, buttons=btns)
    else:
        await bot.send_message(event.chat_id, msg, buttons=btns)

async def send_help_topic(event, topic_key):
    btns = [
        [Button.inline("🔙 Back to Help Menu", "help_main")],
        [Button.url("📞 Contact Support", get_support_url())]
    ]
    if topic_key == "faq":
        text = await build_faq_text()
    else:
        topic = HELP_TOPICS.get(topic_key)
        if not topic:
            return await event.answer("Topic not found.", alert=True)
        text = topic["text"]
    try:
        await event.edit(text, buttons=btns)
    except Exception:
        await bot.send_message(event.chat_id, text, buttons=btns)

async def build_faq_text():
    rows = db.execute("SELECT question, answer FROM faq_entries ORDER BY sort_order ASC, id ASC").fetchall()
    if not rows:
        return (
            "❓ <b>Frequently Asked Questions</b>\n\n"
            "<i>No FAQ entries yet. Check back later or contact Support!</i>"
        )
    text = "❓ <b>Frequently Asked Questions</b>\n\n"
    for i, (q, a) in enumerate(rows, 1):
        text += f"<b>Q{i}: {q}</b>\n{a}\n\n"
    return text.strip()

# ================= ADMIN ACTIONS =================
async def send_pending_deposits_page(event, page=1):
    limit = 8
    offset = (page - 1) * limit
    rows = db.execute(
        "SELECT id, user_id, amount, method_name, date FROM deposits WHERE status='pending' ORDER BY id DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    total = db.execute("SELECT COUNT(*) FROM deposits WHERE status='pending'").fetchone()[0]

    if not rows:
        msg = f"📋 <b>Pending Deposits</b>\n\n{P_YES} No pending deposits! All clear."
        btns = [[Button.inline("🔙 Back to Admin", "adm_adminmain")]]
        try: await event.edit(msg, buttons=btns)
        except Exception as _e:
            logger.debug(f"pending_deposits edit failed, falling back to send: {_e}")
            await bot.send_message(event.chat_id, msg, buttons=btns)
        return

    msg = f"📋 <b>PENDING DEPOSITS</b>  ({total} pending)\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    btns = []
    for dep_id, t_uid, amt, method, date in rows:
        date_str = str(date)[:10] if date else "?"
        msg += f"🔔 <b>#{dep_id}</b>  ·  User <code>{t_uid}</code>  ·  {P_INR}{amt}  ·  {method}  ·  <code>{date_str}</code>\n"
        btns.append([
            Button.inline(f"✅ #{dep_id} Approve ₹{amt}", f"dep_acc|{dep_id}|{t_uid}|{method}|exact|{amt}"),
            Button.inline(f"❌ Reject #{dep_id}", f"dep_rej|{dep_id}|{t_uid}")
        ])

    nav = []
    if page > 1: nav.append(Button.inline("◀ Prev", f"adm_pdpg|{page-1}"))
    if offset + limit < total: nav.append(Button.inline("Next ▶", f"adm_pdpg|{page+1}"))
    if nav: btns.append(nav)
    btns.append([Button.inline("🔄 Refresh", f"adm_pdpg|{page}"), Button.inline("🔙 Back", "adm_adminmain")])

    try: await event.edit(msg, buttons=btns)
    except Exception as _e:
        logger.debug(f"pending_deposits list edit failed, falling back to send: {_e}")
        await bot.send_message(event.chat_id, msg, buttons=btns)

async def admin_panel_handler(event):
    uid = event.sender_id
    if not is_admin(uid): return

    btns = []

    # Bot toggle — main admin ONLY (never grantable to sub-admins)
    if uid == ADMIN_ID:
        status_text = "🟢 Bot is ON" if is_bot_online() else "🔴 Bot is OFF"
        btns.append([Button.inline(f"Status: {status_text}", "adm_togglebot")])

    r1 = []
    if has_perm(uid, 'p_add_stock'):
        r1.extend([Button.inline("Add Single Acc", "adm_addstock"), Button.inline("Add ZIP", "adm_addzip")])
    if r1: btns.append(r1)

    r2 = []
    if has_perm(uid, 'p_manage_stock'):
        r2.extend([Button.inline("Manage Stock", "adm_managestock"), Button.inline("Auto Price", "adm_autoprice")])
    if r2: btns.append(r2)

    r3 = []
    if has_perm(uid, 'p_stats'):
        r3.append(Button.inline("📊 Statistics", "adm_stats"))
        r3.append(Button.inline("📈 Sales Report", "adm_sales_report"))
    if has_perm(uid, 'p_broadcast'):
        r3.append(Button.inline("📣 Broadcast", "adm_bcast"))
    if has_perm(uid, 'p_userinfo', 'p_stats'):
        r3.append(Button.inline("🔍 User Info", "adm_userinfo"))
    if r3: btns.append(r3)
    r3b = []
    if has_perm(uid, 'p_stats'):
        r3b.append(Button.inline("🏆 Country Ranking", "adm_country_rank"))
        r3b.append(Button.inline("📋 Wishlist View", "adm_wishlist_admin"))
    if has_perm(uid, 'p_broadcast'):
        r3b.append(Button.inline("⏰ Schedule Broadcast", "adm_schedule_bcast"))
    if r3b: btns.append(r3b)

    r4 = []
    if has_perm(uid, 'p_bal'):
        r4.append(Button.inline("💰 Change Balance", "adm_bal"))
    if has_perm(uid, 'p_ban'):
        r4.append(Button.inline("🚫 Ban User", "adm_ban"))
    if r4: btns.append(r4)

    if has_perm(uid, 'p_bal'):
        btns.append([Button.inline("📋 Pending Deposits", "adm_pendingdeps")])

    if has_perm(uid, 'p_settings'):
        btns.append([Button.inline("🌟 Reseller Panel", "adm_reseller"), Button.inline("Discount", "adm_discount"), Button.inline("Ref %", "adm_refpct")])
        btns.append([Button.inline("⚠️ Low Stock Limit", "adm_low_stock_limit"), Button.inline("🗓 Stock Expiry Days", "adm_stock_expiry"), Button.inline("💲 Qty Tier Discounts", "adm_qty_tiers")])
        btns.append([Button.inline("Support URL", "adm_supporturl"), Button.inline("Set USDT Rate", "adm_usdtrate")])
        btns.append([Button.inline("🎉 Welcome Msg", "adm_welcomemsg")])
        btns.append([Button.inline("🔘 Button Controls", "adm_btnctrls")])
        btns.append([Button.inline("📋 Activity Log Channel", "adm_activitylog"), Button.inline("💸 Payment Log Channel", "adm_paymentlog")])
        btns.append([Button.inline("🛒 Purchase Log Channel", "adm_purchaselog")])
        btns.append([Button.inline("Backup Users", "adm_backupusr"), Button.inline("Restore Users", "adm_restoreusr")])
        btns.append([Button.inline("🔧 Recover DB & Sessions", "adm_recover")])

    if has_perm(uid, 'p_payments', 'p_settings'):
        btns.append([Button.inline("💳 Payments", "adm_payments")])

    if has_perm(uid, 'p_faq', 'p_settings'):
        btns.append([Button.inline("❓ Manage FAQ", "adm_faq")])

    if has_perm(uid, 'p_forcejoin', 'p_settings'):
        btns.append([Button.inline("📢 Force Join Channels", "adm_forcejoin")])

    if has_perm(uid, 'p_settings'):
        # Features 1+2+4
        btns.append([Button.inline("🎟 Coupons", "adm_coupons"),
                     Button.inline("🔥 Flash Sale", "adm_flashsale"),
                     Button.inline("🎁 Bundles", "adm_bundles")])
        # Feature 12
        btns.append([Button.inline("📜 Audit Log", "adm_auditlog")])
    if uid == ADMIN_ID:
        btns.append([Button.inline("👥 Manage Admins", "adm_manageadmins")])

    if hasattr(event, 'data'):
        try:
            await event.edit(f"{P_PC} <b>ADVANCED ADMIN DASHBOARD</b>", buttons=btns)
        except Exception:
            await bot.send_message(event.chat_id, f"{P_PC} <b>ADVANCED ADMIN DASHBOARD</b>", buttons=btns)
    else:
        await bot.send_message(event.chat_id, f"{P_PC} <b>ADVANCED ADMIN DASHBOARD</b>", buttons=btns)

async def manage_admins_menu(event):
    rows = db.execute("SELECT user_id FROM admins").fetchall()
    msg = f"{P_USERS} <b>Manage Sub-Admins</b>\n\n"
    btns = []
    if rows:
        msg += "<i>Tap an admin to edit their rights.</i>\n"
        for r in rows:
            btns.append([Button.inline(f"👤 {r[0]}", f"adm_editadmin|{r[0]}")])
    else:
        msg += "<i>No sub-admins yet.</i>\n"
    btns.append([Button.inline("➕ Add Admin", "adm_addadmin")])
    btns.append([Button.inline("🔙 Back", "adm_adminmain")])
    try:
        await event.edit(msg, buttons=btns)
    except Exception:
        await bot.send_message(event.chat_id, msg, buttons=btns)

_PERM_LABELS = [
    ("📦 Add Stock",          "p_add_stock"),
    ("🗂 Manage Stock",       "p_manage_stock"),
    ("📊 View Stats",         "p_stats"),
    ("📣 Broadcast",          "p_broadcast"),
    ("🔍 View User Info",     "p_userinfo"),
    ("💰 Manage Balances",    "p_bal"),
    ("🚫 Ban / Unban Users",  "p_ban"),
    ("💳 Manage Payments",    "p_payments"),
    ("❓ Manage FAQ",         "p_faq"),
    ("📢 Force Join",         "p_forcejoin"),
    ("⚙️ Settings",           "p_settings"),
]

async def edit_admin_menu(event, target_id):
    cols = ", ".join(pkey for _, pkey in _PERM_LABELS)
    row = db.execute(f"SELECT {cols} FROM admins WHERE user_id=?", (target_id,)).fetchone()
    if not row: return await event.answer("Admin not found", alert=True)
    vals = list(row)
    btns = []
    for i, (label, pkey) in enumerate(_PERM_LABELS):
        icon = "✅" if vals[i] == 1 else "❌"
        btns.append([Button.inline(f"{icon} {label}", f"adm_tglperm|{target_id}|{pkey}")])

    btns.append([Button.inline("🗑 Remove Admin", f"adm_deladmin|{target_id}")])
    btns.append([Button.inline("🔙 Back", "adm_manageadmins")])

    _ea_msg = f"✏️ <b>Editing Admin:</b> <code>{target_id}</code>\n<i>Tap a right to toggle it on or off.</i>"
    try:
        await event.edit(_ea_msg, buttons=btns)
    except Exception:
        await bot.send_message(event.chat_id, _ea_msg, buttons=btns)

async def send_faq_admin_menu(event, page=1):
    limit = 8
    offset = (page - 1) * limit
    total_row = db.execute("SELECT COUNT(*) FROM faq_entries").fetchone()
    total = total_row[0] if total_row else 0
    rows = db.execute("SELECT id, question FROM faq_entries ORDER BY sort_order ASC, id ASC LIMIT ? OFFSET ?", (limit, offset)).fetchall()

    msg = f"❓ <b>Manage FAQ Entries</b> (Page {page})\n\n"
    if not rows:
        msg += "<i>No FAQ entries yet. Tap Add to create the first one.</i>"
    else:
        for faq_id, q in rows:
            short_q = q[:40] + "…" if len(q) > 40 else q
            msg += f"• <code>[{faq_id}]</code> {short_q}\n"

    btns = []
    for faq_id, q in rows:
        short_q = q[:28] + "…" if len(q) > 28 else q
        btns.append([
            Button.inline(f"✏️ {short_q}", f"adm_faq_edit|{faq_id}"),
            Button.inline("🗑️", f"adm_faq_del|{faq_id}")
        ])

    nav = []
    if page > 1: nav.append(Button.inline("◀ Prev", f"adm_faq_pg|{page-1}"))
    if offset + limit < total: nav.append(Button.inline("Next ▶", f"adm_faq_pg|{page+1}"))
    if nav: btns.append(nav)
    btns.append([Button.inline("➕ Add New FAQ", "adm_faq_add")])
    btns.append([Button.inline("🔙 Back to Admin", "adm_adminmain")])

    try:
        await event.edit(msg, buttons=btns)
    except Exception:
        await bot.send_message(event.chat_id, msg, buttons=btns)

async def send_manage_stock_page(event, page):
    limit = 10
    offset = (page - 1) * limit
    rows = db.execute("SELECT DISTINCT country_name FROM stock WHERE available=1 ORDER BY country_name").fetchall()
    total = len(rows)
    countries = rows[offset:offset+limit]
    
    btns = []
    for (c,) in countries: 
        flag = get_flag_by_country_name(c)
        btns.append([Button.inline(f"{flag} {c}", f"adm_msc|{c}")])
    
    nav = []
    if page > 1: nav.append(Button.inline("Prev", f"adm_mspg|{page-1}"))
    if offset + limit < total: nav.append(Button.inline("Next", f"adm_mspg|{page+1}"))
    if nav: btns.append(nav)
    btns.append([Button.inline("Back", "adm_adminmain")])
    _ms_msg = f"{P_DOC} <b>Manage Stock</b> (Page {page})\nSelect a country to edit its properties:"
    try:
        await event.edit(_ms_msg, buttons=btns)
    except Exception:
        await bot.send_message(event.chat_id, _ms_msg, buttons=btns)

async def send_manage_stock_country(event, c_name):
    years = db.execute("SELECT DISTINCT account_year, COUNT(*) as cnt FROM stock WHERE country_name=? AND available=1 GROUP BY account_year ORDER BY account_year DESC", (c_name,)).fetchall()
    flag = get_flag_by_country_name(c_name)
    total_cnt = db.execute("SELECT COUNT(*) FROM stock WHERE country_name=? AND available=1", (c_name,)).fetchone()[0]
    btns = [
        [Button.inline("✏️ Edit Name", f"adm_msedit|name|{c_name}"), Button.inline("🏳 Edit Flag", f"adm_msedit|flag|{c_name}")],
        [Button.inline("💰 Edit Common Price (All Years)", f"adm_msedit|cprice|{c_name}")],
        [Button.inline("🎯 Single Account Price", f"adm_msedit|aphprice|{c_name}")],
        [Button.inline(
            f"🤖 Auto-Detect Price: {'🟢 ON' if is_auto_price_enabled() else '🔴 OFF'}",
            f"adm_msedit|toggle_autoprice|{c_name}"
        )],
    ]
    if years:
        btns.append([Button.inline("── Set Price by Year ──", "adm_noop")])
        y_btns = []
        for (y, cnt) in years:
            y_btns.append(Button.inline(f"{y} ({cnt})", f"adm_msedit|yprice|{c_name}|{y}"))
        for i in range(0, len(y_btns), 3): btns.append(y_btns[i:i+3])
        btns.append([Button.inline("── Remove Stock ──", "adm_noop")])
        rm_btns = []
        for (y, cnt) in years:
            rm_btns.append(Button.inline(f"🗑 {y} ({cnt})", f"adm_msedit|rmyear|{c_name}|{y}"))
        for i in range(0, len(rm_btns), 3): btns.append(rm_btns[i:i+3])
    btns.append([Button.inline("📊 Bulk % Price Adjust", f"adm_msedit|bulk_price_adj|{c_name}"),
               Button.inline(f"🔔 Wishlist ({db.execute('SELECT COUNT(*) FROM wishlist WHERE country_name=?',(c_name,)).fetchone()[0]})", f"adm_msedit|wishlist_country|{c_name}")])
    btns.append([Button.inline(f"🗑 Remove ALL {c_name} ({total_cnt} accounts)", f"adm_msedit|rmall|{c_name}")])
    btns.append([Button.inline("◀️ Back", "adm_mspg|1")])
    _msc_msg = f"{flag} <b>Managing: {c_name}</b>\n<i>Total: {total_cnt} accounts in stock</i>\n\nSelect an option:"
    try:
        await event.edit(_msc_msg, buttons=btns)
    except Exception:
        await bot.send_message(event.chat_id, _msc_msg, buttons=btns)

async def send_autoprice_page(event, page):
    limit = 10
    offset = (page - 1) * limit
    c_list = set([c[0] for c in COUNTRY_CODES.values()])
    db_countries = db.execute("SELECT DISTINCT country_name FROM stock").fetchall()
    for (c,) in db_countries: c_list.add(c)
    
    custom_countries = db.execute("SELECT DISTINCT name FROM custom_countries").fetchall()
    for (c,) in custom_countries: c_list.add(c)

    c_list = sorted(list(c_list))
    total = len(c_list)
    countries = c_list[offset:offset+limit]
    
    btns = []
    for c in countries: 
        flag = get_flag_by_country_name(c)
        btns.append([Button.inline(f"{flag} {c}", f"adm_apc|{c}")])
        
    nav = []
    if page > 1: nav.append(Button.inline("Prev", f"adm_appg|{page-1}"))
    if offset + limit < total: nav.append(Button.inline("Next", f"adm_appg|{page+1}"))
    if nav: btns.append(nav)
    btns.append([Button.inline("Add Custom Country", "adm_ap_add_country")])
    btns.append([Button.inline("Back", "adm_adminmain")])
    _ap_msg = f"{P_ASST} <b>Auto Price Setup</b> (Page {page})\nSelect a country to set fixed prices:"
    try:
        await event.edit(_ap_msg, buttons=btns)
    except Exception:
        await bot.send_message(event.chat_id, _ap_msg, buttons=btns)

async def send_autoprice_country(event, c_name):
    flag = get_flag_by_country_name(c_name)

    # Load all existing prices for this country into a dict
    existing = {r[0]: r[1] for r in db.execute(
        "SELECT year, price FROM auto_prices WHERE country=?", (c_name,)
    ).fetchall()}

    def ptag(key):
        p = existing.get(key)
        return f" ·₹{p}" if p else ""

    btns = [
        [Button.inline("─── Common / Fallback Prices ───", "adm_noop")],
        [
            Button.inline(f"🟢 Common Fresh{ptag('Common_Fresh')}",  f"adm_apset|{c_name}|Common|Fresh"),
            Button.inline(f"🟡 Common Old{ptag('Common_Old')}",     f"adm_apset|{c_name}|Common|Old"),
        ],
        [Button.inline(f"⚡ Common Any{ptag('Common')} (all-catch fallback)", f"adm_apset|{c_name}|Common|Any")],
        [Button.inline("─── Price by Year ───", "adm_noop")],
    ]

    for y in range(datetime.now().year, 2012, -1):
        btns.append([
            Button.inline(f"🟢 {y}{ptag(f'{y}_Fresh')}", f"adm_apset|{c_name}|{y}|Fresh"),
            Button.inline(f"🟡 {y}{ptag(f'{y}_Old')}",  f"adm_apset|{c_name}|{y}|Old"),
        ])

    btns.append([Button.inline("◀️ Back", "adm_appg|1")])

    msg = (
        f"{flag} <b>Auto Price Setup — {c_name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 = Fresh (year ≥ 2025)   🟡 = Old (year ≤ 2024)\n"
        f"⚡ <b>Common Any</b> = catch-all fallback if no specific price is set.\n"
        f"Prices shown in buttons (·₹) are currently saved values.\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    try:
        await event.edit(msg, buttons=btns)
    except Exception:
        await bot.send_message(event.chat_id, msg, buttons=btns)

BTN_CONTROLS = [
    ("buy_account",  "🛒 Buy Account"),
    ("buy_sessions", "📁 Buy Sessions"),
    ("deposit",      "💰 Deposit"),
    ("my_profile",   "👤 My Profile"),
    ("my_balance",   "💳 My Balance"),
    ("my_stats",     "📊 My Stats"),
    ("support",      "📞 Support"),
    ("help",         "❓ Help"),
    ("stock_info",   "📦 Stock Info"),
]

async def send_force_join_menu(event):
    rows = db.execute("SELECT id, channel_id, join_url, type FROM force_join_channels").fetchall()
    _fj_icons = {'channel': '📢', 'group': '👥', 'bot': '🤖'}
    _fj_labels = {'channel': 'Channel', 'group': 'Group', 'bot': 'Bot'}
    msg = "📢 <b>Force Join / Start</b>\n\n"
    if rows:
        for r in rows:
            t = r[3] or 'channel'
            msg += f"{_fj_icons.get(t,'📢')} <b>{_fj_labels.get(t,'Channel')}:</b> <code>{r[1]}</code>\n  🔗 {r[2]}\n\n"
    else:
        msg += "<i>No entries set. Using hardcoded defaults.</i>\n\n"
    msg += "Tap an entry to remove it, or add a new one."
    btns = []
    for r in rows:
        t = r[3] or 'channel'
        btns.append([Button.inline(f"❌ Remove {_fj_labels.get(t,'')} — {r[1]}", f"adm_fjdel|{r[0]}")])
    btns.append([Button.inline("➕ Add Channel / Group / Bot", "adm_fjadd")])
    btns.append([Button.inline("🔙 Back to Admin", "adm_adminmain")])
    try:
        await event.edit(msg, buttons=btns)
    except Exception:
        await bot.send_message(event.chat_id, msg, buttons=btns)

async def send_btn_controls_menu(event):
    btns = []
    for key, label in BTN_CONTROLS:
        status = "✅ ON" if is_btn_enabled(key) else "❌ OFF"
        btns.append([Button.inline(f"{label}  —  {status}", f"adm_togglebtn|{key}")])
    btns.append([Button.inline("🔙 Back to Admin", "adm_adminmain")])
    msg = "🔘 <b>Button Controls</b>\n\nToggle individual menu buttons ON or OFF.\nWhen OFF, the button is hidden from users and the feature is blocked."
    try:
        await event.edit(msg, buttons=btns)
    except Exception:
        await bot.send_message(event.chat_id, msg, buttons=btns)

async def send_payments_panel(event, uid):
    upi_enabled_row = db.execute("SELECT value FROM settings WHERE key='upi_enabled'").fetchone()
    upi_on = (upi_enabled_row[0] if upi_enabled_row else '1') != '0'
    qr_row = db.execute("SELECT value FROM settings WHERE key='upi_qr_file_id'").fetchone()
    # FIX: also accept HTTP URLs as valid QR values (not just local file paths)
    _upi_qr_val = qr_row[0] if qr_row and qr_row[0] else None
    qr_status = f"{P_YES} Set" if _upi_qr_val else f"{P_NO} Not Set"
    hlk_enabled_row = db.execute("SELECT value FROM settings WHERE key='cwallet_enabled'").fetchone()
    hlk_on = (hlk_enabled_row[0] if hlk_enabled_row else '0') != '0'
    hlk_key_row = db.execute("SELECT value FROM settings WHERE key='cwallet_api_key'").fetchone()
    hlk_key = hlk_key_row[0] if hlk_key_row and hlk_key_row[0] else ""
    hlk_key_status = f"{P_YES} Set ({hlk_key[:6]}…)" if hlk_key else f"{P_NO} Not Set"
    hlk_bonus_row = db.execute("SELECT value FROM settings WHERE key='cwallet_bonus_pct'").fetchone()
    hlk_bonus_pct = int(hlk_bonus_row[0]) if hlk_bonus_row and hlk_bonus_row[0] else 0
    hlk_coin_row = db.execute("SELECT value FROM settings WHERE key='cwallet_coin'").fetchone()
    hlk_coin = hlk_coin_row[0] if hlk_coin_row and hlk_coin_row[0] else CWALLET_COIN
    hlk_net_row = db.execute("SELECT value FROM settings WHERE key='cwallet_network'").fetchone()
    hlk_net = hlk_net_row[0] if hlk_net_row and hlk_net_row[0] else CWALLET_NETWORK
    upi_id_row = db.execute("SELECT value FROM settings WHERE key='upi_id'").fetchone()
    current_upi_id = upi_id_row[0] if upi_id_row and upi_id_row[0] else UPI_ID
    btns = [
        [Button.inline(f"{P_UPI} UPI: {'🟢 ON' if upi_on else '🔴 OFF'}", "adm_upi_toggle")],
        [Button.inline(f"🏦 UPI ID: {current_upi_id[:25]}{'...' if len(current_upi_id) > 25 else ''}", "adm_upi_setid")],
        [Button.inline(f"{P_UPI} UPI QR Image: {qr_status}", "adm_setupi_qr")],
        [Button.inline(f"🔷 CWallet: {'🟢 ON' if hlk_on else '🔴 OFF'}", "adm_hlk_toggle")],
        [Button.inline(f"🔑 CWallet API Key: {hlk_key_status}", "adm_hlk_setkey")],
        [Button.inline(f"💲 CWallet Coin: {hlk_coin} / {hlk_net.upper()}", "adm_hlk_setcoin")],
        [Button.inline(f"🎁 CWallet Bonus: {hlk_bonus_pct}%", "adm_hlk_setbonus")],
        [Button.inline(f"📋 CWallet Pending Invoices", "adm_hlk_pending")],
        [Button.inline("➕ Add Payment Method", "adm_addpay")],
        [Button.inline("➖ Remove Payment Method", "adm_delpay")],
        [Button.inline("🔙 Back to Admin", "adm_adminmain")]
    ]
    try:
        await event.edit(f"{P_CARD} <b>Manage Payment Methods</b>", buttons=btns)
    except Exception:
        await bot.send_message(event.chat_id, f"{P_CARD} <b>Manage Payment Methods</b>", buttons=btns)

async def send_reseller_panel(event, page: int = 1):
    """Show the reseller management panel with per-user Add/Remove/Change Discount buttons."""
    PAGE_SIZE = 8
    uid = event.sender_id

    cur_disc = get_reseller_discount()
    resellers = db.execute(
        "SELECT user_id, discount FROM users WHERE reseller=1 ORDER BY user_id"
    ).fetchall()
    total = len(resellers)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(page, pages))
    slice_start = (page - 1) * PAGE_SIZE
    page_rows = resellers[slice_start: slice_start + PAGE_SIZE]

    lines = [
        f"🌟 <b>Reseller Panel</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷 Global reseller discount: <b>{cur_disc}%</b>\n"
        f"👥 Total resellers: <b>{total}</b>   (page {page}/{pages})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    ]
    btns = []

    for r_uid, r_disc in page_rows:
        eff = r_disc if r_disc else cur_disc
        lines.append(f"• <code>{r_uid}</code>  —  discount: <b>{eff}%</b>")
        btns.append([
            Button.inline(f"✂️ {r_uid}", f"adm_res_rm|{r_uid}"),
            Button.inline(f"💸 Disc%", f"adm_res_disc|{r_uid}"),
        ])

    nav_row = []
    if page > 1:
        nav_row.append(Button.inline("◀️ Prev", f"adm_res_page|{page - 1}"))
    if page < pages:
        nav_row.append(Button.inline("Next ▶️", f"adm_res_page|{page + 1}"))
    if nav_row:
        btns.append(nav_row)

    btns.append([
        Button.inline("➕ Add Reseller", "adm_res_add"),
        Button.inline("🔧 Change Global Disc%", "adm_res_global_disc"),
    ])
    btns.append([Button.inline("🔙 Back", "adm_adminmain")])

    msg = "".join(lines)
    if not page_rows:
        msg += "<i>No resellers yet.</i>\n"

    try:
        await event.edit(msg, buttons=btns)
    except Exception:
        await bot.send_message(event.chat_id, msg, buttons=btns)


async def admin_actions(event):
    data_full = event.data.decode()
    if not data_full.startswith("adm_"): return
    uid = event.sender_id
    action_data = data_full[4:]
    chat = event.chat_id
    
    if action_data == "adminmain":
        try: await event.delete()
        except Exception as _e: logger.debug(f'Admin menu delete ignored: {_e}')
        class _FakeAdminEvent:
            chat_id = chat
            sender_id = uid
            async def edit(self, msg, buttons=None): await bot.send_message(chat, msg, buttons=buttons)
            async def answer(self, msg="", alert=False):
                if msg: await bot.send_message(chat, msg)
        return await admin_panel_handler(_FakeAdminEvent())

    if action_data == "btnctrls" and has_perm(uid, 'p_settings'):
        return await send_btn_controls_menu(event)

    if action_data == "forcejoin" and has_perm(uid, 'p_forcejoin', 'p_settings'):
        return await send_force_join_menu(event)

    if action_data.startswith("fjdel|") and has_perm(uid, 'p_forcejoin', 'p_settings'):
        row_id = action_data.split("|", 1)[1]
        with _db_write_lock:
            db.execute("DELETE FROM force_join_channels WHERE id=?", (row_id,))
            # Reset everyone's verification — channel list changed
            db.execute("UPDATE users SET fj_verified=0")
            db.commit()
        await event.answer("✅ Channel removed. All users will re-verify.", alert=False)
        return await send_force_join_menu(event)

    if action_data.startswith("togglebtn|") and has_perm(uid, 'p_settings'):
        key = action_data.split("|", 1)[1]
        if key in [k for k, _ in BTN_CONTROLS]:
            new_val = 'off' if is_btn_enabled(key) else 'on'
            with _db_write_lock:
                db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f'btn_{key}', new_val))
                db.commit()
            label = next(lbl for k, lbl in BTN_CONTROLS if k == key)
            await event.answer(f"{label} turned {new_val.upper()}", alert=False)
            return await send_btn_controls_menu(event)

    if action_data == "togglebot" and uid == ADMIN_ID:
        new_status = 'off' if is_bot_online() else 'on'
        with _db_write_lock:
            db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('bot_status', ?)", (new_status,))
            db.commit()
        await event.answer(f"✅ Bot turned {new_status.upper()}", alert=True)
        await admin_panel_handler(event)
        return

    # ── Reseller panel (no conversation needed for display and toggle) ─────────
    if action_data == "reseller" and has_perm(uid, 'p_settings'):
        return await send_reseller_panel(event)

    if action_data.startswith("res_page|") and has_perm(uid, 'p_settings'):
        try:
            _rp = int(action_data.split("|", 1)[1])
        except ValueError:
            _rp = 1
        return await send_reseller_panel(event, _rp)

    if action_data.startswith("res_rm|") and has_perm(uid, 'p_settings'):
        try:
            _rm_uid = int(action_data.split("|", 1)[1])
        except ValueError:
            return await event.answer("⚠️ Invalid user ID.", alert=True)
        row = db.execute("SELECT reseller FROM users WHERE user_id=?", (_rm_uid,)).fetchone()
        if not row:
            return await event.answer(f"⚠️ User {_rm_uid} not found.", alert=True)
        new_res = 0 if row[0] else 1
        with _db_write_lock:
            db.execute("UPDATE users SET reseller=? WHERE user_id=?", (new_res, _rm_uid))
            db.commit()
        lbl = "🌟 Reseller" if new_res else "👤 Regular"
        await event.answer(f"✅ User {_rm_uid} is now {lbl}.", alert=False)
        try:
            if new_res:
                await bot.send_message(_rm_uid, f"🌟 <b>You've been upgraded to Reseller!</b>\n\nYou now get <b>{get_reseller_discount()}% discount</b> on all purchases.")
            else:
                await bot.send_message(_rm_uid, f"ℹ️ Your reseller status has been removed.")
        except Exception as _rme: logger.debug(f"reseller notify failed: {_rme}")
        return await send_reseller_panel(event)
    # ── End reseller non-conversation block ────────────────────────────────────

    elif action_data == "stats" and has_perm(uid, 'p_stats'):
        u_row = db.execute("SELECT COUNT(*) FROM users").fetchone()
        u = u_row[0] if u_row else 0
        s_row = db.execute("SELECT COUNT(*) FROM stock WHERE available=1").fetchone()
        s = s_row[0] if s_row else 0
        r_row = db.execute("SELECT value FROM settings WHERE key='upi_revenue'").fetchone()
        r = r_row[0] if r_row else "0"
        bal_row = db.execute("SELECT SUM(balance) FROM users").fetchone()
        total_bal = bal_row[0] if bal_row and bal_row[0] else 0
        o_row = db.execute("SELECT COUNT(*), SUM(price) FROM orders").fetchone()
        total_orders = o_row[0] if o_row else 0
        total_spent = o_row[1] if o_row and o_row[1] else 0
        
        msg = (f"{P_STATS} <b>ADVANCED STATS</b>\n\n{P_USERS} <b>Total Users:</b> {u}\n{P_PKG} <b>Accounts in Stock:</b> {s}\n"
               f"{P_MONEY} <b>Total UPI Revenue:</b> {P_INR}{r}\n\n{P_CARD} <b>Overall Users Balance:</b> {P_INR}{total_bal}\n"
               f"{P_CART} <b>Total Accounts Sold:</b> {total_orders}\n{P_USDT} <b>Overall Sales Amount:</b> {P_INR}{total_spent}")
        return await event.edit(msg, buttons=[[Button.inline("Back", "adm_adminmain")]])

    elif action_data == "payments" and has_perm(uid, 'p_payments', 'p_settings'):
        return await send_payments_panel(event, uid)

    elif action_data == "upi_toggle" and has_perm(uid, 'p_payments', 'p_settings'):
        upi_row = db.execute("SELECT value FROM settings WHERE key='upi_enabled'").fetchone()
        upi_on = (upi_row[0] if upi_row else '1') != '0'
        with _db_write_lock:
            db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('upi_enabled', ?)", ('0' if upi_on else '1',))
            db.commit()
        return await send_payments_panel(event, uid)

    elif action_data == "hlk_toggle" and has_perm(uid, 'p_payments', 'p_settings'):
        hlk_row = db.execute("SELECT value FROM settings WHERE key='cwallet_enabled'").fetchone()
        hlk_on = (hlk_row[0] if hlk_row else '0') != '0'
        with _db_write_lock:
            db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('cwallet_enabled', ?)", ('0' if hlk_on else '1',))
            db.commit()
        return await send_payments_panel(event, uid)

    elif action_data == "hlk_pending" and has_perm(uid, 'p_payments', 'p_settings'):
        rows_hlk = db.execute(
            "SELECT invoice_id, user_id, amount_inr, amount_usdt, status, created_at "
            "FROM cwallet_invoices WHERE status='pending' ORDER BY created_at DESC LIMIT 10"
        ).fetchall()
        if not rows_hlk:
            try: return await event.edit("🔷 <b>CWallet Pending Invoices</b>\n\n<i>No pending invoices.</i>",
                                          buttons=[[Button.inline("🔙 Back", "adm_payments")]])
            except Exception: pass
            return
        msg_hlk = "🔷 <b>CWallet Pending Invoices</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for inv_id, inv_uid, inr, usdt, st, cat in rows_hlk:
            age = int((time.time() - (cat or time.time())) / 60)
            msg_hlk += f"🔑 <code>{inv_id[:16]}…</code>  |  User <code>{inv_uid}</code>  |  ₹{inr} ({usdt} USDT)  |  {age}m ago\n"
        try: await event.edit(msg_hlk, buttons=[[Button.inline("🔙 Back", "adm_payments")]])
        except Exception: await bot.send_message(chat, msg_hlk, buttons=[[Button.inline("🔙 Back", "adm_payments")]])
        return

    elif action_data == "manageadmins" and uid == ADMIN_ID:
        return await manage_admins_menu(event)

    elif action_data.startswith("editadmin|") and uid == ADMIN_ID:
        t_id = int(action_data.split("|")[1])
        return await edit_admin_menu(event, t_id)

    elif action_data.startswith("tglperm|") and uid == ADMIN_ID:
        _, t_id, p_name = action_data.split("|", 2)
        VALID_PERMS = {pkey for _, pkey in _PERM_LABELS}
        if p_name not in VALID_PERMS:
            return await event.answer("❌ Invalid permission name.", alert=True)
        with _db_write_lock:
            db.execute(f"UPDATE admins SET {p_name} = CASE WHEN {p_name}=1 THEN 0 ELSE 1 END WHERE user_id=?", (t_id,))
            db.commit()
        return await edit_admin_menu(event, int(t_id))

    elif action_data.startswith("deladmin|") and uid == ADMIN_ID:
        t_id = action_data.split("|")[1]
        with _db_write_lock:
            db.execute("DELETE FROM admins WHERE user_id=?", (t_id,))
            db.commit()
        await event.answer("✅ Admin Removed", alert=True)
        return await manage_admins_menu(event)

    elif action_data == "country_rank" and has_perm(uid, 'p_stats'):
        rows_rank = db.execute(
            "SELECT country, COUNT(*) as cnt, COALESCE(SUM(price),0) FROM orders GROUP BY country ORDER BY cnt DESC LIMIT 10"
        ).fetchall()
        if not rows_rank:
            return await event.edit(f"{P_NO} No sales data yet.", buttons=[[Button.inline("Back", "adm_adminmain")]])
        msg_rank = "🏆 <b>Country Sales Ranking (All Time)</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        medals = ["🥇","🥈","🥉"] + [f"{i}." for i in range(4,11)]
        for i, (c, cnt, rev) in enumerate(rows_rank):
            flag_r = get_flag_by_country_name(c)
            msg_rank += f"{medals[i]} {flag_r} <b>{c}</b>  —  {cnt} sold  ({P_INR}{rev})\n"
        return await event.edit(msg_rank, buttons=[[Button.inline("🔙 Back", "adm_adminmain")]])

    elif action_data == "wishlist_admin" and has_perm(uid, 'p_stats'):
        rows_wl = db.execute(
            "SELECT country_name, COUNT(*) as cnt FROM wishlist GROUP BY country_name ORDER BY cnt DESC LIMIT 15"
        ).fetchall()
        if not rows_wl:
            return await event.edit("📋 <b>Wishlist</b>\n\n<i>No wishlists added yet.</i>", buttons=[[Button.inline("Back","adm_adminmain")]])
        msg_wl = "📋 <b>Wishlist Summary</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for (c, cnt) in rows_wl:
            flag_w = get_flag_by_country_name(c)
            msg_wl += f"{flag_w} <b>{c}</b>  —  {cnt} user(s) waiting\n"
        return await event.edit(msg_wl, buttons=[[Button.inline("🔙 Back", "adm_adminmain")]])

    # ─── Feature 2: Flash Sale ─────────────────────────────────────────
    elif action_data == "flashsale" and has_perm(uid, 'p_settings'):
        flash = get_active_flash_sale()
        _fs_status = (f"🔥 <b>ACTIVE:</b> {flash['discount']}% OFF — ends in {get_flash_sale_countdown(flash['ends_dt'])}"
                      if flash else "💤 <b>No active flash sale</b>")
        _fs_btns = [
            [Button.inline("🔥 Start Flash Sale", "adm_flashsale_start")],
            [Button.inline("🛑 End Flash Sale Now", "adm_flashsale_end")],
            [Button.inline("🔙 Back", "adm_adminmain")],
        ]
        try: await event.edit(f"🔥 <b>Flash Sale</b>\n\n{_fs_status}", buttons=_fs_btns)
        except Exception: await bot.send_message(chat, f"🔥 <b>Flash Sale</b>\n\n{_fs_status}", buttons=_fs_btns)
        return

    elif action_data == "flashsale_start" and has_perm(uid, 'p_settings'):
        async with bot.conversation(uid, timeout=90) as conv:
            await conv.send_message("🔥 <b>Start Flash Sale</b>\n\n1/2: Discount % (1–90):")
            _dr = (await conv.get_response()).text.strip()
            if not _dr.isdigit() or not (1 <= int(_dr) <= 90):
                return await conv.send_message("❌ Must be 1–90%.")
            _dv = int(_dr)
            await conv.send_message("2/2: Duration in hours (e.g. 2  or  0.5 for 30min):")
            _hr_r = (await conv.get_response()).text.strip()
            try:
                _hours = float(_hr_r)
                if _hours <= 0: raise ValueError
            except ValueError:
                return await conv.send_message("❌ Must be positive number.")
            _ends_str = (datetime.now() + timedelta(hours=_hours)).strftime("%Y-%m-%d %H:%M")
            with _db_write_lock:
                db.execute("INSERT OR REPLACE INTO settings (key,value) VALUES ('flash_sale_discount',?)", (str(_dv),))
                db.execute("INSERT OR REPLACE INTO settings (key,value) VALUES ('flash_sale_ends_at',?)", (_ends_str,))
                db.commit()
            log_admin_action_db(uid, 'flash_sale_started', None, f'disc={_dv}% ends={_ends_str}')
            await conv.send_message(f"🔥 <b>Flash Sale LIVE!</b>\n{_dv}% OFF — ends {_ends_str}")
        return

    elif action_data == "flashsale_end" and has_perm(uid, 'p_settings'):
        with _db_write_lock:
            db.execute("DELETE FROM settings WHERE key IN ('flash_sale_ends_at','flash_sale_discount')")
            db.commit()
        log_admin_action_db(uid, 'flash_sale_ended', None, 'manual')
        try: await event.edit("✅ Flash Sale ended.", buttons=[[Button.inline("🔙 Back","adm_adminmain")]])
        except Exception: await bot.send_message(chat, "✅ Flash Sale ended.")
        return

    # ─── Feature 1: Coupon Codes ───────────────────────────────────────
    elif action_data == "coupons" and has_perm(uid, 'p_settings'):
        crows = db.execute(
            "SELECT code, discount_pct, COALESCE(balance_amount,0), "
            "COALESCE(coupon_type,'discount'), max_uses, uses_count, expires_at "
            "FROM promo_codes ORDER BY id DESC LIMIT 20"
        ).fetchall()
        msg_c = "🎟 <b>Promo Codes</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        btns_c = []
        for code, disc, bal_amt, ctype, mx, used, exp in crows:
            st = "✅" if (mx == 0 or used < mx) else "❌"
            ei = f" | exp {exp[:10]}" if exp else ""
            if ctype == 'balance':
                msg_c += f"{st} 💰 <code>{code}</code> — ₹{bal_amt} balance  ({used}/{mx if mx > 0 else chr(8734)}{ei})\n"
            else:
                msg_c += f"{st} 🎟 <code>{code}</code> — {disc}% off  ({used}/{mx if mx > 0 else chr(8734)}{ei})\n"
            btns_c.append([Button.inline(f"🗑 {code}", f"adm_coupons_del|{code}")])
        if not crows: msg_c += "<i>No coupon codes yet.</i>"
        btns_c += [[Button.inline("➕ Create Coupon", "adm_coupons_add")], [Button.inline("🔙 Back", "adm_adminmain")]]
        try: await event.edit(msg_c, buttons=btns_c)
        except Exception: await bot.send_message(chat, msg_c, buttons=btns_c)
        return

    elif action_data == "coupons_add" and has_perm(uid, 'p_settings'):
        async with bot.conversation(uid, timeout=180) as conv:
            # ── Step 1: pick coupon type ────────────────────────────────
            await conv.send_message(
                "\U0001f39f <b>Create Coupon</b>\n\n"
                "Select coupon type:",
                buttons=[
                    [Button.inline("\U0001f4b0 Balance Add", b"ctype_balance"),
                     Button.inline("\U0001f39f Discount %",  b"ctype_discount")],
                ],
                parse_mode="html"
            )
            _type_ev = await conv.wait_event(
                events.CallbackQuery(chats=uid), timeout=120
            )
            await _type_ev.answer()
            _ctype = "balance" if _type_ev.data == b"ctype_balance" else "discount"

            if _ctype == "balance":
                # ── Balance Add flow ────────────────────────────────────
                await conv.send_message(
                    "\U0001f4b0 <b>Balance Add Coupon</b>\n\n"
                    "Select balance amount to add (admin taps a button):",
                    buttons=[
                        [Button.inline("\u20b95",   b"bamt_5"),
                         Button.inline("\u20b910",  b"bamt_10"),
                         Button.inline("\u20b925",  b"bamt_25")],
                        [Button.inline("\u20b950",  b"bamt_50"),
                         Button.inline("\u20b9100", b"bamt_100"),
                         Button.inline("\u20b9200", b"bamt_200")],
                        [Button.inline("\u20b9500", b"bamt_500"),
                         Button.inline("\u270f Custom", b"bamt_custom")],
                    ],
                    parse_mode="html"
                )
                _amt_ev = await conv.wait_event(
                    events.CallbackQuery(chats=uid), timeout=120
                )
                await _amt_ev.answer()
                if _amt_ev.data == b"bamt_custom":
                    await conv.send_message("Enter custom amount in \u20b9 (numbers only):")
                    _amt_txt = (await conv.get_response()).text.strip()
                    if not _amt_txt.isdigit() or int(_amt_txt) <= 0:
                        return await conv.send_message("\u274c Invalid amount. Must be a positive number.")
                    _bal_amt = int(_amt_txt)
                else:
                    _bal_amt = int(_amt_ev.data.decode().split("_", 1)[1])

                await conv.send_message(
                    "\U0001f465 How many users can redeem this code?\n"
                    "(Enter a number — 0 means unlimited):"
                )
                _mx_r = (await conv.get_response()).text.strip()
                if not _mx_r.isdigit():
                    return await conv.send_message("\u274c Must be a whole number.")
                _mxv = int(_mx_r)

                await conv.send_message(
                    "\U0001f4c5 Expiry date/time (YYYY-MM-DD HH:MM) or type <code>none</code>:",
                    parse_mode="html"
                )
                _exp_r = (await conv.get_response()).text.strip()
                _exp_v = None
                if _exp_r.lower() != "none":
                    try:
                        datetime.strptime(_exp_r, "%Y-%m-%d %H:%M")
                        _exp_v = _exp_r
                    except ValueError:
                        return await conv.send_message("\u274c Use format YYYY-MM-DD HH:MM")

                # Auto-generate random unique code
                for _attempt in range(20):
                    _code_r = ''.join(random.choices(
                        string.ascii_uppercase + string.digits, k=8
                    ))
                    if not db.execute(
                        "SELECT 1 FROM promo_codes WHERE code=? COLLATE NOCASE", (_code_r,)
                    ).fetchone():
                        break

                with _db_write_lock:
                    db.execute(
                        "INSERT INTO promo_codes "
                        "(code, discount_pct, balance_amount, coupon_type, "
                        " max_uses, uses_count, expires_at, created_by) "
                        "VALUES (?, 0, ?, 'balance', ?, 0, ?, ?)",
                        (_code_r, _bal_amt, _mxv, _exp_v, uid)
                    )
                    db.commit()
                log_admin_action_db(uid, 'coupon_created', None,
                    f'code={_code_r} type=balance bal={_bal_amt} max={_mxv}')
                _inf = chr(8734) if _mxv == 0 else str(_mxv)
                await conv.send_message(
                    f"\u2705 <b>Balance Coupon Created!</b>\n"
                    f"Code: <code>{_code_r}</code>\n"
                    f"Type: \U0001f4b0 Balance Add  |  Amount: \u20b9{_bal_amt}\n"
                    f"Max users: {_inf}  |  Expires: {_exp_v or 'Never'}\n\n"
                    f"Share with users: <code>/coupon {_code_r}</code>",
                    parse_mode="html"
                )

            else:
                # ── Discount % flow ─────────────────────────────────────
                await conv.send_message(
                    "\U0001f39f <b>Discount Coupon</b>\n\n"
                    "1/4 \u2014 Coupon code (e.g. SAVE20).\n"
                    "Type <b>AUTO</b> to generate a random code:",
                    parse_mode="html"
                )
                _code_r = (await conv.get_response()).text.strip().upper()
                if _code_r == "AUTO":
                    for _attempt in range(20):
                        _code_r = ''.join(random.choices(
                            string.ascii_uppercase + string.digits, k=8
                        ))
                        if not db.execute(
                            "SELECT 1 FROM promo_codes WHERE code=? COLLATE NOCASE", (_code_r,)
                        ).fetchone():
                            break
                if not _code_r or not re.match(r'^[A-Z0-9_-]{2,20}$', _code_r):
                    return await conv.send_message("\u274c Code must be 2\u201320 chars: A-Z 0-9 _ -")
                if db.execute(
                    "SELECT 1 FROM promo_codes WHERE code=? COLLATE NOCASE", (_code_r,)
                ).fetchone():
                    return await conv.send_message(
                        f"\u274c Code <code>{_code_r}</code> already exists.", parse_mode="html"
                    )
                await conv.send_message("2/4 \u2014 Discount % (1\u2013100):")
                _disc_r = (await conv.get_response()).text.strip()
                if not _disc_r.isdigit() or not (1 <= int(_disc_r) <= 100):
                    return await conv.send_message("\u274c Must be 1\u2013100.")
                _dv = int(_disc_r)
                await conv.send_message("3/4 \u2014 Max uses (0 = unlimited):")
                _mx_r = (await conv.get_response()).text.strip()
                if not _mx_r.isdigit():
                    return await conv.send_message("\u274c Must be a number.")
                _mxv = int(_mx_r)
                await conv.send_message(
                    "4/4 \u2014 Expiry (YYYY-MM-DD HH:MM) or <code>none</code>:",
                    parse_mode="html"
                )
                _exp_r = (await conv.get_response()).text.strip()
                _exp_v = None
                if _exp_r.lower() != "none":
                    try:
                        datetime.strptime(_exp_r, "%Y-%m-%d %H:%M")
                        _exp_v = _exp_r
                    except ValueError:
                        return await conv.send_message("\u274c Use YYYY-MM-DD HH:MM")
                with _db_write_lock:
                    db.execute(
                        "INSERT INTO promo_codes "
                        "(code, discount_pct, balance_amount, coupon_type, "
                        " max_uses, uses_count, expires_at, created_by) "
                        "VALUES (?, ?, 0, 'discount', ?, 0, ?, ?)",
                        (_code_r, _dv, _mxv, _exp_v, uid)
                    )
                    db.commit()
                log_admin_action_db(uid, 'coupon_created', None,
                    f'code={_code_r} disc={_dv}% max={_mxv}')
                _inf = chr(8734) if _mxv == 0 else str(_mxv)
                await conv.send_message(
                    f"\u2705 <b>Coupon Created!</b>\n"
                    f"Code: <code>{_code_r}</code>  |  {_dv}% off  |  max: {_inf}\n"
                    f"Expires: {_exp_v or 'Never'}\n\n"
                    f"Share with users: <code>/coupon {_code_r}</code>",
                    parse_mode="html"
                )
        return

    elif action_data == "managestock" and has_perm(uid, 'p_manage_stock'): return await send_manage_stock_page(event, 1)
    elif action_data.startswith("mspg|") and has_perm(uid, 'p_manage_stock'): return await send_manage_stock_page(event, int(action_data.split("|")[1]))
    elif action_data.startswith("msc|") and has_perm(uid, 'p_manage_stock'): return await send_manage_stock_country(event, action_data.split("|", 1)[1])
    elif action_data == "autoprice" and has_perm(uid, 'p_manage_stock'): return await send_autoprice_page(event, 1)
    elif action_data.startswith("appg|") and has_perm(uid, 'p_manage_stock'): return await send_autoprice_page(event, int(action_data.split("|")[1]))
    elif action_data.startswith("apc|") and has_perm(uid, 'p_manage_stock'): return await send_autoprice_country(event, action_data.split("|", 1)[1])
        
    elif action_data == "backupusr" and has_perm(uid, 'p_settings'):
        _csv_cur = db.cursor()
        _csv_cur.execute("SELECT * FROM users")
        with open("users_backup.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow([i[0] for i in _csv_cur.description]); w.writerows(_csv_cur.fetchall())
        await bot.send_file(chat, "users_backup.csv", caption=f"{P_USERS} <b>Users Backup CSV</b>")
        os.remove("users_backup.csv")
        return await event.answer("✅ Backup Generated!", alert=True)

    elif action_data == "faq" and has_perm(uid, 'p_faq', 'p_settings'):
        return await send_faq_admin_menu(event)

    elif action_data.startswith("faq_pg|") and has_perm(uid, 'p_faq', 'p_settings'):
        try:
            page = max(1, int(action_data.split("|")[1]))
        except (ValueError, IndexError):
            return await event.answer("⚠️ Invalid page.", alert=True)
        return await send_faq_admin_menu(event, page)

    elif action_data.startswith("faq_del|") and has_perm(uid, 'p_faq', 'p_settings'):
        faq_id = int(action_data.split("|")[1])
        with _db_write_lock:
            db.execute("DELETE FROM faq_entries WHERE id=?", (faq_id,))
            db.commit()
        await event.answer("🗑️ FAQ entry deleted.", alert=True)
        return await send_faq_admin_menu(event)

    elif action_data == "welcomemsg" and has_perm(uid, 'p_settings'):
        current = get_welcome_message()
        btn_text, btn_url = get_welcome_button()
        _sp_row = db.execute("SELECT value FROM settings WHERE key='start_photo'").fetchone()
        _sp = _sp_row[0] if _sp_row and _sp_row[0] else None
        if current:
            preview = f"\n\n<b>Current message:</b>\n{current}"
        else:
            preview = "\n\n<i>No welcome message set. New users will not receive one.</i>"
        if btn_text and btn_url:
            btn_preview = f"\n\n<b>Current button:</b> <code>{btn_text}</code> → {btn_url}"
        else:
            btn_preview = "\n\n<i>No button attached.</i>"
        if _sp:
            photo_preview = f"\n\n📸 <b>Start Photo:</b> <code>{html.escape(_sp)}</code>"
        else:
            photo_preview = "\n\n📸 <b>Start Photo:</b> <i>Not set (no photo sent on /start).</i>"
        btns = [
            [Button.inline("✏️ Set / Update Message", "adm_welcomeset")],
            [Button.inline("🗑️ Reset / Remove Message", "adm_welcomereset")],
            [Button.inline("🔘 Set Button", "adm_welcomebtnset"), Button.inline("🗑 Clear Button", "adm_welcomebtnreset")],
            [Button.inline("📸 Set Start Photo", "adm_welcomephoto"), Button.inline("🗑 Clear Photo", "adm_welcomephotoreset")],
            [Button.inline("🔙 Back to Admin", "adm_adminmain")],
        ]
        display = f"🎉 <b>Welcome Message</b>{preview}{btn_preview}{photo_preview}"
        try:
            await event.edit(display, buttons=btns)
        except Exception:
            await bot.send_message(chat, display, buttons=btns)
        return

    elif action_data == "welcomereset" and has_perm(uid, 'p_settings'):
        with _db_write_lock:
            db.execute("DELETE FROM settings WHERE key='welcome_message'")
            db.commit()
        btns = [[Button.inline("🔙 Back to Welcome Settings", "adm_welcomemsg")]]
        try:
            await event.edit(f"{P_YES} <b>Welcome message removed.</b>\n\n<i>New users will not receive a welcome message.</i>", buttons=btns)
        except Exception:
            await bot.send_message(chat, f"{P_YES} <b>Welcome message removed.</b>\n\n<i>New users will not receive a welcome message.</i>", buttons=btns)
        return

    elif action_data == "welcomebtnreset" and has_perm(uid, 'p_settings'):
        with _db_write_lock:
            db.execute("DELETE FROM settings WHERE key='welcome_btn_text'")
            db.execute("DELETE FROM settings WHERE key='welcome_btn_url'")
            db.commit()
        btns = [[Button.inline("🔙 Back to Welcome Settings", "adm_welcomemsg")]]
        try:
            await event.edit(f"{P_YES} <b>Welcome button removed.</b>\n\n<i>The welcome message will no longer have an attached button.</i>", buttons=btns)
        except Exception:
            await bot.send_message(chat, f"{P_YES} <b>Welcome button removed.</b>", buttons=btns)
        return

    elif action_data == "welcomephotoreset" and has_perm(uid, 'p_settings'):
        _delete_media_blob('start_photo')  # FIX: remove blob so DB stays clean
        with _db_write_lock:
            db.execute("DELETE FROM settings WHERE key='start_photo'")
            db.commit()
        btns = [[Button.inline("🔙 Back to Welcome Settings", "adm_welcomemsg")]]
        try:
            await event.edit(f"{P_YES} <b>Start photo removed.</b>\n\n<i>No photo will be sent on /start.</i>", buttons=btns)
        except Exception:
            await bot.send_message(chat, f"{P_YES} <b>Start photo removed.</b>", buttons=btns)
        return

    elif action_data == "pendingdeps" and has_perm(uid, 'p_bal'):
        return await send_pending_deposits_page(event)

    elif action_data.startswith("pdpg|") and has_perm(uid, 'p_bal'):
        try:
            page = int(action_data.split("|")[1])
        except (IndexError, ValueError):
            page = 1
        return await send_pending_deposits_page(event, page)

    elif action_data.startswith("coupons_del|") and has_perm(uid, 'p_settings'):
        _del_c = action_data.split("|",1)[1]
        with _db_write_lock:
            db.execute("DELETE FROM promo_codes WHERE code=? COLLATE NOCASE", (_del_c,))
            db.commit()
        log_admin_action_db(uid, 'coupon_deleted', None, f'code={_del_c}')
        await event.answer(f"🗑 Coupon {_del_c} deleted.", alert=True)
        return await admin_actions(FakeCbEvent(event, "coupons"))

    # ─── Feature 4: Bundle Deals ───────────────────────────────────────
    elif action_data == "bundles" and has_perm(uid, 'p_settings'):
        brows = db.execute("SELECT id,name,category,buy_qty,free_qty,active FROM bundle_deals ORDER BY id DESC").fetchall()
        msg_b = "🎁 <b>Bundle Deals</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        btns_b = []
        for bid, bname, bcat, bqty, fqty, bact in brows:
            msg_b += f"{'🟢' if bact else '🔴'} [{bid}] <b>{bname or bcat}</b>: Buy {bqty} get {fqty} free ({bcat})\n"
            btns_b.append([
                Button.inline(f"{'🔴 Disable' if bact else '🟢 Enable'} #{bid}", f"adm_bundles_toggle|{bid}"),
                Button.inline(f"🗑 #{bid}", f"adm_bundles_del|{bid}")
            ])
        if not brows: msg_b += "<i>No bundle deals yet.</i>"
        btns_b += [[Button.inline("➕ Add Bundle","adm_bundles_add")],[Button.inline("🔙 Back","adm_adminmain")]]
        try: await event.edit(msg_b, buttons=btns_b)
        except Exception: await bot.send_message(chat, msg_b, buttons=btns_b)
        return

    elif action_data == "bundles_add" and has_perm(uid, 'p_settings'):
        async with bot.conversation(uid, timeout=120) as conv:
            await conv.send_message("🎁 <b>Add Bundle</b>\n\n1/4 — Name (e.g. Fresh 3+1):")
            _bn = (await conv.get_response()).text.strip()
            await conv.send_message("2/4 — Category (Fresh / Old / Sessions):")
            _bc = (await conv.get_response()).text.strip()
            await conv.send_message("3/4 — Buy quantity (≥2):")
            _bq_r = (await conv.get_response()).text.strip()
            if not _bq_r.isdigit() or int(_bq_r)<2: return await conv.send_message("❌ Must be ≥2.")
            _bq = int(_bq_r)
            await conv.send_message("4/4 — Free quantity (≥1):")
            _fq_r = (await conv.get_response()).text.strip()
            if not _fq_r.isdigit() or int(_fq_r)<1: return await conv.send_message("❌ Must be ≥1.")
            _fq = int(_fq_r)
            with _db_write_lock:
                db.execute("INSERT INTO bundle_deals (name,category,buy_qty,free_qty,active) VALUES (?,?,?,?,1)",
                           (_bn, _bc, _bq, _fq))
                db.commit()
            log_admin_action_db(uid, 'bundle_created', None, f'{_bn}: buy={_bq} free={_fq} cat={_bc}')
            await conv.send_message(f"✅ <b>Bundle Created!</b>\n<b>{_bn}</b>: Buy {_bq} {_bc} → {_fq} FREE!")
        return

    elif action_data.startswith("bundles_toggle|") and has_perm(uid, 'p_settings'):
        _bid = int(action_data.split("|")[1])
        with _db_write_lock:
            db.execute("UPDATE bundle_deals SET active=CASE WHEN active=1 THEN 0 ELSE 1 END WHERE id=?",(_bid,))
            db.commit()
        await event.answer("✅ Bundle toggled.", alert=False)
        return await admin_actions(FakeCbEvent(event, "bundles"))

    elif action_data.startswith("bundles_del|") and has_perm(uid, 'p_settings'):
        _bid = int(action_data.split("|")[1])
        with _db_write_lock:
            db.execute("DELETE FROM bundle_deals WHERE id=?",(_bid,))
            db.commit()
        log_admin_action_db(uid, 'bundle_deleted', None, f'id={_bid}')
        await event.answer("🗑 Bundle deleted.", alert=True)
        return await admin_actions(FakeCbEvent(event, "bundles"))

    # ─── Feature 12: Sub-Admin Audit Log ──────────────────────────────
    elif action_data == "auditlog" and has_perm(uid, 'p_settings'):
        arows = db.execute(
            "SELECT id,admin_id,action,target_uid,details,created_at FROM admin_audit_log ORDER BY id DESC LIMIT 30"
        ).fetchall()
        msg_a = "📜 <b>Admin Audit Log</b>  (last 30)\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        if not arows:
            msg_a += "<i>No actions logged yet.</i>"
        else:
            for _, adm_id, action, tgt, det, ts in arows:
                ts_s = str(ts)[:16]
                tgt_s = f" → <code>{tgt}</code>" if tgt else ""
                det_s = f"  <i>{html.escape(str(det)[:40])}</i>" if det else ""
                msg_a += f"[{ts_s}] <code>{adm_id}</code> <b>{action}</b>{tgt_s}{det_s}\n"
        try: await event.edit(msg_a, buttons=[[Button.inline("🔙 Back","adm_adminmain")]])
        except Exception: await bot.send_message(chat, msg_a, buttons=[[Button.inline("🔙 Back","adm_adminmain")]])
        return

    elif action_data == "noop": return await event.answer("", alert=False)

    # ─────────────── RECOVERY PANEL — non-conversation actions ────────────────
    elif action_data == "recover" and has_perm(uid, 'p_settings'):
        btns_rec = [
            [Button.inline("📥 Download Current DB",       "adm_recover_dl_db")],
            [Button.inline("📤 Upload DB to Restore",      "adm_recover_up_db")],
            [Button.inline("📦 Download All Sessions ZIP", "adm_recover_dl_sess")],
            [Button.inline("📤 Upload Sessions ZIP",       "adm_recover_up_sess")],
            [Button.inline("📊 Backup Status",             "adm_recover_status")],
            [Button.inline("🔙 Back",                      "adm_adminmain")],
        ]
        _rec_msg = (
            "🔧 <b>Database & Session Recovery</b>\n\n"
            "⚠️ <i>Upload/restore actions overwrite current data — create a download backup first!</i>\n\n"
            "• <b>Download DB</b>       — save a copy of the live database\n"
            "• <b>Upload DB</b>         — restore a previously downloaded .db file\n"
            "• <b>Download Sessions</b> — ZIP of all .session files\n"
            "• <b>Upload Sessions</b>   — extract a sessions ZIP back to disk\n"
            "• <b>Backup Status</b>     — view auto-backup files and paths"
        )
        try: await event.edit(_rec_msg, buttons=btns_rec)
        except Exception: await bot.send_message(chat, _rec_msg, buttons=btns_rec)
        return

    elif action_data == "recover_dl_db" and has_perm(uid, 'p_settings'):
        try:
            await event.answer("📦 Preparing database file…", alert=False)
            if not os.path.exists(_database_path):
                return await event.answer("❌ Database file not found!", alert=True)
            ts_dl = datetime.now().strftime("%Y%m%d_%H%M%S")
            await bot.send_file(
                uid, _database_path,
                caption=(
                    f"📥 <b>Live Database Backup</b>\n"
                    f"<code>otp_bot_{ts_dl}.db</code>\n\n"
                    f"Use <b>📤 Upload DB to Restore</b> to restore from this file.\n"
                    f"Keep it somewhere safe!"
                ),
                force_document=True,
                attributes=[]
            )
        except Exception as _dldb_e:
            logger.error(f"recover_dl_db failed: {_dldb_e}")
            try: await event.answer("❌ Failed to send DB file.", alert=True)
            except Exception: pass
        return

    elif action_data == "recover_dl_sess" and has_perm(uid, 'p_settings'):
        try:
            await event.answer("📦 Building sessions ZIP…", alert=False)
            sess_all = [f for f in os.listdir(_sessions_dir) if os.path.isfile(os.path.join(_sessions_dir, f))]
            sess_only = [f for f in sess_all if f.endswith('.session')]
            if not sess_only:
                return await event.answer("❌ No .session files found.", alert=True)
            ts_sz = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_path_sz = os.path.join(_backups_dir, f"sessions_bkp_{ts_sz}.zip")
            with zipfile.ZipFile(zip_path_sz, 'w', zipfile.ZIP_DEFLATED) as zf_s:
                for fname_s in sess_all:
                    zf_s.write(os.path.join(_sessions_dir, fname_s), fname_s)
            await bot.send_file(
                uid, zip_path_sz,
                caption=(
                    f"📦 <b>Sessions Backup ZIP</b>\n"
                    f"{len(sess_only)} .session file(s) + WAL/SHM extras included.\n\n"
                    f"Use <b>📤 Upload Sessions ZIP</b> to restore."
                ),
                force_document=True,
                attributes=[]
            )
            try: os.remove(zip_path_sz)
            except Exception: pass
        except Exception as _dlsess_e:
            logger.error(f"recover_dl_sess failed: {_dlsess_e}")
            try: await event.answer("❌ Failed to create sessions ZIP.", alert=True)
            except Exception: pass
        return

    elif action_data == "recover_status" and has_perm(uid, 'p_settings'):
        try:
            bkp_files = sorted(
                f for f in os.listdir(_backups_dir)
                if f.startswith("otp_bot_") and f.endswith(".db")
            )
            sess_cnt = len([f for f in os.listdir(_sessions_dir) if f.endswith('.session')])
            db_size_kb = os.path.getsize(_database_path) // 1024 if os.path.exists(_database_path) else 0
            bkp_lines = "\n".join(f"  • {b}" for b in bkp_files[-5:]) or "  <i>No auto-backups yet</i>"
            msg_st = (
                f"📊 <b>Recovery Status</b>\n\n"
                f"🗄 <b>Live DB size:</b>   {db_size_kb} KB\n"
                f"📂 <b>Session files:</b>  {sess_cnt}\n\n"
                f"<b>Latest auto-backups (last 5):</b>\n{bkp_lines}\n\n"
                f"📁 <b>DB path:</b>\n<code>{_database_path}</code>\n\n"
                f"📁 <b>Sessions dir:</b>\n<code>{_sessions_dir}</code>\n\n"
                f"💾 <b>Backups dir:</b>\n<code>{_backups_dir}</code>"
            )
            try: await event.edit(msg_st, buttons=[[Button.inline("🔙 Back", "adm_recover")]])
            except Exception: await bot.send_message(chat, msg_st, buttons=[[Button.inline("🔙 Back", "adm_recover")]])
        except Exception as _rse:
            await event.answer(f"Error: {_rse}", alert=True)
        return
    # ─────────────── end non-conversation recovery ───────────────────

    # Cancel any existing admin conversation task for this user before starting a new one.
    # This allows pressing a new conversation-requiring button to cleanly abort a stuck one.
    _old_adm_task = _active_admin_conv.pop(uid, None)
    if _old_adm_task and not _old_adm_task.done():
        _old_adm_task.cancel()
        await asyncio.sleep(0.1)   # brief yield so the old task's __aexit__ can run

    try:
      conv_ctx = bot.conversation(chat, timeout=600)
    except Exception as _conv_e:
      logger.error(f'Conversation start failed: {_conv_e}')
      try: await event.answer("⚠️ Unexpected error starting action.", alert=True)
      except Exception as _e2: logger.debug(f'answer() also failed: {_e2}')
      return

    # Register the current event-handler task so /cancel can cancel it
    _current_task = asyncio.current_task()
    if _current_task:
        _active_admin_conv[uid] = _current_task

    # Dismiss the button spinner before entering the blocking conversation
    try: await event.answer()
    except Exception as _ans_e: logger.debug(f'Pre-conv event.answer() failed: {_ans_e}')

    try:
      async with conv_ctx as conv:
        async def get_reply(txt):
            await conv.send_message(txt + "\n\n<i>(Type /cancel to abort)</i>")
            resp = await conv.get_response()
            # Catch /cancel explicitly
            if resp.text and resp.text.strip().lower() == "/cancel":
                raise ValueError("Cancelled")
            # Catch ANY other bot command typed mid-conversation — abort cleanly
            if resp.text and resp.text.strip().startswith("/"):
                await conv.send_message(
                    f"⚠️ Command <code>{html.escape(resp.text.strip())}</code> received while "
                    f"an action was in progress.\n\n"
                    f"Action cancelled. Please tap the button again to restart."
                )
                raise ValueError("Cancelled by command")
            return resp

        try:
            if action_data == "ap_add_country" and has_perm(uid, 'p_manage_stock'):
                code = (await get_reply(f"{P_PHONE} <b>Enter Country Calling Code (without +):</b>\n<i>Example: 91</i>")).text.replace("+", "").strip()
                flag = html.escape((await get_reply(f"{P_FLAG} <b>Enter Country Flag Emoji:</b>\n<i>Example: 🇮🇳</i>")).text.strip())
                name = html.escape((await get_reply(f"{P_GLOBE} <b>Enter Country Name:</b>\n<i>Example: India</i>")).text.strip())
                
                with _db_write_lock:
                    db.execute("INSERT OR REPLACE INTO custom_countries (code, name, flag) VALUES (?,?,?)", (code, name, flag))
                    db.commit()
                await conv.send_message(f"{P_YES} <b>Custom Country Added Successfully!</b>\n{flag} {name} (+{code})\n\n<i>It will now automatically be recognized when adding stock!</i>")

            elif action_data == "userinfo" and has_perm(uid, 'p_userinfo', 'p_stats'):
                _r = (await get_reply(f"{P_ACC} <b>Enter User ID:</b>")).text.strip()
                if not _r.isdigit(): return await conv.send_message(f"{P_NO} User ID must be a positive number.")
                t_uid = int(_r)
                u_row = db.execute("SELECT balance, total_deposited, joined_date, banned, discount FROM users WHERE user_id=?", (t_uid,)).fetchone()
                if not u_row: return await conv.send_message(f"{P_NO} User not found.")
                
                o_row = db.execute("SELECT COUNT(*), SUM(price) FROM orders WHERE user_id=?", (t_uid,)).fetchone()
                up_row = db.execute("SELECT SUM(amount) FROM upi_orders WHERE user_id=? AND status='success'", (t_uid,)).fetchone()
                
                bal, dep, joined, is_banned, disc = u_row
                o_count = o_row[0] if o_row else 0
                o_spent = o_row[1] if o_row and o_row[1] else 0
                u_upi = up_row[0] if up_row and up_row[0] else 0
                
                msg = (f"{P_ACC} <b>USER INFO:</b> <code>{t_uid}</code>\n\n"
                       f"{P_MONEY} Balance: {P_INR}{bal}\n"
                       f"{P_CARD} Total Deposited: {P_INR}{dep}\n"
                       f"{P_UPI} UPI Deposited: {P_INR}{u_upi}\n"
                       f"{P_CART} Total Orders: {o_count}\n"
                       f"{P_USDT} Total Spent: {P_INR}{o_spent}\n"
                       f"{P_GIFT} Discount: {disc}%\n"
                       f"{P_CAL} Joined: {joined}\n"
                       f"{P_OFF} Banned: {'Yes' if is_banned else 'No'}")
                await conv.send_message(msg)

            elif action_data == "addadmin" and uid == ADMIN_ID:
                _r = (await get_reply(f"{P_ACC} <b>Enter User ID for new Admin:</b>")).text.strip()
                if not _r.isdigit(): return await conv.send_message(f"{P_NO} User ID must be a positive number.")
                new_ad = int(_r)
                with _db_write_lock:
                    db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_ad,))
                    db.commit()
                await conv.send_message(f"{P_YES} Admin added!")
                class FakeEvent:
                    # FIX Bug 3: provide sender_id and chat_id so edit_admin_menu
                    # can access event.sender_id without raising AttributeError.
                    sender_id = new_ad
                    chat_id   = chat
                    async def edit(self, text, buttons): await bot.send_message(chat, text, buttons=buttons)
                    async def answer(self, txt, alert): pass
                await edit_admin_menu(FakeEvent(), new_ad)
                

            elif action_data.startswith("msedit|") and has_perm(uid, 'p_manage_stock'):
                parts = action_data.split("|", 3)
                if len(parts) < 3:
                    return await conv.send_message(f"{P_NO} Invalid action. Please try again.")
                action, c_name = parts[1], parts[2]
                
                if action == "name":
                    new_name = html.escape((await get_reply(f"{P_DOC} <b>Enter NEW Name for {c_name}:</b>")).text)
                    with _db_write_lock:
                        db.execute("UPDATE stock SET country_name=? WHERE country_name=?", (new_name, c_name))
                        db.execute("UPDATE auto_prices SET country=? WHERE country=?", (new_name, c_name))
                        db.commit()
                    await conv.send_message(f"{P_YES} Country '{c_name}' successfully renamed to '{new_name}'!")
                    
                elif action == "flag":
                    new_flag = html.escape((await get_reply(f"{P_FLAG} <b>Enter NEW Flag Emoji for {c_name}:</b>")).text)
                    with _db_write_lock:
                        db.execute("UPDATE stock SET country_icon=? WHERE country_name=?", (new_flag, c_name))
                        db.commit()
                    await conv.send_message(f"{P_YES} Flag updated to {new_flag} for '{c_name}'!")
                    
                elif action == "cprice":
                    _r = (await get_reply(f"{P_MONEY} <b>Enter NEW Common Price for all {c_name} accounts:</b>")).text.strip()
                    if not _r.isdigit() or int(_r) <= 0: return await conv.send_message(f"{P_NO} Price must be a positive number.")
                    new_p = int(_r)
                    with _db_write_lock:
                        db.execute("UPDATE stock SET price=? WHERE country_name=?", (new_p, c_name))
                        db.commit()
                    await conv.send_message(f"{P_YES} All existing '{c_name}' accounts updated to {P_INR}{new_p}!")
                    
                elif action == "yprice":
                    year = parts[3]
                    _r = (await get_reply(f"{P_MONEY} <b>Enter NEW Price for {c_name} ({year}):</b>")).text.strip()
                    if not _r.isdigit() or int(_r) <= 0: return await conv.send_message(f"{P_NO} Price must be a positive number.")
                    new_p = int(_r)
                    with _db_write_lock:
                        db.execute("UPDATE stock SET price=? WHERE country_name=? AND account_year=?", (new_p, c_name, int(year)))
                        db.commit()
                    await conv.send_message(f"{P_YES} All existing '{c_name}' ({year}) accounts updated to {P_INR}{new_p}!")

                elif action == "bulk_price_adj":
                    _pct_resp = (await get_reply(
                        f"📊 <b>Bulk % Price Adjust — {c_name}</b>\n\n"
                        f"Enter a percentage to <b>increase</b> (e.g. <code>+10</code>) or "
                        f"<b>decrease</b> (e.g. <code>-15</code>) all prices for this country.\n\n"
                        f"<i>Example: +10 makes ₹100 → ₹110 | -20 makes ₹100 → ₹80</i>\n"
                        f"Send /cancel to abort."
                    )).text.strip()
                    if _pct_resp == "/cancel":
                        return await conv.send_message(f"{P_NO} Cancelled.")
                    _sign = 1 if not _pct_resp.startswith("-") else -1
                    _pct_clean = _pct_resp.lstrip("+-")
                    if not _pct_clean.isdigit() or not (1 <= int(_pct_clean) <= 100):
                        return await conv.send_message(f"{P_NO} Enter a valid % like +10 or -20 (1-100).")
                    _pct_val = _sign * int(_pct_clean)
                    _all_prices = db.execute("SELECT DISTINCT price FROM stock WHERE country_name=?", (c_name,)).fetchall()
                    with _db_write_lock:
                        for (_old_p,) in _all_prices:
                            _new_p = max(1, int(_old_p * (100 + _pct_val) / 100))
                            db.execute("UPDATE stock SET price=? WHERE country_name=? AND price=?", (_new_p, c_name, _old_p))
                        db.commit()
                    _sign_sym = "+" if _pct_val > 0 else ""
                    await conv.send_message(
                        f"{P_YES} <b>Bulk Price Updated!</b>\n\n"
                        f"🌍 {c_name}: all prices adjusted by <b>{_sign_sym}{_pct_val}%</b>\n"
                        f"📦 {len(_all_prices)} price tier(s) updated."
                    )

                elif action == "wishlist_country":
                    _wl_rows = db.execute("SELECT user_id FROM wishlist WHERE country_name=?", (c_name,)).fetchall()
                    _wl_count = len(_wl_rows)
                    if not _wl_rows:
                        return await conv.send_message(f"📋 No users have wishlisted <b>{c_name}</b> yet.")
                    _wl_ids = ", ".join(f"<code>{r[0]}</code>" for r in _wl_rows[:20])
                    await conv.send_message(
                        f"🔔 <b>Wishlist — {c_name}</b>\n\n"
                        f"👥 <b>{_wl_count}</b> user(s) waiting for stock:\n{_wl_ids}"
                        + ("\n<i>...and more</i>" if _wl_count > 20 else "")
                    )

                elif action == "toggle_autoprice":
                    cur = is_auto_price_enabled()
                    new_val = '0' if cur else '1'
                    with _db_write_lock:
                        db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('auto_price_enabled', ?)", (new_val,))
                        db.commit()
                    state_str = "🟢 ON" if not cur else "🔴 OFF"
                    await event.answer(f"Auto-Detect Price is now {state_str}", alert=True)
                    return await send_manage_stock_country(event, c_name)

                elif action == "aphprice":
                    # ── Single account price — show full list ordered by year ────
                    all_accs = db.execute(
                        "SELECT phone, account_year, price, category, available FROM stock "
                        "WHERE country_name=? AND available=1 ORDER BY account_year DESC, phone LIMIT 25",
                        (c_name,)
                    ).fetchall()

                    if not all_accs:
                        return await conv.send_message(f"{P_NO} No accounts found in stock for <b>{c_name}</b>.")

                    lines_msg = [
                        f"🎯 <b>Single Account Price — {c_name}</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"Select an account to change its price:\n"
                    ]
                    for _i, (_p, _y, _pr2, _cat, _av) in enumerate(all_accs, 1):
                        _av_icon = "✅" if _av else "🔴"
                        _badge = get_cat_badge(_cat)
                        _y_disp = str(_y) if _y and int(_y) > 2000 else "Unknown"
                        lines_msg.append(
                            f"{_i}. {_av_icon} <code>+{_p}</code>  "
                            f"📅 <b>{_y_disp}</b>  {_badge}  {P_INR}{_pr2}"
                        )
                    if len(all_accs) == 25:
                        lines_msg.append("\n<i>Showing first 25. Send /cancel to abort.</i>")
                    lines_msg.append("\n\nReply with the <b>number</b> of the account, or /cancel to abort.")

                    _sel = await get_reply("\n".join(lines_msg))
                    sel_text = _sel.text.strip()
                    if sel_text == "/cancel":
                        return await conv.send_message(f"{P_NO} Cancelled.")
                    if not sel_text.isdigit() or not (1 <= int(sel_text) <= len(all_accs)):
                        return await conv.send_message(
                            f"{P_NO} Invalid selection. Enter a number between 1 and {len(all_accs)}."
                        )

                    _aph_phone, _aph_year, _aph_cur_price, _aph_cat, _aph_avail = all_accs[int(sel_text) - 1]
                    _aph_avail_text = "✅ Available" if _aph_avail else "🔴 Sold/Unavailable"
                    _aph_badge = get_cat_badge(_aph_cat)
                    _aph_y_disp = str(_aph_year) if _aph_year and int(_aph_year) > 2000 else "Unknown"

                    _pr = (await get_reply(
                        f"📱 <b>Account Selected:</b>\n\n"
                        f"📞 Phone: <code>+{_aph_phone}</code>\n"
                        f"📅 Year: <b>{_aph_y_disp}</b>\n"
                        f"🏷 Category: {_aph_badge}\n"
                        f"💰 Current Price: <b>{P_INR}{_aph_cur_price}</b>\n"
                        f"📦 Status: {_aph_avail_text}\n\n"
                        f"Enter the <b>new price</b> (₹, numbers only):"
                    )).text.strip()
                    if not _pr.isdigit() or int(_pr) <= 0:
                        return await conv.send_message(f"{P_NO} Price must be a positive number. No changes made.")
                    _aph_new_price = int(_pr)
                    with _db_write_lock:
                        db.execute("UPDATE stock SET price=? WHERE phone=?", (_aph_new_price, _aph_phone))
                        db.commit()
                    await conv.send_message(
                        f"{P_YES} <b>Price Updated!</b>\n\n"
                        f"📞 <code>+{_aph_phone}</code>\n"
                        f"📅 Year: <b>{_aph_y_disp}</b>\n"
                        f"💰 {P_INR}{_aph_cur_price} → <b>{P_INR}{_aph_new_price}</b>"
                    )

                elif action == "rmyear":
                    if len(parts) < 4:
                        return await conv.send_message(f"{P_NO} Missing year parameter. Please try again.")
                    year = parts[3]
                    cnt = db.execute("SELECT COUNT(*) FROM stock WHERE country_name=? AND account_year=?", (c_name, year)).fetchone()[0]
                    confirm = (await get_reply(
                        f"{P_WARN} <b>Remove Stock — {c_name} ({year})</b>\n\n"
                        f"This will permanently delete <b>{cnt} account(s)</b> from stock.\n\n"
                        f"Type <code>YES</code> to confirm or anything else to cancel."
                    )).text.strip()
                    if confirm.upper() != "YES":
                        return await conv.send_message(f"{P_NO} Cancelled. No accounts removed.")
                    sessions_to_del = db.execute("SELECT session_file FROM stock WHERE country_name=? AND account_year=?", (c_name, int(year))).fetchall()
                    with _db_write_lock:
                        db.execute("DELETE FROM stock WHERE country_name=? AND account_year=?", (c_name, int(year)))
                        db.commit()
                    for (sf,) in sessions_to_del:
                        if sf:
                            try: delete_session_files(sf)
                            except Exception as _e:
                                logger.debug(f'Suppressed non-critical error: {_e}')
                    remaining = db.execute("SELECT COUNT(*) FROM stock WHERE country_name=?", (c_name,)).fetchone()[0]
                    if remaining == 0:
                        with _db_write_lock:
                            db.execute("DELETE FROM auto_prices WHERE country=?", (c_name,))
                            db.commit()
                    await conv.send_message(f"{P_YES} Removed <b>{cnt}</b> account(s) for <b>{c_name} ({year})</b> from stock.")

                elif action == "rmall":
                    cnt = db.execute("SELECT COUNT(*) FROM stock WHERE country_name=?", (c_name,)).fetchone()[0]
                    confirm = (await get_reply(
                        f"⚠️ <b>Remove ALL Stock — {c_name}</b>\n\n"
                        f"This will permanently delete <b>ALL {cnt} account(s)</b> across all years for <b>{c_name}</b>.\n\n"
                        f"Type <code>YES</code> to confirm or anything else to cancel."
                    )).text.strip()
                    if confirm.upper() != "YES":
                        return await conv.send_message(f"{P_NO} Cancelled. No accounts removed.")
                    sessions_to_del = db.execute("SELECT session_file FROM stock WHERE country_name=?", (c_name,)).fetchall()
                    with _db_write_lock:
                        db.execute("DELETE FROM stock WHERE country_name=?", (c_name,))
                        db.execute("DELETE FROM auto_prices WHERE country=?", (c_name,))
                        db.commit()
                    for (sf,) in sessions_to_del:
                        if sf:
                            try: delete_session_files(sf)
                            except Exception as _e:
                                logger.debug(f'Suppressed non-critical error: {_e}')
                    await conv.send_message(f"{P_YES} Removed all <b>{cnt}</b> account(s) for <b>{c_name}</b> from stock.\n\n<i>Auto-prices for {c_name} have also been cleared.</i>")
                    
            elif action_data == "setupi_qr" and has_perm(uid, 'p_payments', 'p_settings'):
                qr_msg = await get_reply("📸 <b>Send the UPI QR Code Image:</b>\n<i>(Or type <code>skip</code> to remove the current QR)</i>")
                if qr_msg.text and qr_msg.text.lower() == 'skip':
                    old = db.execute("SELECT value FROM settings WHERE key='upi_qr_file_id'").fetchone()
                    if old and old[0] and os.path.exists(old[0]):
                        try: os.remove(old[0])
                        except Exception as _e:
                            logger.debug(f'Suppressed non-critical error: {_e}')
                    with _db_write_lock:
                        db.execute("DELETE FROM settings WHERE key='upi_qr_file_id'")
                        db.commit()
                    _delete_media_blob('upi_qr')
                    await conv.send_message(f"{P_YES} UPI QR removed.")
                elif qr_msg.photo:
                    # FIX: store bytes in DB blob — survives Termux restarts
                    _img_bytes = await _read_photo_bytes(qr_msg)
                    if _img_bytes:
                        _save_media_blob('upi_qr', _img_bytes)
                        qr_path = f"upi_qr_{int(time.time())}.jpg"
                        try:
                            with open(qr_path, 'wb') as _f: _f.write(_img_bytes)
                        except Exception as _e:
                            logger.debug(f'UPI QR local file write failed (non-critical): {_e}')
                            qr_path = ''
                        old = db.execute("SELECT value FROM settings WHERE key='upi_qr_file_id'").fetchone()
                        if old and old[0] and os.path.exists(old[0]):
                            try: os.remove(old[0])
                            except Exception as _e:
                                logger.debug(f'Suppressed non-critical error: {_e}')
                        with _db_write_lock:
                            db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('upi_qr_file_id', ?)", (qr_path,))
                            db.commit()
                        await conv.send_message(f"{P_YES} UPI QR image saved! It will now be shown to users when they deposit via UPI.")
                    else:
                        await conv.send_message(f"{P_NO} Failed to read the image. Please try again.")
                else:
                    await conv.send_message(f"{P_NO} Please send an image or type 'skip'.")
            elif action_data == "upi_setid" and has_perm(uid, 'p_payments', 'p_settings'):
                cur_upi = (db.execute("SELECT value FROM settings WHERE key='upi_id'").fetchone() or [UPI_ID])[0]
                new_upi = (await get_reply(f"🏦 <b>Enter New UPI ID:</b>\n<i>Current: <code>{cur_upi}</code></i>\n\n<i>Example: yourname@bank</i>")).text.strip()
                with _db_write_lock:
                    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('upi_id', ?)", (new_upi,))
                    db.commit()
                await conv.send_message(f"{P_YES} UPI ID updated!\n<code>{new_upi}</code>\n\n<i>New QR codes will use this UPI ID.</i>")

            elif action_data == "hlk_setkey" and has_perm(uid, 'p_payments', 'p_settings'):
                cur_key = (db.execute("SELECT value FROM settings WHERE key='cwallet_api_key'").fetchone() or [''])[0]
                cur_disp = f"{cur_key[:6]}…{cur_key[-4:]}" if len(cur_key) > 10 else (cur_key or "Not set")
                new_key = (await get_reply(
                    f"🔑 <b>Enter CWallet API Key:</b>\n"
                    f"<i>Current: <code>{cur_disp}</code></i>\n\n"
                    f"Only enter a credential supplied by Cwallet for the payment/API product you are using.\n"
                    f"<b>Do not use a Giveaway callback API key.</b>"
                )).text.strip()
                with _db_write_lock:
                    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('cwallet_api_key', ?)", (new_key,))
                    db.commit()
                await conv.send_message(f"{P_YES} CWallet API Key saved!\n<code>{new_key[:6]}…</code>")

            elif action_data == "hlk_setcoin" and has_perm(uid, 'p_payments', 'p_settings'):
                coin_resp = await get_reply(
                    "💲 <b>Set CWallet Coin & Network</b>\n\n"
                    "Enter coin and network separated by space:\n"
                    "<code>USDT trc20</code> — USDT on TRON (default)\n"
                    "<code>USDT erc20</code> — USDT on Ethereum\n"
                    "<code>TRX trc20</code> — TRX\n"
                    "<code>BTC bitcoin</code> — Bitcoin\n\n"
                    "Example: <code>USDT trc20</code>"
                )
                parts_coin = coin_resp.text.strip().split()
                if len(parts_coin) >= 2:
                    new_coin = parts_coin[0].upper()
                    new_net = parts_coin[1].lower()
                    with _db_write_lock:
                        db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('cwallet_coin', ?)", (new_coin,))
                        db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('cwallet_network', ?)", (new_net,))
                        db.commit()
                    await conv.send_message(f"{P_YES} CWallet coin set to <b>{new_coin}</b> on <b>{new_net}</b>!")
                else:
                    await conv.send_message(f"{P_NO} Invalid format. Please enter like: <code>USDT trc20</code>")

            elif action_data == "hlk_setbonus" and has_perm(uid, 'p_payments', 'p_settings'):
                cur_bonus = (db.execute("SELECT value FROM settings WHERE key='cwallet_bonus_pct'").fetchone() or ['0'])[0]
                bonus_resp = (await get_reply(
                    f"🎁 <b>Enter CWallet Bonus Percentage:</b>\n"
                    f"<i>Current: {cur_bonus}% — Enter 0 to disable bonus</i>"
                )).text.strip()
                new_bonus = int(re.sub(r'[^\d]', '', bonus_resp) or '0')
                with _db_write_lock:
                    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('cwallet_bonus_pct', ?)", (str(new_bonus),))
                    db.commit()
                await conv.send_message(f"{P_YES} CWallet Bonus set to <b>{new_bonus}%</b>!")

            elif action_data == "addpay" and has_perm(uid, 'p_payments', 'p_settings'):
                name = html.escape((await get_reply(f"{P_CARD} <b>Enter Payment Method Name:</b>\n<i>(e.g., Binance Pay, TRX)</i>")).text)
                qr_msg = await get_reply("📸 <b>Send QR Code Image:</b>\n<i>(Or type <code>skip</code> if no QR needed)</i>")
                qr_path = ""
                _custom_img_bytes = None
                if qr_msg.photo:
                    # FIX: read into memory and store in DB blob
                    _custom_img_bytes = await _read_photo_bytes(qr_msg)
                    if _custom_img_bytes:
                        qr_path = f"qr_{int(time.time())}.jpg"
                        try:
                            with open(qr_path, 'wb') as _f: _f.write(_custom_img_bytes)
                        except Exception as _e:
                            logger.debug(f'Custom QR local file write failed (non-critical): {_e}')
                            qr_path = ''
                cap_msg = (await get_reply(f"{P_DOC} <b>Enter Payment Caption:</b>\n<i>(Use <code>text</code> to make wallet IDs or UPI copyable)</i>")).text
                cap_msg = html.escape(cap_msg).replace("&lt;code&gt;", "<code>").replace("&lt;/code&gt;", "</code>")
                with _db_write_lock:
                    db.execute("INSERT INTO custom_payments (name, caption, qr_file_id) VALUES (?,?,?)", (name, cap_msg, qr_path))
                    db.commit()
                # Store bytes in media_cache so QR survives restarts
                if _custom_img_bytes:
                    _save_media_blob(f'custom_pay_qr_{name}', _custom_img_bytes)
                await conv.send_message(f"{P_YES} Payment Method '{name}' added successfully!")
            elif action_data == "delpay" and has_perm(uid, 'p_payments', 'p_settings'):
                rows = db.execute("SELECT id, name FROM custom_payments").fetchall()
                if not rows: return await conv.send_message(f"{P_NO} No custom payment methods.")
                msg = f"{P_DOC} <b>Reply with the ID of the method to delete:</b>\n\n"
                for r in rows: msg += f"ID: {r[0]} - {r[1]}\n"
                del_id = (await get_reply(msg)).text
                try:
                    del_id = int(del_id)
                    pay_row = db.execute("SELECT name, qr_file_id FROM custom_payments WHERE id=?", (del_id,)).fetchone()
                    if pay_row:
                        _del_name, _del_qr = pay_row
                        # Remove legacy local file
                        if _del_qr and os.path.exists(_del_qr):
                            try: os.remove(_del_qr)
                            except Exception as _e: logger.debug(f'QR file remove failed: {_e}')
                        # Remove DB blob (FIX: was previously orphaned)
                        _delete_media_blob(f'custom_pay_qr_{_del_name}')
                    with _db_write_lock:
                        db.execute("DELETE FROM custom_payments WHERE id=?", (del_id,))
                        db.commit()
                    await conv.send_message(f"{P_YES} Deleted!")
                except Exception as _e:
                    logger.warning(f"custom_payment delete failed: {_e}")
                    await conv.send_message(f"{P_NO} Invalid ID.")

            elif action_data == "addzip" and has_perm(uid, 'p_add_stock'):
                resp = await get_reply(f"{P_PKG} <b>Send the ZIP file containing <code>.session</code> files:</b>")
                if not resp.file or not resp.file.name.endswith('.zip'): return await conv.send_message(f"{P_NO} Invalid file.")
                _ZIP_MAX_MB = 50
                _ZIP_MAX_BYTES = _ZIP_MAX_MB * 1024 * 1024
                if resp.file.size and resp.file.size > _ZIP_MAX_BYTES:
                    return await conv.send_message(f"{P_NO} ZIP too large! Max allowed: {_ZIP_MAX_MB} MB. Got: {resp.file.size // (1024*1024)} MB.")
                await conv.send_message(f"{P_WAIT} <b>Extracting & Scanning Accounts...</b>")
                zip_path = None
                extracted_dir = os.path.join(
                    _data_dir, f"temp_extracted_{int(time.time())}"
                )
                try:
                    zip_path = await bot.download_media(
                        resp, os.path.join(_data_dir, "temp_sessions.zip")
                    )
                    os.makedirs(extracted_dir, exist_ok=True)
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        _safe_extract_zip(zip_ref, extracted_dir)
                except Exception as _zip_err:
                    await conv.send_message(f"{P_NO} Failed to extract ZIP: {html.escape(str(_zip_err))}")
                    if zip_path and os.path.exists(zip_path):
                        try: os.remove(zip_path)
                        except Exception: pass
                    if os.path.exists(extracted_dir):
                        try: shutil.rmtree(extracted_dir)
                        except Exception: pass
                    return

                groups = {}
                for file in os.listdir(extracted_dir):
                    if not file.endswith(".session"): continue
                    sess_path = os.path.join(extracted_dir, file)
                    clean_path = sess_path[:-8]
                    client = TelegramClient(clean_path, API_ID, API_HASH)
                    try:
                        await client.connect()
                        if not await client.is_user_authorized(): continue
                        me = await client.get_me()
                        phone = getattr(me, 'phone', None)
                        if not phone: continue
                        
                        c_name, c_icon = get_country_info(phone)
                        pwd = await client(GetPasswordRequest())
                        has_2fa = pwd.has_password
                        year = await detect_account_year(client)

                        # Auto-classify: year <= 2024 → Old, 2025+ → Fresh, 0 → unknown
                        # FIX Bug 9: handle year==0 explicitly so unknown-year accounts are
                        # not silently mislabelled as Old via the else-branch fall-through.
                        if year == 0:
                            logger.warning(f"detect_account_year returned 0 for phone={phone}; defaulting to Old")
                            auto_cat = 'Old'
                        elif year > 2024:
                            auto_cat = 'Fresh'
                        else:
                            auto_cat = 'Old'
                        key = (c_name, year, auto_cat, has_2fa)
                        if key not in groups: groups[key] = []
                        groups[key].append({"phone": phone, "path": clean_path, "c_icon": c_icon})
                    except Exception as scan_err:
                        logger.error(f"Scan error: {scan_err}")
                    finally:
                        # FIX: always disconnect regardless of success or error
                        try: await client.disconnect()
                        except Exception as _e:
                            logger.debug(f'Suppressed non-critical error: {_e}')

                for key in list(groups.keys()):
                    if key[0] == "Unknown":
                        sample_phone = groups[key][0]["phone"]
                        await conv.send_message(f"{P_WARN} <b>Country not recognized for +{sample_phone}!</b>")
                        new_icon = html.escape((await get_reply(f"{P_FLAG} <b>Enter Country Flag Emoji:</b>\n<i>Example: 🇮🇳</i>")).text)
                        new_name = html.escape((await get_reply(f"{P_GLOBE} <b>Enter Country Name:</b>\n<i>Example: India</i>")).text)
                        new_key = (new_name, key[1], key[2], key[3])
                        groups[new_key] = groups.pop(key)
                        for acc in groups[new_key]: acc["c_icon"] = new_icon

                success = 0
                for (c_name, year, category, has_2fa), accs in groups.items():
                    c_icon = accs[0]["c_icon"]
                    twofa_pass = "None"
                    cat_badge = get_cat_badge(category)
                    if has_2fa: twofa_pass = html.escape((await get_reply(f"{P_2FA} <b>Enter 2FA Password for {len(accs)}x {c_name} ({year}, {cat_badge}) accounts:</b>")).text)

                    # Always ask admin to confirm/enter price (auto-price shown as hint if enabled)
                    _hint_price = get_auto_price(c_name, year, category) if is_auto_price_enabled() else None
                    _hint_str = f" [Auto-price: {P_INR}{_hint_price}]" if _hint_price else ""
                    _r = (await get_reply(
                        f"📌 Found {len(accs)}x {c_name} ({year}, {cat_badge}).{_hint_str}\n"
                        f"{P_MONEY} Enter Price (₹) for this group:"
                    )).text.strip()
                    if not _r.isdigit() or int(_r) <= 0:
                        return await conv.send_message(f"{P_NO} Price must be a positive number.")
                    price = int(_r)

                    with _db_write_lock:
                        for acc in accs:
                            perm_base = os.path.join(_sessions_dir, str(acc['phone']))
                            for ext in ['.session', '.session-wal', '.session-shm', '.session-journal']:
                                if os.path.exists(acc['path'] + ext): shutil.move(acc['path'] + ext, perm_base + ext)
                            db.execute(
                                "INSERT OR REPLACE INTO stock (phone, session_file, country_name, country_icon, account_year, category, price, available, twofa) VALUES (?,?,?,?,?,?,?,?,?)",
                                (acc['phone'], perm_base + ".session", c_name, c_icon, year, category, price, 1, twofa_pass)
                            )
                            success += 1
                        db.commit()
                await conv.send_message(f"{P_YES} <b>Bulk Upload Complete!</b>\n{P_ON} Added: <b>{success}</b> accounts\n🟢 Fresh auto-tagged for year ≥ 2025, 🟡 Old for ≤ 2024.")
                # Notify wishlist users for each country in this batch
                for _wl_c in set(acc_group_key[0] for acc_group_key in groups.keys()):
                    asyncio.create_task(notify_wishlist_users(_wl_c))
                try: os.remove(zip_path)
                except Exception as _e:
                    logger.debug(f'Suppressed non-critical error: {_e}')
                try: shutil.rmtree(extracted_dir)
                except Exception as _e:
                    logger.debug(f'Suppressed non-critical error: {_e}')

            elif action_data == "addstock" and has_perm(uid, 'p_add_stock'):
                phone = (await get_reply(f"{P_PHONE} Enter Phone (+919999...):")).text.replace(" ", "").replace("+", "")
                sp = os.path.join(_sessions_dir, str(phone))
                client = TelegramClient(sp, API_ID, API_HASH)
                try:
                    await client.connect()
                    sreq = await client.send_code_request(phone)
                    
                    twofa_pass = "None"
                    try: 
                        await client.sign_in(phone, (await get_reply(f"{P_OTP} OTP:")).text, phone_code_hash=sreq.phone_code_hash)
                    except SessionPasswordNeededError: 
                        twofa_pass = html.escape((await get_reply(f"{P_2FA} 2FA Pass required. Enter it now:")).text)
                        await client.sign_in(password=twofa_pass)
                    
                    c_name, c_icon = get_country_info(phone)
                    
                    if c_name == "Unknown":
                        await conv.send_message(f"{P_WARN} <b>Country not recognized for +{phone}!</b>")
                        c_icon = html.escape((await get_reply(f"{P_FLAG} <b>Enter Country Flag Emoji:</b>\n<i>Example: 🇮🇳</i>")).text)
                        c_name = html.escape((await get_reply(f"{P_GLOBE} <b>Enter Country Name:</b>\n<i>Example: India</i>")).text)
                    
                    auto_year = await detect_account_year(client)
                finally:
                    try: await client.disconnect()
                    except Exception as _e:
                        logger.debug(f'Suppressed non-critical error: {_e}')
                
                _r = (await get_reply(f"{P_CAL} Detected Year: <b>{auto_year}</b>\nReply with the year to confirm or change (e.g. <code>2021</code>):")).text.strip()
                if not _r.isdigit(): return await conv.send_message(f"{P_NO} Year must be a number (e.g. 2023).")
                year = int(_r)

                # Auto-suggest category based on year, but let admin override
                auto_cat_suggest = "old" if year <= 2024 else "fresh"
                auto_cat_badge   = "🟡 Old" if year <= 2024 else "🟢 Fresh"
                cat_reply = (await get_reply(
                    f"📂 <b>Account Category</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Auto-detected: <b>{auto_cat_badge}</b> (based on year {year})\n\n"
                    f"Options: <code>fresh</code> 🟢  |  <code>cheap</code> 💸  |  <code>old</code> 🟡\n"
                    f"         <code>spam</code> 🔴  |  <code>rare</code> 💎  |  <code>change</code> 🔄\n"
                    f"<i>(or just send any other text to keep auto-suggestion)</i>"
                )).text.strip().lower()
                # Accept plain-text replies matching any category name or shorthand
                _cat_reply_lc = cat_reply.strip().lower()
                if _cat_reply_lc == 'old':
                    category = 'Old'
                elif _cat_reply_lc in ('good', 'fresh'):
                    category = 'Fresh'
                elif _cat_reply_lc == 'cheap':
                    category = 'Cheap'
                elif _cat_reply_lc == 'spam':
                    category = 'Spam'
                elif _cat_reply_lc == 'rare':
                    category = 'Rare'
                elif _cat_reply_lc in ('number change', 'change'):
                    category = 'Number Change'
                else:
                    category = 'Fresh' if auto_cat_suggest == 'fresh' else 'Old'
                cat_badge = get_cat_badge(category)

                # Always ask admin to enter price (auto-price shown as hint if enabled)
                _hint_price = get_auto_price(c_name, year, category) if is_auto_price_enabled() else None
                _hint_str = f"  [Auto-price hint: {P_INR}{_hint_price}]" if _hint_price else ""
                _r = (await get_reply(
                    f"{P_MONEY} <b>Enter Price (₹) for this account:</b>{_hint_str}\n"
                    f"<i>{c_name} — {year} — {cat_badge}</i>"
                )).text.strip()
                if not _r.isdigit() or int(_r) <= 0:
                    return await conv.send_message(f"{P_NO} Price must be a positive number.")
                price = int(_r)

                with _db_write_lock:
                    db.execute(
                        "INSERT OR REPLACE INTO stock (phone, session_file, country_name, country_icon, account_year, category, price, available, twofa) VALUES (?,?,?,?,?,?,?,?,?)",
                        (phone, sp + ".session", c_name, c_icon, year, category, price, 1, twofa_pass)
                    )
                    db.commit()
                asyncio.create_task(notify_wishlist_users(c_name))
                asyncio.create_task(check_low_stock_alert(c_name))
                await conv.send_message(
                    f"{P_YES} <b>Account Added!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📱 Phone: <code>+{phone}</code>\n"
                    f"🌍 Country: {c_icon} {c_name}\n"
                    f"📅 Year: {year}\n"
                    f"📂 Category: {cat_badge}\n"
                    f"💰 Price: {P_INR}{price}"
                )

            elif action_data == "supporturl" and has_perm(uid, 'p_settings'):
                url = (await get_reply("🔗 Enter new Support URL (must start with http:// or https://):")).text
                if not url.startswith("http"): url = "https://" + url.replace("@", "t.me/")
                with _db_write_lock:
                    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('support_url', ?)", (url,))
                    db.commit()
                await conv.send_message(f"{P_YES} Support URL updated.")

            elif action_data == "activitylog" and has_perm(uid, 'p_settings'):
                cur_ch = get_activity_log_channel()
                _explicit = db.execute("SELECT value FROM settings WHERE key='activity_log_channel'").fetchone()
                cur_text = f"<code>{cur_ch}</code>" if (_explicit and _explicit[0]) else f"<i>Using default: <code>{USER_INFO_CHANNEL_ID}</code></i>"
                resp = (await get_reply(
                    f"📋 <b>Activity Log Channel</b>\n\n"
                    f"Current: {cur_text}\n\n"
                    f"Send the <b>Channel ID</b> where user activity (starts, new users) will be logged.\n"
                    f"It must start with <code>-100</code> (e.g. <code>-1001234567890</code>).\n\n"
                    f"⚠️ Make sure this bot is an <b>admin</b> in that channel.\n\n"
                    f"Type <code>remove</code> to disable activity logging."
                )).text.strip()
                if resp.lower() == "remove":
                    with _db_write_lock:
                        db.execute("DELETE FROM settings WHERE key='activity_log_channel'")
                        db.commit()
                    await conv.send_message(f"{P_YES} Activity log channel removed. User activity will no longer be logged.")
                elif resp.lstrip('-').isdigit():
                    with _db_write_lock:
                        db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('activity_log_channel', ?)", (resp,))
                        db.commit()
                    await conv.send_message(
                        f"{P_YES} <b>Activity Log Channel set!</b>\n\n"
                        f"📋 Channel ID: <code>{resp}</code>\n\n"
                        f"<i>Every time a user starts the bot, a log entry will be sent there.</i>"
                    )
                else:
                    await conv.send_message(f"{P_NO} Invalid ID. Must be a number like <code>-1001234567890</code> or type <code>remove</code>.")

            elif action_data == "paymentlog" and has_perm(uid, 'p_settings'):
                cur_ch = get_payment_log_channel()
                _explicit_pay = db.execute("SELECT value FROM settings WHERE key='payment_log_channel'").fetchone()
                cur_text = f"<code>{cur_ch}</code>" if (_explicit_pay and _explicit_pay[0]) else f"<i>Using default: <code>{PAYMENT_LOG_CHANNEL_ID}</code></i>"
                resp = (await get_reply(
                    f"💸 <b>Payment Log Channel</b>\n\n"
                    f"Current: {cur_text}\n\n"
                    f"This channel receives <b>deposit requests, approvals, and rejections</b>.\n\n"
                    f"Send the <b>Channel ID</b> (must start with <code>-100</code>).\n"
                    f"⚠️ Make sure this bot is an <b>admin</b> in that channel.\n\n"
                    f"Type <code>remove</code> to revert to the default hardcoded channel."
                )).text.strip()
                if resp.lower() == "remove":
                    with _db_write_lock:
                        db.execute("DELETE FROM settings WHERE key='payment_log_channel'")
                        db.commit()
                    await conv.send_message(f"{P_YES} Payment log channel reset to default.")
                elif resp.lstrip('-').isdigit():
                    with _db_write_lock:
                        db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('payment_log_channel', ?)", (resp,))
                        db.commit()
                    await conv.send_message(
                        f"{P_YES} <b>Payment Log Channel set!</b>\n\n"
                        f"💸 Channel ID: <code>{resp}</code>\n\n"
                        f"<i>All deposits, approvals and rejections will be logged there.</i>"
                    )
                else:
                    await conv.send_message(f"{P_NO} Invalid ID. Must be a number like <code>-1001234567890</code> or type <code>remove</code>.")

            elif action_data == "purchaselog" and has_perm(uid, 'p_settings'):
                cur_ch = get_purchase_log_channel()
                _explicit_pur = db.execute("SELECT value FROM settings WHERE key='purchase_log_channel'").fetchone()
                cur_text = f"<code>{cur_ch}</code>" if (_explicit_pur and _explicit_pur[0]) else f"<i>Using default: <code>{PURCHASE_LOG_CHANNEL_ID}</code></i>"
                resp = (await get_reply(
                    f"🛒 <b>Purchase Log Channel</b>\n\n"
                    f"Current: {cur_text}\n\n"
                    f"This channel receives logs for every <b>account or session purchase</b> made by users.\n\n"
                    f"Send the <b>Channel ID</b> (must start with <code>-100</code>).\n"
                    f"⚠️ Make sure this bot is an <b>admin</b> in that channel.\n\n"
                    f"Type <code>remove</code> to revert to the default hardcoded channel."
                )).text.strip()
                if resp.lower() == "remove":
                    with _db_write_lock:
                        db.execute("DELETE FROM settings WHERE key='purchase_log_channel'")
                        db.commit()
                    await conv.send_message(f"{P_YES} Purchase log channel reset to default.")
                elif resp.lstrip('-').isdigit():
                    with _db_write_lock:
                        db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('purchase_log_channel', ?)", (resp,))
                        db.commit()
                    await conv.send_message(
                        f"{P_YES} <b>Purchase Log Channel set!</b>\n\n"
                        f"🛒 Channel ID: <code>{resp}</code>\n\n"
                        f"<i>All account and session purchases will be logged there.</i>"
                    )
                else:
                    await conv.send_message(f"{P_NO} Invalid ID. Must be a number like <code>-1001234567890</code> or type <code>remove</code>.")

            elif action_data == "fjadd" and has_perm(uid, 'p_forcejoin', 'p_settings'):
                type_resp = (await get_reply(
                    "📢 <b>Add Force Join / Start Entry</b>\n\n"
                    "What type are you adding? Send one of:\n\n"
                    "• <code>channel</code> — force join a Telegram channel\n"
                    "• <code>group</code> — force join a supergroup\n"
                    "• <code>bot</code> — force start another bot"
                )).text.strip().lower()
                if type_resp not in ('channel', 'group', 'bot'):
                    await conv.send_message(f"{P_NO} Invalid type. Send <code>channel</code>, <code>group</code>, or <code>bot</code>.")
                elif type_resp == 'bot':
                    bot_user = (await get_reply(
                        "🤖 <b>Force Start Bot</b>\n\n"
                        "Send the bot's <b>username</b> (without @).\n"
                        "Example: <code>MyAwesomeBot</code>"
                    )).text.strip().lstrip('@')
                    join_url = sanitize_url(f"https://t.me/{bot_user}")
                    with _db_write_lock:
                        db.execute("INSERT INTO force_join_channels (channel_id, join_url, type) VALUES (?,?,?)", (bot_user, join_url, 'bot'))
                        db.execute("UPDATE users SET fj_verified=0")
                        db.commit()
                    await conv.send_message(
                        f"{P_YES} <b>Bot added!</b>\n\n"
                        f"🤖 @{bot_user}\n🔗 {join_url}\n\n"
                        f"<i>Users will see a 'Start Bot' button before accessing this bot.</i>"
                    )
                else:
                    type_label = 'Channel' if type_resp == 'channel' else 'Group'
                    type_icon = '📢' if type_resp == 'channel' else '👥'
                    ch_id = (await get_reply(
                        f"{type_icon} <b>Force Join {type_label} — Step 1/2</b>\n\n"
                        f"Send the <b>{type_label} ID</b>.\n"
                        f"It must start with <code>-100</code> (e.g. <code>-1002175693260</code>)\n\n"
                        f"<i>Tip: forward any message from the {type_resp} to @userinfobot to get the ID.</i>"
                    )).text.strip()
                    if not ch_id.lstrip('-').isdigit():
                        await conv.send_message(f"{P_NO} Invalid ID. Must be a number like <code>-1002175693260</code>.")
                    else:
                        join_url = sanitize_url((await get_reply(
                            f"Step 2/2 — Send the <b>Join URL</b> for this {type_resp}.\n"
                            f"Example: <code>https://t.me/your{type_resp}link</code>"
                        )).text.strip())
                        if not join_url.startswith("http"):
                            join_url = "https://t.me/" + join_url.lstrip("@")
                        with _db_write_lock:
                            db.execute("INSERT INTO force_join_channels (channel_id, join_url, type) VALUES (?,?,?)", (ch_id, join_url, type_resp))
                            db.execute("UPDATE users SET fj_verified=0")
                            db.commit()
                        await conv.send_message(
                            f"{P_YES} <b>{type_label} added!</b>\n\n"
                            f"ID: <code>{ch_id}</code>\nURL: {join_url}\n\n"
                            f"<i>Users must now join this {type_resp} before using the bot.</i>"
                        )

            elif action_data == "welcomeset" and has_perm(uid, 'p_settings'):
                current = get_welcome_message()
                current_preview = f"\n\n<b>Current message:</b>\n{current}" if current else "\n\n<i>No welcome message set yet.</i>"
                resp = (await get_reply(
                    f"🎉 <b>Set Welcome Message</b>{current_preview}\n\n"
                    f"📝 Send the new welcome message below.\n"
                    f"HTML tags &lt;b&gt;, &lt;i&gt;, &lt;code&gt; are supported.\n\n"
                    f"👤 <b>User placeholders</b> (auto-replaced when sent):\n"
                    f"  <code>{{mention}}</code> — clickable name mention\n"
                    f"  <code>{{first_name}}</code> — user's first name\n"
                    f"  <code>{{last_name}}</code> — user's last name\n"
                    f"  <code>{{full_name}}</code> — first + last name\n"
                    f"  <code>{{username}}</code> — @username (or first name if none)\n"
                    f"  <code>{{user_id}}</code> — numeric Telegram ID\n\n"
                    f"<i>Note: {{mention}} links are sent without link preview.</i>\n"
                    f"<i>Example: Hello {{mention}}, welcome to our store! 🎉</i>"
                )).text.strip()
                resp = resp.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>") \
                           .replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>") \
                           .replace("&lt;code&gt;", "<code>").replace("&lt;/code&gt;", "</code>")
                with _db_write_lock:
                    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('welcome_message', ?)", (resp,))
                    db.commit()
                btn_text, btn_url = get_welcome_button()
                btn_note = f"\n\n🔘 <i>Button attached: <b>{btn_text}</b></i>" if btn_text else "\n\n<i>No button attached. Use the '🔘 Set Button' option in the welcome settings panel to add one.</i>"
                await conv.send_message(
                    f"{P_YES} <b>Welcome message saved!</b>\n\n"
                    f"<b>Preview:</b>\n{resp}"
                    f"{btn_note}\n\n"
                    f"<i>This message is sent every time a user types /start (after passing all checks), and also when they first accept the Terms & Conditions.</i>"
                )

            elif action_data == "welcomebtnset" and has_perm(uid, 'p_settings'):
                btn_text_resp = (await get_reply(
                    "🔘 <b>Set Welcome Message Button</b>\n\n"
                    "Step 1/2 — Enter the <b>button label</b> (text shown on the button):\n"
                    "<i>Example: 📢 Join Our Channel</i>"
                )).text.strip()
                btn_url_resp = sanitize_url((await get_reply(
                    f"Step 2/2 — Enter the <b>button URL</b> for <b>{html.escape(btn_text_resp)}</b>:\n"
                    "<i>Example: https://t.me/yourchannel</i>"
                )).text.strip())
                if not btn_url_resp.startswith("http"):
                    btn_url_resp = "https://" + btn_url_resp.lstrip("@").replace("@", "t.me/")
                with _db_write_lock:
                    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('welcome_btn_text', ?)", (btn_text_resp,))
                    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('welcome_btn_url', ?)", (btn_url_resp,))
                    db.commit()
                await conv.send_message(
                    f"{P_YES} <b>Welcome button saved!</b>\n\n"
                    f"🔘 Label: <b>{html.escape(btn_text_resp)}</b>\n"
                    f"🔗 URL: <code>{html.escape(btn_url_resp)}</code>\n\n"
                    f"<i>This button will appear below the welcome message.</i>"
                )

            elif action_data == "welcomephoto" and has_perm(uid, 'p_settings'):
                _cur_sp = db.execute("SELECT value FROM settings WHERE key='start_photo'").fetchone()
                _cur_sp_val = _cur_sp[0] if _cur_sp and _cur_sp[0] else None
                cur_note = f"\n\n<b>Current:</b> <code>{html.escape(_cur_sp_val)}</code>" if _cur_sp_val else "\n\n<i>No start photo set yet.</i>"
                await conv.send_message(
                    f"📸 <b>Set Start Photo</b>{cur_note}\n\n"
                    f"<b>Send the photo</b> you want shown on /start, or send a direct <code>https://</code> image URL.\n\n"
                    f"<i>Type /cancel to abort.</i>"
                )
                _photo_msg = await conv.get_response()
                if getattr(_photo_msg, 'text', '') == '/cancel':
                    raise ValueError("Cancelled")
                _photo_val = None
                if _photo_msg.photo:
                    # FIX: store in DB blob (survives Termux restarts); also keep local file
                    try:
                        _sp_bytes = await _read_photo_bytes(_photo_msg)
                        if _sp_bytes:
                            _save_media_blob('start_photo', _sp_bytes)
                            try:
                                with open('start_photo.jpg', 'wb') as _spf: _spf.write(_sp_bytes)
                                _photo_val = 'start_photo.jpg'
                            except Exception as _fe:
                                logger.debug(f'start_photo local write failed (non-critical): {_fe}')
                                _photo_val = 'start_photo.jpg'  # settings value, blob is the real source
                        else:
                            raise ValueError("Empty image data")
                    except Exception as _pe:
                        logger.error(f'Start photo download failed: {_pe}')
                        await conv.send_message(f"{P_NO} <b>Failed to save photo.</b> Try again.")
                elif _photo_msg.text and _photo_msg.text.strip().startswith('http'):
                    _photo_val = _photo_msg.text.strip()
                else:
                    await conv.send_message(f"{P_NO} <b>Invalid input.</b> Please send a photo or a https:// URL.")
                if _photo_val:
                    with _db_write_lock:
                        db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('start_photo', ?)", (_photo_val,))
                        db.commit()
                    await conv.send_message(
                        f"{P_YES} <b>Start photo saved!</b>\n\n"
                        f"📸 Saved as: <code>{html.escape(_photo_val)}</code>\n\n"
                        f"<i>This photo will be sent before the welcome message on every /start.</i>"
                    )

            elif action_data == "bcast" and has_perm(uid, 'p_broadcast'):
                # Step 1: get the broadcast message object (supports ALL types:
                #   text, links, photos, videos, documents, audio, stickers, polls, etc.)
                bcast_obj = await get_reply(
                    f"{P_DOC} <b>Send your broadcast message now.</b>\n\n"
                    f"✅ Supported: text, links, photos, videos, documents, audio, polls, stickers.\n"
                    f"<i>Send exactly what you want users to receive.</i>"
                )
                # Step 2: optional inline URL button (not supported for polls)
                btn_name_raw = (await get_reply("🔘 <b>Button Name (or 'skip' to send without button):</b>")).text.strip()
                btns = None
                if btn_name_raw.lower() != 'skip':
                    url_raw = (await get_reply("🔗 <b>Button URL:</b>")).text.strip()
                    url_clean = sanitize_url(url_raw)
                    if url_clean.startswith('http'):
                        btns = [[Button.url(btn_name_raw, url_clean)]]

                users = db.execute("SELECT user_id FROM users").fetchall()
                s, f = 0, 0
                await conv.send_message(f"{P_TG} Broadcasting to {len(users)} users...")

                # Detect message type so we send the right content
                _has_media = bool(bcast_obj.media)
                _is_poll = _has_media and type(bcast_obj.media).__name__ == 'MessageMediaPoll'

                for (u_id,) in users:
                    try:
                        if _is_poll:
                            # Polls must be forwarded — there is no copy API for polls in Telegram
                            await _tg_call(
                                bot.forward_messages, int(u_id),
                                messages=[bcast_obj.id], from_peer=uid
                            )
                        elif _has_media:
                            # Photos, videos, documents, audio, stickers, GIFs, etc.
                            await _tg_call(
                                bot.send_file, int(u_id), bcast_obj.media,
                                caption=bcast_obj.text or bcast_obj.message or '',
                                buttons=btns, parse_mode='html'
                            )
                        else:
                            # Plain text or text with link preview
                            await _tg_call(
                                bot.send_message, int(u_id),
                                bcast_obj.text or bcast_obj.message or '',
                                buttons=btns, parse_mode='html', link_preview=True
                            )
                        s += 1
                    except Exception:
                        f += 1
                    # Telegram's non-channel rate limit is ~30 msg/s to different users.
                    # 0.05 s ≈ 20 msg/s — keeps us safely under the limit.
                    await asyncio.sleep(0.05)
                await conv.send_message(f"{P_YES} Done! Sent: {s} | Failed: {f}")

            elif action_data == "bal" and has_perm(uid, 'p_bal'):
                _ru = (await get_reply(f"{P_ACC} <b>User ID:</b>")).text.strip()
                if not _ru.isdigit(): return await conv.send_message(f"{P_NO} User ID must be a positive number.")
                t_uid = int(_ru)
                if not db.execute("SELECT user_id FROM users WHERE user_id=?", (t_uid,)).fetchone():
                    return await conv.send_message(f"{P_NO} User not found.")
                _ra = (await get_reply(f"{P_MONEY} <b>Amount (Negative to deduct):</b>")).text.strip()
                if not _ra.lstrip('-').isdigit(): return await conv.send_message(f"{P_NO} Amount must be a number (e.g. 100 or -50).")
                amt = int(_ra)
                # FIX: read old balance before updating so log can show before→after
                old_bal_row = db.execute("SELECT balance FROM users WHERE user_id=?", (t_uid,)).fetchone()
                old_bal = old_bal_row[0] if old_bal_row else 0
                update_balance(t_uid, amt)
                new_bal_row = db.execute("SELECT balance FROM users WHERE user_id=?", (t_uid,)).fetchone()
                new_bal = new_bal_row[0] if new_bal_row else 0
                await conv.send_message(f"{P_YES} {'Added' if amt >= 0 else 'Deducted'} {P_INR}{abs(amt)} {'to' if amt >= 0 else 'from'} <code>{t_uid}</code>.\n"
                                        f"💼 New balance: <code>{P_INR}{new_bal}</code>")
                # FIX: send log to purchase-log channel
                await log_balance_change(uid, t_uid, amt, old_bal, new_bal)
                # Feature 12: audit log
                log_admin_action_db(uid, 'balance_changed', t_uid, f'delta={amt} old={old_bal} new={new_bal}')
                
            elif action_data == "discount" and has_perm(uid, 'p_settings'):
                _ru = (await get_reply(f"{P_ACC} <b>User ID:</b>")).text.strip()
                if not _ru.isdigit(): return await conv.send_message(f"{P_NO} User ID must be a positive number.")
                t_uid = int(_ru)
                _rp = (await get_reply(f"{P_GIFT} <b>Discount % (0 to remove):</b>")).text.strip()
                if not _rp.isdigit(): return await conv.send_message(f"{P_NO} Discount must be a number between 0 and 100.")
                pct = int(_rp)
                if not 0 <= pct <= 100: return await conv.send_message(f"{P_NO} Discount must be between 0 and 100.")
                with _db_write_lock:
                    db.execute("UPDATE users SET discount=? WHERE user_id=?", (pct, t_uid))
                    db.commit()
                await conv.send_message(f"{P_YES} User <code>{t_uid}</code> now has <b>{pct}% discount</b>.")
                
            elif action_data == "refpct" and has_perm(uid, 'p_settings'):
                _r = (await get_reply(f"{P_USERS} <b>New Referral %:</b>")).text.strip()
                if not _r.isdigit() or int(_r) > 100: return await conv.send_message(f"{P_NO} Referral % must be a number between 0 and 100.")
                pct = int(_r)
                with _db_write_lock:
                    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('ref_percent', ?)", (str(pct),))
                    db.commit()
                await conv.send_message(f"{P_YES} Referral percent set to {pct}%.")

            elif action_data == "usdtrate" and has_perm(uid, 'p_settings'):
                _r = (await get_reply(f"{P_USDT} <b>New USDT Rate (INR):</b>")).text.strip()
                try:
                    r = float(_r)
                    if r <= 0: raise ValueError
                except ValueError:
                    return await conv.send_message(f"{P_NO} Rate must be a positive number (e.g. 94.5).")
                with _db_write_lock:
                    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('usdt_rate', ?)", (str(r),))
                    db.commit()
                await conv.send_message(f"{P_YES} Rate set to {r}.")

            elif action_data == "restoreusr" and has_perm(uid, 'p_settings'):
                resp = await get_reply("📤 <b>Send the <code>users_backup.csv</code> file:</b>")
                if not resp.file or not resp.file.name.endswith('.csv'): return await conv.send_message(f"{P_NO} Invalid file.")
                await bot.download_media(resp, "temp_restore.csv")
                with open("temp_restore.csv", "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    try: next(reader)
                    except StopIteration:
                        await conv.send_message(f"{P_NO} CSV file is empty.")
                        os.remove("temp_restore.csv")
                        return
                    count = 0
                    failed = 0
                    with _db_write_lock:
                        for row in reader:
                            try:
                                db.execute("INSERT OR REPLACE INTO users (user_id, balance, referred_by, total_deposited, joined_date, banned, discount, terms_accepted) VALUES (?,?,?,?,?,?,?,?)", 
                                            (int(row[0]), int(row[1]), row[2] if row[2] else None, int(row[3]), row[4], int(row[5]), int(row[6]), int(row[7])))
                                count += 1
                            except Exception: failed += 1
                        db.commit()
                os.remove("temp_restore.csv")
                fail_note = f"\n⚠️ {failed} row(s) skipped (invalid data)." if failed else ""
                await conv.send_message(f"{P_YES} Restored <b>{count}</b> users.{fail_note}")

            elif action_data == "ban" and has_perm(uid, 'p_ban'):
                _r = (await get_reply(f"{P_ACC} <b>User ID:</b>")).text.strip()
                if not _r.isdigit(): return await conv.send_message(f"{P_NO} User ID must be a positive number.")
                t_uid = int(_r)
                is_ban = db.execute("SELECT banned FROM users WHERE user_id=?", (t_uid,)).fetchone()
                if not is_ban: return await conv.send_message(f"{P_NO} User not found.")
                ns = 0 if is_ban[0] == 1 else 1
                action_word = "BAN 🚫" if ns == 1 else "UNBAN ✅"
                current_word = "currently BANNED 🚫" if is_ban[0] == 1 else "currently ACTIVE ✅"
                confirm_resp = (await get_reply(
                    f"{P_WARN} <b>Confirm Action</b>\n\n"
                    f"{P_ACC} User: <code>{t_uid}</code>\n"
                    f"📌 Status: <b>{current_word}</b>\n"
                    f"🔄 Action: <b>{action_word}</b>\n\n"
                    f"Type <code>YES</code> to confirm or anything else to cancel."
                )).text.strip()
                if confirm_resp.upper() != "YES":
                    return await conv.send_message(f"{P_NO} Cancelled. No changes made.")
                with _db_write_lock:
                    db.execute("UPDATE users SET banned=? WHERE user_id=?", (ns, t_uid))
                    db.commit()
                await conv.send_message(f"User {t_uid} is {'Banned 🚫' if ns == 1 else 'Unbanned ✅'}.")
                if ns == 1:
                    try:
                        await bot.send_message(t_uid,
                            f"{P_NO} <b>Your account has been banned.</b>\n\n"
                            f"You are no longer able to use this bot.\n"
                            f"If you believe this is a mistake, please contact support."
                        )
                    except Exception as _e: logger.debug(f'Ban notify to {t_uid} failed: {_e}')
                else:
                    try:
                        await bot.send_message(t_uid,
                            f"{P_YES} <b>Your account has been unbanned.</b>\n\n"
                            f"You can now use the bot again. Type /start to continue."
                        )
                    except Exception as _e: logger.debug(f'Unban notify to {t_uid} failed: {_e}')

            elif action_data == "faq_add" and has_perm(uid, 'p_faq', 'p_settings'):
                question = html.escape((await get_reply(
                    "❓ <b>Enter the FAQ Question:</b>\n<i>e.g. How do I get a refund?</i>"
                )).text.strip())
                answer = html.escape((await get_reply(
                    f"📝 <b>Enter the Answer for:</b>\n<i>{question}</i>\n\n<i>HTML tags &lt;b&gt;, &lt;i&gt;, &lt;code&gt; are supported.</i>"
                )).text.strip())
                answer = answer.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>") \
                               .replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>") \
                               .replace("&lt;code&gt;", "<code>").replace("&lt;/code&gt;", "</code>")
                order_str = (await get_reply(
                    "🔢 <b>Sort Order (lower = shown first):</b>\n<i>Enter a number, e.g. 1, 2, 3 — or 0 to append at end.</i>"
                )).text.strip()
                sort_order = int(order_str) if order_str.isdigit() else 0
                with _db_write_lock:
                    db.execute("INSERT INTO faq_entries (question, answer, sort_order) VALUES (?,?,?)", (question, answer, sort_order))
                    db.commit()
                await conv.send_message(
                    f"{P_YES} <b>FAQ Entry Added!</b>\n\n"
                    f"<b>Q:</b> {question}\n"
                    f"<b>A:</b> {answer}\n"
                    f"<b>Order:</b> {sort_order}\n\n"
                    f"<i>It will now appear in the ❓ Help → FAQ section for all users.</i>"
                )

            elif action_data.startswith("faq_edit|") and has_perm(uid, 'p_faq', 'p_settings'):
                faq_id = int(action_data.split("|")[1])
                row = db.execute("SELECT question, answer, sort_order FROM faq_entries WHERE id=?", (faq_id,)).fetchone()
                if not row:
                    return await conv.send_message(f"{P_NO} FAQ entry not found.")
                old_q, old_a, old_order = row
                await conv.send_message(
                    f"✏️ <b>Editing FAQ [{faq_id}]</b>\n\n"
                    f"<b>Current Q:</b> {old_q}\n"
                    f"<b>Current A:</b> {old_a}\n\n"
                    f"<i>Reply with <code>skip</code> to keep the current value.</i>"
                )
                new_q_msg = (await get_reply("❓ <b>New Question</b> (or <code>skip</code>):")).text.strip()
                new_q = old_q if new_q_msg.lower() == "skip" else html.escape(new_q_msg)
                new_a_msg = (await get_reply("📝 <b>New Answer</b> (or <code>skip</code>):")).text.strip()
                if new_a_msg.lower() == "skip":
                    new_a = old_a
                else:
                    new_a = html.escape(new_a_msg)
                    new_a = new_a.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>") \
                                 .replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>") \
                                 .replace("&lt;code&gt;", "<code>").replace("&lt;/code&gt;", "</code>")
                new_order_msg = (await get_reply(f"🔢 <b>New Sort Order</b> (current: {old_order}, or <code>skip</code>):")).text.strip()
                new_order = old_order if new_order_msg.lower() == "skip" else (int(new_order_msg) if new_order_msg.isdigit() else old_order)
                with _db_write_lock:
                    db.execute("UPDATE faq_entries SET question=?, answer=?, sort_order=? WHERE id=?", (new_q, new_a, new_order, faq_id))
                    db.commit()
                await conv.send_message(
                    f"{P_YES} <b>FAQ Entry Updated!</b>\n\n"
                    f"<b>Q:</b> {new_q}\n"
                    f"<b>A:</b> {new_a}\n"
                    f"<b>Order:</b> {new_order}"
                )

            elif action_data == "sales_report" and has_perm(uid, 'p_stats'):
                period_resp = (await get_reply(
                    f"📈 <b>Sales Report</b>\n\nChoose period:\n"
                    f"1️⃣ Today\n2️⃣ This Week\n3️⃣ This Month\n4️⃣ All Time"
                )).text.strip()
                today = datetime.now().strftime('%Y-%m-%d')
                week_start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                month_start = datetime.now().strftime('%Y-%m-01')
                if period_resp == "1":
                    period_label = "Today"
                    date_filter = f"AND date LIKE '{today}%'"
                elif period_resp == "2":
                    period_label = "Last 7 Days"
                    date_filter = f"AND date >= '{week_start}'"
                elif period_resp == "3":
                    period_label = "This Month"
                    date_filter = f"AND date >= '{month_start}'"
                else:
                    period_label = "All Time"
                    date_filter = ""
                o_row = db.execute(f"SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE 1=1 {date_filter}").fetchone()
                top_countries = db.execute(
                    f"SELECT country, COUNT(*) as cnt, COALESCE(SUM(price),0) FROM orders WHERE 1=1 {date_filter} GROUP BY country ORDER BY cnt DESC LIMIT 5"
                ).fetchall()
                dep_row = db.execute(
                    f"SELECT COUNT(*), COALESCE(SUM(amount),0) FROM deposits WHERE status='approved' {date_filter.replace('date','date')}"
                ).fetchone()
                top_msg = "\n".join(
                    f"  {i+1}. {c} — {n} sold  ({P_INR}{rev})" for i, (c, n, rev) in enumerate(top_countries)
                ) or "  <i>No sales yet</i>"
                await conv.send_message(
                    f"📈 <b>Sales Report — {period_label}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🛒 <b>Orders:</b> {o_row[0]}  |  {P_INR}{o_row[1]} revenue\n"
                    f"💰 <b>Deposits Approved:</b> {dep_row[0]}  |  {P_INR}{dep_row[1]}\n\n"
                    f"🏆 <b>Top Countries:</b>\n{top_msg}"
                )

            elif action_data == "schedule_bcast" and has_perm(uid, 'p_broadcast'):
                txt = (await get_reply(f"{P_DOC} <b>Broadcast Message (HTML supported):</b>")).text
                btn_name = (await get_reply("🔘 <b>Button Name</b> (or <code>skip</code>):")).text
                if btn_name.lower() == 'skip':
                    btn_name_val, btn_url_val = None, None
                else:
                    btn_url_val = (await get_reply("🔗 <b>Button URL:</b>")).text.strip()
                    btn_name_val = btn_name
                send_at_raw = (await get_reply(
                    "⏰ <b>Send At (24h format):</b>\n<i>Example: 2024-07-20 18:30</i>"
                )).text.strip()
                try:
                    datetime.strptime(send_at_raw, "%Y-%m-%d %H:%M")
                except ValueError:
                    return await conv.send_message(f"{P_NO} Invalid format. Use: YYYY-MM-DD HH:MM")
                with _db_write_lock:
                    db.execute(
                        "INSERT INTO scheduled_broadcasts (message, btn_name, btn_url, send_at, created_by, sent) VALUES (?,?,?,?,?,0)",
                        (txt, btn_name_val, btn_url_val, send_at_raw, uid)
                    )
                    db.commit()
                await conv.send_message(f"{P_YES} <b>Broadcast scheduled!</b>\nIt will be sent at <b>{send_at_raw}</b>.")

            elif action_data == "low_stock_limit" and has_perm(uid, 'p_settings'):
                cur_row = db.execute("SELECT value FROM settings WHERE key='low_stock_threshold'").fetchone()
                cur = cur_row[0] if cur_row else "5"
                _r = (await get_reply(
                    f"⚠️ <b>Low Stock Alert Threshold</b>\n\n"
                    f"Current: <b>{cur}</b> accounts\n\n"
                    f"Enter the new minimum count. When any country drops to or below this number, "
                    f"you'll get a DM alert. Enter 0 to disable."
                )).text.strip()
                if not _r.isdigit():
                    return await conv.send_message(f"{P_NO} Must be a number.")
                with _db_write_lock:
                    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('low_stock_threshold', ?)", (_r,))
                    db.commit()
                await conv.send_message(f"{P_YES} Low stock threshold set to <b>{_r}</b>.")

            elif action_data == "stock_expiry" and has_perm(uid, 'p_settings'):
                cur_row = db.execute("SELECT value FROM settings WHERE key='stock_expiry_days'").fetchone()
                cur = cur_row[0] if cur_row else "0 (disabled)"
                _r = (await get_reply(
                    f"🗓 <b>Stock Expiry Days</b>\n\n"
                    f"Current: <b>{cur}</b>\n\n"
                    f"Accounts that remain unsold for this many days will be automatically marked unavailable.\n"
                    f"Enter 0 to disable expiry."
                )).text.strip()
                if not _r.isdigit():
                    return await conv.send_message(f"{P_NO} Must be a number.")
                with _db_write_lock:
                    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('stock_expiry_days', ?)", (_r,))
                    db.commit()
                lbl = f"{_r} days" if _r != "0" else "disabled"
                await conv.send_message(f"{P_YES} Stock expiry set to <b>{lbl}</b>.")

            elif action_data == "qty_tiers" and has_perm(uid, 'p_settings'):
                t5, t10, t20 = get_qty_tier_info()
                _r = (await get_reply(
                    f"💲 <b>Qty Tier Discounts</b>\n\n"
                    f"Current tiers:\n"
                    f"• 5+ accounts: <b>{t5}%</b> off\n"
                    f"• 10+ accounts: <b>{t10}%</b> off\n"
                    f"• 20+ accounts: <b>{t20}%</b> off\n\n"
                    f"Enter new values as <code>5pct 10pct 20pct</code>\n"
                    f"Example: <code>5 10 15</code>\nOr send <code>skip</code> to keep current."
                )).text.strip()
                if _r.lower() != 'skip':
                    _parts = _r.split()
                    if len(_parts) != 3 or not all(p.isdigit() for p in _parts):
                        return await conv.send_message(f"{P_NO} Enter exactly 3 numbers, e.g. <code>5 10 15</code>")
                    v5, v10, v20 = int(_parts[0]), int(_parts[1]), int(_parts[2])
                    with _db_write_lock:
                        db.execute("INSERT OR REPLACE INTO settings VALUES ('qty_tier_5_pct', ?)", (str(v5),))
                        db.execute("INSERT OR REPLACE INTO settings VALUES ('qty_tier_10_pct', ?)", (str(v10),))
                        db.execute("INSERT OR REPLACE INTO settings VALUES ('qty_tier_20_pct', ?)", (str(v20),))
                        db.commit()
                    await conv.send_message(f"{P_YES} Tiers updated: 5+→{v5}%, 10+→{v10}%, 20+→{v20}%")
                else:
                    await conv.send_message(f"{P_NO} No changes made.")

            elif action_data == "res_add" and has_perm(uid, 'p_settings'):
                # Add a user as reseller by ID
                _r = (await get_reply(
                    f"🌟 <b>Add Reseller</b>\n\n"
                    f"Enter the <b>User ID</b> to add as reseller:\n"
                    f"<i>Send /cancel to abort.</i>"
                )).text.strip()
                if _r == '/cancel':
                    return await conv.send_message(f"{P_NO} Cancelled.")
                if not _r.isdigit():
                    return await conv.send_message(f"{P_NO} Invalid user ID.")
                t_uid = int(_r)
                row = db.execute("SELECT reseller FROM users WHERE user_id=?", (t_uid,)).fetchone()
                if not row:
                    return await conv.send_message(f"{P_NO} User <code>{t_uid}</code> not found.")
                if row[0]:
                    return await conv.send_message(f"{P_WARN} User <code>{t_uid}</code> is already a reseller.")
                with _db_write_lock:
                    db.execute("UPDATE users SET reseller=1 WHERE user_id=?", (t_uid,))
                    db.commit()
                await conv.send_message(f"{P_YES} User <code>{t_uid}</code> is now a <b>🌟 Reseller</b>.")
                try:
                    await bot.send_message(t_uid, f"🌟 <b>You've been upgraded to Reseller!</b>\n\nYou now get <b>{get_reseller_discount()}% discount</b> on all purchases.")
                except Exception as _e:
                    logger.debug(f"reseller notify failed: {_e}")

            elif action_data.startswith("res_disc|") and has_perm(uid, 'p_settings'):
                # Change individual user's reseller discount
                try:
                    t_uid = int(action_data.split("|", 1)[1])
                except ValueError:
                    return await conv.send_message(f"{P_NO} Invalid user ID.")
                cur_row = db.execute("SELECT discount, reseller FROM users WHERE user_id=?", (t_uid,)).fetchone()
                if not cur_row:
                    return await conv.send_message(f"{P_NO} User <code>{t_uid}</code> not found.")
                cur_d = cur_row[0] or 0
                _r = (await get_reply(
                    f"💸 <b>Change Discount for {t_uid}</b>\n\n"
                    f"Current discount: <b>{cur_d}%</b>\n"
                    f"Global reseller discount: <b>{get_reseller_discount()}%</b>\n\n"
                    f"Enter new discount % (0-100), or 0 to use global rate:\n"
                    f"<i>Send /cancel to abort.</i>"
                )).text.strip()
                if _r == '/cancel':
                    return await conv.send_message(f"{P_NO} Cancelled.")
                if not _r.isdigit() or not (0 <= int(_r) <= 100):
                    return await conv.send_message(f"{P_NO} Discount must be 0-100.")
                new_disc = int(_r)
                with _db_write_lock:
                    db.execute("UPDATE users SET discount=? WHERE user_id=?", (new_disc, t_uid))
                    db.commit()
                await conv.send_message(f"{P_YES} User <code>{t_uid}</code> discount set to <b>{new_disc}%</b>.")

            elif action_data == "res_global_disc" and has_perm(uid, 'p_settings'):
                # Change the global reseller discount %
                cur_disc = get_reseller_discount()
                _r = (await get_reply(
                    f"🔧 <b>Change Global Reseller Discount</b>\n\n"
                    f"Current: <b>{cur_disc}%</b>\n\n"
                    f"Enter new global reseller discount % (0-80):\n"
                    f"<i>Send /cancel to abort.</i>"
                )).text.strip()
                if _r == '/cancel':
                    return await conv.send_message(f"{P_NO} Cancelled.")
                if not _r.isdigit() or not (0 <= int(_r) <= 80):
                    return await conv.send_message(f"{P_NO} Discount must be 0-80.")
                with _db_write_lock:
                    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('reseller_discount', ?)", (_r,))
                    db.commit()
                await conv.send_message(f"{P_YES} Global reseller discount set to <b>{_r}%</b>.")

            elif action_data.startswith("apset|") and has_perm(uid, 'p_manage_stock'):
                parts = action_data.split("|", 3)
                if len(parts) < 3:
                    return await conv.send_message(f"{P_NO} Invalid action data. Please try again.")
                c_name = parts[1]
                year    = parts[2]
                cat     = parts[3] if len(parts) > 3 else 'Any'

                # DB storage key: "2021_Good", "2021_Old", "Common_Good", "Common_Old", "Common" (Any)
                # Normalise legacy 'Good' → 'Fresh' in admin auto-price keys
                if cat == 'Good':
                    cat = 'Fresh'
                db_key = year if cat == 'Any' else f"{year}_{cat}"

                flag = get_flag_by_country_name(c_name)
                if cat == 'Any':
                    cat_label = "⚡ Any (all-catch fallback)"
                elif cat == 'Fresh':
                    cat_label = "🟢 Fresh"
                else:
                    cat_label = "🟡 Old"
                year_label = "Common" if year == "Common" else str(year)

                price_resp = await get_reply(
                    f"{P_MONEY} <b>Set Auto Price</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🌍 Country : {flag} {c_name}\n"
                    f"📅 Year    : {year_label}\n"
                    f"📂 Category: {cat_label}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Enter the price in {P_INR} INR:"
                )
                _price_digits = re.sub(r'[^\d]', '', price_resp.text)
                if not _price_digits:
                    await conv.send_message(f"{P_NO} Invalid price. Please enter a number.")
                    return
                price = int(_price_digits)
                if price <= 0:
                    await conv.send_message(f"{P_NO} Price must be greater than 0.")
                    return
                with _db_write_lock:
                    db.execute("INSERT OR REPLACE INTO auto_prices (country, year, price) VALUES (?,?,?)", (c_name, db_key, price))
                    db.commit()
                await conv.send_message(
                    f"{P_YES} <b>Auto Price Saved!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🌍 Country : {flag} {c_name}\n"
                    f"📅 Year    : {year_label}\n"
                    f"📂 Category: {cat_label}\n"
                    f"💰 Price   : {P_INR}{price}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"<i>Will auto-apply when adding stock for this country / year / category.</i>"
                )

            # ───── RECOVERY UPLOAD HANDLERS (need file uploads via conversation) ─────
            elif action_data == "recover_up_db" and has_perm(uid, 'p_settings'):
                resp_db = await get_reply(
                    f"📤 <b>Restore Database</b>\n\n"
                    f"⚠️ <b>WARNING:</b> The live database will be <b>replaced</b>.\n"
                    f"A safety backup is created automatically first.\n\n"
                    f"Send a <code>.db</code> SQLite file, or /cancel to abort."
                )
                _db_fname = ''
                try: _db_fname = resp_db.file.name or ''
                except Exception: pass
                if not _db_fname.endswith('.db'):
                    return await conv.send_message(
                        f"{P_NO} Please send a file with a <code>.db</code> extension.\n"
                        f"Tap the button again to retry.")
                await conv.send_message(f"{P_WAIT} <b>Downloading and verifying...</b>")
                _tmp_db = os.path.join(_backups_dir, f"restore_tmp_{int(time.time())}.db")
                try:
                    await bot.download_media(resp_db, _tmp_db)
                    _tc = sqlite3.connect(_tmp_db)
                    _tc.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone()
                    _tc.close()
                    _safe_bkp = os.path.join(
                        _backups_dir,
                        f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    )
                    with _db_write_lock:
                        _bc = sqlite3.connect(_safe_bkp)
                        try: db.backup(_bc)
                        finally: _bc.close()
                    shutil.copy2(_tmp_db, _database_path)
                    os.remove(_tmp_db)
                    await conv.send_message(
                        f"{P_YES} <b>Database Restored!</b>\n\n"
                        f"✅ Safety backup: <code>{_safe_bkp}</code>\n\n"
                        f"⚠️ <b>Restart the bot</b> for changes to take full effect."
                    )
                    logger.info(f"Admin uid={uid} restored database. Safety backup: {_safe_bkp}")
                except sqlite3.DatabaseError:
                    try: os.remove(_tmp_db)
                    except Exception: pass
                    return await conv.send_message(
                        f"{P_NO} Not a valid SQLite database. Send a <code>.db</code> file exported by this bot.")
                except Exception as _dbe:
                    try: os.remove(_tmp_db)
                    except Exception: pass
                    logger.error(f"recover_up_db failed: {_dbe}")
                    return await conv.send_message(f"{P_NO} Restore failed: {html.escape(str(_dbe))}")

            elif action_data == "recover_up_sess" and has_perm(uid, 'p_settings'):
                resp_zip = await get_reply(
                    f"📤 <b>Restore Sessions ZIP</b>\n\n"
                    f"Send a <code>.zip</code> file containing <code>.session</code> files.\n"
                    f"Same-name files will be <b>overwritten</b> on disk.\n\n"
                    f"Send the ZIP, or /cancel to abort."
                )
                _zip_fname = ''
                try: _zip_fname = resp_zip.file.name or ''
                except Exception: pass
                if not _zip_fname.endswith('.zip'):
                    return await conv.send_message(
                        f"{P_NO} Please send a <code>.zip</code> file. Tap the button again to retry.")
                await conv.send_message(f"{P_WAIT} <b>Downloading and extracting sessions...</b>")
                _tmp_zip = os.path.join(_backups_dir, f"sess_restore_{int(time.time())}.zip")
                try:
                    await bot.download_media(resp_zip, _tmp_zip)
                    if not zipfile.is_zipfile(_tmp_zip):
                        os.remove(_tmp_zip)
                        return await conv.send_message(f"{P_NO} Not a valid ZIP archive.")
                    with zipfile.ZipFile(_tmp_zip, 'r') as _zfr:
                        _safe_extract_zip(_zfr, _sessions_dir)
                        _ext_count = sum(1 for n in _zfr.namelist() if n.endswith('.session'))
                    os.remove(_tmp_zip)
                    await conv.send_message(
                        f"{P_YES} <b>Sessions Restored!</b>\n\n"
                        f"✅ Extracted <b>{_ext_count}</b> .session file(s) to:\n"
                        f"<code>{_sessions_dir}</code>\n\n"
                        f"<i>Bot will use restored sessions for new purchases immediately.</i>"
                    )
                    logger.info(f"Admin uid={uid} restored {_ext_count} sessions from ZIP.")
                except ValueError as _ve:
                    try: os.remove(_tmp_zip)
                    except Exception: pass
                    return await conv.send_message(
                        f"{P_NO} Unsafe ZIP entry — restore aborted.\n<code>{html.escape(str(_ve))}</code>")
                except Exception as _ze:
                    try: os.remove(_tmp_zip)
                    except Exception: pass
                    logger.error(f"recover_up_sess failed: {_ze}")
                    return await conv.send_message(f"{P_NO} Restore failed: {html.escape(str(_ze))}")
            # ───────────────── end recovery upload handlers ──────────────────

        except ValueError:
            try: await conv.send_message(f"{P_NO} Cancelled.")
            except Exception: pass
        except asyncio.CancelledError:
            # Task cancelled by /cancel command or new button press
            try: await bot.send_message(
                chat,
                f"{P_NO} <b>Action cancelled.</b>\n\n"
                f"Tap any button or use /start to continue.")
            except Exception: pass
            raise   # re-raise so asyncio cleanup runs properly
        except asyncio.TimeoutError:
            # Conversation timed out — conv is already closed, cannot send through it
            try: await bot.send_message(chat, f"{P_NO} <b>Session timed out.</b> No response received in 10 minutes. Please tap the button again to restart.")
            except Exception as _te: logger.debug(f"Timeout notify failed: {_te}")
        except Exception as e:
            try: await conv.send_message(f"{P_NO} Error: {html.escape(str(e))}")
            except Exception: pass
    except AlreadyInConversationError:
        # FIX: send a visible TEXT message (not just a vanishing popup alert)
        try: await event.answer("⚠️ Another action is in progress — type /cancel to stop it.", alert=True)
        except Exception: pass
        try:
            await bot.send_message(
                chat,
                f"⚠️ <b>Another action is already in progress.</b>\n\n"
                f"Type /cancel to stop the current action, then tap the button again.")
        except Exception as _e: logger.debug(f'AlreadyInConversation message failed: {_e}')
    except asyncio.CancelledError:
        pass   # /cancel already sent the cancellation message above
    except asyncio.TimeoutError:
        try: await bot.send_message(chat, f"{P_NO} <b>Session timed out.</b> Please tap the button again.")
        except Exception: pass
    finally:
        # Always remove task reference when conversation ends (success, cancel, timeout, error)
        _active_admin_conv.pop(uid, None)

# ================= ADMIN COMMANDS =================

class FakeCbEvent:
    """Wraps a message event so admin_actions (which expects a callback event) can be triggered from a command."""
    def __init__(self, e, action):
        self.chat_id = e.chat_id
        self.sender_id = e.sender_id
        self.data = f"adm_{action}".encode()
        self.message = e.message
    async def edit(self, msg, buttons=None):
        await bot.send_message(self.chat_id, msg, buttons=buttons)
    async def answer(self, msg="", alert=False):
        if msg: await bot.send_message(self.chat_id, msg)
    async def delete(self):
        pass
    async def respond(self, msg, buttons=None):
        await bot.send_message(self.chat_id, msg, buttons=buttons)

@bot.on(events.NewMessage(pattern=r"(?i)^/togglebot$"))
async def cmd_togglebot(e):
    if not has_perm(e.sender_id, 'p_settings'): return
    new_status = 'off' if is_bot_online() else 'on'
    with _db_write_lock:
        db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('bot_status', ?)", (new_status,))
        db.commit()
    await e.respond(f"{P_YES} Bot turned <b>{new_status.upper()}</b>.")

@bot.on(events.NewMessage(pattern=r"(?i)^/stats$"))
async def cmd_stats(e):
    if not has_perm(e.sender_id, 'p_stats'): return
    u = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    s = db.execute("SELECT COUNT(*) FROM stock WHERE available=1").fetchone()[0]
    r_row = db.execute("SELECT value FROM settings WHERE key='upi_revenue'").fetchone()
    r = r_row[0] if r_row else "0"
    bal_row = db.execute("SELECT SUM(balance) FROM users").fetchone()
    total_bal = bal_row[0] if bal_row and bal_row[0] else 0
    o_row = db.execute("SELECT COUNT(*), SUM(price) FROM orders").fetchone()
    total_orders = o_row[0] if o_row else 0
    total_spent = o_row[1] if o_row and o_row[1] else 0
    msg = (f"{P_STATS} <b>ADVANCED STATS</b>\n\n{P_USERS} <b>Total Users:</b> {u}\n{P_PKG} <b>Accounts in Stock:</b> {s}\n"
           f"{P_MONEY} <b>Total Revenue:</b> {P_INR}{r}\n\n{P_CARD} <b>Overall Users Balance:</b> {P_INR}{total_bal}\n"
           f"{P_CART} <b>Total Accounts Sold:</b> {total_orders}\n{P_USDT} <b>Overall Sales Amount:</b> {P_INR}{total_spent}")
    await e.respond(msg)

@bot.on(events.NewMessage(pattern=r"(?i)^/daystats$"))
async def cmd_daystats(e):
    if not has_perm(e.sender_id, 'p_stats'): return
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    date_label = now.strftime('%d %b %Y')
    day_label  = now.strftime('%A')

    new_users = db.execute(
        "SELECT COUNT(*) FROM users WHERE date(joined_date) = ?", (today,)
    ).fetchone()[0]
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    dep_row = db.execute(
        "SELECT COUNT(*), COALESCE(SUM(amount),0) FROM deposits WHERE status='approved' AND date(date) = ?", (today,)
    ).fetchone()
    dep_count, dep_total = (dep_row[0], dep_row[1]) if dep_row else (0, 0)

    upi_row = db.execute(
        "SELECT COUNT(*), COALESCE(SUM(amount),0) FROM upi_orders WHERE status='success' AND date(date) = ?", (today,)
    ).fetchone()
    upi_count, upi_total = (upi_row[0], upi_row[1]) if upi_row else (0, 0)

    ord_row = db.execute(
        "SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE date(date) = ?", (today,)
    ).fetchone()
    ord_count, ord_total = (ord_row[0], ord_row[1]) if ord_row else (0, 0)

    stock_left  = db.execute("SELECT COUNT(*) FROM stock WHERE available=1").fetchone()[0]
    stock_total = db.execute("SELECT COUNT(*) FROM stock").fetchone()[0]

    total_dep_count = dep_count + upi_count
    total_dep       = dep_total + upi_total

    SEP = "─" * 28

    msg = (
        f"📅 <b>DAILY STATS</b>\n"
        f"<code>{date_label}  ·  {day_label}</code>\n"
        f"<code>{SEP}</code>\n\n"

        f"👥 <b>USERS</b>\n"
        f"  <code>+{new_users:>4}</code>  joined today\n"
        f"  <code>{total_users:>5}</code>  total registered\n\n"

        f"<code>{SEP}</code>\n\n"

        f"💰 <b>DEPOSITS</b>  —  <b>{total_dep_count} transaction(s)</b>\n"
        f"  {'Manual':<10}  {dep_count:>3}   <b>₹{dep_total:,}</b>\n"
        f"  {'UPI':<10}  {upi_count:>3}   <b>₹{upi_total:,}</b>\n"
        f"  {'─'*10}  {'─'*3+'─'*8+'─'*5}\n"
        f"  {'Total':<10}  {total_dep_count:>3}   <b>₹{total_dep:,}</b>\n\n"

        f"<code>{SEP}</code>\n\n"

        f"🛒 <b>PURCHASES</b>  —  <b>{ord_count} order(s)</b>\n"
        f"  Revenue today   <b>₹{ord_total:,}</b>\n\n"

        f"<code>{SEP}</code>\n\n"

        f"📦 <b>STOCK</b>\n"
        f"  <code>{stock_left:>5}</code>  available now\n"
        f"  <code>{stock_total:>5}</code>  total in DB\n"
    )
    await e.respond(msg)

@bot.on(events.NewMessage(pattern=r"(?i)^/userinfo(?:\s+(\d+))?$"))
async def cmd_userinfo(e):
    if not has_perm(e.sender_id, 'p_userinfo', 'p_stats'): return
    t_uid_str = (e.pattern_match.group(1) or "").strip()
    if not t_uid_str:
        return await e.respond("Usage: <code>/userinfo &lt;user_id&gt;</code>")
    try:
        t_uid = int(t_uid_str)
    except ValueError:
        return await e.respond(f"{P_NO} Invalid user ID.")
    u_row = db.execute("SELECT balance, total_deposited, joined_date, banned, discount FROM users WHERE user_id=?", (t_uid,)).fetchone()
    if not u_row: return await e.respond(f"{P_NO} User not found.")
    o_row = db.execute("SELECT COUNT(*), SUM(price) FROM orders WHERE user_id=?", (t_uid,)).fetchone()
    up_row = db.execute("SELECT SUM(amount) FROM upi_orders WHERE user_id=? AND status='success'", (t_uid,)).fetchone()
    bal, dep, joined, is_banned, disc = u_row
    o_count = o_row[0] if o_row else 0
    o_spent = o_row[1] if o_row and o_row[1] else 0
    u_upi = up_row[0] if up_row and up_row[0] else 0
    msg = (f"{P_ACC} <b>USER INFO:</b> <code>{t_uid}</code>\n\n"
           f"{P_MONEY} Balance: {P_INR}{bal}\n"
           f"{P_CARD} Total Deposited: {P_INR}{dep}\n"
           f"{P_UPI} UPI Deposited: {P_INR}{u_upi}\n"
           f"{P_CART} Total Orders: {o_count}\n"
           f"{P_USDT} Total Spent: {P_INR}{o_spent}\n"
           f"{P_GIFT} Discount: {disc}%\n"
           f"{P_CAL} Joined: {joined}\n"
           f"{P_OFF} Banned: {'Yes ⛔' if is_banned else 'No ✅'}")
    await e.respond(msg)

@bot.on(events.NewMessage(pattern=r"(?i)^/addbal(?:\s+(\d+)\s+(-?\d+))?$"))
async def cmd_addbal(e):
    if not has_perm(e.sender_id, 'p_bal'): return
    m = e.pattern_match
    if not m.group(1) or not m.group(2):
        return await e.respond("Usage: <code>/addbal &lt;user_id&gt; &lt;amount&gt;</code>\n<i>Use negative to deduct.</i>")
    t_uid, amt = int(m.group(1)), int(m.group(2))
    bal_check = db.execute("SELECT balance FROM users WHERE user_id=?", (t_uid,)).fetchone()
    if not bal_check:
        return await e.respond(f"{P_NO} User not found.")
    # FIX: capture old balance before update so log shows before→after
    old_bal = bal_check[0]
    update_balance(t_uid, amt)
    new_bal_row = db.execute("SELECT balance FROM users WHERE user_id=?", (t_uid,)).fetchone()
    new_bal = new_bal_row[0] if new_bal_row else 0
    await e.respond(f"{P_YES} {'Added' if amt >= 0 else 'Deducted'} {P_INR}{abs(amt)} {'to' if amt >= 0 else 'from'} <code>{t_uid}</code>.\n"
                    f"💼 New balance: <code>{P_INR}{new_bal}</code>")
    # FIX: send log to purchase-log channel
    await log_balance_change(e.sender_id, t_uid, amt, old_bal, new_bal)

@bot.on(events.NewMessage(pattern=r"(?i)^/ban(?:\s+(\d+))?$"))
async def cmd_ban(e):
    if not has_perm(e.sender_id, 'p_ban'): return
    t_uid_str = (e.pattern_match.group(1) or "").strip()
    if not t_uid_str:
        return await e.respond("Usage: <code>/ban &lt;user_id&gt;</code>")
    t_uid = int(t_uid_str)
    row = db.execute("SELECT banned FROM users WHERE user_id=?", (t_uid,)).fetchone()
    if not row: return await e.respond(f"{P_NO} User not found.")
    ns = 0 if row[0] == 1 else 1
    action_word = "Ban 🚫" if ns == 1 else "Unban ✅"
    current_word = "currently BANNED 🚫" if row[0] == 1 else "currently ACTIVE ✅"
    await e.respond(
        f"{P_WARN} <b>Confirm {action_word}</b>\n\n"
        f"{P_ACC} User: <code>{t_uid}</code>\n"
        f"📌 Status: <b>{current_word}</b>\n\n"
        f"Are you sure you want to <b>{action_word}</b> this user?",
        buttons=[
            [Button.inline(f"✅ Yes, {action_word}", f"confirm_ban|{t_uid}|{ns}")],
            [Button.inline("❌ No, Cancel", "cancel_ban")]
        ]
    )

@bot.on(events.NewMessage(pattern=r"(?i)^/discount(?:\s+(\d+)\s+(\d+))?$"))
async def cmd_discount(e):
    if not has_perm(e.sender_id, 'p_settings'): return
    m = e.pattern_match
    if not m.group(1) or not m.group(2):
        return await e.respond("Usage: <code>/discount &lt;user_id&gt; &lt;percent&gt;</code>\n<i>Use 0 to remove discount.</i>")
    t_uid, pct = int(m.group(1)), int(m.group(2))
    with _db_write_lock:
        db.execute("UPDATE users SET discount=? WHERE user_id=?", (pct, t_uid))
        db.commit()
    await e.respond(f"{P_YES} User <code>{t_uid}</code> now has <b>{pct}% discount</b>.")

@bot.on(events.NewMessage(pattern=r"(?i)^/refpct(?:\s+(\d+))?$"))
async def cmd_refpct(e):
    if not has_perm(e.sender_id, 'p_settings'): return
    pct = (e.pattern_match.group(1) or "").strip()
    if not pct:
        cur_pct = db.execute("SELECT value FROM settings WHERE key='ref_percent'").fetchone()
        return await e.respond(f"Usage: <code>/refpct &lt;percent&gt;</code>\n<i>Current: {cur_pct[0] if cur_pct else '3'}%</i>")
    with _db_write_lock:
        db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('ref_percent', ?)", (pct,))
        db.commit()
    await e.respond(f"{P_YES} Referral % set to <b>{pct}%</b>.")

@bot.on(events.NewMessage(pattern=r"(?i)^/usdtrate(?:\s+(.+))?$"))
async def cmd_usdtrate(e):
    if not has_perm(e.sender_id, 'p_settings'): return
    rate_str = (e.pattern_match.group(1) or "").strip()
    if not rate_str:
        return await e.respond(f"Usage: <code>/usdtrate &lt;rate&gt;</code>\n<i>Current: {P_INR}{get_usdt_rate()}</i>")
    try:
        r = float(rate_str.strip())
        with _db_write_lock:
            db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('usdt_rate', ?)", (str(r),))
            db.commit()
        await e.respond(f"{P_YES} USDT rate set to <b>{P_INR}{r}</b>.")
    except ValueError:
        await e.respond(f"{P_NO} Invalid value. Example: <code>/usdtrate 88.5</code>")

@bot.on(events.NewMessage(pattern=r"(?i)^/supporturl(?:\s+(.+))?$"))
async def cmd_supporturl(e):
    if not has_perm(e.sender_id, 'p_settings'): return
    url = (e.pattern_match.group(1) or "").strip()
    if not url:
        return await e.respond("Usage: <code>/supporturl &lt;url or @username&gt;</code>")
    if not url.startswith("http"): url = "https://" + url.replace("@", "t.me/")
    with _db_write_lock:
        db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('support_url', ?)", (url,))
        db.commit()
    await e.respond(f"{P_YES} Support URL set to <code>{url}</code>.")

@bot.on(events.NewMessage(pattern=r"(?i)^/backup(?:\s+(.+))?$"))
async def cmd_backup(e):
    """Feature 11: /backup [filter]
    Filters: balance>N  balance<N  active:N  all
    """
    if not has_perm(e.sender_id, 'p_settings'): return
    raw_filter = (e.pattern_match.group(1) or '').strip().lower()
    base_q = "SELECT * FROM users"
    params = ()
    caption_note = ""
    if raw_filter.startswith('balance>'):
        try:
            thresh = int(raw_filter[len('balance>'):])
            base_q = "SELECT * FROM users WHERE balance > ?"
            params = (thresh,); caption_note = f" (balance > {P_INR}{thresh})"
        except ValueError:
            return await e.reply(f"{P_NO} Usage: /backup balance>100")
    elif raw_filter.startswith('balance<'):
        try:
            thresh = int(raw_filter[len('balance<'):])
            base_q = "SELECT * FROM users WHERE balance < ?"
            params = (thresh,); caption_note = f" (balance < {P_INR}{thresh})"
        except ValueError:
            return await e.reply(f"{P_NO} Usage: /backup balance<50")
    elif raw_filter.startswith('active:'):
        try:
            days = int(raw_filter[len('active:'):])
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            base_q = ("SELECT DISTINCT u.* FROM users u "
                      "INNER JOIN orders o ON o.user_id = u.user_id "
                      "WHERE date(o.date) >= ?")
            params = (cutoff,); caption_note = f" (active last {days}d)"
        except ValueError:
            return await e.reply(f"{P_NO} Usage: /backup active:7")
    elif raw_filter and raw_filter != 'all':
        return await e.reply(
            f"{P_NO} <b>Unknown filter.</b>\n\n"
            "Filters: <code>/backup balance&gt;100</code>  <code>/backup balance&lt;10</code>  "
            "<code>/backup active:7</code>  <code>/backup all</code>"
        )
    _csv_cur = db.cursor()
    _csv_cur.execute(base_q, params) if params else _csv_cur.execute(base_q)
    rows_out = _csv_cur.fetchall()
    with open("users_backup.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([i[0] for i in _csv_cur.description])
        w.writerows(rows_out)
    await bot.send_file(
        e.chat_id, "users_backup.csv",
        caption=f"{P_USERS} <b>Users Backup CSV{caption_note}</b>\nExported <b>{len(rows_out)}</b> user(s)."
    )
    os.remove("users_backup.csv")

# ──────────────────────────────────────────────────────────────────
# Feature 8: /lang
# ──────────────────────────────────────────────────────────────────
@bot.on(events.NewMessage(pattern=r"(?i)^/lang$"))
async def cmd_lang(e):
    uid = e.sender_id
    if not is_bot_online() and not is_admin(uid): return
    ensure_user(uid)
    if is_user_banned(uid): return
    if not await check_channel_joined(uid):
        return await _send_fj_prompt(e, uid)
    cur_lang = get_user_language(uid)
    _ln = {'en': 'English', 'hi': 'हिन्दी', 'ar': 'العربية'}
    btns = [[
        Button.inline(f"{'✅ ' if cur_lang=='en' else ''}🇬🇧 English", "set_lang|en"),
        Button.inline(f"{'✅ ' if cur_lang=='hi' else ''}🇮🇳 हिन्दी", "set_lang|hi"),
        Button.inline(f"{'✅ ' if cur_lang=='ar' else ''}🇸🇦 العربية", "set_lang|ar")
    ]]
    await e.respond(
        f"🌐 <b>Language / भाषा / اللغة</b>\n\nCurrent: <b>{_ln.get(cur_lang, 'English')}</b>\n\nSelect:",
        buttons=btns
    )

# ──────────────────────────────────────────────────────────────────
# Feature 1: /coupon
# ──────────────────────────────────────────────────────────────────
@bot.on(events.NewMessage(pattern=r"(?i)^/coupon(?:\s+(\S+))?$"))
async def cmd_coupon(e):
    uid = e.sender_id
    if not is_bot_online() and not is_admin(uid): return
    ensure_user(uid)
    if is_user_banned(uid): return
    if not await check_channel_joined(uid):
        return await _send_fj_prompt(e, uid)
    code = (e.pattern_match.group(1) or "").strip().upper()
    if not code:
        return await e.reply(
            "🎟 <b>Apply Coupon</b>\n\n"
            "Usage: <code>/coupon YOURCODE</code>\nExample: <code>/coupon SAVE20</code>"
        )
    if user_has_used_coupon(uid, code):
        return await e.reply(_t(uid, 'coupon_already_used'))
    info = get_coupon_info(code)
    if not info:
        return await e.reply(_t(uid, 'coupon_invalid'))
    if info.get('coupon_type') == 'balance':
        if apply_coupon_to_user(uid, code):
            update_balance(uid, info['balance_amount'])
            _nb = db.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
            await e.reply(
                f"✅ <b>Coupon Applied!</b>\n"
                f"💰 <b>₹{info['balance_amount']}</b> added to your balance.\n"
                f"💳 New Balance: <b>₹{_nb[0] if _nb else 0}</b>",
                parse_mode="html"
            )
        else:
            await e.reply(_t(uid, 'coupon_already_used'))
    else:
        set_user_coupon_session(uid, code)
        await e.reply(_t(uid, 'coupon_applied', code=info['code'], pct=info['discount_pct']))

# ──────────────────────────────────────────────────────────────────
# Feature 7: /receipt
# ──────────────────────────────────────────────────────────────────
@bot.on(events.NewMessage(pattern=r"(?i)^/receipt(?:\s+(\d+))?$"))
async def cmd_receipt(e):
    uid = e.sender_id
    if not is_bot_online() and not is_admin(uid): return
    ensure_user(uid)
    if is_user_banned(uid): return
    if not await check_channel_joined(uid):
        return await _send_fj_prompt(e, uid)
    order_id_str = (e.pattern_match.group(1) or "").strip()
    if not order_id_str:
        rows = db.execute(
            "SELECT id, phone, country, year, price, date FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 8",
            (uid,)
        ).fetchall()
        if not rows:
            return await e.reply("📋 <b>No orders found.</b>\n<i>Buy an account first to get a receipt.</i>")
        btns = [[Button.inline(f"#{r[0]} | +{r[1]} | {P_INR}{r[4]}", f"get_receipt|{r[0]}")] for r in rows]
        return await e.reply("🧾 <b>Download Receipt</b>\n\nSelect an order:", buttons=btns)
    oid = int(order_id_str)
    row = db.execute(
        "SELECT id, phone, country, year, price, date FROM orders WHERE id=? AND user_id=?",
        (oid, uid)
    ).fetchone()
    if not row:
        return await e.reply(f"❌ Order #{oid} not found or doesn't belong to you.")
    await _send_receipt(e, uid, row)

async def _send_receipt(event_or_cb, uid: int, row):
    """Generate and send PDF (or text fallback) receipt."""
    order_id = row[0]
    pdf_bytes = generate_receipt_pdf(uid, row)
    if not pdf_bytes:
        phone, country, year, price, date_str = row[1], row[2], row[3], row[4], row[5]
        yr_s = str(year) if year and str(year).strip().isdigit() and int(str(year).strip()) > 2000 else "Unknown"
        text = (
            f"🧾 <b>Purchase Receipt</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 Order No: #{order_id}\n"
            f"📱 Number: +{phone}\n"
            f"🌍 Country: {country}\n"
            f"📅 Year: {yr_s}\n"
            f"💰 Amount: {P_INR}{price}\n"
            f"🕐 Date: {str(date_str)[:16]}\n\n"
            f"<i>Thanks for shopping at Fresh Tg Store!</i>"
        )
        chat_id = getattr(event_or_cb, 'chat_id', uid)
        await bot.send_message(chat_id, text)
        return
    import io as _io2
    class _PDF(_io2.BytesIO):
        name = f"receipt_{order_id}.pdf"
    buf = _PDF(pdf_bytes)
    chat_id = getattr(event_or_cb, 'chat_id', uid)
    await bot.send_file(
        chat_id, buf,
        caption=f"🧾 <b>Receipt #{order_id}</b>\n<i>Fresh Tg Store — Thank you!</i>"
    )

@bot.on(events.NewMessage(pattern=r"(?i)^/admins$"))
async def cmd_admins(e):
    if e.sender_id != ADMIN_ID: return
    rows = db.execute("SELECT user_id FROM admins").fetchall()
    msg = f"{P_USERS} <b>Sub-Admins List</b>\n\n"
    msg += "\n".join(f"{P_ACC} <code>{r[0]}</code>" for r in rows) if rows else "No sub-admins added yet."
    await e.respond(msg)

@bot.on(events.NewMessage(pattern=r"(?i)^/myorders$"))
async def cmd_myorders(e):
    uid = e.sender_id
    if not is_bot_online() and not is_admin(uid):
        return
    ensure_user(uid)
    if is_user_banned(uid): return
    if not await check_channel_joined(uid):
        return await _send_fj_prompt(e, uid)
    await send_purchase_page(e, uid, 1)

@bot.on(events.NewMessage(pattern=r"(?i)^/addstock$"))
async def cmd_addstock(e):
    if not has_perm(e.sender_id, 'p_add_stock'): return
    await admin_actions(FakeCbEvent(e, "addstock"))

@bot.on(events.NewMessage(pattern=r"(?i)^/addzip$"))
async def cmd_addzip(e):
    if not has_perm(e.sender_id, 'p_add_stock'): return
    await admin_actions(FakeCbEvent(e, "addzip"))

@bot.on(events.NewMessage(pattern=r"(?i)^/broadcast$"))
async def cmd_broadcast(e):
    if not has_perm(e.sender_id, 'p_broadcast'): return
    await admin_actions(FakeCbEvent(e, "bcast"))

@bot.on(events.NewMessage(pattern=r"(?i)^/managestock$"))
async def cmd_managestock(e):
    if not has_perm(e.sender_id, 'p_manage_stock'): return
    await send_manage_stock_page(FakeCbEvent(e, "managestock"), 1)

@bot.on(events.NewMessage(pattern=r"(?i)^/autoprice$"))
async def cmd_autoprice(e):
    if not has_perm(e.sender_id, 'p_manage_stock'): return
    await send_autoprice_page(FakeCbEvent(e, "autoprice"), 1)

@bot.on(events.NewMessage(pattern=r"(?i)^/payments$"))
async def cmd_payments(e):
    if not has_perm(e.sender_id, 'p_settings'): return
    await admin_actions(FakeCbEvent(e, "payments"))

@bot.on(events.NewMessage(pattern=r"(?i)^/help$"))
async def cmd_user_help(e):
    uid = e.sender_id
    if not is_bot_online() and not is_admin(uid):
        return await e.respond(f"{P_OFF} <b>Bot is currently under maintenance.</b> Please try again later.")
    ensure_user(uid)
    if is_user_banned(uid): return
    if not await check_channel_joined(uid):
        return await _send_fj_prompt(e, uid)
    await send_help_main(e)

@bot.on(events.NewMessage(pattern=r"(?i)^/status$"))
async def cmd_status(e):
    """Admin-only: live bot health dashboard."""
    if not is_admin(e.sender_id):
        return
    now = datetime.now()
    t = now.strftime('%d %b %Y  %I:%M %p')
    today = now.strftime('%Y-%m-%d')

    # ── DB metrics ──
    total_users  = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    banned_users = db.execute("SELECT COUNT(*) FROM users WHERE banned=1").fetchone()[0]
    total_stock  = db.execute("SELECT COUNT(*) FROM stock WHERE available=1").fetchone()[0]
    total_orders = db.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    today_orders = db.execute(
        "SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE date LIKE ?",
        (today + '%',)
    ).fetchone()
    today_deps = db.execute(
        "SELECT COUNT(*), COALESCE(SUM(amount),0) FROM deposits WHERE status='approved' AND date LIKE ?",
        (today + '%',)
    ).fetchone()
    pending_deps = db.execute("SELECT COUNT(*) FROM deposits WHERE status='pending'").fetchone()[0]

    # ── Live runtime metrics ──
    active_ord_count  = len(active_orders)
    waiting_proof_cnt = len(waiting_proof)
    deposit_input_cnt = len(deposit_input)
    user_spam_cnt     = len(user_spam_cooldown)
    user_locks_cnt    = len(user_locks)
    active_locks_cnt  = sum(1 for lk in user_locks.values() if lk.locked())

    # ── Uptime ──
    uptime_secs = int(time.time() - BOT_START_TIME)
    up_h, rem   = divmod(uptime_secs, 3600)
    up_m, up_s  = divmod(rem, 60)
    uptime_str  = f"{up_h}h {up_m}m {up_s}s"

    bot_on = '🟢 Online' if is_bot_online() else '🔴 Offline'

    # ── UPI / CWallet revenue totals ──
    upi_rev_row  = db.execute("SELECT value FROM settings WHERE key='upi_revenue'").fetchone()
    upi_rev      = int(upi_rev_row[0]) if upi_rev_row and upi_rev_row[0] else 0
    total_dep_row = db.execute(
        "SELECT COALESCE(SUM(amount),0) FROM deposits WHERE status='approved'"
    ).fetchone()
    total_dep_all = int(total_dep_row[0]) if total_dep_row else 0

    msg = (
        f"📊 <b>BOT HEALTH STATUS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🤖 <b>Bot:</b>  {bot_on}\n"
        f"⏱ <b>Uptime:</b>  <code>{uptime_str}</code>\n"
        f"🕐 <b>Time:</b>  {t}\n\n"
        f"┄┄┄┄  🔴 Live State  ┄┄┄┄\n"
        f"Active Orders (OTP listening):  <code>{active_ord_count}</code>\n"
        f"Waiting Proof (deposit):        <code>{waiting_proof_cnt}</code>\n"
        f"Deposit Input (keypad):         <code>{deposit_input_cnt}</code>\n"
        f"Spam-Cooldown Users:            <code>{user_spam_cnt}</code>\n"
        f"User Locks (total / active):    <code>{user_locks_cnt}</code> / <code>{active_locks_cnt}</code>\n\n"
        f"┄┄┄┄  👥 Users  ┄┄┄┄\n"
        f"Total Users:   <code>{total_users}</code>\n"
        f"Banned:        <code>{banned_users}</code>\n\n"
        f"┄┄┄┄  📦 Stock & Orders  ┄┄┄┄\n"
        f"Available Stock:   <code>{total_stock}</code>\n"
        f"All-time Orders:   <code>{total_orders}</code>\n\n"
        f"┄┄┄┄  📅 Today  ┄┄┄┄\n"
        f"Orders:            <code>{today_orders[0]}</code>  (₹<code>{today_orders[1]}</code>)\n"
        f"Deposits Approved: <code>{today_deps[0]}</code>  (₹<code>{today_deps[1]}</code>)\n"
        f"Pending Deposits:  <code>{pending_deps}</code>\n\n"
        f"┄┄┄┄  💰 Revenue  ┄┄┄┄\n"
        f"UPI Revenue:       ₹<code>{upi_rev}</code>\n"
        f"Total Approved Deposits (all-time): ₹<code>{total_dep_all}</code>"
    )
    await e.respond(msg)

@bot.on(events.NewMessage(pattern=r"(?i)^/pendingdeps$"))
async def cmd_pendingdeps(e):
    if not has_perm(e.sender_id, 'p_bal'): return
    await send_pending_deposits_page(FakeCbEvent(e, "pendingdeps"), 1)

@bot.on(events.NewMessage(pattern=r"(?i)^/cmds$"))
async def cmd_help(e):
    if not is_admin(e.sender_id): return
    msg = (
        f"💻 <b>Admin Commands</b>\n\n"

        f"<b>📊 Info &amp; Stats</b>\n"
        f"/status — Quick bot status &amp; today's stats\n"
        f"/stats — View bot statistics\n"
        f"/daystats — Today's users, deposits &amp; sales\n"
        f"/userinfo &lt;id&gt; — Lookup a user\n\n"

        f"<b>💰 Balance &amp; Users</b>\n"
        f"/addbal &lt;id&gt; &lt;amount&gt; — Add/deduct balance\n"
        f"/pendingdeps — View &amp; approve pending deposits\n"
        f"/ban &lt;id&gt; — Ban or unban a user\n"
        f"/discount &lt;id&gt; &lt;%&gt; — Set user discount\n\n"

        f"<b>⚙️ Settings</b>\n"
        f"/togglebot — Toggle bot ON/OFF\n"
        f"/usdtrate &lt;rate&gt; — Set USDT rate\n"
        f"/refpct &lt;%&gt; — Set referral %\n"
        f"/supporturl &lt;url&gt; — Set support URL\n\n"

        f"<b>📦 Stock</b>\n"
        f"/addstock — Add single account\n"
        f"/addzip — Bulk add via ZIP\n"
        f"/managestock — Manage existing stock\n"
        f"/autoprice — Set auto prices\n\n"

        f"<b>📢 Other</b>\n"
        f"/broadcast — Send message to all users\n"
        f"/backup — Download users CSV\n"
        f"/payments — Manage payment methods\n"
        f"/admins — List sub-admins\n"
        f"/cmds — Show this list"
    )
    await e.respond(msg)

@bot.on(events.NewMessage(pattern=r"(?i)^/cancel$"))
async def cmd_cancel(e):
    """Global /cancel — stops any active admin conversation and clears all pending user states."""
    if not e.is_private: return
    uid = e.sender_id
    ensure_user(uid)

    # Cancel any active admin conversation task for this user
    _cancel_task = _active_admin_conv.pop(uid, None)
    task_was_live = _cancel_task and not _cancel_task.done()
    if task_was_live:
        _cancel_task.cancel()

    # Clear all in-memory pending states regardless
    deposit_input.pop(uid, None)
    if waiting_proof.pop(uid, None) is not None:
        _clear_waiting_proof_db(uid)
    session_buy_state.pop(uid, None)
    admin_dep_state.pop(uid, None)

    if task_was_live:
        await e.respond(
            f"{P_NO} <b>Action Cancelled!</b>\n\n"
            f"✅ Your previous operation has been stopped and all pending states cleared.\n"
            f"Tap any button or use /start to continue."
        )
    else:
        await e.respond(
            f"{P_NO} <b>Nothing active to cancel.</b>\n\n"
            f"No running operation was found. All pending states cleared anyway.\n"
            f"Tap any button or use /start to continue."
        )

@bot.on(events.NewMessage(pattern=r"(?i)^/commands?$"))
async def cmd_user_commands(e):
    uid = e.sender_id
    if not is_bot_online() and not is_admin(uid):
        return await e.respond(f"{P_OFF} <b>Bot is currently under maintenance.</b> Please try again later.")
    ensure_user(uid)
    if is_user_banned(uid): return
    if not await check_channel_joined(uid):
        return await _send_fj_prompt(e, uid)

    msg = (
        f"💻 <b>User Commands</b>\n\n"
        f"<b>🚀 Getting Started</b>\n"
        f"/start — Open bot & show main menu\n"
        f"/commands — Show this commands list\n"
        f"/help — Help center & FAQ topics\n\n"

        f"<b>🛒 Shopping</b>\n"
        f"🛒 Buy Account — Browse &amp; buy OTP accounts by country\n"
        f"📁 Buy Sessions — Download bulk .session files (ZIP)\n"
        f"/myorders — View your full order history\n\n"

        f"<b>💰 Wallet &amp; Deposits</b>\n"
        f"💰 Deposit — Add funds (UPI / CWallet / other methods)\n"
        f"💳 My Balance — Check your current wallet balance\n"
        f"👤 My Profile — Profile details &amp; referral link\n"
        f"📊 My Stats — Purchase stats &amp; referral earnings\n\n"

        f"<b>📦 Inventory</b>\n"
        f"📦 Stock Info — View all available countries &amp; stock counts\n\n"

        f"<b>📞 Help &amp; Support</b>\n"
        f"📢 Support — Contact admin &amp; support links\n"
        f"❓ Help — FAQ, how-to guides &amp; OTP tips\n\n"

        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Tap any menu button below the keyboard to use these features.</i>"
    )
    await e.respond(msg)

# ================= CORE EVENT ROUTERS =================
@bot.on(events.NewMessage(pattern=r"(?i)^/start(?:@\w+)?(?:\s+.*)?$"))
async def handle_start(e):
    try:
        uid = e.sender_id
        if not uid: return

        if not is_bot_online() and not is_admin(uid):
            return await e.respond(f"{P_OFF} <b>Bot is currently under maintenance.</b> Please try again later.")

        is_brand_new = db.execute("SELECT user_id FROM users WHERE user_id=?", (uid,)).fetchone() is None
        ensure_user(uid)
        if is_user_banned(uid): return

        # Clear ALL mid-flow states so /start always gives a clean slate
        session_buy_state.pop(uid, None)
        deposit_input.pop(uid, None)
        admin_dep_state.pop(uid, None)
        if waiting_proof.pop(uid, None) is not None:
            _clear_waiting_proof_db(uid)

        try:
            _sender_obj = await e.get_sender()
            _uname = getattr(_sender_obj, 'username', None)
        except Exception:
            _sender_obj = None
            _uname = None
        asyncio.create_task(log_user_activity(uid, _uname, is_brand_new))

        text = e.text or ''
        if len(text.split()) > 1:
            start_param = text.split()[1]
            if start_param.startswith("ref_"):
                ref = start_param.replace("ref_", "")
                if ref.isdigit() and int(ref) != uid:
                    with _db_write_lock:
                        db.execute("UPDATE users SET referred_by=? WHERE user_id=? AND referred_by IS NULL", (int(ref), uid))
                        db.commit()

        if not await check_channel_joined(uid):
            # /start is an explicit retry action. Clear the prompt cooldown so
            # a previous failed/old force-join prompt cannot make /start appear
            # to do nothing.
            force_join_prompt_cooldown.pop(uid, None)
            return await _send_fj_prompt(e, uid)

        row = db.execute("SELECT terms_accepted FROM users WHERE user_id=?", (uid,)).fetchone()
        terms_acc = row[0] if row else 0
        if not terms_acc:
            msg = f"{P_DOC} <b>TERMS & CONDITIONS</b>\nPlease read and accept our Terms & Conditions before using the bot."
            btns = [
                [Button.url("📜 Read Terms & Conditions", TERMS_URL)],
                [Button.inline("✅ Accept", "tc_accept"), Button.inline("❌ Reject", "tc_reject")]
            ]
            return await e.respond(msg, buttons=btns)

        welcome = get_welcome_message()
        if welcome:
            _ws = _sender_obj or await e.get_sender()
            welcome = format_welcome(welcome, _ws)
            w_btn_text, w_btn_url = get_welcome_button()
            w_btns = [[Button.url(w_btn_text, w_btn_url)]] if w_btn_text and w_btn_url else None
            # Send photo attached to welcome message as caption (if set)
            _sp_row = db.execute("SELECT value FROM settings WHERE key='start_photo'").fetchone()
            _sp = _sp_row[0] if _sp_row and _sp_row[0] else None
            # FIX: use blob fallback — local file is unreliable after Termux restart
            _sp_sent = None
            if _sp or _load_media_blob('start_photo'):
                try:
                    async def _sp_send(file, **kw): return await bot.send_file(uid, file, **kw)
                    _sp_sent = await _send_with_blob_fallback(
                        _sp_send, 'start_photo', _sp,
                        caption=welcome, buttons=w_btns, parse_mode='html'
                    )
                except Exception as _spe:
                    logger.debug(f'Could not send start photo: {_spe}')
            if not _sp_sent:
                await bot.send_message(uid, welcome, buttons=w_btns, link_preview=False)
            keyboard = get_persistent_menu(uid)
            if keyboard:
                await bot.send_message(uid, "👇 <b>Choose an option:</b>", buttons=keyboard)
        else:
            await send_main_menu(e, uid, sender=_sender_obj)
    except Exception as ex:
        logger.error(f"Start Error for uid={e.sender_id}: {ex}", exc_info=True)
        try:
            await e.respond("⚠️ Something went wrong. Please try again or contact support.")
        except Exception as _e:
            logger.debug(f'Suppressed non-critical error: {_e}')

@bot.on(events.NewMessage())
async def handle_all_messages(e):
    try:
        uid = e.sender_id
        if not uid: return
        if not e.is_private: return
        if getattr(e, 'text', None) and e.text.startswith('/'): return
        if not is_bot_online() and not is_admin(uid):
            return await e.respond(f"{P_OFF} <b>Bot is currently under maintenance.</b> Please try again later.")
        
        ensure_user(uid)
        if is_user_banned(uid): return

        # Ignore arbitrary messages while force-join is pending.  The /start
        # handler and supported commands display the single prompt instead.
        if not await check_channel_joined(uid):
            return

        if uid in waiting_proof:
            if e.photo:
                # FIX Bug 6: check expiry before accepting the proof — the background
                # proof_timeout_task runs every 30s, leaving a race window where an
                # expired entry could otherwise still be processed and submitted.
                _proof_info_check = waiting_proof.get(uid, {})
                if time.time() >= _proof_info_check.get('expires_at', 0):
                    waiting_proof.pop(uid, None)
                    _clear_waiting_proof_db(uid)
                    await e.reply(
                        f"⌛ <b>Session Expired.</b>\n\n"
                        f"Your deposit window timed out. Please tap 💰 Deposit to start a new request."
                    )
                    return
                info = waiting_proof.pop(uid)
                _clear_waiting_proof_db(uid)
                final_amt = info['amount']
                # Guard: amount must be a positive integer
                if not isinstance(final_amt, (int, float)) or final_amt <= 0:
                    logger.error(f"handle_all_messages: invalid proof amount uid={uid} amt={final_amt}")
                    await e.reply(f"{P_NO} Invalid deposit amount. Please start over.")
                    return
                final_amt = int(final_amt)
                with _db_write_lock:
                    _dep_ins = db.execute(
                        "INSERT INTO deposits (user_id, amount, method_name, status) VALUES (?,?,?,?)",
                        (uid, final_amt, info['method'], "pending")
                    )
                    db.commit()
                dep_id = _dep_ins.lastrowid
                # Permanently store proof so it can be audited even if admin channel fails
                _proof_data = str(getattr(e.photo, 'id', None))
                _save_payment_proof(uid, info['amount'], info['method'], 'photo', _proof_data or '', dep_id)
                await e.reply(f"{P_YES} Deposit Request Submitted! Wait for Admin Approval.")
                cap = (
                    f"🔔 <b>NEW DEPOSIT REQUEST</b>\n"
                    f"{P_ACC} User: <code>{uid}</code>\n"
                    f"{P_MONEY} Request: <b>{P_INR}{info['amount']}</b>\n"
                    f"{P_CARD} Method: {info['method']}\n"
                    f"{P_ID} Ref: <code>{dep_id}</code>"
                )
                btns = [
                    [Button.inline(f"✅ Accept (₹{final_amt})", f"dep_acc|{dep_id}|{uid}|{info['method']}|exact|{final_amt}"),
                     Button.inline("❌ Reject", f"dep_rej|{dep_id}|{uid}")],
                    [Button.inline("📝 Custom Amount", f"dep_acc|{dep_id}|{uid}|{info['method']}|custom|0")]
                ]
                try:
                    await bot.send_message(get_payment_log_channel(), cap, file=e.media, buttons=btns)
                except Exception as log_err:
                    logger.error(f"Failed to log deposit to channel: {log_err}")
                    try:
                        await bot.send_message(
                            ADMIN_ID,
                            cap + "\n\n⚠️ <i>(Screenshot could not be forwarded — check user DMs)</i>"
                                  "\n\n⚠️ <b>Log channel send failed — please approve manually!</b>",
                            buttons=btns
                        )
                    except Exception as fb_err:
                        logger.error(f"Fallback admin deposit notify also failed: {fb_err}")
            else:
                await e.reply(
                    f"📸 <b>Please send a Screenshot!</b>\n\n"
                    f"Send a clear screenshot of your payment to submit your deposit request.\n\n"
                    f"<i>Tap ❌ Cancel below to cancel this request.</i>",
                    buttons=[[Button.inline("❌ Cancel", "cancel_action")]]
                )
            return

        text = e.text or ""
        if not text: return

        if is_admin(uid) and uid in admin_dep_state:
            st = admin_dep_state[uid]
            if st['step'] == 'wait_reason':
                t_uid, dep_id, msg_id = st['target_uid'], st['dep_id'], st['msg_id']
                with _db_write_lock:
                    _rej_rc = db.execute(
                        "UPDATE deposits SET status='rejected' WHERE id=? AND status='pending'",
                        (dep_id,)
                    )
                    if _rej_rc.rowcount == 0:
                        # Already processed by another admin
                        admin_dep_state.pop(uid, None)
                        await e.reply(f"{P_WARN} Deposit already processed by another admin.")
                        return
                    db.commit()
                
                try: await bot.edit_message(get_payment_log_channel(), msg_id, f"{P_NO} <b>REJECTED USER {t_uid}</b>\nReason: {html.escape(text)}", buttons=None)
                except Exception as _e:
                    logger.debug(f'Suppressed non-critical error: {_e}')
                
                await bot.send_message(int(t_uid), f"{P_NO} <b>Deposit Rejected!</b>\n📋 Reason: {html.escape(text)}")
                await e.reply(f"{P_YES} Rejection reason sent.")
                admin_dep_state.pop(uid)
                return

        if "Buy Account" in text or "Buy Sessions" in text or "Deposit" in text or "My Profile" in text or "My Balance" in text or "My Stats" in text or "Support" in text or "Help" in text or "Admin Panel" in text or "Stock Info" in text:
            session_buy_state.pop(uid, None)
            deposit_input.pop(uid, None)
            if waiting_proof.pop(uid, None) is not None:
                _clear_waiting_proof_db(uid)
            admin_dep_state.pop(uid, None)

        # ── Busy-state guard: user already has an active OTP order ─────────────
        _busy_phone = get_user_active_phone(uid)
        if _busy_phone and ("Buy Account" in text or "Buy Sessions" in text):
            await e.reply(
                f"⏳ <b>You already have an active order in progress!</b>\n\n"
                f"📱 <b>Phone:</b> <code>{_busy_phone}</code>\n\n"
                f"Please wait for the OTP or let it expire (auto-cancels in 10 min).\n"
                f"Once it's done you can purchase again.",
                buttons=[[Button.inline("🚪 Logout & Cancel Order", f"logout_bot|{_busy_phone}")]]
            )
            return

        if uid in session_buy_state:
            state = session_buy_state[uid]
            try:
                qty = int(re.sub(r'[^\d]', '', text))
                if qty < 1: raise ValueError
                live_stock_row = db.execute(
                    "SELECT COUNT(*) FROM stock WHERE country_name=? AND price=? AND category=? AND available=1",
                    (state['country'], state['price'], state.get('category', 'Fresh'))
                ).fetchone()
                live_stock = live_stock_row[0] if live_stock_row else 0
                state['stock'] = live_stock
                if qty > live_stock: return await e.respond(f"{P_WARN} <b>Not enough stock!</b> Only {live_stock} available now.")
                
                _eff_disc = get_effective_discount(uid)
                _tier_price = apply_qty_discount(state['price'], qty, _eff_disc)
                total_cost = qty * _tier_price
                # Update state price so process_bulk_sessions uses the discounted per-unit cost
                state = dict(state); state['price'] = _tier_price
                    
                bal_row = db.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
                user_bal = bal_row[0] if bal_row else 0
                if user_bal < total_cost: return await e.respond(f"{P_NO} <b>Insufficient Balance!</b>\nYou need {P_INR}{total_cost} to buy {qty} sessions.")

                session_buy_state.pop(uid)
                await process_bulk_sessions(e, uid, qty, state, total_cost)
                return
            except ValueError: return await e.respond(f"{P_NO} Please enter a valid number.")

        if uid in deposit_input and deposit_input[uid]['step'] == 'wait_amt':
            try:
                amt = int(re.sub(r'[^\d]', '', text))
                if amt < 10: return await e.reply(f"{P_WARN} Minimum Deposit is ₹10.")
                method = deposit_input[uid]['method']
                waiting_proof[uid] = {'amount': amt, 'method': method, 'expires_at': time.time() + 600}
                deposit_input.pop(uid)
                
                rate = get_usdt_rate()
                usdt_amt = round(amt / rate, 2)
                rate_text = f"\n\n{P_MONEY} <b>Amount to Pay:</b> {P_INR}{amt} (~{P_USDT}{usdt_amt} USDT)\n💱 <i>Exchange Rate: {P_INR}{rate} = $1</i>"
                
                row = db.execute("SELECT caption, qr_file_id FROM custom_payments WHERE name=?", (method,)).fetchone()
                sent_cust_msg = None
                if row:
                    cap = row[0] + f"{rate_text}\n\n👇 <b>After paying, send a clear Screenshot here:</b>"
                    btns = [[Button.inline("❌ Cancel", "cancel_action")]]
                    # FIX: also support HTTP URLs for custom payment QR
                    _cust_qr = row[1]
                    # FIX: use DB blob (survives Termux restarts), fall back to legacy file path
                    async def _cust_send_fn(file, **kw): return await bot.send_file(e.chat_id, file, **kw)
                    sent_cust_msg = await _send_with_blob_fallback(
                        _cust_send_fn, f'custom_pay_qr_{method}',
                        _cust_qr if _cust_qr else None,
                        caption=cap, buttons=btns
                    )
                    if not sent_cust_msg:
                        sent_cust_msg = await e.reply(cap, buttons=btns)
                else: sent_cust_msg = await e.reply(f"{P_CARD} <b>{method} Deposit</b>{rate_text}\n\n👇 Send Screenshot here:", buttons=[[Button.inline("❌ Cancel", "cancel_action")]])
                if sent_cust_msg and uid in waiting_proof:
                    # BUG FIX: guard against race where waiting_proof[uid] was cleared
                    waiting_proof[uid]['msg_id'] = sent_cust_msg.id
                    _save_waiting_proof(uid, waiting_proof[uid])
            except ValueError: await e.respond(f"{P_NO} Please enter a valid number in {P_INR} (INR).")
            return

        if "Buy Account" in text:
            if not is_btn_enabled('buy_account'): return await e.reply(f"{P_OFF} <b>Buy Account is currently unavailable.</b>")
            await show_category_select(e, 'single')
        elif "Buy Sessions" in text:
            if not is_btn_enabled('buy_sessions'): return await e.reply(f"{P_OFF} <b>Buy Sessions is currently unavailable.</b>")
            await show_category_select(e, 'bulk')
        elif "Deposit" in text:
            if not is_btn_enabled('deposit'): return await e.reply(f"{P_OFF} <b>Deposits are currently unavailable.</b>")
            await deposit_menu(e)
        elif "My Profile" in text:
            if not is_btn_enabled('my_profile'): return await e.reply(f"{P_OFF} <b>Profile is currently unavailable.</b>")
            await profile_handler(e)
        elif "My Balance" in text:
            if not is_btn_enabled('my_balance'): return await e.reply(f"{P_OFF} <b>Balance check is currently unavailable.</b>")
            row = db.execute("SELECT balance, total_deposited, discount FROM users WHERE user_id=?", (uid,)).fetchone()
            if not row: return await e.reply("⚠️ Account not found. Please type /start first.")
            bal, dep, discount = row
            disc_msg = f"\n{P_GIFT} <b>Active Discount:</b> <code>{discount}% OFF</code>" if discount > 0 else ""
            await e.reply(
                f"💳 <b>My Balance</b>\n\n"
                f"{P_MONEY} <b>Available Balance:</b> <code>{P_INR}{bal}</code>\n"
                f"{P_CARD} <b>Total Deposited:</b> <code>{P_INR}{dep}</code>"
                f"{disc_msg}\n\n"
                f"<i>Tap 💰 Deposit to add funds to your account.</i>"
            )
        elif "My Stats" in text:
            if not is_btn_enabled('my_stats'): return await e.reply(f"{P_OFF} <b>Stats are currently unavailable.</b>")
            await stats_handler(e)
        elif "Support" in text:
            if not is_btn_enabled('support'): return await e.reply(f"{P_OFF} <b>Support is currently unavailable.</b>")
            _join_urls = get_join_urls()
            await e.reply(f"{P_ON} <b>OTP Shop Support & Relevant Information</b>\n\n{P_WARN} For Support Contact Admin ..", buttons=[[Button.url("📩 Support", get_support_url())], [Button.url("📜 Terms & Conditions", TERMS_URL)], [Button.url("📢 Channel", _join_urls[0] if _join_urls else "https://t.me/")]])
        elif "Help" in text:
            if not is_btn_enabled('help'): return await e.reply(f"{P_OFF} <b>Help is currently unavailable.</b>")
            await send_help_main(e)
        elif "Stock Info" in text:
            if not is_btn_enabled('stock_info'): return await e.reply(f"{P_OFF} <b>Stock Info is currently unavailable.</b>")
            await show_stock_info(e)
        elif "Admin Panel" in text:
            if is_admin(uid): await admin_panel_handler(e)
        elif "Language" in text:
            # Feature 8: language selector
            cur_lang = get_user_language(uid)
            _ln = {'en': 'English', 'hi': 'हिन्दी', 'ar': 'العربية'}
            _lb = [[
                Button.inline(f"{'✅ ' if cur_lang=='en' else ''}🇬🇧 English", "set_lang|en"),
                Button.inline(f"{'✅ ' if cur_lang=='hi' else ''}🇮🇳 हिन्दी", "set_lang|hi"),
                Button.inline(f"{'✅ ' if cur_lang=='ar' else ''}🇸🇦 العربية", "set_lang|ar")
            ]]
            await e.reply(
                f"🌐 <b>Select Language</b>\n<i>Current: {_ln.get(cur_lang, 'English')}</i>",
                buttons=_lb
            )
        elif "My Favourites" in text or "Favourites" in text:
            # Feature 6: show favourite countries
            _favs = get_user_fav_countries(uid)
            if not _favs:
                await e.reply(
                    "⭐ <b>My Favourite Countries</b>\n\n"
                    "<i>No favourites yet.\nTap ☆ Fav on any country while browsing Buy Account.</i>"
                )
            else:
                _fl = "\n".join(f"{get_flag_by_country_name(c)} {c}" for c in _favs)
                await e.reply(
                    f"⭐ <b>My Favourite Countries</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{_fl}\n\n<i>These appear at the top when you browse Buy Account.</i>"
                )
        elif not is_admin(uid):
            # ── Catch-all: regular user sent text that doesn't match any flow or
            # button — respond with a nudge instead of staying silent.
            # Admins are excluded because their text messages are often replies
            # to active bot.conversation() prompts (discount %, reason, etc.)
            # and those conversations handle the input themselves.
            await e.reply(
                f"👋 <b>Not sure what you mean.</b>\n\n"
                f"Use the buttons below to navigate, or tap /start to return to the main menu.",
                buttons=[[Button.inline("🏠 Main Menu", "noop_main_menu")]]
            )

    except Exception as ex:
        logger.error(f"Message Error uid={e.sender_id}: {ex}", exc_info=True)

@bot.on(events.CallbackQuery)
async def handle_callback_query(e):
    try:
        uid = e.sender_id
        if not is_bot_online() and not is_admin(uid):
            return await e.answer("⚙️ Bot is under maintenance.", alert=True)
            
        ensure_user(uid)
        now = time.time()
        if uid in user_spam_cooldown and now - user_spam_cooldown[uid] < 0.5:
            return await e.answer("⚠️ Please slow down! Don't spam buttons.", alert=True)
        user_spam_cooldown[uid] = now

        if is_user_banned(uid): return await e.answer("🚫 BANNED", alert=True)
        data = e.data.decode()

        _fj_exempt = ("verify_join", "tc_accept", "tc_reject")
        if data not in _fj_exempt and not await check_channel_joined(uid):
            await e.answer("⚠️ You must join our channel(s) first!", alert=True)
            return

        if data == "verify_join":
            # Best-effort membership check via Telegram API.
            # If the bot has admin rights, UserNotParticipantError means the user
            # definitely hasn't joined. If bot lacks admin rights (ChatAdminRequiredError)
            # or any other error, we trust the user and let them through.
            denied_url = None
            for en in get_force_join_entries():
                if en['type'] == 'bot':
                    continue  # can't verify bot starts from bot side
                try:
                    entity = await bot.get_entity(int(en['cid']))
                except Exception:
                    continue  # can't resolve channel entity, skip
                try:
                    try:
                        participant = await bot.get_input_entity(uid)
                    except Exception:
                        participant = uid
                    await bot(GetParticipantRequest(channel=entity, participant=participant))
                except UserNotParticipantError:
                    denied_url = en['url']
                    break
                except Exception as _fj_err:
                    _err_name = type(_fj_err).__name__
                    # Only trust user if bot genuinely lacks admin rights (can't verify)
                    if any(k in _err_name for k in ('AdminRequired', 'ChatAdmin', 'Rights', 'Forbidden', 'ChatWriteForbidden')):
                        continue
                    # Network, timeout, or unexpected error — deny to prevent bypass
                    logger.warning(f"force_join check error uid={uid} ch={en['cid']}: {_err_name}: {_fj_err}")
                    denied_url = en['url']
                    break
            if denied_url:
                return await e.answer("⚠️ Please join all required channels first!", alert=True)
            # Mark user as verified in DB
            force_join_prompt_cooldown.pop(uid, None)
            with _db_write_lock:
                db.execute("UPDATE users SET fj_verified=1 WHERE user_id=?", (uid,))
                db.commit()
            row = db.execute("SELECT terms_accepted FROM users WHERE user_id=?", (uid,)).fetchone()
            terms = row[0] if row else 0
            if not terms:
                msg = "📜 <b>TERMS & CONDITIONS</b>\nPlease read and accept our Terms & Conditions before using the bot."
                btns = [[Button.url("📜 Read Terms & Conditions", TERMS_URL)], [Button.inline("✅ Accept", "tc_accept"), Button.inline("❌ Reject", "tc_reject")]]
                # FIX: answer the callback before editing so Telegram clears the spinner
                await e.answer("✅ Verified! Please accept the Terms & Conditions.", alert=False)
                try: await e.edit(msg, buttons=btns)
                except MessageNotModifiedError: pass
                return
            # FIX: answer the callback query before proceeding to clear the spinner
            await e.answer("✅ Verified! Welcome!", alert=False)
            await send_main_menu(e, uid)

        elif data == "tc_accept":
            with _db_write_lock:
                db.execute("UPDATE users SET terms_accepted=1 WHERE user_id=?", (uid,))
                db.commit()
            await e.answer("✅ Terms Accepted!", alert=True)
            welcome = get_welcome_message()
            if welcome:
                _sender = await e.get_sender()
                welcome = format_welcome(welcome, _sender)
                w_btn_text, w_btn_url = get_welcome_button()
                w_btns = [[Button.url(w_btn_text, w_btn_url)]] if w_btn_text and w_btn_url else None
                await bot.send_message(uid, welcome, buttons=w_btns, link_preview=False)
                keyboard = get_persistent_menu(uid)
                if keyboard:
                    await bot.send_message(uid, "👇 <b>Choose an option:</b>", buttons=keyboard)
            else:
                await send_main_menu(e, uid)

        elif data == "tc_reject":
            try: await e.edit(f"{P_NO} You cannot use the bot without accepting the terms.")
            except MessageNotModifiedError: pass
            
        elif data == "cancel_action":
            deposit_input.pop(uid, None)
            if waiting_proof.pop(uid, None) is not None: _clear_waiting_proof_db(uid)
            session_buy_state.pop(uid, None); admin_dep_state.pop(uid, None)
            try: await e.edit(f"{P_NO} <b>Cancelled.</b>")
            except MessageNotModifiedError: await e.answer()

        elif data.startswith("cat_sel|"):
            p = data.split("|", 2)
            flow = p[1]
            cat  = p[2] if len(p) > 2 else 'Fresh'
            await e.answer()
            await show_countries(e, flow, 1, cat)

        elif data.startswith("back_cat|"):
            flow = data.split("|", 1)[1]
            await e.answer()
            await show_category_select(e, flow)

        elif data.startswith("pg_c|"):
            p = data.split("|")
            cat = p[3] if len(p) > 3 else 'Fresh'
            try:
                _pg = max(1, int(p[2]))
            except (ValueError, IndexError):
                return await e.answer("⚠️ Invalid page.", alert=True)
            await show_countries(e, p[1], _pg, cat)

        elif data.startswith("bc|"):
            p = data.split("|", 3)
            if len(p) < 3: return await e.answer("⚠️ Invalid action.", alert=True)
            cat = p[3] if len(p) > 3 else 'Fresh'
            await show_years(e, p[1], p[2], cat)

        elif data.startswith("by|"):
            p = data.split("|", 5)
            if len(p) < 5: return await e.answer("⚠️ Invalid action.", alert=True)
            cat = p[5] if len(p) > 5 else 'Fresh'
            if p[1] == 'single':
                _by_busy = get_user_active_phone(uid)
                if _by_busy:
                    return await e.answer(
                        f"⏳ Active order in progress for {_by_busy}! Wait for the OTP or let it expire (10 min).",
                        alert=True
                    )
                await confirm_purchase(e, p[2], p[3], p[4], cat)
            else: await init_session_purchase(e, p[2], p[3], p[4], cat)

        elif data.startswith("buy_cf|"):
            p = data.split("|", 4)
            if len(p) < 4: return await e.answer("⚠️ Invalid action.", alert=True)
            cat = p[4] if len(p) > 4 else 'Fresh'
            # Guard: block new purchase if user already has an active OTP order
            _cf_busy = get_user_active_phone(uid)
            if _cf_busy:
                return await e.answer(
                    f"⏳ Active order in progress for {_cf_busy}! Wait for the OTP or let it expire (10 min).",
                    alert=True
                )
            await process_purchase(e, p[1], p[2], p[3], cat)

        elif data.startswith("get_otp_again|"):
            _otp_parts = data.split("|", 1)
            if len(_otp_parts) < 2: return await e.answer("⚠️ Invalid action.", alert=True)
            phone = _otp_parts[1]
            if phone not in active_orders:
                return await e.answer("⚠️ Session already logged out or expired.", alert=True)
            
            order = active_orders[phone]
            client = order['client']
            start_time = order['start_time']
            
            await e.answer("🔄 Fetching latest OTP...", alert=False)
            try:
                msgs = await client.get_messages(777000, limit=5)
                latest_code = None
                for m in msgs:
                    if m.date.timestamp() > start_time - 10:
                        if m.message and "Login detected" not in m.message:
                            _m2 = re.search(OTP_REGEX, m.message)
                            if _m2:
                                latest_code = _m2.group(1)  # group(1) = captured digits
                            break
                
                if latest_code:
                    twofa_text = f"{P_2FA} <b>2FA:</b> <code>{order['twofa']}</code>" if order['twofa'] != "None" else "🔓 <b>2FA:</b> <code>Disabled (No Password)</code>"
                    # FIX: include year in Get-OTP-Again message (was missing)
                    _yr = order.get('year', 0)
                    _yr_line = f"📅 <b>Acc Year:</b>  <code>{_yr}</code>\n" if _yr and _yr > 2000 else ""
                    msg = (f"{P_YES} <b>Latest OTP Fetched!</b>\n\n"
                           f"{P_PHONE} <b>Phone:</b> <code>{phone}</code>\n"
                           f"{P_FLAG} <b>Country:</b> {order['c_icon']} {order['country']}\n"
                           f"{_yr_line}"
                           f"{P_OTP} <b>OTP:</b> <code>{latest_code}</code>\n"
                           f"{twofa_text}")
                    try: await e.edit(msg, buttons=[[Button.inline("🔄 Get OTP Again", f"get_otp_again|{phone}")], [Button.inline("🚪 Finish & Logout", f"logout_bot|{phone}")]])
                    except MessageNotModifiedError: pass
                else:
                    await e.answer("⏳ No new OTP found yet. Try again in a few seconds.", alert=True)
            except Exception:
                await e.answer("❌ Error fetching OTP.", alert=True)

        elif data.startswith("logout_bot|"):
            _lo_parts = data.split("|", 1)
            if len(_lo_parts) < 2: return await e.answer("⚠️ Invalid action.", alert=True)
            phone = _lo_parts[1]
            if phone in active_orders:
                order = active_orders.pop(phone)
                _clear_active_order_db(phone)
                try: await order['client'].log_out()
                except Exception as _e:
                    logger.debug(f'Suppressed non-critical error: {_e}')
                try: await order['client'].disconnect()
                except Exception as _e:
                    logger.debug(f'Suppressed non-critical error: {_e}')
                delete_session_files(order['sess'])
                await e.edit(f"{P_YES} <b>Session Finished & Logged out successfully.</b>")
            else:
                await e.answer("⚠️ No active order found or already logged out.", alert=True)
        
        elif data == "help_main":
            await send_help_main(e, edit=True)

        elif data.startswith("help_"):
            topic_key = data[5:]
            await send_help_topic(e, topic_key)

        elif data.startswith("page_purchases_"):
            try:
                _pg = max(1, int(data.split("_")[2]))
            except (ValueError, IndexError):
                return await e.answer("⚠️ Invalid page.", alert=True)
            await send_purchase_page(e, uid, _pg)
        elif data == "back_to_stats": await stats_handler(e, is_callback=True)
        elif data == "my_orders_cb": await send_purchase_page(e, uid, 1)
        elif data == "view_referrals": await view_referrals(e)

        elif data.startswith("wishlist_add|"):
            c_wish = data.split("|", 1)[1]
            existing = db.execute("SELECT 1 FROM wishlist WHERE user_id=? AND country_name=?", (uid, c_wish)).fetchone()
            if existing:
                await e.answer(f"⚠️ {c_wish} is already in your wishlist!", alert=True)
            else:
                with _db_write_lock:
                    db.execute("INSERT OR IGNORE INTO wishlist (user_id, country_name) VALUES (?,?)", (uid, c_wish))
                    db.commit()
                await e.answer(f"🔔 Added {c_wish} to your wishlist! You'll be notified when stock arrives.", alert=True)

        elif data.startswith("wishlist_rm|"):
            c_wish = data.split("|", 1)[1]
            with _db_write_lock:
                db.execute("DELETE FROM wishlist WHERE user_id=? AND country_name=?", (uid, c_wish))
                db.commit()
            await e.answer(f"✅ Removed {c_wish} from your wishlist.", alert=True)

        elif data == "my_wishlist":
            wl_rows = db.execute("SELECT country_name FROM wishlist WHERE user_id=? ORDER BY country_name", (uid,)).fetchall()
            if not wl_rows:
                return await e.answer("📋 Your wishlist is empty. Tap 'Notify Me' on any out-of-stock country to add it.", alert=True)
            wl_msg = "📋 <b>My Wishlist</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            wl_btns = []
            for (wl_c,) in wl_rows:
                flag_wl = get_flag_by_country_name(wl_c)
                cnt_wl = db.execute("SELECT COUNT(*) FROM stock WHERE country_name=? AND available=1", (wl_c,)).fetchone()[0]
                stock_icon = "✅" if cnt_wl > 0 else "❌"
                wl_msg += f"{stock_icon} {flag_wl} <b>{wl_c}</b>  —  {cnt_wl} in stock\n"
                wl_btns.append([Button.inline(f"❌ Remove {wl_c}", f"wishlist_rm|{wl_c}")])
            wl_btns.append([Button.inline("🔙 Back", "back_to_stats")])
            try: await e.edit(wl_msg, buttons=wl_btns)
            except Exception: await bot.send_message(uid, wl_msg, buttons=wl_btns)
            
        # Feature 6: Fav country toggle
        elif data.startswith("fav_toggle|"):
            _fc = data.split("|", 1)[1]
            _added = toggle_fav_country(uid, _fc)
            await e.answer(f"⭐ Added {_fc} to favourites!" if _added else f"✅ Removed {_fc} from favourites.", alert=False)
        # Feature 8: set language
        elif data.startswith("set_lang|"):
            _lc = data.split("|")[1]
            if _lc in TRANSLATIONS:
                with _db_write_lock:
                    db.execute("UPDATE users SET language=? WHERE user_id=?", (_lc, uid))
                    db.commit()
                _ln = {'en': 'English', 'hi': 'हिन्दी', 'ar': 'العربية'}.get(_lc, _lc)
                await e.answer(f"✅ Language set to {_ln}!", alert=True)
            else:
                await e.answer("❌ Unknown language", alert=True)
        # Feature 7: get PDF receipt
        elif data.startswith("get_receipt|"):
            _oid = int(data.split("|")[1])
            _row_r = db.execute(
                "SELECT id, phone, country, year, price, date FROM orders WHERE id=? AND user_id=?",
                (_oid, uid)
            ).fetchone()
            if not _row_r:
                return await e.answer("❌ Order not found.", alert=True)
            await e.answer("Generating receipt...", alert=False)
            await _send_receipt(e, uid, _row_r)
        elif data == "noop_wl": await e.answer("🔔 Already in your wishlist!", alert=False)
        elif data == "noop_main_menu":
            await e.answer()
            await send_main_menu(e, uid)
        elif data.startswith("depm_"): await manual_deposit_init(e, data.replace("depm_", ""))
        elif data == "dep_upi": await init_upi_keypad(e)
        elif data == "dep_cwallet": await show_cwallet_networks(e)
        elif data.startswith("cw_net|"):
            await init_cwallet_keypad(e, data.split("|", 1)[1])
        elif data.startswith("kp_"): await keypad_logic(e)
        
        elif data.startswith("adm_") and is_admin(uid): await admin_actions(e)
        
        elif data.startswith("dkp|") and has_perm(uid, 'p_bal'):
            parts_dkp = data.split("|", 2)
            if len(parts_dkp) < 3: return await e.answer("⚠️ Invalid action.", alert=True)
            _, dep_id_str, action = parts_dkp
            dep_id = int(dep_id_str)
            row = db.execute("SELECT user_id, method_name, status, amount FROM deposits WHERE id=?", (dep_id,)).fetchone()
            if not row or row[2] != 'pending':
                try: return await e.edit(f"{P_WARN} Already processed.")
                except MessageNotModifiedError: return
            t_uid, method, orig_amt = row[0], row[1], row[3]
            
            curr = custom_dep_amt.get(dep_id_str, "0")
            
            if action.isdigit():
                if curr == "0": curr = action
                else: curr += action
                if len(curr) > 7: curr = curr[:7]
            elif action == "del": curr = curr[:-1] or "0"
            elif action == "cancel":
                btns = [[Button.inline(f"✅ Accept (₹{orig_amt})", f"dep_acc|{dep_id}|{t_uid}|{method}|exact|{orig_amt}"), Button.inline("❌ Reject", f"dep_rej|{dep_id}|{t_uid}")],
                        [Button.inline("📝 Custom Amount", f"dep_acc|{dep_id}|{t_uid}|{method}|custom|0")]]
                try: return await e.edit(f"🔔 <b>NEW DEPOSIT REQUEST</b>\n{P_ACC} User: <code>{t_uid}</code>\n{P_MONEY} Request: <b>{P_INR}{orig_amt}</b>\n{P_CARD} Method: {method}\n{P_ID} Ref: <code>{dep_id}</code>", buttons=btns)
                except MessageNotModifiedError: return
            elif action == "conf":
                amt = int(curr)
                if amt <= 0: return await e.answer("Amount must be > 0", alert=True)
                
                # ── Atomic approval (custom amount) ────────────────────────────────
                async with get_user_lock(t_uid):
                    with _db_write_lock:
                        _wrc = db.execute(
                            "UPDATE deposits SET status='approved', amount=? WHERE id=? AND status='pending'",
                            (amt, dep_id)
                        )
                        if _wrc.rowcount == 0:
                            # No write happened — deposit was already processed. Nothing to roll back.
                            try: return await e.edit(f"{P_WARN} Already processed.")
                            except MessageNotModifiedError: return

                        prev_row = db.execute("SELECT balance FROM users WHERE user_id=?", (t_uid,)).fetchone()
                        prev_bal = prev_row[0] if prev_row else 0
                        db.execute(
                            "UPDATE users SET balance = balance + ?, total_deposited = total_deposited + ? WHERE user_id=?",
                            (amt, amt, t_uid)
                        )
                        if 'upi' in method.lower():
                            _rev_row2 = db.execute("SELECT value FROM settings WHERE key='upi_revenue'").fetchone()
                            _rev_cur2 = int(_rev_row2[0]) if _rev_row2 and _rev_row2[0] else 0
                            db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('upi_revenue', ?)", (str(_rev_cur2 + amt),))
                        db.commit()

                custom_dep_amt.pop(dep_id_str, None)
                custom_dep_ts.pop(dep_id_str, None)
                await process_referral_bonus(t_uid, amt)
                await log_primary_deposit(t_uid, amt, method)
                try: await e.edit(f"{P_YES} <b>APPROVED {P_INR}{amt} TO {t_uid} (Custom Amount)</b>")
                except MessageNotModifiedError: pass
                try:
                    await bot.send_message(int(t_uid), f"{P_YES} <b>Deposit Approved!</b>\n{P_MONEY} Amount Added: {P_INR}{amt}\n📉 Old: {P_INR}{prev_bal} | 📈 New: {P_INR}{prev_bal+amt}")
                except Exception as _e:
                    logger.debug(f'Custom deposit approval notify to {t_uid} failed: {_e}')
                return

            custom_dep_amt[dep_id_str] = curr
            custom_dep_ts.setdefault(dep_id_str, time.time())
            try: await e.edit(f"{P_KEY} <b>Enter Custom Amount for User {t_uid}:</b>\n\n{P_MONEY} {curr}", buttons=get_admin_custom_keypad(dep_id))
            except MessageNotModifiedError: pass

        elif data.startswith("dep_acc|") and has_perm(uid, 'p_bal'):
            p = data.split("|", 5)
            if len(p) < 5: return await e.answer("⚠️ Invalid action.", alert=True)
            try:
                dep_id, t_uid, method, a_type = p[1], int(p[2]), p[3], p[4]
            except (ValueError, IndexError):
                return await e.answer("⚠️ Invalid data.", alert=True)

            if a_type == "exact":
                if len(p) < 6: return await e.answer("⚠️ Invalid action.", alert=True)
                try:
                    amt = int(p[5])
                except (ValueError, IndexError):
                    return await e.answer("⚠️ Invalid amount.", alert=True)
                # ── Atomic approval ─────────────────────────────────────────────────
                # The status check and all balance/deposit updates are performed inside
                # a single DB transaction protected by the per-user lock.  This prevents
                # two admins from double-crediting the same deposit if they both click
                # "Approve" nearly simultaneously.
                async with get_user_lock(t_uid):
                    with _db_write_lock:
                        # Attempt to flip the deposit to 'approved' in one statement.
                        # If another admin already approved it, rowcount will be 0.
                        _wrc = db.execute(
                            "UPDATE deposits SET status='approved', amount=? WHERE id=? AND status='pending'",
                            (amt, dep_id)
                        )
                        if _wrc.rowcount == 0:
                            # No write happened — deposit was already processed. Nothing to roll back.
                            try: return await e.edit(f"{P_WARN} Already processed.")
                            except MessageNotModifiedError: return

                        prev_row = db.execute("SELECT balance FROM users WHERE user_id=?", (t_uid,)).fetchone()
                        prev_bal = prev_row[0] if prev_row else 0
                        # Inline balance update — no intermediate commit so the whole
                        # transaction (deposit + balance + total_deposited) is atomic.
                        db.execute(
                            "UPDATE users SET balance = balance + ?, total_deposited = total_deposited + ? WHERE user_id=?",
                            (amt, amt, t_uid)
                        )
                        if 'upi' in method.lower():
                            _rev_row = db.execute("SELECT value FROM settings WHERE key='upi_revenue'").fetchone()
                            _rev_cur = int(_rev_row[0]) if _rev_row and _rev_row[0] else 0
                            db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('upi_revenue', ?)", (str(_rev_cur + amt),))
                        db.commit()

                custom_dep_amt.pop(dep_id, None)
                custom_dep_ts.pop(dep_id, None)
                await process_referral_bonus(t_uid, amt)
                await log_primary_deposit(t_uid, amt, method)

                # Feature 5: rich deposit approved notification
                user_msg = (
                    f"{P_YES} <b>Deposit Approved!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{P_MONEY} <b>Amount Added:</b>  {P_INR}{amt}  (${to_usd(amt):.2f})\n"
                    f"📉 <b>Prev Balance:</b>  {P_INR}{prev_bal}\n"
                    f"📈 <b>New Balance:</b>   {P_INR}{prev_bal+amt}\n\n"
                    f"🏦 <b>Method:</b> {method}\n"
                    f"🕐 <b>Time:</b> {datetime.now().strftime('%d %b %Y  %H:%M')}\n\n"
                    f"<i>Your funds are ready! Happy shopping 🛍️</i>"
                )
                try:
                    await bot.send_message(int(t_uid), user_msg)
                except Exception as _e:
                    logger.debug(f'Deposit approval notify to {t_uid} failed: {_e}')
                # Feature 12: audit log
                log_admin_action_db(uid, 'deposit_approved', t_uid, f'dep_id={dep_id} amt={amt} method={method}')
                try: await e.edit(f"{P_YES} <b>INSTANT CREDITED {P_INR}{amt} TO {t_uid}</b>")
                except MessageNotModifiedError: pass
                
            elif a_type == "custom":
                # BUG FIX: always use str(dep_id) as key so keypad handler
                # (which uses dep_id_str from button data) can find and clean it up
                _dep_id_str = str(dep_id)
                custom_dep_amt[_dep_id_str] = "0"
                custom_dep_ts[_dep_id_str] = time.time()
                try: await e.edit(f"{P_KEY} <b>Enter Custom Amount for User {t_uid}:</b>\n\n{P_MONEY} 0", buttons=get_admin_custom_keypad(dep_id))
                except MessageNotModifiedError: pass
                
        elif data.startswith("dep_rej|") and has_perm(uid, 'p_bal'):
            p = data.split("|", 2)
            if len(p) < 3: return await e.answer("⚠️ Invalid action.", alert=True)
            try:
                dep_id, t_uid = p[1], int(p[2])
            except (ValueError, IndexError):
                return await e.answer("⚠️ Invalid data.", alert=True)
            row = db.execute("SELECT status FROM deposits WHERE id=?", (dep_id,)).fetchone()
            if not row or row[0] != 'pending':
                try: return await e.edit(f"{P_WARN} Already processed.")
                except MessageNotModifiedError: return
            admin_dep_state[uid] = {'target_uid': t_uid, 'dep_id': dep_id, 'step': 'wait_reason', 'msg_id': e.message_id, 'ts': time.time()}
            await bot.send_message(uid, f"{P_WARN} Reply to this message with the REASON for rejecting user <code>{t_uid}</code>:")
            try: await e.answer("Check your bot PMs to enter the reason.", alert=True)
            except Exception as _e:
                logger.debug(f'Suppressed non-critical error: {_e}')

        elif data.startswith("confirm_ban|") and has_perm(uid, 'p_ban'):
            parts = data.split("|", 2)
            if len(parts) < 3: return await e.answer("⚠️ Invalid action.", alert=True)
            t_uid, ns = int(parts[1]), int(parts[2])
            row = db.execute("SELECT banned FROM users WHERE user_id=?", (t_uid,)).fetchone()
            if not row:
                try: return await e.edit(f"{P_NO} User not found.")
                except MessageNotModifiedError: return
            if row[0] == ns:
                try: return await e.edit(f"{P_WARN} User status was already updated. No change made.")
                except MessageNotModifiedError: return
            with _db_write_lock:
                db.execute("UPDATE users SET banned=? WHERE user_id=?", (ns, t_uid))
                db.commit()
            result_text = "🚫 Banned" if ns == 1 else "✅ Unbanned"
            try: await e.edit(f"{P_YES} User <code>{t_uid}</code> is now <b>{result_text}</b>.")
            except MessageNotModifiedError: pass
            if ns == 1:
                try:
                    await bot.send_message(t_uid,
                        f"{P_NO} <b>Your account has been banned.</b>\n\n"
                        f"You are no longer able to use this bot.\n"
                        f"If you believe this is a mistake, please contact support."
                    )
                except Exception as _e: logger.debug(f'Ban callback notify {t_uid} failed: {_e}')
            else:
                try:
                    await bot.send_message(t_uid,
                        f"{P_YES} <b>Your account has been unbanned.</b>\n\n"
                        f"You can now use the bot again. Type /start to continue."
                    )
                except Exception as _e: logger.debug(f'Unban callback notify {t_uid} failed: {_e}')

        elif data == "cancel_ban":
            try: await e.edit(f"{P_NO} <b>Cancelled.</b> No changes made.")
            except MessageNotModifiedError: pass

    except Exception as ex:
        logger.error(f"Callback Error uid={e.sender_id} data={e.data}: {ex}", exc_info=True)
        try: await e.answer("⚠️ Something went wrong. Please try again.", alert=True)
        except Exception as _e:
            logger.debug(f'Suppressed non-critical error: {_e}')

async def proof_timeout_task():
    while True:
        await asyncio.sleep(30)
        try:
            now = time.time()
            expired = [uid for uid, info in list(waiting_proof.items()) if now >= info.get('expires_at', 0)]
            for uid in expired:
                info = waiting_proof.pop(uid, None)
                _clear_waiting_proof_db(uid)
                if not info:
                    continue
                msg_id = info.get('msg_id')
                expire_text = (
                    f"⌛ <b>Session Expired</b>\n\n"
                    f"Your deposit request of <b>₹{info['amount']}</b> via <b>{info['method']}</b> "
                    f"was automatically cancelled (no proof received within 10 minutes).\n\n"
                    f"<i>Tap Deposit from the menu to start a new request.</i>"
                )
                try:
                    if msg_id:
                        # Edit the original payment message (UPI QR / payment screen)
                        try:
                            await bot.edit_message(uid, msg_id, expire_text)
                        except Exception:
                            await bot.send_message(uid, expire_text)
                    else:
                        await bot.send_message(uid, expire_text)
                except Exception as err:
                    logger.error(f"proof_timeout_task: failed to notify uid={uid}: {err}")
        except Exception as _proof_err:
            # Never let a single iteration error kill the background task
            logger.error(f"proof_timeout_task loop error (task continues): {_proof_err}")


async def _stale_cleanup_task():
    """Periodically prune in-memory dicts that would otherwise grow forever.

    Every dict that maps a user/session to transient state is pruned here using
    a strict TTL so no entry can accumulate unboundedly regardless of how the
    user exits (crash, close app, blocked, ignore).

    TTLs (conservative — chosen to never disrupt a real active flow):
      user_spam_cooldown : 90 s  (matches anti-spam window)
      force_join_prompt_cooldown : 24 h (one prompt per user per process)
      deposit_input      : 20 min (keypad + text input)
      session_buy_state  : 15 min (bulk-quantity entry)
      admin_dep_state    : 30 min (admin rejection reason prompt)
      custom_dep_amt/ts  : 2 h   (admin custom amount keypad; longer because admins
                                   may be interrupted mid-entry)
      user_locks         : evict only when idle AND user not active
    """
    COOLDOWN_TTL    =   90        # seconds
    FJ_PROMPT_TTL   = 86400       # 24 h
    DEP_INPUT_TTL   = 1200        # 20 min
    SESSION_TTL     =  900        # 15 min
    ADMIN_STATE_TTL = 1800        # 30 min
    CUSTOM_AMT_TTL  = 7200        # 2 h

    while True:
        await asyncio.sleep(120)  # run every 2 minutes
        try:
            now = time.time()

            # ── spam cooldown (keyed by uid → timestamp float) ───────────────
            stale_cd = [u for u, t in list(user_spam_cooldown.items()) if now - t > COOLDOWN_TTL]
            for u in stale_cd:
                user_spam_cooldown.pop(u, None)

            # ── force-join prompt cooldown ───────────────────────────────────
            stale_fj = [
                u for u, t in list(force_join_prompt_cooldown.items())
                if now - t > FJ_PROMPT_TTL
            ]
            for u in stale_fj:
                force_join_prompt_cooldown.pop(u, None)

            # ── deposit keypad state (uid → dict with 'ts') ─────────────────
            stale_dep = [
                u for u, v in list(deposit_input.items())
                if now - v.get('ts', now) > DEP_INPUT_TTL
            ]
            for u in stale_dep:
                deposit_input.pop(u, None)

            # ── session-buy quantity state (uid → dict with 'ts') ────────────
            stale_sess = [
                u for u, v in list(session_buy_state.items())
                if now - v.get('ts', now) > SESSION_TTL
            ]
            for u in stale_sess:
                session_buy_state.pop(u, None)

            # ── admin deposit-rejection prompt (uid → dict with 'ts') ────────
            stale_adm = [
                u for u, v in list(admin_dep_state.items())
                if now - v.get('ts', now) > ADMIN_STATE_TTL
            ]
            for u in stale_adm:
                admin_dep_state.pop(u, None)

            # ── custom deposit amount keypad (dep_id → str, parallel ts dict) ─
            stale_cdep = [
                dep_id for dep_id, ts in list(custom_dep_ts.items())
                if now - ts > CUSTOM_AMT_TTL
            ]
            for dep_id in stale_cdep:
                custom_dep_amt.pop(dep_id, None)
                custom_dep_ts.pop(dep_id, None)

            # ── user locks — only evict idle locks for inactive users ────────
            idle_lock_uids = [
                u for u, lk in list(user_locks.items())
                if not lk.locked() and u not in active_orders
            ]
            for u in idle_lock_uids:
                user_locks.pop(u, None)

            logger.debug(
                f"_stale_cleanup_task: pruned "
                f"cd={len(stale_cd)} fj={len(stale_fj)} dep={len(stale_dep)} sess={len(stale_sess)} "
                f"adm={len(stale_adm)} cdep={len(stale_cdep)} locks={len(idle_lock_uids)} | "
                f"live: dep_input={len(deposit_input)} sess={len(session_buy_state)} "
                f"adm={len(admin_dep_state)} cdep_amt={len(custom_dep_amt)}"
            )
        except Exception as _cleanup_err:
            # Never let a cleanup error kill the background task
            logger.error(f"_stale_cleanup_task error (task continues): {_cleanup_err}")

def _sync_exception_handler(exc_type, exc_value, exc_tb):
    """Log uncaught synchronous exceptions instead of letting them silently disappear."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))

def _async_exception_handler(loop, context):
    """Log uncaught asyncio exceptions (e.g. exceptions in fire-and-forget tasks)."""
    exc = context.get('exception')
    msg = context.get('message', 'Unknown async error')
    if exc:
        logger.error(f"Unhandled async exception: {msg}", exc_info=exc)
    else:
        logger.error(f"Unhandled async error: {msg}")

sys.excepthook = _sync_exception_handler

async def _daily_revenue_report_task():
    """Feature 9: Send daily revenue summary to log channel at midnight."""
    while True:
        _now = datetime.now()
        _midnight = (_now + timedelta(days=1)).replace(hour=0, minute=1, second=0, microsecond=0)
        await asyncio.sleep(max((_midnight - _now).total_seconds(), 0))
        try:
            _rdate = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            _sales = db.execute(
                "SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE date LIKE ?",
                (_rdate + "%",)
            ).fetchone()
            _deps = db.execute(
                "SELECT COUNT(*), COALESCE(SUM(amount),0) FROM deposits "
                "WHERE status='approved' AND date LIKE ?",
                (_rdate + "%",)
            ).fetchone()
            _new_u = db.execute(
                "SELECT COUNT(*) FROM users WHERE date(joined_date)=?", (_rdate,)
            ).fetchone()[0]
            _top = db.execute(
                "SELECT country, COUNT(*) c FROM orders WHERE date LIKE ? "
                "GROUP BY country ORDER BY c DESC LIMIT 1",
                (_rdate + "%",)
            ).fetchone()
            _top_s = (f"{get_flag_by_country_name(_top[0])} <b>{_top[0]}</b> ({_top[1]} sold)" if _top else "<i>—</i>")
            _msg = (
                f"📊 <b>DAILY REVENUE REPORT</b>\n"
                f"📅 <b>{_rdate}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🛍 <b>Sales:</b>     {_sales[0]} orders  —  {P_INR}{_sales[1]}\n"
                f"💳 <b>Deposits:</b>  {_deps[0]} approved  —  {P_INR}{_deps[1]}\n"
                f"👤 <b>New Users:</b> {_new_u}\n"
                f"🏆 <b>Top Country:</b> {_top_s}\n\n"
                f"<i>Auto-generated midnight report</i>"
            )
            await bot.send_message(ADMIN_ID, _msg)
            logger.info(f"Daily revenue report sent for {_rdate}")
        except Exception as _drr:
            logger.error(f"_daily_revenue_report_task: {_drr}")

async def _db_backup_task():
    """Create a daily timestamped copy of the SQLite database. Keeps the last 7 backups."""
    # FIX Bug 10: sleep was at the TOP of the loop, meaning the first backup only
    # happened 24h after startup. A crash in that window would leave no backup at all.
    # Now the backup runs once immediately on start, then every 24h thereafter.
    while True:
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(_backups_dir, f"otp_bot_{ts}.db")
            with _db_write_lock:
                backup_conn = sqlite3.connect(backup_path)
                try:
                    db.backup(backup_conn)
                finally:
                    backup_conn.close()
            backups = sorted(
                f for f in os.listdir(_backups_dir)
                if f.startswith("otp_bot_") and f.endswith(".db")
            )
            for old in backups[:-7]:
                try: os.remove(os.path.join(_backups_dir, old))
                except Exception: pass
            logger.info(f"Daily DB backup created: {backup_path}")
            try:
                await bot.send_message(ADMIN_ID, f"✅ <b>Daily DB Backup</b>\n<code>{backup_path}</code>")
            except Exception as _e:
                logger.debug(f"Backup notify failed: {_e}")
        except Exception as _bkp_err:
            logger.error(f"_db_backup_task error: {_bkp_err}")
        await asyncio.sleep(86400)  # wait 24 hours before the next backup

async def _expired_order_cleanup_task():
    """Catch stuck active_orders that auto_otp_task may have missed (e.g. after exceptions)."""
    while True:
        await asyncio.sleep(120)  # every 2 minutes
        try:
            now = time.time()
            stuck = [
                phone for phone, order in list(active_orders.items())
                if not order.get('paid') and (now - order.get('start_time', now)) > AUTO_CANCEL_SECONDS + 60
            ]
            for phone in stuck:
                order = active_orders.pop(phone, None)
                _clear_active_order_db(phone)
                if not order or order.get('paid'):
                    continue
                uid = order['uid']
                logger.warning(f"_expired_order_cleanup_task: refunding stuck order phone={phone} uid={uid}")
                try: await order['client'].disconnect()
                except Exception: pass
                async with get_user_lock(uid):
                    with _db_write_lock:
                        db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (order['price'], uid))
                        db.execute("UPDATE stock SET available=1 WHERE phone=?", (phone,))
                        db.commit()
                user_locks.pop(uid, None)
                try:
                    await bot.send_message(uid,
                        f"{P_WARN} <b>Order Auto-Cancelled</b>\n\n"
                        f"No OTP was received in time. ₹{order['price']} has been refunded to your balance."
                    )
                except Exception as _e:
                    logger.debug(f"Stuck order refund notify failed uid={uid}: {_e}")
        except Exception as _oce:
            logger.error(f"_expired_order_cleanup_task error: {_oce}")

async def _restore_and_refund_stale_orders():
    """On startup: refund any active orders persisted before the last bot restart.

    Edge-case guard: if the bot crashed after recording the OTP in the orders
    table but before removing the phone from active_orders_db, we must NOT
    refund — the account was already delivered.  We check the orders table
    first and skip the refund (just clean up) when that happens.
    """
    try:
        rows = db.execute(
            "SELECT phone, user_id, price FROM active_orders_db"
        ).fetchall()
        if not rows:
            return
        logger.info(f"Processing {len(rows)} stale active_orders_db rows from before last restart")
        refund_count = 0
        skip_count = 0
        for phone, uid, price in rows:
            try:
                with _db_write_lock:
                    # FIX: check whether the OTP was already delivered for this phone.
                    # If an orders row exists, the crash happened AFTER the commit that
                    # recorded the sale — issuing a refund here would give the user
                    # money back for an account they successfully received.
                    already_delivered = db.execute(
                        "SELECT id FROM orders WHERE phone=? LIMIT 1", (phone,)
                    ).fetchone()
                    if already_delivered:
                        # Just remove the stale tracking row; no refund needed.
                        db.execute("DELETE FROM active_orders_db WHERE phone=?", (phone,))
                        db.commit()
                        skip_count += 1
                        logger.info(
                            f"Stale active_orders_db phone={phone} uid={uid}: "
                            f"OTP already delivered — skipping refund, cleaning up."
                        )
                        continue
                    db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (price, uid))
                    db.execute("UPDATE stock SET available=1 WHERE phone=?", (phone,))
                    db.execute("DELETE FROM active_orders_db WHERE phone=?", (phone,))
                    db.commit()
                    refund_count += 1
                try:
                    await bot.send_message(
                        uid,
                        f"{P_WARN} <b>Order Refunded (Bot Restart)</b>\n\n"
                        f"Your order for <code>+{phone}</code> was cancelled because the bot was restarted.\n"
                        f"₹{price} has been returned to your balance. Sorry for the inconvenience!"
                    )
                except Exception as _e:
                    logger.debug(f"Stale order refund notify failed uid={uid}: {_e}")
            except Exception as _row_err:
                logger.error(f"Stale order refund failed phone={phone}: {_row_err}")
        logger.info(f"Stale order recovery complete — refunded: {refund_count}, already-delivered skipped: {skip_count}")
    except Exception as _e:
        logger.error(f"_restore_and_refund_stale_orders failed: {_e}")

@bot.on(events.ChatAction)
async def handle_chat_action(e):
    """
    Fires whenever a user joins or leaves any chat the bot is in.
    If the chat is one of the configured force-join channels and the user
    left / was kicked, reset their fj_verified so the bot blocks them
    until they rejoin and tap ✅ Verify again.
    """
    try:
        # Only care about departures (voluntary leave or kick/ban)
        if not (e.user_left or e.user_kicked):
            return

        left_uid = e.action_message.action.users[0] if e.user_kicked else e.user_id
        if not left_uid:
            return

        # Skip if it's the bot itself leaving
        # FIX Bug 7: use the ID cached at startup — avoids a network round-trip on every event
        if _BOT_ID and left_uid == _BOT_ID:
            return

        # Check if this chat is one of our force-join channels
        event_chat_id = str(e.chat_id)
        fj_ids = [str(en['cid']) for en in get_force_join_entries() if en['type'] != 'bot']
        # Telegram channel IDs can appear as negative numbers (e.g. -1001234567890)
        # or without the -100 prefix depending on context — normalise both
        def _norm(cid: str) -> str:
            s = cid.lstrip('-')
            return s[3:] if s.startswith('100') else s

        normalised_event = _norm(event_chat_id)
        is_fj_channel = any(_norm(fid) == normalised_event for fid in fj_ids)
        if not is_fj_channel:
            return

        # Reset DB verification flag
        row = db.execute("SELECT user_id FROM users WHERE user_id=?", (left_uid,)).fetchone()
        if not row:
            return  # user not in our DB, nothing to do

        with _db_write_lock:
            db.execute("UPDATE users SET fj_verified=0 WHERE user_id=?", (left_uid,))
            db.commit()
        logger.info(f"Auto-reset fj_verified for uid={left_uid} (left channel {e.chat_id})")

        # Notify the user so they know why the bot stopped working
        try:
            _fj_entries = get_force_join_entries()
            _fj_btn_labels = {'channel': 'Join Channel', 'group': 'Join Group', 'bot': 'Start Bot'}
            _fj_btn_icons  = {'channel': '📢', 'group': '👥', 'bot': '🤖'}
            btns = [
                [Button.url(
                    f"{_fj_btn_icons.get(en['type'], '📢')} {_fj_btn_labels.get(en['type'], 'Join')} {i+1}",
                    sanitize_url(en['url'])
                )]
                for i, en in enumerate(_fj_entries)
                if sanitize_url(en['url']).startswith('http')
            ]
            btns.append([Button.inline("✅ Verify", "verify_join")])
            await bot.send_message(
                left_uid,
                f"⚠️ <b>Access Revoked!</b>\n\n"
                f"You left one of our required channels, so your bot access has been paused.\n\n"
                f"📌 <b>To regain access:</b>\n"
                f"1️⃣ Rejoin the channel(s) below.\n"
                f"2️⃣ Tap <b>✅ Verify</b> to restore access.\n\n"
                f"<i>Your balance and data are safe — just rejoin!</i>",
                buttons=btns
            )
        except Exception as _notify_err:
            logger.debug(f"Auto-kick notify failed uid={left_uid}: {_notify_err}")

    except Exception as _e:
        logger.debug(f"handle_chat_action error: {_e}")


async def _stock_expiry_task():
    """Daily: mark accounts as unavailable if unsold for > stock_expiry_days."""
    while True:
        await asyncio.sleep(86400)  # run once per day
        try:
            row = db.execute("SELECT value FROM settings WHERE key='stock_expiry_days'").fetchone()
            days = int(row[0]) if row and row[0] and int(row[0]) > 0 else 0
            if days <= 0:
                continue
            with _db_write_lock:
                result = db.execute(
                    "UPDATE stock SET available=0 WHERE available=1 AND "
                    "julianday('now') - julianday(added_date) > ?",
                    (days,)
                )
                db.commit()
            expired = result.rowcount
            if expired > 0:
                await bot.send_message(ADMIN_ID,
                    f"🗓 <b>Stock Expiry Task</b>\n\n"
                    f"Marked <b>{expired}</b> account(s) as unavailable\n"
                    f"(unsold for more than <b>{days} days</b>)."
                )
            logger.info(f"_stock_expiry_task: expired {expired} accounts")
        except Exception as _exp_err:
            logger.error(f"_stock_expiry_task error: {_exp_err}")

async def _hourly_stock_cleanup_task():
    """Every hour: remove stale stock entries from the database.

    Covers two cases that earlier code left as available=0 rows instead of
    deleting them:
      1. Entries already recorded in the `orders` table — the sale completed,
         the number was delivered, nothing should re-use that phone row.
      2. Entries whose .session file no longer exists on disk — these are
         physically gone and can never be sold, so keeping them wastes space
         and can mislead stock-count queries.

    Any entry removed here is logged at INFO level so the admin can audit it
    with grep or the bot logs.  The task is intentionally conservative: it
    only touches rows that are provably dead.  Live available=1 entries whose
    session files exist are left completely alone.
    """
    while True:
        await asyncio.sleep(3600)  # run once per hour
        try:
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # ── Case 1: available=0 entries that are already in `orders` ──────
            # These were sold but the DELETE in auto_otp_task/process_purchase
            # didn't fire (e.g. crash, restart, or added before the fix).
            sold_rows = db.execute(
                "SELECT s.phone FROM stock s "
                "WHERE s.available=0 AND EXISTS "
                "(SELECT 1 FROM orders o WHERE o.phone=s.phone)"
            ).fetchall()
            sold_phones = [r[0] for r in sold_rows]
            if sold_phones:
                ph_placeholders = ','.join('?' for _ in sold_phones)
                with _db_write_lock:
                    db.execute(f"DELETE FROM stock WHERE phone IN ({ph_placeholders})", sold_phones)
                    db.commit()
                logger.info(
                    f"_hourly_stock_cleanup_task [{now_str}]: "
                    f"removed {len(sold_phones)} already-sold stock entries: {sold_phones}"
                )

            # ── Case 2: any stock entry whose session file is missing on disk ──
            # Both available=0 and available=1 are checked — a missing file means
            # the account can never be used regardless of its availability flag.
            all_stock = db.execute("SELECT phone, session_file FROM stock").fetchall()
            dead_phones = []
            for phone, sess in all_stock:
                if phone in sold_phones:
                    continue  # already removed above
                base = _resolve_session_base(sess)
                if not base or not os.path.exists(base + '.session'):
                    dead_phones.append(phone)

            if dead_phones:
                dp_placeholders = ','.join('?' for _ in dead_phones)
                with _db_write_lock:
                    db.execute(f"DELETE FROM stock WHERE phone IN ({dp_placeholders})", dead_phones)
                    db.commit()
                logger.info(
                    f"_hourly_stock_cleanup_task [{now_str}]: "
                    f"removed {len(dead_phones)} stock entries with missing session files: {dead_phones}"
                )

            total_removed = len(sold_phones) + len(dead_phones)
            if total_removed > 0:
                try:
                    await bot.send_message(
                        ADMIN_ID,
                        f"🧹 <b>Hourly Stock Cleanup</b>\n\n"
                        f"🗑 Removed <b>{len(sold_phones)}</b> already-sold entries\n"
                        f"🗑 Removed <b>{len(dead_phones)}</b> missing-session entries\n\n"
                        f"<i>Total cleaned: {total_removed} | {now_str}</i>"
                    )
                except Exception as _notify_err:
                    logger.debug(f"_hourly_stock_cleanup_task notify failed: {_notify_err}")
            else:
                logger.info(f"_hourly_stock_cleanup_task [{now_str}]: no stale entries found")

        except Exception as _hsc_err:
            logger.error(f"_hourly_stock_cleanup_task error: {_hsc_err}")


async def _scheduled_broadcast_task():
    """Check every 60s for broadcasts whose send_at has passed."""
    while True:
        await asyncio.sleep(60)
        try:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            rows_sb = db.execute(
                "SELECT id, message, btn_name, btn_url FROM scheduled_broadcasts "
                "WHERE send_at <= ? AND (sent=0 OR (sent=2 AND claimed_at < ?))",
                (now_str, time.time() - 86400)
            ).fetchall()
            for (sb_id, sb_msg, sb_btn, sb_url) in rows_sb:
                # Claim before the first await. A second bot process or a
                # restarted scheduler must not send the same broadcast again.
                # sent=2 means claimed/in progress; old claims are retryable.
                with _db_write_lock:
                    claim = db.execute(
                        "UPDATE scheduled_broadcasts SET sent=2, claimed_at=? "
                        "WHERE id=? AND (sent=0 OR (sent=2 AND claimed_at < ?))",
                        (time.time(), sb_id, time.time() - 86400),
                    )
                    db.commit()
                if claim.rowcount != 1:
                    continue

                btns_sb = [[Button.url(sb_btn, sb_url)]] if sb_btn and sb_url else None
                users_sb = db.execute("SELECT user_id FROM users").fetchall()
                s_sb, f_sb = 0, 0
                for (u_sb,) in users_sb:
                    try:
                        await _tg_call(bot.send_message, int(u_sb), sb_msg, buttons=btns_sb, parse_mode='html')
                        s_sb += 1
                    except Exception:
                        f_sb += 1
                    await asyncio.sleep(0.05)
                with _db_write_lock:
                    db.execute(
                        "UPDATE scheduled_broadcasts SET sent=1, claimed_at=0 WHERE id=?",
                        (sb_id,),
                    )
                    db.commit()
                await bot.send_message(ADMIN_ID,
                    f"✅ <b>Scheduled Broadcast Sent!</b>\n"
                    f"Sent: {s_sb} | Failed: {f_sb}"
                )
                logger.info(f"_scheduled_broadcast_task: sent broadcast id={sb_id} to {s_sb} users")
        except Exception as _sb_err:
            logger.error(f"_scheduled_broadcast_task error: {_sb_err}")


if __name__ == '__main__':
    async def main():
        await bot.start(bot_token=BOT_TOKEN)
        print("✅ BOT STARTED SUCCESSFULLY")
        # FIX Bug 7: cache the bot's own ID once so handle_chat_action can use it
        # without issuing a get_me() network call on every chat-action event.
        global _BOT_ID
        _BOT_ID = (await bot.get_me()).id
        # Set asyncio exception handler for unhandled task errors
        asyncio.get_running_loop().set_exception_handler(_async_exception_handler)
        # Restore persisted state before accepting any traffic
        _restore_waiting_proof()
        await _restore_and_refund_stale_orders()
        await asyncio.gather(
            bot.run_until_disconnected(),
            proof_timeout_task(),
            _stale_cleanup_task(),          # prunes user_spam_cooldown, user_locks, etc.
            _db_backup_task(),              # daily DB backup
            _expired_order_cleanup_task(),  # catch any stuck active_orders
            _stock_expiry_task(),           # daily stock expiry
            _scheduled_broadcast_task(),    # scheduled broadcasts
            _daily_revenue_report_task(),   # Feature 9: midnight revenue report
            _hourly_stock_cleanup_task(),   # hourly: remove sold/dead stock rows
        )

    print("✅ BOT STARTING...")
    # BUG FIX: asyncio.run(main()) was missing — the bot never actually started
    # before this fix.  Always use asyncio.run() (or loop.run_until_complete) to
    # drive the top-level coroutine; just calling print() does not start it.
    asyncio.run(main())

"""
FastAPI backend for XauBot Dashboard
Provides REST API to start/stop the bot, manage credentials, and fetch live data.
"""

import subprocess
import sys
import os
import csv
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv, set_key

load_dotenv()

app = FastAPI(title="XauBot API", version="1.0.0")

# Allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_DIR = Path(__file__).parent
ENV_FILE = BOT_DIR / ".env"
LOG_FILE = BOT_DIR / "trades_log.csv"
ANALYSIS_CSV = BOT_DIR / "analysis_results.csv"
ANALYSIS_TXT = BOT_DIR / "analysis_results.txt"

# Bot process tracker
_bot_process: Optional[subprocess.Popen] = None
_bot_lock = threading.Lock()

# Supabase Sync
from supabase import create_client, Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
# Use Service Role Key if available (bypasses RLS), fallback to Anon Key
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def sync_with_supabase():
    """Background loop to check cloud status and start/stop bot."""
    global _bot_process
    user_id = os.getenv("USER_ID")
    if not user_id:
        print("[SYNC ERROR] USER_ID not set in .env. Skipping sync.")
        return
        
    print(f"[SYNC] Started monitor for User: {user_id}")
    while True:
        try:
            res = supabase.table("bot_config").select("*").eq("user_id", user_id).single().execute()
            if res.data:
                should_run = res.data.get("is_running", False)
                currently_running = is_bot_running()
                
                # Sync Risk Management Settings
                max_pos = res.data.get("max_positions", 5)
                risk_pct = res.data.get("risk_percent", 1.0)
                
                set_key(str(ENV_FILE), "MAX_POSITIONS", str(max_pos))
                set_key(str(ENV_FILE), "RISK_PERCENT", str(risk_pct))
                
                if should_run and not currently_running:
                    print("[SYNC] Cloud says START. Launching bot...")
                    start_bot()
                elif not should_run and currently_running:
                    print("[SYNC] Cloud says STOP. Terminating bot...")
                    stop_bot()
        except Exception as e:
            print(f"[SYNC ERROR] {e}")
        time.sleep(10) # Poll every 10 seconds

# Start the sync thread
import time
threading.Thread(target=sync_with_supabase, daemon=True).start()


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────
class Credentials(BaseModel):
    account: str
    password: str
    server: str
    path: str = ""


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def is_bot_running() -> bool:
    global _bot_process
    if _bot_process is None:
        return False
    poll = _bot_process.poll()
    return poll is None  # None means still running


def read_csv_safe(filepath: Path) -> list[dict]:
    if not filepath.exists():
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception:
        return []


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "XauBot API running"}


@app.get("/status")
def get_status():
    """Returns bot running state + quick summary stats."""
    running = is_bot_running()
    trades = read_csv_safe(LOG_FILE)
    closed = [t for t in trades if t.get("Status") == "CLOSED"]
    total_pnl = sum(float(t.get("Profit", 0)) for t in closed)
    wins = [t for t in closed if float(t.get("Profit", 0)) > 0]
    win_rate = (len(wins) / len(closed) * 100) if closed else 0.0

    return {
        "running": running,
        "total_trades": len(closed),
        "total_pnl": round(total_pnl, 2),
        "win_rate": round(win_rate, 1),
        "open_positions": len([t for t in trades if t.get("Status") == "OPEN"]),
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/start")
def start_bot():
    global _bot_process
    with _bot_lock:
        if is_bot_running():
            return {"message": "Bot is already running"}
        try:
            _bot_process = subprocess.Popen(
                [sys.executable, str(BOT_DIR / "main.py")],
                cwd=str(BOT_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            return {"message": "Bot started", "pid": _bot_process.pid}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/stop")
def stop_bot():
    global _bot_process
    with _bot_lock:
        if not is_bot_running():
            return {"message": "Bot is not running"}
        try:
            _bot_process.terminate()
            _bot_process.wait(timeout=10)
            return {"message": "Bot stopped"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/positions")
def get_positions():
    """Return open trades from the log."""
    trades = read_csv_safe(LOG_FILE)
    open_trades = [t for t in trades if t.get("Status") == "OPEN"]
    return {"positions": open_trades}


@app.get("/trades")
def get_trades(limit: int = 50):
    """Return the last N closed trades."""
    trades = read_csv_safe(LOG_FILE)
    closed = [t for t in trades if t.get("Status") == "CLOSED"]
    return {"trades": closed[-limit:]}


@app.get("/analysis")
def get_analysis():
    """Return per-symbol analysis summary."""
    rows = read_csv_safe(ANALYSIS_CSV)
    txt_summary = ""
    if ANALYSIS_TXT.exists():
        try:
            txt_summary = ANALYSIS_TXT.read_text(encoding="utf-8")
        except Exception:
            pass
    return {"symbols": rows, "summary": txt_summary}


@app.post("/credentials")
def save_credentials(creds: Credentials):
    """Persist MT5 credentials to .env file."""
    try:
        set_key(str(ENV_FILE), "MT5_ACCOUNT", creds.account)
        set_key(str(ENV_FILE), "MT5_PASSWORD", creds.password)
        set_key(str(ENV_FILE), "MT5_SERVER", creds.server)
        if creds.path:
            set_key(str(ENV_FILE), "MT5_PATH", creds.path)
        return {"message": "Credentials saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/credentials")
def get_credentials():
    """Return current credentials (masked password)."""
    load_dotenv(override=True)
    return {
        "account": os.getenv("MT5_ACCOUNT", ""),
        "server": os.getenv("MT5_SERVER", ""),
        "path": os.getenv("MT5_PATH", ""),
        "has_password": bool(os.getenv("MT5_PASSWORD", "")),
    }

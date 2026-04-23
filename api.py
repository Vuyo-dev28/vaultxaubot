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
import queue
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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

# Real-time logs queue
_logs_queue: queue.Queue = queue.Queue(maxsize=100)

def push_realtime_log(message: str) -> None:
    """Send important backend events to both console and SSE queue."""
    print(message)
    log_entry = {
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    try:
        _logs_queue.put_nowait(log_entry)
    except queue.Full:
        _logs_queue.get()
        _logs_queue.put_nowait(log_entry)

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
    last_timeframe = None
    
    # If USER_ID not in .env, fetch it from bot_config table
    if not user_id:
        try:
            res = supabase.table("bot_config").select("user_id").limit(1).execute()
            if res.data and len(res.data) > 0:
                user_id = res.data[0].get("user_id")
                print(f"[SYNC] Fetched USER_ID from database: {user_id}")
            else:
                print("[SYNC ERROR] No bot_config found in database. Skipping sync.")
                return
        except Exception as e:
            print(f"[SYNC ERROR] Failed to fetch USER_ID: {e}")
            return
    
    print(f"[SYNC] Started monitor for User: {user_id}")
    while True:
        try:
            res = supabase.table("bot_config").select("*").eq("user_id", user_id).single().execute()
            if res.data:
                should_run = res.data.get("is_running", False)
                currently_running = is_bot_running()
                
                # Sync Settings
                max_pos = res.data.get("max_positions", 5)
                risk_pct = res.data.get("risk_percent", 1.0)
                timeframe = res.data.get("trading_timeframe", "5m")
                
                set_key(str(ENV_FILE), "MAX_POSITIONS", str(max_pos))
                set_key(str(ENV_FILE), "RISK_PERCENT", str(risk_pct))
                set_key(str(ENV_FILE), "TRADING_TIMEFRAME", str(timeframe))
                # Keep this process env synced so subprocess inherits fresh values.
                os.environ["MAX_POSITIONS"] = str(max_pos)
                os.environ["RISK_PERCENT"] = str(risk_pct)
                os.environ["TRADING_TIMEFRAME"] = str(timeframe).lower()

                # Notify UI logs whenever timeframe changes
                if last_timeframe != timeframe:
                    push_realtime_log(f"[SYNC] Trading timeframe updated to {timeframe}.")
                    if currently_running:
                        push_realtime_log(f"[SYNC] Restarting bot to apply timeframe {timeframe}...")
                        stop_bot()
                        _start_bot_process(user_id, timeframe)
                    last_timeframe = timeframe
                
                if should_run and not currently_running:
                    push_realtime_log(f"[SYNC] Cloud says START. Launching bot with timeframe: {timeframe}")
                    _start_bot_process(user_id, timeframe)
                elif not should_run and currently_running:
                    push_realtime_log("[SYNC] Cloud says STOP. Terminating bot...")
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


@app.get("/test-sse")
def test_sse():
    """Simple test to verify SSE works"""
    def event_generator():
        for i in range(5):
            yield f"data: {json.dumps({'message': f'Test message {i}', 'timestamp': datetime.now().isoformat()})}\n\n"
            import time
            time.sleep(1)
    
    response = StreamingResponse(event_generator(), media_type="text/event-stream")
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "no-cache, no-transform"
    response.headers["X-Accel-Buffering"] = "no"
    return response


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

@app.options("/logs")
def logs_options():
    """CORS preflight for logs endpoint."""
    return {}


@app.get("/logs")
def get_logs_sse():
    """Server-Sent Events endpoint for real-time logs."""
    print("[SSE] ✅ Client connected to /logs endpoint")
    
    def event_generator():
        try:
            consecutive_empty = 0
            while consecutive_empty < 600:  # 10 minutes timeout
                try:
                    log = _logs_queue.get(timeout=1)
                    consecutive_empty = 0
                    print(f"[SSE] Sending: {log['message'][:60]}")
                    yield f"data: {json.dumps(log)}\n\n"
                except queue.Empty:
                    consecutive_empty += 1
                    if consecutive_empty % 5 == 0:
                        yield ": keep-alive\n\n"
        except Exception as e:
            print(f"[SSE] Error in event_generator: {e}")
        finally:
            print("[SSE] ❌ Client disconnected from /logs endpoint")
    
    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/start")
def start_bot_endpoint(user_id: str = None):
    timeframe = os.getenv("TRADING_TIMEFRAME", "5m")
    # If user_id not provided, fetch from database
    if not user_id:
        try:
            res = supabase.table("bot_config").select("user_id,trading_timeframe").limit(1).execute()
            if res.data and len(res.data) > 0:
                user_id = res.data[0].get("user_id")
                timeframe = res.data[0].get("trading_timeframe", timeframe)
        except Exception:
            pass
    
    return _start_bot_process(user_id, timeframe)


def _start_bot_process(user_id: str = None, timeframe: str = None):
    global _bot_process
    with _bot_lock:
        if is_bot_running():
            return {"message": "Bot is already running"}
        try:
            # Prepare environment with USER_ID and latest timeframe
            env = os.environ.copy()
            if user_id:
                env["USER_ID"] = user_id
            if timeframe:
                env["TRADING_TIMEFRAME"] = str(timeframe).lower()
            
            _bot_process = subprocess.Popen(
                [sys.executable, str(BOT_DIR / "main.py")],
                cwd=str(BOT_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env
            )

            # Helper to stream logs to queue and console
            def stream_logs(pipe):
                print("[STREAM] Starting to read subprocess stdout...")
                log_count = 0
                try:
                    for line in iter(pipe.readline, ''):
                        clean_line = line.strip()
                        if not clean_line: 
                            continue
                        print(f"🤖 {clean_line}")
                        log_count += 1
                        
                        # Add to queue for frontend
                        log_entry = {
                            "message": clean_line,
                            "timestamp": datetime.now().isoformat()
                        }
                        try:
                            _logs_queue.put_nowait(log_entry)
                            if log_count % 20 == 0:
                                print(f"[STREAM] Queued {log_count} logs so far, queue size: {_logs_queue.qsize()}")
                        except queue.Full:
                            removed = _logs_queue.get()
                            _logs_queue.put_nowait(log_entry)
                            print(f"[STREAM] Queue full, removed: {removed['message'][:50]}")
                except Exception as e:
                    print(f"[STREAM] Exception reading pipe: {e}")
                finally:
                    pipe.close()
                    print(f"[STREAM] Pipe closed. Total logs queued: {log_count}")

            stream_thread = threading.Thread(target=stream_logs, args=(_bot_process.stdout,), daemon=True)
            stream_thread.start()
            effective_tf = env.get("TRADING_TIMEFRAME", os.getenv("TRADING_TIMEFRAME", "5m"))
            print(f"[SUBPROCESS] Bot process started with PID {_bot_process.pid}, timeframe={effective_tf}, stream thread started")
            
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

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8888)
    args = parser.parse_args()

    print(f"\n🚀 XauBot API Server Starting on port {args.port}...")
    print("Keep this window open to stay connected to your Cloud Dashboard.\n")
    uvicorn.run(app, host="0.0.0.0", port=args.port)

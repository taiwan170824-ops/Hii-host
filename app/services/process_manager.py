import subprocess
import psutil
import os
import signal
import asyncio
import time
from pathlib import Path
from datetime import datetime
from app.models.database import get_db

BOTS_DIR = Path(__file__).parent.parent.parent / "bots"
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"

BOTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# In-memory process registry: bot_id -> process
_processes: dict[int, subprocess.Popen] = {}
_monitor_task = None

def get_bot_dir(bot_id: int) -> Path:
    d = BOTS_DIR / str(bot_id)
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_log_path(bot_id: int) -> Path:
    return LOGS_DIR / f"bot_{bot_id}.log"

def get_err_log_path(bot_id: int) -> Path:
    return LOGS_DIR / f"bot_{bot_id}_err.log"

def is_process_alive(pid: int) -> bool:
    try:
        p = psutil.Process(pid)
        return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False

def start_bot(bot_id: int) -> dict:
    db = get_db()
    try:
        bot = db.execute("SELECT * FROM bots WHERE id=?", (bot_id,)).fetchone()
        if not bot:
            return {"success": False, "error": "Bot not found"}

        # Kill existing process if any
        if bot_id in _processes:
            try:
                _processes[bot_id].terminate()
            except Exception:
                pass
            del _processes[bot_id]

        bot_dir = get_bot_dir(bot_id)
        startup_file = bot["startup_file"]
        command = bot["startup_command"]

        if not (bot_dir / startup_file).exists():
            return {"success": False, "error": f"Startup file '{startup_file}' not found"}

        # Build env
        env = os.environ.copy()
        env_rows = db.execute("SELECT key, value FROM bot_env WHERE bot_id=?", (bot_id,)).fetchall()
        for row in env_rows:
            env[row["key"]] = row["value"]

        log_f = open(get_log_path(bot_id), "a")
        err_f = open(get_err_log_path(bot_id), "a")
        log_f.write(f"\n{'='*50}\n[{datetime.now()}] Starting bot...\n{'='*50}\n")
        log_f.flush()

        cmd = [command, startup_file] if command else ["python", startup_file]
        proc = subprocess.Popen(
            cmd,
            cwd=str(bot_dir),
            env=env,
            stdout=log_f,
            stderr=err_f,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )

        _processes[bot_id] = proc
        now = datetime.now().isoformat()
        db.execute(
            "UPDATE bots SET status='running', pid=?, last_started=?, uptime_start=? WHERE id=?",
            (proc.pid, now, now, bot_id)
        )
        db.commit()
        return {"success": True, "pid": proc.pid}
    finally:
        db.close()

def stop_bot(bot_id: int) -> dict:
    db = get_db()
    try:
        bot = db.execute("SELECT * FROM bots WHERE id=?", (bot_id,)).fetchone()
        if not bot:
            return {"success": False, "error": "Bot not found"}

        stopped = False
        if bot_id in _processes:
            proc = _processes[bot_id]
            try:
                if os.name != 'nt':
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                else:
                    proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            del _processes[bot_id]
            stopped = True

        # Also kill by PID from DB
        pid = bot["pid"]
        if pid and is_process_alive(pid):
            try:
                psutil.Process(pid).terminate()
                stopped = True
            except Exception:
                pass

        db.execute(
            "UPDATE bots SET status='stopped', pid=NULL, last_stopped=?, uptime_start=NULL WHERE id=?",
            (datetime.now().isoformat(), bot_id)
        )
        db.commit()
        return {"success": True, "stopped": stopped}
    finally:
        db.close()

def restart_bot(bot_id: int) -> dict:
    stop_bot(bot_id)
    time.sleep(1)
    return start_bot(bot_id)

def get_bot_stats(bot_id: int) -> dict:
    db = get_db()
    try:
        bot = db.execute("SELECT * FROM bots WHERE id=?", (bot_id,)).fetchone()
        if not bot:
            return {}

        stats = {
            "status": bot["status"],
            "pid": bot["pid"],
            "restart_count": bot["restart_count"],
            "uptime_seconds": 0,
            "cpu_percent": 0.0,
            "memory_mb": 0.0,
        }

        pid = bot["pid"]
        if pid and is_process_alive(pid):
            try:
                p = psutil.Process(pid)
                stats["cpu_percent"] = p.cpu_percent(interval=0.1)
                stats["memory_mb"] = round(p.memory_info().rss / 1024 / 1024, 2)
                if bot["uptime_start"]:
                    uptime_start = datetime.fromisoformat(bot["uptime_start"])
                    stats["uptime_seconds"] = int((datetime.now() - uptime_start).total_seconds())
            except Exception:
                pass
        elif bot["status"] == "running":
            # Process died
            db.execute("UPDATE bots SET status='stopped', pid=NULL WHERE id=?", (bot_id,))
            db.commit()
            stats["status"] = "stopped"

        return stats
    finally:
        db.close()

async def monitor_loop():
    """Background task: check bots and auto-restart crashed ones."""
    while True:
        await asyncio.sleep(10)
        db = get_db()
        try:
            bots = db.execute(
                "SELECT * FROM bots WHERE status='running' AND auto_restart=1"
            ).fetchall()
            for bot in bots:
                pid = bot["pid"]
                bot_id = bot["id"]
                if not pid or not is_process_alive(pid):
                    # Log crash
                    db.execute(
                        "INSERT INTO crash_logs (bot_id, reason) VALUES (?, ?)",
                        (bot_id, "Process not found / crashed")
                    )
                    db.execute(
                        "UPDATE bots SET restart_count=restart_count+1 WHERE id=?",
                        (bot_id,)
                    )
                    db.commit()
                    # Write to log
                    with open(get_err_log_path(bot_id), "a") as f:
                        f.write(f"\n[{datetime.now()}] BOT CRASHED - Auto restarting...\n")
                    start_bot(bot_id)
        except Exception as e:
            print(f"Monitor error: {e}")
        finally:
            db.close()

def get_system_stats() -> dict:
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    boot_time = psutil.boot_time()
    uptime_s = int(time.time() - boot_time)
    return {
        "cpu_percent": cpu,
        "ram_used_mb": round(mem.used / 1024 / 1024, 1),
        "ram_total_mb": round(mem.total / 1024 / 1024, 1),
        "ram_percent": mem.percent,
        "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
        "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
        "disk_percent": disk.percent,
        "uptime_seconds": uptime_s,
    }

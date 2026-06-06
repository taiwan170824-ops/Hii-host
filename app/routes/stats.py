from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from app.services.auth import get_current_user
from app.services.process_manager import get_log_path, get_err_log_path, get_system_stats
from app.models.database import get_db

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get("/stats")
def system_stats():
    stats = get_system_stats()
    db = get_db()
    try:
        total = db.execute("SELECT COUNT(*) as c FROM bots").fetchone()["c"]
        running = db.execute("SELECT COUNT(*) as c FROM bots WHERE status='running'").fetchone()["c"]
        stats["total_bots"] = total
        stats["running_bots"] = running
        stats["stopped_bots"] = total - running
        return stats
    finally:
        db.close()

@router.get("/logs/{bot_id}")
def get_logs(
    bot_id: int,
    lines: int = Query(100, ge=1, le=2000),
    error: bool = False
):
    log_path = get_err_log_path(bot_id) if error else get_log_path(bot_id)
    if not log_path.exists():
        return PlainTextResponse("No logs yet.")
    
    try:
        with open(log_path, "r", errors="replace") as f:
            all_lines = f.readlines()
        tail = all_lines[-lines:]
        return PlainTextResponse("".join(tail))
    except Exception as e:
        raise HTTPException(400, str(e))

@router.delete("/logs/{bot_id}")
def clear_logs(bot_id: int):
    for p in [get_log_path(bot_id), get_err_log_path(bot_id)]:
        if p.exists():
            p.write_text("")
    return {"success": True}

@router.get("/dashboard")
def dashboard():
    stats = get_system_stats()
    db = get_db()
    try:
        total = db.execute("SELECT COUNT(*) as c FROM bots").fetchone()["c"]
        running = db.execute("SELECT COUNT(*) as c FROM bots WHERE status='running'").fetchone()["c"]
        stats["total_bots"] = total
        stats["running_bots"] = running
        stats["stopped_bots"] = total - running
        return stats
    finally:
        db.close()

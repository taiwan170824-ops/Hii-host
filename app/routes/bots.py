from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.models.database import get_db
from app.services.auth import get_current_user
from app.services import process_manager as pm

router = APIRouter(prefix="/bot", dependencies=[Depends(get_current_user)])

class CreateBot(BaseModel):
    name: str
    startup_file: str
    startup_command: str = "python"

class RenameBot(BaseModel):
    bot_id: int
    new_name: str

class BotAction(BaseModel):
    bot_id: int

class EnvVar(BaseModel):
    bot_id: int
    key: str
    value: str

@router.post("/create")
def create_bot(data: CreateBot):
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO bots (name, directory, startup_file, startup_command) VALUES (?, ?, ?, ?)",
            (data.name, "", data.startup_file, data.startup_command)
        )
        bot_id = cur.lastrowid
        bot_dir = pm.get_bot_dir(bot_id)
        db.execute("UPDATE bots SET directory=? WHERE id=?", (str(bot_dir), bot_id))
        db.commit()
        return {"success": True, "bot_id": bot_id}
    finally:
        db.close()

@router.post("/start")
def start_bot(data: BotAction):
    return pm.start_bot(data.bot_id)

@router.post("/stop")
def stop_bot(data: BotAction):
    return pm.stop_bot(data.bot_id)

@router.post("/restart")
def restart_bot(data: BotAction):
    return pm.restart_bot(data.bot_id)

@router.post("/delete")
def delete_bot(data: BotAction):
    pm.stop_bot(data.bot_id)
    db = get_db()
    try:
        db.execute("DELETE FROM bots WHERE id=?", (data.bot_id,))
        db.commit()
        import shutil
        bot_dir = pm.get_bot_dir(data.bot_id)
        if bot_dir.exists():
            shutil.rmtree(bot_dir)
        return {"success": True}
    finally:
        db.close()

@router.post("/rename")
def rename_bot(data: RenameBot):
    db = get_db()
    try:
        db.execute("UPDATE bots SET name=? WHERE id=?", (data.new_name, data.bot_id))
        db.commit()
        return {"success": True}
    finally:
        db.close()

@router.get("/list")
def list_bots():
    db = get_db()
    try:
        bots = db.execute("SELECT * FROM bots ORDER BY created_at DESC").fetchall()
        result = []
        for bot in bots:
            b = dict(bot)
            stats = pm.get_bot_stats(bot["id"])
            b.update(stats)
            result.append(b)
        return result
    finally:
        db.close()

@router.get("/detail/{bot_id}")
def bot_detail(bot_id: int):
    db = get_db()
    try:
        bot = db.execute("SELECT * FROM bots WHERE id=?", (bot_id,)).fetchone()
        if not bot:
            raise HTTPException(404, "Not found")
        b = dict(bot)
        b.update(pm.get_bot_stats(bot_id))
        envs = db.execute("SELECT key, value FROM bot_env WHERE bot_id=?", (bot_id,)).fetchall()
        b["env"] = [dict(e) for e in envs]
        crashes = db.execute(
            "SELECT * FROM crash_logs WHERE bot_id=? ORDER BY crashed_at DESC LIMIT 10",
            (bot_id,)
        ).fetchall()
        b["crash_logs"] = [dict(c) for c in crashes]
        return b
    finally:
        db.close()

@router.post("/env/set")
def set_env(data: EnvVar):
    db = get_db()
    try:
        db.execute(
            "INSERT INTO bot_env (bot_id, key, value) VALUES (?, ?, ?) ON CONFLICT(bot_id, key) DO UPDATE SET value=?",
            (data.bot_id, data.key, data.value, data.value)
        )
        db.commit()
        return {"success": True}
    finally:
        db.close()

@router.post("/env/delete")
def del_env(data: dict):
    db = get_db()
    try:
        db.execute("DELETE FROM bot_env WHERE bot_id=? AND key=?", (data["bot_id"], data["key"]))
        db.commit()
        return {"success": True}
    finally:
        db.close()

@router.post("/toggle-auto-restart")
def toggle_auto_restart(data: BotAction):
    db = get_db()
    try:
        db.execute(
            "UPDATE bots SET auto_restart = CASE WHEN auto_restart=1 THEN 0 ELSE 1 END WHERE id=?",
            (data.bot_id,)
        )
        db.commit()
        bot = db.execute("SELECT auto_restart FROM bots WHERE id=?", (data.bot_id,)).fetchone()
        return {"success": True, "auto_restart": bool(bot["auto_restart"])}
    finally:
        db.close()

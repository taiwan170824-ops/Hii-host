import os
import tempfile
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from app.services.auth import get_current_user
from app.services import file_manager as fm

router = APIRouter(prefix="/files", dependencies=[Depends(get_current_user)])

@router.get("/list/{bot_id}")
def list_files(bot_id: int, path: str = ""):
    return fm.list_files(bot_id, path)

@router.get("/read/{bot_id}")
def read_file(bot_id: int, path: str):
    try:
        content = fm.read_file(bot_id, path)
        return {"content": content, "path": path}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post("/write/{bot_id}")
async def write_file(bot_id: int, data: dict):
    try:
        fm.write_file(bot_id, data["path"], data["content"])
        return {"success": True}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post("/upload/{bot_id}")
async def upload_file(
    bot_id: int,
    file: UploadFile = File(...),
    path: str = Form("")
):
    try:
        bot_dir = fm.get_bot_dir(bot_id)
        dest_dir = fm.safe_path(bot_id, path) if path else bot_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / file.filename
        
        content = await file.read()
        dest_file.write_bytes(content)

        # Auto-extract zip
        if file.filename.endswith(".zip"):
            fm.extract_zip(bot_id, dest_file, path)
            return {"success": True, "extracted": True}
        
        return {"success": True, "filename": file.filename}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post("/delete/{bot_id}")
def delete_file(bot_id: int, data: dict):
    try:
        fm.delete_path(bot_id, data["path"])
        return {"success": True}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post("/rename/{bot_id}")
def rename_file(bot_id: int, data: dict):
    try:
        fm.rename_path(bot_id, data["path"], data["new_name"])
        return {"success": True}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post("/mkdir/{bot_id}")
def mkdir(bot_id: int, data: dict):
    try:
        fm.create_folder(bot_id, data["path"])
        return {"success": True}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.get("/download/{bot_id}")
def download_file(bot_id: int, path: str):
    try:
        p = fm.safe_path(bot_id, path)
        if not p.is_file():
            raise HTTPException(404, "File not found")
        return FileResponse(str(p), filename=p.name)
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post("/backup/{bot_id}")
def backup_bot(bot_id: int):
    try:
        filename = fm.create_backup(bot_id)
        return {"success": True, "filename": filename}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.get("/backups/{bot_id}")
def list_backups(bot_id: int):
    return fm.list_backups(bot_id)

@router.post("/restore/{bot_id}")
def restore_backup(bot_id: int, data: dict):
    try:
        fm.restore_backup(bot_id, data["filename"])
        return {"success": True}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.get("/backup/download/{filename}")
def download_backup(filename: str):
    from app.services.file_manager import BACKUPS_DIR
    p = BACKUPS_DIR / filename
    if not p.exists():
        raise HTTPException(404, "Backup not found")
    return FileResponse(str(p), filename=filename)

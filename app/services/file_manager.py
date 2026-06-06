import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

BOTS_DIR = Path(__file__).parent.parent.parent / "bots"
BACKUPS_DIR = Path(__file__).parent.parent.parent / "backups"

ALLOWED_EXTENSIONS = {
    '.py', '.txt', '.env', '.json', '.yaml', '.yml', '.cfg', '.ini',
    '.md', '.sh', '.toml', '.xml', '.csv', '.log', '.html', '.js', '.css'
}

def get_bot_dir(bot_id: int) -> Path:
    d = BOTS_DIR / str(bot_id)
    d.mkdir(parents=True, exist_ok=True)
    return d

def safe_path(bot_id: int, rel: str) -> Path:
    base = get_bot_dir(bot_id).resolve()
    target = (base / rel).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("Path traversal not allowed")
    return target

def list_files(bot_id: int, subpath: str = "") -> list:
    base = get_bot_dir(bot_id)
    target = safe_path(bot_id, subpath) if subpath else base
    if not target.exists():
        return []

    entries = []
    for item in sorted(target.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
        rel = str(item.relative_to(base))
        stat = item.stat()
        entries.append({
            "name": item.name,
            "path": rel,
            "is_dir": item.is_dir(),
            "size": stat.st_size if item.is_file() else 0,
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "editable": item.suffix in ALLOWED_EXTENSIONS if item.is_file() else False,
        })
    return entries

def read_file(bot_id: int, rel: str) -> str:
    p = safe_path(bot_id, rel)
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {rel}")
    if p.suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("File type not editable")
    return p.read_text(errors="replace")

def write_file(bot_id: int, rel: str, content: str):
    p = safe_path(bot_id, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)

def delete_path(bot_id: int, rel: str):
    p = safe_path(bot_id, rel)
    if p.is_dir():
        shutil.rmtree(p)
    else:
        p.unlink()

def rename_path(bot_id: int, rel: str, new_name: str):
    p = safe_path(bot_id, rel)
    new_p = p.parent / new_name
    p.rename(new_p)

def create_folder(bot_id: int, rel: str):
    p = safe_path(bot_id, rel)
    p.mkdir(parents=True, exist_ok=True)

def extract_zip(bot_id: int, zip_path: Path, dest_rel: str = ""):
    dest = safe_path(bot_id, dest_rel) if dest_rel else get_bot_dir(bot_id)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(dest)
    zip_path.unlink(missing_ok=True)

def create_backup(bot_id: int) -> str:
    bot_dir = get_bot_dir(bot_id)
    BACKUPS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"bot_{bot_id}_{ts}.zip"
    out = BACKUPS_DIR / filename
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in bot_dir.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(bot_dir))
    return filename

def list_backups(bot_id: int) -> list:
    BACKUPS_DIR.mkdir(exist_ok=True)
    result = []
    for f in sorted(BACKUPS_DIR.glob(f"bot_{bot_id}_*.zip"), reverse=True):
        stat = f.stat()
        result.append({
            "filename": f.name,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return result

def restore_backup(bot_id: int, filename: str):
    backup_file = BACKUPS_DIR / filename
    if not backup_file.exists():
        raise FileNotFoundError("Backup not found")
    bot_dir = get_bot_dir(bot_id)
    shutil.rmtree(bot_dir)
    bot_dir.mkdir(parents=True)
    with zipfile.ZipFile(backup_file, 'r') as zf:
        zf.extractall(bot_dir)

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.models.database import init_db
from app.routes import auth, bots, files, stats
from app.services.process_manager import monitor_loop

BASE = Path(__file__).parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(monitor_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="BotPanel", lifespan=lifespan, docs_url=None, redoc_url=None)

# Static files
static_dir = BASE / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# API Routes
app.include_router(auth.router, prefix="/api")
app.include_router(bots.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(stats.router, prefix="/api")

# Serve SPA for all non-API routes
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    index = BASE / "templates" / "index.html"
    return FileResponse(str(index))

@app.get("/")
async def root():
    index = BASE / "templates" / "index.html"
    return FileResponse(str(index))

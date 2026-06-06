#!/usr/bin/env python3
"""
BotPanel — Lightweight Telegram Bot Hosting Panel
Run: python run.py
"""
import uvicorn
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="warning",
        access_log=False,
        # Limit workers for low-RAM usage
        workers=1,
    )

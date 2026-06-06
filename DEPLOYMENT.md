# BotPanel — Deployment Guide

A lightweight Telegram Bot Hosting Panel optimized for 300–400MB RAM VPS.

---

## Quick Start (Ubuntu VPS)

```bash
# 1. Clone or upload the project
cd /opt
git clone <your-repo> botpanel
cd botpanel

# 2. Install Python 3.10+
sudo apt update && sudo apt install -y python3 python3-pip python3-venv

# 3. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run
python run.py
```

Visit: **http://your-server-ip:8000**
Default login: `admin` / `admin123`

---

## Run as Systemd Service (Recommended)

```bash
sudo nano /etc/systemd/system/botpanel.service
```

```ini
[Unit]
Description=BotPanel - Telegram Bot Manager
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/botpanel
Environment=SECRET_KEY=change-this-to-random-string
ExecStart=/opt/botpanel/venv/bin/python run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable botpanel
sudo systemctl start botpanel
sudo systemctl status botpanel
```

---

## Nginx Reverse Proxy (Optional)

```nginx
server {
    listen 80;
    server_name panel.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable SSL with Certbot:
```bash
sudo certbot --nginx -d panel.yourdomain.com
```

---

## Deploy on Railway

1. Push code to GitHub
2. Create new Railway project → Deploy from GitHub
3. Set environment variables:
   - `SECRET_KEY` = random 32-char string
   - `PORT` = 8000
4. Deploy

---

## Deploy on Render (Background Worker)

1. Create Web Service
2. Build command: `pip install -r requirements.txt`
3. Start command: `python run.py`
4. Environment: `SECRET_KEY=your-secret`

---

## Deploy on Koyeb

1. Create App → GitHub
2. Run command: `python run.py`
3. Port: 8000
4. Set `SECRET_KEY` env var

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | auto | JWT secret (CHANGE IN PRODUCTION) |
| `PORT` | 8000 | HTTP port |
| `HOST` | 0.0.0.0 | Bind address |

---

## Change Admin Password

After login, open browser console and run:
```javascript
// Or use the API directly
fetch('/api/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({username: 'admin', password: 'admin123'})
})
```

To manually change password via SQLite:
```bash
cd /opt/botpanel
source venv/bin/activate
python3 -c "
from app.services.auth import hash_password
from app.models.database import get_db
db = get_db()
db.execute(\"UPDATE users SET password_hash=? WHERE username='admin'\", (hash_password('newpassword'),))
db.commit()
print('Password updated')
"
```

---

## RAM Optimization Tips

1. **Use Python bots only** — they run in-process without overhead
2. **Avoid keeping many bots running simultaneously** on 300MB VPS
3. **Use swap file** as safety net:
   ```bash
   sudo fallocate -l 1G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```
4. Panel itself uses **~40–60MB RAM** with no bots running

---

## Project Structure

```
botpanel/
├── run.py                  # Entry point
├── requirements.txt
├── app/
│   ├── main.py             # FastAPI app
│   ├── routes/
│   │   ├── auth.py         # Login/JWT
│   │   ├── bots.py         # Bot CRUD + process control
│   │   ├── files.py        # File manager
│   │   └── stats.py        # Monitoring + logs
│   ├── services/
│   │   ├── auth.py         # JWT + password hashing
│   │   ├── process_manager.py  # Bot processes + auto-restart
│   │   └── file_manager.py     # File operations
│   ├── models/
│   │   └── database.py     # SQLite schema + init
│   └── templates/
│       └── index.html      # Complete SPA frontend
├── database/
│   └── panel.db            # SQLite database (auto-created)
├── bots/
│   └── {bot_id}/           # Each bot's files
├── backups/                # ZIP backups
└── logs/
    ├── bot_1.log           # stdout logs
    └── bot_1_err.log       # stderr logs
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/login` | Authenticate, get JWT |
| GET | `/api/dashboard` | System stats + bot counts |
| GET | `/api/stats` | System resource usage |
| GET | `/api/bot/list` | List all bots |
| POST | `/api/bot/create` | Create bot |
| POST | `/api/bot/start` | Start bot |
| POST | `/api/bot/stop` | Stop bot |
| POST | `/api/bot/restart` | Restart bot |
| POST | `/api/bot/delete` | Delete bot + files |
| POST | `/api/bot/rename` | Rename bot |
| GET | `/api/bot/detail/{id}` | Bot details + env + crash logs |
| POST | `/api/bot/env/set` | Set env variable |
| POST | `/api/bot/env/delete` | Remove env variable |
| GET | `/api/files/list/{bot_id}` | List files |
| GET | `/api/files/read/{bot_id}` | Read file content |
| POST | `/api/files/write/{bot_id}` | Save file content |
| POST | `/api/files/upload/{bot_id}` | Upload file (auto-extracts ZIP) |
| POST | `/api/files/delete/{bot_id}` | Delete file/folder |
| POST | `/api/files/rename/{bot_id}` | Rename file/folder |
| POST | `/api/files/mkdir/{bot_id}` | Create folder |
| GET | `/api/files/download/{bot_id}` | Download file |
| POST | `/api/files/backup/{bot_id}` | Create ZIP backup |
| GET | `/api/files/backups/{bot_id}` | List backups |
| POST | `/api/files/restore/{bot_id}` | Restore backup |
| GET | `/api/logs/{bot_id}` | Get bot logs |
| DELETE | `/api/logs/{bot_id}` | Clear bot logs |

---

## Security Notes

- Change `SECRET_KEY` in production
- Change default admin password immediately
- Use Nginx + SSL in production
- The panel runs bot processes as the same user — use a dedicated low-privilege user
- File access is sandboxed to each bot's directory

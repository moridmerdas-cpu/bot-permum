# Instagram Account Manager Bot

Telegram bot for managing your own Instagram account — bulk comment deletion, unlike-all, account info. Admin panel included.

## Architecture

```
├── main.py                 # Entry point
├── app/
│   ├── bot.py              # Telegram application setup
│   ├── instagram.py        # Instagram client wrapper (instagrapi)
│   └── handlers.py         # User + Admin command/callback handlers
├── config/
│   └── settings.py         # Environment-based config
├── utils/
│   └── database.py         # SQLAlchemy models (User, AdminLog, BotStats)
├── render.yaml              # Render deployment config
├── runtime.txt              # Python 3.14 pin
└── requirements.txt
```

## Setup (Local)

```bash
python3.14 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill in TELEGRAM_TOKEN and ADMIN_TELEGRAM_ID
python main.py
```

## Deploy to Render

1. Push this repo to GitHub.
2. On Render: New → Blueprint → connect repo. `render.yaml` handles the rest.
3. Set secret env vars in the Render dashboard (not committed):
   - `TELEGRAM_TOKEN`
   - `ADMIN_TELEGRAM_ID`
   - `ADMIN_PASSWORD`
   - `DATABASE_URL` (use Render Postgres for production, not SQLite — SQLite on Render's ephemeral disk won't survive redeploys without the mounted disk)
   - `TELEGRAM_WEBHOOK_URL` — set to `https://<your-service>.onrender.com/webhook` once the service is live
4. Disk is mounted at `/var/data` for session persistence — sessions live at `/var/data/sessions`.

## Admin Panel

Only `ADMIN_TELEGRAM_ID` can open `/admin`. Shows:
- Total / active user counts
- Recent user list
- Action logs (every delete-comments / unlike-all call is logged with timestamp)

## What this does NOT do

- No password storage. Login uses `instagrapi`, dumps a cookie-based session to disk, never persists the raw password.
- No mass actions against accounts you don't control. Every action (`delete_own_comments`, `unlike_all_posts`) operates strictly on the authenticated account's own media.
- No bypass of Instagram's 2FA or challenge flow — if Instagram throws a checkpoint, the login fails cleanly and the user is told to check the app.

## Known Instagram API risk

`instagrapi` reverse-engineers the private mobile API. Instagram can and does rate-limit or flag accounts that automate actions aggressively. Keep the per-run media limit (currently 100) reasonable, and don't run `unlike_all` / `delete_comments` back-to-back in tight loops — that's the fastest path to a temporary action block.

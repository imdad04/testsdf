# BUTA STORE

Telegram WebApp marketplace for digital goods (Spotify / YouTube Premium / Discord Nitro / etc.) with semi-manual fulfillment: client pays via Platega or CryptoBot, an operator gets a card in Telegram with a "buy from here" link to the source shop, fulfills the order and pastes the key — bot delivers it to the client.

## Stack
- **Backend:** Python 3.11, FastAPI, aiogram 3, SQLAlchemy 2 async, Alembic, Redis
- **DB:** PostgreSQL 16
- **Frontend:** React 18 + Vite + TypeScript + Tailwind (dark UI)
- **Payments:** Platega, CryptoBot (Crypto Pay API)
- **Infra:** Docker Compose, nginx (prod)

## Quick start (local dev)

```bash
cp .env.example .env       # fill in secrets
docker compose up -d postgres redis
docker compose up backend  # runs FastAPI + bot
docker compose up webapp   # Vite on :5173
```

Open the bot in Telegram → `/start` → tap "Open store".

To expose the WebApp HTTPS URL to Telegram in dev, use ngrok / cloudflared:
```bash
cloudflared tunnel --url http://localhost:5173
# put the resulting https:// url into WEBAPP_URL in .env, restart backend
```

## Production (Ubuntu 24.04 VPS)

See `deploy/README.md`. Short version:
```bash
git clone <repo> /opt/buta-store && cd /opt/buta-store
cp .env.example .env && nano .env   # fill in real secrets
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Project layout
```
backend/        FastAPI + aiogram bot (single process)
  app/
    bot/        Telegram handlers (client / operator / admin)
    routers/    REST endpoints used by WebApp
    services/   Platega, CryptoBot, backup, notifications
    models.py   SQLAlchemy models
webapp/         React + Vite frontend
deploy/         nginx config + deploy notes
scripts/        Seed / utility scripts
```

## Security
- All secrets live in `.env` (gitignored). **Never** commit `.env`.
- Rotate `BOT_TOKEN` and `PLATEGA_API_KEY` if they ever leak.
- WebApp auth uses Telegram `initData` HMAC verification — clients can't spoof user IDs.
- Payment webhooks verify signatures (Platega) and tokens (CryptoBot).
- Daily encrypted DB backups → private Telegram channel.

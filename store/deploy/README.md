# BUTA STORE — Production deploy on Ubuntu 24.04 VPS

## 1. Prepare VPS

```bash
# as root
apt update && apt upgrade -y
apt install -y docker.io docker-compose-v2 git ufw certbot
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
```

## 2. Get the code

```bash
mkdir -p /opt && cd /opt
git clone <your repo url> buta-store
cd buta-store
cp .env.example .env
nano .env   # fill in real BOT_TOKEN, PLATEGA_*, CRYPTOBOT_TOKEN, ADMIN_IDS, BACKUP_PASSWORD, WEBAPP_URL
```

Set `WEBAPP_URL=https://your.domain` to match the cert below.

## 3. TLS cert (Let's Encrypt)

Stop nginx first if running, then:
```bash
certbot certonly --standalone -d your.domain
mkdir -p /opt/buta-store/deploy/certs
cp /etc/letsencrypt/live/your.domain/fullchain.pem /opt/buta-store/deploy/certs/
cp /etc/letsencrypt/live/your.domain/privkey.pem  /opt/buta-store/deploy/certs/
```

Edit `deploy/nginx.conf` — replace `your.domain` with the actual domain.

Auto-renew (run once):
```bash
(crontab -l 2>/dev/null; echo "15 3 * * * certbot renew --deploy-hook 'cp /etc/letsencrypt/live/your.domain/fullchain.pem /opt/buta-store/deploy/certs/ && cp /etc/letsencrypt/live/your.domain/privkey.pem /opt/buta-store/deploy/certs/ && docker compose -f /opt/buta-store/docker-compose.yml -f /opt/buta-store/docker-compose.prod.yml restart nginx'") | crontab -
```

## 4. Launch

```bash
cd /opt/buta-store
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose logs -f backend     # watch the bot start polling
```

## 5. Tell Telegram about the WebApp

In @BotFather:
```
/setdomain  → BUTAStoreBot → your.domain
/newapp     → BUTAStoreBot → name + description + icon + URL https://your.domain
/setmenubutton → BUTAStoreBot → 🛒 Магазин → https://your.domain
```

## 6. Configure payment webhooks

- **Platega** — webhook URL is set automatically when each invoice is created. No dashboard config needed.
- **CryptoBot** — in @CryptoBot → Crypto Pay → My Apps → set webhook URL: `https://your.domain/webhooks/cryptobot`

## 7. Seed initial catalog (one-time)

```bash
docker compose exec backend python -m scripts.seed
```

Or use the bot: `/admin → Категории → /addcat games Игры 🎮` etc., then `/addproduct`.

## 8. Operating it

- `/admin` in bot — full control panel
- `/backup` — manual encrypted backup → posted into BACKUP_CHAT_ID
- `/key <order_id> <key>` in operator chat — fast manual delivery
- Daily backups run at 04:00 UTC; old ones (>30 days) are auto-pruned

## 9. Updating

```bash
cd /opt/buta-store
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Migrations run automatically on backend container start (entrypoint.sh).

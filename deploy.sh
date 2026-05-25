#!/bin/bash
# ══════════════════════════════════════════════════════
# تبيان الطبي — Server Setup & Deploy Script
# Run on Oracle Cloud ARM VM (Ubuntu 22.04)
#
# First time:  bash deploy.sh setup
# Update code: bash deploy.sh deploy
# View logs:   bash deploy.sh logs
# ══════════════════════════════════════════════════════

set -e
REPO_URL="${REPO_URL:-https://github.com/YOUR_USERNAME/tebyan-medical.git}"
APP_DIR="/opt/tebyan"
COMPOSE="docker compose -f docker-compose.prod.yml"

# ── Colors ────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
err()  { echo -e "${RED}✗ $1${NC}"; exit 1; }

# ══════════════════════════════════════════════════════
case "${1:-help}" in

# ── SETUP: run once on a fresh server ────────────────
setup)
  echo "━━━ تبيان الطبي — Server Setup ━━━"

  # Docker
  if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker "$USER"
    ok "Docker installed"
  else
    ok "Docker already installed"
  fi

  # Docker Compose v2
  if ! docker compose version &>/dev/null; then
    apt-get install -y docker-compose-plugin
    ok "Docker Compose plugin installed"
  fi

  # Firewall
  ufw allow 22/tcp   # SSH
  ufw allow 80/tcp   # HTTP
  ufw allow 443/tcp  # HTTPS
  ufw --force enable
  ok "Firewall configured (22, 80, 443)"

  # Clone repo
  if [ ! -d "$APP_DIR" ]; then
    git clone "$REPO_URL" "$APP_DIR"
    ok "Repository cloned to $APP_DIR"
  else
    warn "Directory $APP_DIR already exists — skipping clone"
  fi

  # .env
  if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.production.example" "$APP_DIR/.env"
    warn "Created $APP_DIR/.env — FILL IN YOUR KEYS NOW:"
    warn "  nano $APP_DIR/.env"
    warn "Then run: bash $APP_DIR/deploy.sh ssl"
  else
    ok ".env already exists"
  fi

  echo ""
  echo "Next steps:"
  echo "  1. nano $APP_DIR/.env          ← fill in your API keys"
  echo "  2. DOMAIN=yourdomain.com EMAIL=you@example.com bash $APP_DIR/nginx/init-letsencrypt.sh"
  echo "  3. bash $APP_DIR/deploy.sh deploy"
  ;;

# ── DEPLOY: pull latest and restart ──────────────────
deploy)
  echo "━━━ Deploying تبيان الطبي ━━━"
  cd "$APP_DIR"

  [ ! -f .env ] && err ".env not found. Run: bash deploy.sh setup"

  git pull origin main
  ok "Code updated"

  $COMPOSE build --pull
  ok "Images built"

  $COMPOSE up -d
  ok "Containers started"

  echo "Waiting for health checks..."
  sleep 10
  $COMPOSE ps
  ;;

# ── SSL: get Let's Encrypt cert ───────────────────────
ssl)
  [ -z "$DOMAIN" ] && err "Set DOMAIN=yourdomain.com before running"
  [ -z "$EMAIL"  ] && err "Set EMAIL=you@example.com before running"
  cd "$APP_DIR"
  DOMAIN="$DOMAIN" EMAIL="$EMAIL" bash nginx/init-letsencrypt.sh
  ;;

# ── LOGS ──────────────────────────────────────────────
logs)
  cd "$APP_DIR"
  $COMPOSE logs -f --tail=100 "${2:-}"
  ;;

# ── STATUS ────────────────────────────────────────────
status)
  cd "$APP_DIR"
  $COMPOSE ps
  echo ""
  curl -s http://localhost/health | python3 -m json.tool 2>/dev/null || echo "Backend not reachable"
  ;;

# ── STOP ──────────────────────────────────────────────
stop)
  cd "$APP_DIR"
  $COMPOSE down
  ok "All containers stopped"
  ;;

# ── HELP ──────────────────────────────────────────────
*)
  echo "Usage: bash deploy.sh [setup|deploy|ssl|logs|status|stop]"
  echo ""
  echo "  setup   — Install Docker, clone repo, configure firewall"
  echo "  deploy  — Pull latest code and restart containers"
  echo "  ssl     — Get Let's Encrypt certificate (set DOMAIN= EMAIL= first)"
  echo "  logs    — Follow container logs (optional: logs backend)"
  echo "  status  — Show container status and health"
  echo "  stop    — Stop all containers"
  ;;
esac

#!/bin/bash
# ══════════════════════════════════════════════════════
# تبيان الطبي — Let's Encrypt Initial Certificate Setup
# Run ONCE on the server after DNS points to this IP
#
# Usage:
#   chmod +x nginx/init-letsencrypt.sh
#   DOMAIN=yourdomain.com EMAIL=you@email.com bash nginx/init-letsencrypt.sh
# ══════════════════════════════════════════════════════

set -e

DOMAIN="${DOMAIN:-example.com}"
EMAIL="${EMAIL:-admin@example.com}"
COMPOSE="docker compose -f docker-compose.prod.yml"

echo "━━━ Let's Encrypt Setup for $DOMAIN ━━━"

# 1. Replace DOMAIN placeholder in nginx.conf
sed -i "s/DOMAIN/$DOMAIN/g" nginx/nginx.conf
echo "✓ nginx.conf updated with domain: $DOMAIN"

# 2. Start nginx in HTTP-only mode (needs 80 open for ACME challenge)
# Temporarily use a self-signed cert so nginx can start
mkdir -p nginx/certs
if [ ! -f nginx/certs/fullchain.pem ]; then
  openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout nginx/certs/privkey.pem \
    -out nginx/certs/fullchain.pem \
    -days 1 -subj "/CN=$DOMAIN" 2>/dev/null
  echo "✓ Temporary self-signed cert created"
fi

# Start nginx
$COMPOSE up -d nginx
sleep 3

# 3. Get real certificate
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  -d "$DOMAIN" \
  -d "www.$DOMAIN"

echo "✓ Certificate obtained!"

# 4. Reload nginx with real cert
$COMPOSE exec nginx nginx -s reload
echo "✓ Nginx reloaded with Let's Encrypt certificate"

echo ""
echo "━━━ Done! Site available at https://$DOMAIN ━━━"

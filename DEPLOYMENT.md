# تبيان الطبي — Deployment Guide

## Prerequisites

- Docker ≥ 24 + Docker Compose v2
- A server with ≥ 4 GB RAM, ≥ 20 GB disk
- Domain name with DNS pointed to your server (for HTTPS)

---

## 1. Environment Setup

Copy and populate the environment file:

```bash
cp .env.example .env
```

Required variables:

```
GROQ_API_KEY=gsk_...
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_KEY=eyJ...
SUPABASE_DB_URL=postgresql+psycopg://...
FRONTEND_URL=https://your-domain.com
NEXTAUTH_SECRET=<32+ random chars>
```

Optional (features degrade gracefully without them):

```
COHERE_API_KEY=...          # reranking (falls back to BM25 only)
GOOGLE_VISION_API_KEY=...   # Vision OCR (falls back to EasyOCR)
GOOGLE_TTS_KEY=...          # Google TTS (falls back to gTTS)
ELEVENLABS_API_KEY=...      # ElevenLabs TTS
SENTRY_DSN=...              # Error monitoring
```

---

## 2. Nginx Configuration

Create `nginx/nginx.conf`:

```nginx
events { worker_connections 1024; }

http {
    upstream backend  { server backend:8000; }
    upstream frontend { server frontend:3000; }

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl;
        server_name your-domain.com;

        ssl_certificate     /etc/nginx/certs/fullchain.pem;
        ssl_certificate_key /etc/nginx/certs/privkey.pem;

        client_max_body_size 25M;

        location /api/    { proxy_pass http://backend; proxy_set_header Host $host; }
        location /health  { proxy_pass http://backend; }
        location /        { proxy_pass http://frontend; proxy_set_header Host $host; }
    }
}
```

Place TLS certificates in `nginx/certs/` (Let's Encrypt recommended).

---

## 3. Frontend Dockerfile

Create `frontend/Dockerfile`:

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
ENV PORT=3000
EXPOSE 3000
CMD ["node", "server.js"]
```

Enable standalone output in `next.config.js`:

```js
module.exports = { output: "standalone" }
```

---

## 4. Deploy

```bash
# Build and start all services
docker compose -f docker-compose.prod.yml up -d --build

# Check logs
docker compose -f docker-compose.prod.yml logs -f backend

# Check health
curl https://your-domain.com/health
```

---

## 5. Supabase Setup

Run once to set up the pgvector extension and required tables:

```sql
-- Enable pgvector
create extension if not exists vector;

-- Documents table for RAG
create table if not exists documents (
  id         bigserial primary key,
  content    text,
  embedding  vector(1024),
  metadata   jsonb
);
create index on documents using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- match_documents RPC
create or replace function match_documents(
  query_embedding vector(1024),
  match_count     int default 10,
  filter          jsonb default '{}'
)
returns table(id bigint, content text, metadata jsonb, similarity float)
language plpgsql as $$
begin
  return query
  select d.id, d.content, d.metadata,
         1 - (d.embedding <=> query_embedding) as similarity
  from documents d
  order by d.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Analyses table
create table if not exists analyses (
  id         uuid default gen_random_uuid() primary key,
  session_id text not null,
  findings   jsonb,
  summary    text,
  report     jsonb,
  created_at timestamptz default now()
);
create index on analyses(session_id, created_at desc);
```

---

## 6. PEFT/LoRA Fine-Tuning (Optional)

To improve Arabic medical analysis quality with your own data:

```bash
# 1. Prepare dataset from Supabase analyses
python training/prepare_dataset.py --source supabase --output_dir data/

# 2. Train LoRA adapter (requires GPU with ≥16 GB VRAM)
python training/train_lora.py \
    --model_name core42/jais-13b-chat \
    --data_dir data/ \
    --output_dir checkpoints/tebyan-v1 \
    --num_epochs 3 \
    --load_4bit

# 3. Evaluate
python training/evaluate_model.py \
    --base_model core42/jais-13b-chat \
    --lora_adapter checkpoints/tebyan-v1/lora_adapter \
    --val_data data/val.jsonl \
    --use_llm_judge \
    --groq_key $GROQ_API_KEY
```

Results are written to `eval_results/eval_summary.json`.

---

## 7. Monitoring

The `/api/metrics` endpoint exposes Prometheus-format metrics. Scrape with:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: tebyan
    static_configs:
      - targets: ['your-domain.com']
    metrics_path: /api/metrics
    scheme: https
```

Audit logs are written to the `audit_logs` Docker volume at `logs/audit/audit.jsonl` (rotating, max 50 MB × 10 files).

---

## 8. Updating

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build --no-deps backend
docker compose -f docker-compose.prod.yml up -d --build --no-deps frontend
```

The `--no-deps` flag updates only the specified service without restarting nginx or volumes.

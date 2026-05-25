# تبيان الطبي — Architecture

## System Overview

Tebyan Medical is a production-grade Arabic medical report analysis platform. Users upload lab reports (PDF or image), the system extracts findings, generates a clinical interpretation in Arabic, and provides an interactive voice-enabled chat assistant.

```
Frontend (Next.js 15)          Backend (FastAPI)              External Services
─────────────────────          ─────────────────              ─────────────────
Upload → /api/analyze ────────► AgentCoordinator              Groq (LLM/STT)
Chat   → /api/chat   ────────► RAG + LLM streaming            Supabase (pgvector)
Voice  → /api/voice  ────────► WhisperSTT / TTS               Cohere (rerank)
Risk   → /api/risk   ────────► RiskEngine                     Google Vision/TTS
```

---

## Backend Layer

### Entry Point

`backend/main.py` — FastAPI application. Registers all routes, mounts middleware, and wires dependency-injected singletons via `@lru_cache`.

### Multi-Agent Pipeline (`services/agents/`)

Replaces the flat `services/agent/pipeline.py` (kept for backward compat) with a structured agent graph:

```
AgentCoordinator
├── OCRAgent           — PDF (fitz + EasyOCR) + Image (Google Vision fallback)
├── ExtractionAgent    — regex parse → LLM fallback → physiological bounds filter
├── ClassificationAgent — panel detection (CBC, Thyroid, Liver, Kidney, Lipid, Diabetes)
├── MedicalReasoningAgent — RAG retrieval + panel-specific LLM prompt
└── SafetyAgent        — PDPL/NDMO compliance filter + emergency detection
```

Each agent extends `AgentBase` which provides retry-with-backoff and structured logging via `AgentContext`.

### RAG Stack (`services/rag/`, `services/search/`)

- **Embedding**: `intfloat/multilingual-e5-large` (1024-dim, via HuggingFace)
- **Vector store**: Supabase pgvector (`match_documents` RPC, 2834+ medical chunks)
- **Query expansion**: Groq LLM generates 3 alternate queries; `query_parser.py` adds Arabic synonym expansions
- **Retrieval**: BM25 fallback + Cohere `rerank-v3.5` cross-encoder
- **Cache**: 5-minute TTL in-memory LRU (`services/cache.py`) prevents redundant embedding calls

### Risk Engine (`services/risk/`)

Evidence-based clinical threshold scoring for 6 conditions. `FeatureExtractor` normalises findings into a 35-feature vector; each scorer (`_score_diabetes`, `_score_cardiovascular`, etc.) applies WHO/ADA/ACC clinical cutoffs. ML `.pkl` model files in `services/risk/models/` override rule-based scores when present.

### Voice (`services/voice/`)

- **STT**: `WhisperSTT` wraps Groq `whisper-large-v3`. Accepts WebM/MP4/OGG/WAV (25 MB max).
- **TTS**: Provider chain — Google Cloud TTS (Wavenet-A) → gTTS (free fallback) → ElevenLabs.

### LLM Router (`services/llm/router.py`)

`LLMRouter` wraps a primary provider (`GroqProvider`) and optional fallback (`HuggingFaceProvider`). Model selection: `llama-3.3-70b-versatile` for analysis, `llama-3.1-8b-instant` for chat.

### Security (`middleware/`)

- **`AuditMiddleware`**: Writes one JSON record per request to rotating log files (`logs/audit/audit.jsonl`). Marks PDPL-sensitive paths. Skips health/docs endpoints.
- **`validate_upload`**: Magic-byte sniffing (anti-MIME-spoofing), 20 MB size limit, extension blocklist.
- **`sanitize_text`**: Strips HTML tags, null bytes, XSS patterns, and SQL injection signatures from all user text inputs.

### Rate Limiting (`services/ratelimit.py`)

In-memory sliding window (no external dependency). Limits: analyze=5/min, chat=30/min, search=60/min. Uses `X-Forwarded-For` for IP detection behind proxies.

---

## Frontend Layer

**Next.js 15 App Router**, RTL Arabic, Tailwind CSS v4, Framer Motion.

| Component | Purpose |
|---|---|
| `upload-section.tsx` | File picker + `/api/analyze` call + loading state |
| `analysis-history.tsx` | Saved analyses list + semantic search + health trend chart |
| `health-trend-chart.tsx` | Recharts line chart — tracks lab values over time with alerts |
| `risk-dashboard.tsx` | Calls `/api/risk` + renders 6 radial gauge cards (collapsible) |
| `chat-bot.tsx` | Floating chat panel — streaming SSE + voice input/output |
| `voice-recorder.tsx` | MediaRecorder → `/api/voice/transcribe` + TTS playback |
| `compare-analyses.tsx` | Side-by-side analysis diff |

---

## Data Flow — Analysis Request

```
1. User uploads PDF/image
2. validate_upload() — size + MIME + magic bytes
3. AgentCoordinator.run()
   a. OCRAgent       → raw_text
   b. ExtractionAgent → findings[] (with impossible-value filter)
   c. ClassificationAgent → panel_code
   d. MedicalReasoningAgent → RAG context + LLM report
   e. SafetyAgent    → filtered report
4. Response: { findings, summary, report }
5. Frontend saves to Supabase via /api/analyses/save
6. RiskDashboard calls /api/risk with findings
```

---

## Key Design Decisions

- **No streaming for analysis**: Analysis takes 8–15 s; streaming a partial JSON would be malformed. Response is returned in full after all agents complete.
- **RAG cache before agent**: MedicalReasoningAgent checks `rag_cache` before calling pgvector — avoids redundant 300 ms embedding round-trips on identical queries.
- **Agents over monolith**: Each agent is independently retryable and observable via `AgentContext.logs`. Failures degrade gracefully — OCR failure sets `raw_text=""`, downstream agents handle empty input without crashing.
- **Rule-based risk scoring**: ML `.pkl` models are optional overrides. The platform is useful immediately without training data.
- **In-memory rate limiter**: Avoids Redis dependency for MVP. Replace with Redis-backed limiter for multi-process deployments.

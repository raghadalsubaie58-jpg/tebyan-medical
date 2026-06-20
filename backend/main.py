import os
from dotenv import load_dotenv
load_dotenv()  # local .env | Railway/Vercel: env vars set in dashboard
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
# HF_HOME: set as env var in production, or default to local cache
_here = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('HF_HOME', os.path.join(_here, '..', 'model_cache'))

# ── Sentry error monitoring (requires SENTRY_DSN in .env / Railway vars) ──
_SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if _SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        sentry_sdk.init(
            dsn=_SENTRY_DSN,
            integrations=[FastApiIntegration(transaction_style="endpoint")],
            traces_sample_rate=0.05,          # 5% of requests
            environment=os.getenv("ENVIRONMENT", "production"),
            release=os.getenv("RAILWAY_DEPLOYMENT_ID", "local"),
        )
        print("[Sentry] initialized")
    except ImportError:
        pass  # sentry-sdk not installed

import re
import json
import base64
import logging
from functools import lru_cache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

import requests as http_requests
import cohere
from groq import Groq   # used only by load_tools() to build raw client for agents

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi.responses import Response as HttpResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ── Internal services ──────────────────────────────────────────────────────
from services.search.embedding_service import get_embeddings
from services.search.semantic_search import SemanticSearchService
from services.rag.retriever import Retriever, RetrievalConfig
from services.rag.context_builder import build_context
from services.safety import filter_analysis_report, filter_chat_response, check_emergency, sanitize_query
from services.agents import AgentCoordinator
from services.llm import get_router, LLMRouter
from services.ratelimit import limit_analyze, limit_chat, limit_search
from services.cache import rag_cache, rag_cache_key, search_cache
from services.search.embedding_service import EMBED_MODEL
from medical_kb import kb as medical_kb
from prompts.loader import render as render_prompt, load as load_prompt
from middleware import AuditMiddleware, validate_upload, sanitize_text
from middleware.auth_middleware import optional_user

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY environment variable is not set")
COHERE_API_KEY    = os.getenv("COHERE_API_KEY")
SUPABASE_URL      = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY      = os.getenv("SUPABASE_KEY", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")  # service_role bypasses RLS
SUPABASE_DB_URL   = os.getenv("SUPABASE_DB_URL")
GOOGLE_VISION_KEY  = os.getenv("GOOGLE_VISION_API_KEY", "")
GOOGLE_TTS_KEY     = os.getenv("GOOGLE_TTS_KEY", "")
ELEVENLABS_KEY     = os.getenv("ELEVENLABS_API_KEY", "")
FRONTEND_URL      = os.getenv("FRONTEND_URL", "http://localhost:3000")

GROQ_MODEL      = "llama-3.3-70b-versatile"
GROQ_MODEL_CHAT = "llama-3.1-8b-instant"

log = logging.getLogger("tebyan.main")

app = FastAPI(title="تبيان الطبي API")

_is_production = os.getenv("ENVIRONMENT", "development") == "production"
_allowed_origins: list[str] = list(filter(None, [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    FRONTEND_URL if FRONTEND_URL != "http://localhost:3000" else None,
]))
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Session-Id", "X-Forwarded-For"],
    allow_credentials=False,
    max_age=600,
)
app.add_middleware(AuditMiddleware, environment=os.getenv("ENVIRONMENT", "development"))


def _pg_connect():
    # Try direct host connection first (pooler rejected tenant format)
    direct = re.sub(
        r"postgresql(?:\+psycopg)?://[^:]+:[^@]+@[^/]+/",
        f"postgresql://postgres:{os.getenv('SUPABASE_DB_PASSWORD', 'R1a2g3h4d56')}@db.assxdosinubpubeqjrso.supabase.co:5432/",
        SUPABASE_DB_URL,
    )
    import psycopg2
    try:
        return psycopg2.connect(direct, sslmode="require", connect_timeout=8)
    except Exception:
        fallback = SUPABASE_DB_URL.replace("postgresql+psycopg://", "postgresql://")
        return psycopg2.connect(fallback, sslmode="require", connect_timeout=8)


def ensure_analyses_table():
    """ينشئ جدول analyses في Supabase تلقائياً إذا لم يكن موجوداً"""
    if not SUPABASE_DB_URL:
        log.debug("SUPABASE_DB_URL not set — skipping DB setup")
        return
    try:
        conn = _pg_connect()
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
                session_id  text NOT NULL,
                findings    jsonb,
                summary     text,
                report      jsonb,
                created_at  timestamptz DEFAULT now()
            )
        """)
        cur.close()
        conn.close()
        log.info("analyses table ready")
    except Exception as e:
        log.error("analyses table setup failed: %s", e)


def ensure_chat_table():
    """ينشئ جدول chat_messages لحفظ تاريخ المحادثات عبر الجلسات"""
    if not SUPABASE_DB_URL:
        return
    try:
        conn = _pg_connect()
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id         uuid DEFAULT gen_random_uuid() PRIMARY KEY,
                session_id text NOT NULL,
                role       text NOT NULL,
                content    text NOT NULL,
                created_at timestamptz DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS idx_chat_session
                ON chat_messages(session_id, created_at);
        """)
        cur.close()
        conn.close()
        log.info("chat_messages table ready")
    except Exception as e:
        log.error("chat table setup failed: %s", e)


_START_TIME = __import__("time").time()
_REQUEST_COUNTS: dict[str, int] = {}
_ERROR_COUNTS:   dict[str, int] = {}


@app.middleware("http")
async def _track_requests(request: Request, call_next):
    path = request.url.path
    _REQUEST_COUNTS[path] = _REQUEST_COUNTS.get(path, 0) + 1
    response = await call_next(request)
    if response.status_code >= 500:
        _ERROR_COUNTS[path] = _ERROR_COUNTS.get(path, 0) + 1
    return response


@app.get("/health")
async def health():
    import time
    uptime_s = int(time.time() - _START_TIME)
    db_ok, chunk_count = False, 0
    try:
        _, _, search_svc, _ = load_tools()
        chunk_count = search_svc.count()
        db_ok = chunk_count > 0
    except Exception:
        pass
    return {
        "ok": True,
        "version":     os.getenv("RAILWAY_DEPLOYMENT_ID", "local"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "uptime_s":    uptime_s,
        "db": {
            "ok":     db_ok,
            "chunks": chunk_count,
            "source": "pgvector/supabase",
        },
        "model": {
            "name":   os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-large"),
            "loaded": db_ok,
        },
        "services": {
            "groq":   bool(GROQ_API_KEY),
            "cohere": bool(COHERE_API_KEY),
            "vision": bool(os.getenv("GOOGLE_VISION_API_KEY")),
        },
    }


@app.get("/api/metrics")
async def metrics():
    """Prometheus-style plaintext metrics for uptime monitoring."""
    import time
    uptime_s = int(time.time() - _START_TIME)
    cache_stats = rag_cache.stats()
    lines = [
        "# HELP tebyan_uptime_seconds Seconds since server start",
        "# TYPE tebyan_uptime_seconds counter",
        f"tebyan_uptime_seconds {uptime_s}",
        "",
        "# HELP tebyan_requests_total Total HTTP requests per path",
        "# TYPE tebyan_requests_total counter",
    ]
    for path, count in sorted(_REQUEST_COUNTS.items()):
        lines.append(f'tebyan_requests_total{{path="{path}"}} {count}')
    lines += [
        "",
        "# HELP tebyan_errors_total Total 5xx errors per path",
        "# TYPE tebyan_errors_total counter",
    ]
    for path, count in sorted(_ERROR_COUNTS.items()):
        lines.append(f'tebyan_errors_total{{path="{path}"}} {count}')
    lines += [
        "",
        "# HELP tebyan_rag_cache_size Current RAG cache entries",
        "# TYPE tebyan_rag_cache_size gauge",
        f"tebyan_rag_cache_size {cache_stats.get('size', 0)}",
        "",
        "# HELP tebyan_rag_cache_hits RAG cache hit count",
        "# TYPE tebyan_rag_cache_hits counter",
        f"tebyan_rag_cache_hits {cache_stats.get('hits', 0)}",
        "",
        "# HELP tebyan_rag_cache_misses RAG cache miss count",
        "# TYPE tebyan_rag_cache_misses counter",
        f"tebyan_rag_cache_misses {cache_stats.get('misses', 0)}",
        "",
        "# HELP tebyan_rag_cache_hit_rate RAG cache hit rate (0-1)",
        "# TYPE tebyan_rag_cache_hit_rate gauge",
        f"tebyan_rag_cache_hit_rate {cache_stats.get('hit_rate', 0)}",
        "",
        "# HELP tebyan_rag_cache_evictions RAG cache eviction count",
        "# TYPE tebyan_rag_cache_evictions counter",
        f"tebyan_rag_cache_evictions {cache_stats.get('evictions', 0)}",
    ]
    return HttpResponse(content="\n".join(lines), media_type="text/plain; version=0.0.4")


@app.on_event("startup")
async def startup():
    ensure_analyses_table()
    ensure_chat_table()
    load_router()
    load_tools()   # pre-load Groq client + embedding model + Supabase (NOT EasyOCR — loaded lazily)
    _load_lora_adapter()
    log.info("startup complete — all services warm")


@lru_cache(maxsize=1)
def load_router() -> LLMRouter:
    """Returns the LLM router singleton (Groq primary, HF fallback if configured)."""
    router = get_router()
    log.info("LLM router ready | provider=%s", router.provider_name)
    return router


@lru_cache(maxsize=1)
def load_tools():
    get_embeddings()   # warm up the embedding singleton
    groq_client   = Groq(api_key=GROQ_API_KEY)   # raw client for agents
    cohere_client = cohere.ClientV2(api_key=COHERE_API_KEY) if COHERE_API_KEY else None
    search_svc    = SemanticSearchService(SUPABASE_URL, SUPABASE_KEY)
    retriever     = Retriever(
        search_svc,
        co_client=cohere_client,
        query_expander=lambda q: generate_search_queries(groq_client, q),
    )
    log.info("tools loaded | db=%d chunks", search_svc.count())
    return groq_client, cohere_client, search_svc, retriever


@lru_cache(maxsize=1)
def load_coordinator() -> AgentCoordinator:
    groq_client, _, _, retriever = load_tools()
    return AgentCoordinator(
        groq_client=groq_client,
        retriever=retriever,
        kb=medical_kb,
        render_prompt_fn=render_prompt,
        retrieval_config_cls=RetrievalConfig,
        vision_key=GOOGLE_VISION_KEY,
    )


# ── PEFT/LoRA adapter auto-loader ──────────────────────────────────────────
# Place a trained adapter in backend/models/lora/ to activate local inference.
# When absent, the system uses Groq API transparently.

_LORA_PATH = os.path.join(os.path.dirname(__file__), "models", "lora")
_lora_model_info: dict = {"loaded": False, "path": None, "model_name": None}


def _load_lora_adapter() -> None:
    if not os.path.isdir(_LORA_PATH):
        log.info("No LoRA adapter directory found — using Groq API")
        return
    adapter_files = [f for f in os.listdir(_LORA_PATH) if f.endswith((".bin", ".safetensors"))]
    if not adapter_files:
        log.info("LoRA directory exists but is empty — using Groq API")
        return
    try:
        from peft import PeftModel  # noqa: F401
        _lora_model_info.update({"loaded": True, "path": _LORA_PATH,
                                  "model_name": adapter_files[0]})
        log.info("LoRA adapter detected at %s — local inference active", _LORA_PATH)
    except ImportError:
        log.warning("LoRA adapter found but peft not installed — using Groq API")


# ══════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════

def groq_generate(client, prompt: str, max_tokens: int = 2048) -> str:
    r = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=max_tokens,
    )
    return r.choices[0].message.content



def generate_search_queries(client, query: str) -> list:
    prompt = f"""أنت مساعد بحث طبي. حوّل السؤال إلى 3 استعلامات بحث مختلفة.
واحدة بالعربية واثنتان بالإنجليزية مع المصطلحات الطبية الدقيقة.
السؤال: {query}
أجب بقائمة JSON فقط: ["استعلام1", "query2", "query3"]"""
    try:
        raw = groq_generate(client, prompt, max_tokens=200).strip()
        if '[' in raw:
            raw = raw[raw.index('['):raw.rindex(']') + 1]
        queries = json.loads(raw)
        return [query] + [q for q in queries if isinstance(q, str)][:3]
    except Exception:
        return [query]




def get_rag_context(
    _db_unused,
    query: str,
    co_client=None,
    multi_query_client=None,
    k: int = 10,
    topic_type: str = None,
) -> tuple[str, str]:
    """Thin wrapper over Retriever — kept for backward compatibility."""
    try:
        _, _, _, retriever = load_tools()
        use_mq = multi_query_client is not None
        results, conf = retriever.retrieve(
            query,
            RetrievalConfig(k=k, use_multi_query=use_mq, topic_type=topic_type),
        )
        return build_context(results), conf
    except Exception as e:
        log.error("RAG retrieval failed: %s", e)
        return "", "لا يوجد"


# ══════════════════════════════════════════════
# M4 — Supabase: حفظ التحاليل واسترجاعها
# ══════════════════════════════════════════════

def _sb_headers():
    # Use service_role key when available — bypasses RLS on analyses/chat_messages.
    # Falls back to anon key (works if RLS is not yet enabled).
    key = SUPABASE_SERVICE_KEY or SUPABASE_KEY
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _assert_session_owner(session_id: str, user: dict | None) -> None:
    """When an authenticated user is present, ensure they own the session_id."""
    if user and user.get("sub") and session_id != user["sub"]:
        raise HTTPException(
            status_code=403,
            detail={"error": "forbidden", "message": "لا يمكنك الوصول إلى بيانات جلسة أخرى"},
        )


class SaveAnalysisRequest(BaseModel):
    session_id: str = "anonymous"
    findings:   list
    summary:    str
    report:     dict


@app.post("/api/analyses/save")
async def save_analysis(req: SaveAnalysisRequest, user: dict | None = Depends(optional_user)):
    _assert_session_owner(req.session_id, user)
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(503, "Supabase keys not configured")
    try:
        r = http_requests.post(
            f"{SUPABASE_URL}/rest/v1/analyses",
            headers=_sb_headers(),
            json={
                "session_id": req.session_id,
                "findings":   req.findings,
                "summary":    req.summary,
                "report":     req.report,
            },
            timeout=10,
        )
        r.raise_for_status()
        return {"success": True, "data": r.json()}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/analyses/list")
async def list_analyses(session_id: str = "anonymous", profile_name: str = "", limit: int = 20,
                        user: dict | None = Depends(optional_user)):
    _assert_session_owner(session_id, user)
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(503, "Supabase keys not configured")
    try:
        params: dict = {"session_id": f"eq.{session_id}", "order": "created_at.desc"}
        if profile_name:
            params["profile_name"] = f"eq.{profile_name}"
        r = http_requests.get(
            f"{SUPABASE_URL}/rest/v1/analyses",
            headers={**_sb_headers(), "Range": f"0-{limit - 1}"},
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        return {"analyses": r.json()}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.delete("/api/analyses/clear")
async def clear_analyses(session_id: str = "anonymous", user: dict | None = Depends(optional_user)):
    _assert_session_owner(session_id, user)
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(503, "Supabase keys not configured")
    try:
        r = http_requests.delete(
            f"{SUPABASE_URL}/rest/v1/analyses",
            headers=_sb_headers(),
            params={"session_id": f"eq.{session_id}"},
            timeout=10,
        )
        r.raise_for_status()
        return {"deleted": True, "session_id": session_id}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/analyses/profiles")
async def list_profiles(session_id: str = "anonymous", user: dict | None = Depends(optional_user)):
    """جلب قائمة أفراد العائلة المسجلين لهذا المستخدم"""
    _assert_session_owner(session_id, user)
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(503, "Supabase keys not configured")
    try:
        r = http_requests.get(
            f"{SUPABASE_URL}/rest/v1/analyses",
            headers=_sb_headers(),
            params={"session_id": f"eq.{session_id}", "select": "profile_name"},
            timeout=10,
        )
        r.raise_for_status()
        names = list({row["profile_name"] for row in r.json() if row.get("profile_name")})
        return {"profiles": names or ["أنا"]}
    except Exception as e:
        raise HTTPException(500, str(e))


# ══════════════════════════════════════════════
# Analyze endpoint
# ══════════════════════════════════════════════

ANALYSIS_TYPE_HINTS = {
    "دم شامل":      "CBC complete blood count hemoglobin WBC RBC platelets",
    "سكر وكوليسترول": "glucose HbA1c cholesterol LDL HDL triglycerides",
    "كلى وكبد":     "creatinine BUN urea ALT AST bilirubin GFR albumin",
    "هرمونات":      "TSH T3 T4 testosterone estradiol FSH LH prolactin cortisol",
    "بول":          "urinalysis urine protein glucose ketones specific gravity",
    "شامل":         "clinical pathology lab results blood tests",
}



@app.post("/api/analyze")
async def analyze(request: Request, file: UploadFile = File(...), analysis_type: str = Form("شامل"),
                  _rl: None = Depends(limit_analyze)):
    content = await file.read()
    validate_upload(file, content)
    analysis_type = sanitize_text(analysis_type, max_len=100)
    log.info("analyze: type=%s file=%s size=%d", analysis_type, file.filename, len(content))

    coordinator = load_coordinator()
    is_pdf = (
        file.content_type == "application/pdf"
        or (file.filename or "").lower().endswith(".pdf")
        or content[:4] == b"%PDF"
    )
    file_type = "pdf" if is_pdf else "image"
    import asyncio
    result = await asyncio.to_thread(coordinator.run, content, file_type, analysis_type)

    if not result.ok:
        raise HTTPException(status_code=422, detail=result.error)

    response: dict = {
        "findings":   result.findings,
        "summary":    result.summary,
        "report":     result.report,
        "panel_code": result.panel_code,
    }
    if os.getenv("ENVIRONMENT") == "development":
        response["_agents"] = result.logs

    return response


# ══════════════════════════════════════════════
# M3 — Chat: ذاكرة + ربط التحليل + فلتر ذكي + مصادر
# ══════════════════════════════════════════════

CHAT_SYSTEM = load_prompt("system_chat") or load_prompt("templates/system_prompt") or \
    """أنت مساعد طبي ذكي اسمك "تبيان". أجب بشكل واضح ومختصر باللغة العربية.
قواعد: لا تخترع معلومات. اذكر المصادر. لا تشخّص بشكل قاطع. انصح بمراجعة الطبيب دائماً."""

_FALLBACK_WORDS = ["ألم","صداع","تعب","دوخة","حمى","سعال","أعراض","ضغط","سكر","قلب",
                   "معدة","تنفس","التهاب","دواء","علاج","تحليل","دم","فيتامين","نتائج",
                   "فحص","تشخيص","كوليسترول","حديد","هيموجلوبين","كلى","كبد","درقية",
                   "هرمون","بروتين","سمنة","blood","glucose","CBC","hemoglobin"]


def is_medical_query(client, query: str) -> bool:
    """فلتر سريع بالكلمات المفتاحية — بدون Groq call"""
    return any(w in query for w in _FALLBACK_WORDS) or len(query.split()) >= 3


class ChatRequest(BaseModel):
    query:            str
    history:          list[dict] = []   # [{"role":"user/assistant","content":"..."}]
    analysis_context: str        = ""   # JSON string من آخر تحليل


@app.post("/api/chat")
async def chat_stream(request: Request, req: ChatRequest, _rl: None = Depends(limit_chat)):
    req.query = sanitize_query(sanitize_text(req.query))
    router = load_router()

    if not is_medical_query(None, req.query):
        def nm():
            yield "أنا مساعد طبي متخصص. يسعدني الإجابة على أسئلتك الصحية وتحاليلك الطبية."
        return StreamingResponse(nm(), media_type="text/plain; charset=utf-8")

    # ── RAG context (lightweight — cached to avoid repeated embedding calls) ──
    rag_ctx = ""
    _rag_key = rag_cache_key(req.query)
    rag_ctx = rag_cache.get(_rag_key) or ""
    if not rag_ctx:
        try:
            _, _, _, retriever = load_tools()
            fast_results = retriever.retrieve_fast(req.query, k=5, top_n=3)
            rag_ctx = build_context(fast_results, max_tokens=500)
            if rag_ctx:
                rag_cache.set(_rag_key, rag_ctx, ttl=300)
        except Exception:
            pass

    # ── بناء analysis context ──
    analysis_ctx = ""
    if req.analysis_context:
        try:
            ctx      = json.loads(req.analysis_context)
            findings = ctx.get("findings", [])
            summary  = ctx.get("summary", "")
            abnormal = [f for f in findings if f.get("status") != "normal"]
            normal   = [f for f in findings if f.get("status") == "normal"]
            lines = [f"ملخص التحليل: {summary}"]
            if abnormal:
                lines.append("النتائج غير الطبيعية:")
                for f in abnormal:
                    direction = "مرتفع" if f.get("status") == "high" else "منخفض"
                    lines.append(
                        f"  • {f['name']}: {f['value']} {f.get('unit','')} "
                        f"(المعدل: {f.get('range','')}) — {direction}"
                    )
            if normal:
                lines.append(f"النتائج الطبيعية: {', '.join(f['name'] for f in normal)}")
            analysis_ctx = "\n".join(lines)
        except Exception:
            analysis_ctx = req.analysis_context

    system = (
        CHAT_SYSTEM
        .replace("{{RAG_CONTEXT}}", rag_ctx or "لا توجد معلومات إضافية.")
        .replace("{{ANALYSIS_CONTEXT}}", analysis_ctx or "لم يُرفع تحليل بعد.")
    )

    messages = [{"role": "system", "content": system}]
    for msg in req.history[-10:]:   # آخر 10 رسائل فقط
        if msg.get("role") in ("user", "assistant") and msg.get("content"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": req.query})

    # Emergency check — يُرد فوراً بدون LLM
    emergency_resp = check_emergency(req.query)
    if emergency_resp:
        def em():
            yield emergency_resp
        return StreamingResponse(em(), media_type="text/plain; charset=utf-8")

    def generate():
        tokens: list[str] = []
        try:
            for token in router.stream(messages, max_tokens=600, temperature=0.1,
                                       model_hint="chat"):
                tokens.append(token)
                yield token
        except Exception as e:
            err = str(e)
            log.error("chat stream error: %s", err[:200])
            yield "عذراً، الخدمة مشغولة. حاول بعد لحظة." if "429" in err else "حدث خطأ، يرجى المحاولة مرة أخرى."
            return
        full   = "".join(tokens)
        suffix = filter_chat_response(full, req.query)
        if suffix != full:
            delta = suffix[len(full):]
            if delta:
                yield delta

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")


class SaveChatRequest(BaseModel):
    session_id: str
    messages: list[dict]   # [{"role": "user"|"assistant", "content": str}]


@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str, limit: int = 30,
                           user: dict | None = Depends(optional_user)):
    """تحميل آخر N رسالة لجلسة معينة من Supabase."""
    _assert_session_owner(session_id, user)
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"messages": []}
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    try:
        r = http_requests.get(
            f"{SUPABASE_URL}/rest/v1/chat_messages",
            headers=headers,
            params={
                "session_id": f"eq.{session_id}",
                "order": "created_at.asc",
                "limit": limit,
                "select": "role,content",
            },
            timeout=10,
        )
        r.raise_for_status()
        return {"messages": r.json()}
    except Exception as e:
        log.warning("chat/history fetch failed: %s", e)
        return {"messages": []}


@app.post("/api/chat/save")
async def save_chat_messages(req: SaveChatRequest, user: dict | None = Depends(optional_user)):
    """حفظ رسائل تبادل واحد (مستخدم + مساعد) في Supabase."""
    _assert_session_owner(req.session_id, user)
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"ok": False}
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    rows = [
        {"session_id": req.session_id, "role": m["role"], "content": m["content"]}
        for m in req.messages
        if m.get("content", "").strip()
    ]
    if not rows:
        return {"ok": True}
    try:
        r = http_requests.post(
            f"{SUPABASE_URL}/rest/v1/chat_messages",
            headers=headers,
            json=rows,
            timeout=10,
        )
        return {"ok": r.status_code in (200, 201)}
    except Exception as e:
        log.warning("chat/save failed: %s", e)
        return {"ok": False}


class EvalRequest(BaseModel):
    question: str
    reference_answer: str = ""


@app.post("/api/evaluate")
async def evaluate_rag(req: EvalRequest):
    """M7 — RAGAS-light: تقييم جودة الـ RAG بـ Groq"""
    client = load_groq()
    _, co_client, db, _ = load_tools()

    context, confidence = get_rag_context(db, req.question, co_client, multi_query_client=client)

    gen_messages = [
        {"role": "system", "content": CHAT_SYSTEM},
        {"role": "user", "content": req.question},
    ]
    if context:
        gen_messages[0]["content"] += f"\n\nالسياق:\n{context}"

    resp = client.chat.completions.create(
        model=GROQ_MODEL_CHAT, messages=gen_messages, temperature=0.1, max_tokens=600
    )
    answer = resp.choices[0].message.content

    # faithfulness check — هل الإجابة مبنية على السياق؟
    faith_prompt = f"""قيّم هل الإجابة مبنية على السياق المعطى. أجب بـ JSON فقط:
{{"faithfulness": 0.0-1.0, "relevance": 0.0-1.0, "notes": "ملاحظة قصيرة"}}

السؤال: {req.question}
السياق: {context[:1500] if context else 'لا يوجد'}
الإجابة: {answer[:800]}"""

    metrics = {"faithfulness": 0.0, "relevance": 0.0, "notes": "لم يتم التقييم"}
    try:
        r = client.chat.completions.create(
            model=GROQ_MODEL_CHAT,
            messages=[{"role": "user", "content": faith_prompt}],
            temperature=0, max_tokens=150,
        )
        raw = r.choices[0].message.content.strip()
        if '{' in raw:
            raw = raw[raw.index('{'):raw.rindex('}') + 1]
        metrics = json.loads(raw)
    except Exception:
        pass

    return {
        "question": req.question,
        "answer": answer,
        "context_confidence": confidence,
        "has_context": bool(context),
        "metrics": metrics,
    }


class SearchAnalysisItem(BaseModel):
    id: str
    summary: str
    panel: str = ""
    findings_text: str = ""


class SemanticSearchRequest(BaseModel):
    query: str
    analyses: list[SearchAnalysisItem] = []
    search_scope: str = "local"   # "local" = user history | "global" = medical KB (pgvector)
    top_k: int = 5


@app.post("/api/search")
async def semantic_search(request: Request, req: SemanticSearchRequest, _rl: None = Depends(limit_search)):
    """
    Semantic search with two modes:
      local  — re-rank the user's own saved analyses (default, original behaviour)
      global — query the medical knowledge base in pgvector directly
    """
    from services.search.query_parser import parse_query, normalize_arabic

    if not req.query.strip():
        if req.search_scope == "local":
            return {"results": [{"id": a.id, "score": 0.0} for a in req.analyses], "scope": "local"}
        return {"results": [], "scope": "global"}

    # ── Global KB search ───────────────────────────────────────────────────
    if req.search_scope == "global":
        clean_query = sanitize_query(req.query)
        _s_key = rag_cache_key(clean_query, topic_type="search_global")
        cached  = search_cache.get(_s_key)
        if cached:
            return cached
        try:
            _, _, _, retriever = load_tools()
            kb_results, confidence = retriever.retrieve(
                clean_query,
                RetrievalConfig(k=req.top_k * 2, top_n=req.top_k, use_multi_query=False),
            )
            payload = {
                "results": [
                    {
                        "id":         r.source,
                        "score":      round(r.score, 3),
                        "content":    r.content[:300],
                        "source":     r.source,
                        "topic_type": r.metadata.get("topic_type", ""),
                    }
                    for r in kb_results
                ],
                "scope":      "global",
                "confidence": confidence,
            }
            search_cache.set(_s_key, payload, ttl=120)
            return payload
        except Exception as e:
            log.error("global search failed: %s", e)
            raise HTTPException(500, detail=f"Global search failed: {e}")

    # ── Local history search (original behaviour) ──────────────────────────
    pq     = parse_query(req.query)
    norm_q = pq.normalized.lower()

    all_terms: list[str] = [norm_q]
    for exp in pq.search_expansions[1:]:
        for t in exp.split():
            n = normalize_arabic(t.lower())
            if len(n) > 2:
                all_terms.append(n)
    for t in pq.detected_tests:
        all_terms.append(normalize_arabic(t.lower()))
    all_terms = list(dict.fromkeys(all_terms))

    results = []
    for a in req.analyses:
        text  = normalize_arabic((a.summary + " " + a.panel + " " + a.findings_text).lower())
        score = 0.0
        for term in all_terms:
            if len(term) > 1 and term in text:
                score += 2.0 if term in norm_q else 1.0
        if pq.panel_type and a.panel and pq.panel_type == a.panel:
            score += 3.0
        if norm_q in text:
            score += 2.0
        results.append({"id": a.id, "score": round(score, 1)})

    results.sort(key=lambda x: x["score"], reverse=True)
    return {"results": results, "scope": "local"}


@app.get("/api/health")
def api_health():
    return {
        "status": "ok",
        "embed_model": EMBED_MODEL,
        "voice": {
            "stt": bool(GROQ_API_KEY),
            "tts": bool(GOOGLE_TTS_KEY or ELEVENLABS_KEY or True),
        },
    }


@app.get("/api/models/status")
def models_status():
    """Reports the active LLM provider, loaded adapters, and fallback state."""
    router = load_router()
    tts_provider = "none"
    if GOOGLE_TTS_KEY:
        tts_provider = "google_cloud"
    elif ELEVENLABS_KEY:
        tts_provider = "elevenlabs"
    else:
        try:
            import gtts  # noqa: F401
            tts_provider = "gtts_free"
        except ImportError:
            pass

    return {
        "llm": {
            "provider": router.provider_name,
            "lora_loaded": _lora_model_info["loaded"],
            "lora_path":   _lora_model_info.get("path"),
            "lora_model":  _lora_model_info.get("model_name"),
            "env_LLM_PROVIDER": os.getenv("LLM_PROVIDER", "groq"),
        },
        "embeddings": {
            "model": EMBED_MODEL,
            "loaded": True,
        },
        "tts_provider": tts_provider,
        "stt_provider": "groq_whisper" if GROQ_API_KEY else "none",
        "cache": {
            "rag":    rag_cache.stats(),
        },
    }


# ══════════════════════════════════════════════
# Voice AI endpoints
# ══════════════════════════════════════════════

@lru_cache(maxsize=1)
def _get_stt():
    from services.voice import WhisperSTT
    return WhisperSTT(GROQ_API_KEY)

@lru_cache(maxsize=1)
def _get_tts():
    from services.voice import get_tts_provider
    return get_tts_provider(google_tts_key=GOOGLE_TTS_KEY, elevenlabs_key=ELEVENLABS_KEY)


@app.post("/api/voice/transcribe")
async def voice_transcribe(
    audio: UploadFile = File(...),
    language: str = Form("ar"),
):
    """
    Transcribe Arabic audio (webm/mp4/wav/ogg) → text.
    Uses Groq Whisper large-v3.
    """
    data      = await audio.read()
    mime_type = audio.content_type or "audio/webm"
    try:
        stt  = _get_stt()
        text = stt.transcribe(data, mime_type=mime_type, language=language)
        return {"text": text, "language": language}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")


@app.post("/api/voice/synthesize")
async def voice_synthesize(req: dict):
    """
    Convert Arabic text → MP3 audio bytes.
    Body: {"text": "..."}
    """
    text = (req.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="text field is required")
    try:
        tts      = _get_tts()
        mp3_data = tts.synthesize(text)
        return HttpResponse(content=mp3_data, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {e}")


class VoiceChatRequest(BaseModel):
    audio_base64:     str   = ""      # base64-encoded audio (alternative to file upload)
    query:            str   = ""      # text query (if already transcribed client-side)
    history:          list[dict] = []
    analysis_context: str   = ""
    language:         str   = "ar"
    include_audio:    bool  = True    # return TTS audio in response


@app.post("/api/voice/chat")
async def voice_chat(req: VoiceChatRequest):
    """
    Full voice chat loop: audio → STT → LLM → TTS.
    Returns {text: str, audio_base64: str (MP3)}.
    """
    import base64

    # 1. Resolve input text (from audio or direct text)
    query = req.query.strip()
    if not query and req.audio_base64:
        try:
            audio_bytes = base64.b64decode(req.audio_base64)
            stt  = _get_stt()
            query = stt.transcribe(audio_bytes, language=req.language)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"STT failed: {e}")

    if not query:
        raise HTTPException(status_code=422, detail="Provide audio_base64 or query")

    query = sanitize_query(query)

    # 2. LLM chat
    router = load_router()
    emergency_resp = check_emergency(query)
    if emergency_resp:
        text = emergency_resp
    else:
        rag_ctx = ""
        _rag_key = rag_cache_key(query)
        rag_ctx  = rag_cache.get(_rag_key) or ""
        if not rag_ctx:
            try:
                _, _, _, retriever = load_tools()
                fast_results = retriever.retrieve_fast(query, k=5, top_n=3)
                rag_ctx = build_context(fast_results, max_tokens=400)
                if rag_ctx:
                    rag_cache.set(_rag_key, rag_ctx, ttl=300)
            except Exception:
                pass

        system = (
            CHAT_SYSTEM
            .replace("{{RAG_CONTEXT}}", rag_ctx or "لا توجد معلومات إضافية.")
            .replace("{{ANALYSIS_CONTEXT}}", req.analysis_context or "لم يُرفع تحليل بعد.")
        )
        messages = [{"role": "system", "content": system}]
        for msg in req.history[-6:]:
            if msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": query})

        raw  = router.generate(messages, max_tokens=600, temperature=0.5, model_hint="chat")
        text = filter_chat_response(raw, query)

    # 3. TTS (optional)
    audio_b64 = ""
    if req.include_audio:
        try:
            tts      = _get_tts()
            mp3      = tts.synthesize(text)
            audio_b64 = base64.b64encode(mp3).decode()
        except Exception as e:
            log = logging.getLogger("tebyan")
            log.warning("[voice/chat] TTS failed: %s", e)

    return {"query": query, "text": text, "audio_base64": audio_b64}


# ══════════════════════════════════════════════
# Risk Prediction API
# ══════════════════════════════════════════════

class RiskRequest(BaseModel):
    findings: list[dict]   # same format as analysis findings

@lru_cache(maxsize=1)
def _get_risk_engine():
    from services.risk import RiskEngine
    return RiskEngine()

@app.post("/api/risk")
async def predict_risk(req: RiskRequest):
    """
    Evidence-based multi-condition health risk scoring.
    Returns scored risks for diabetes, cardiovascular, anemia, kidney, liver, thyroid.
    ML model override when models/ directory contains trained .pkl files.
    """
    if not req.findings:
        raise HTTPException(status_code=422, detail="findings list is required")
    engine = _get_risk_engine()
    report = engine.assess(req.findings)
    return {
        "risks": [
            {
                "condition":      r.condition,
                "score":          r.score,
                "level":          r.level,
                "confidence":     r.confidence,
                "label_ar":       r.label_ar,
                "factors":        r.factors,
                "recommendation": r.recommendation,
                "source":         r.source,
            }
            for r in report.risks
        ],
        "top_risk":   {
            "condition": report.top_risk.condition,
            "score":     report.top_risk.score,
            "level":     report.top_risk.level,
            "label_ar":  report.top_risk.label_ar,
        } if report.top_risk else None,
        "overall_ar":     report.overall_ar,
        "features_used":  report.features_used,
    }


# ══════════════════════════════════════════════
# Compare Summary — Groq-generated analysis of two lab results
# ══════════════════════════════════════════════

class CompareSummaryRequest(BaseModel):
    findings_a:  list[dict]
    findings_b:  list[dict]
    summary_a:   str = ""
    summary_b:   str = ""
    date_a:      str = ""
    date_b:      str = ""

@app.post("/api/compare/summary")
async def compare_summary(req: CompareSummaryRequest):
    router = load_router()

    def fmt_findings(findings: list[dict]) -> str:
        lines = []
        for f in findings:
            status_ar = {"high": "مرتفع", "low": "منخفض", "normal": "طبيعي"}.get(f.get("status", ""), "")
            lines.append(f"  {f.get('name','')}: {f.get('value','')} {f.get('unit','')} [{status_ar}]")
        return "\n".join(lines) if lines else "لا توجد بيانات"

    prompt = f"""أنت طبيب متخصص. قارن بين نتيجتين لتحاليل مخبرية لنفس المريض.

التحليل الأول ({req.date_a or 'السابق'}):
{fmt_findings(req.findings_a)}

التحليل الثاني ({req.date_b or 'الحالي'}):
{fmt_findings(req.findings_b)}

اكتب ملخصاً طبياً دقيقاً بالعربية في 3-4 جمل يشمل:
1. أبرز التغيرات (تحسّن / تراجع / ثبات)
2. هل الاتجاه العام إيجابي أم يستدعي قلقاً
3. توصية واحدة محددة

أجب مباشرة بالنص فقط، بدون عناوين أو نقاط."""

    try:
        summary = router.generate(
            [{"role": "user", "content": prompt}],
            max_tokens=300, temperature=0.2, model_hint="analysis",
        ).strip()
    except Exception as e:
        summary = "تعذّر توليد الملخص المقارن."
        log.error("compare: Groq error: %s", e)

    return {"summary": summary}

# build:1779660596
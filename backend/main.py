import os
from dotenv import load_dotenv
load_dotenv()  # local .env | Railway/Vercel: env vars set in dashboard
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
# HF_HOME: set as env var in production, or default to local cache
_here = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('HF_HOME', os.path.join(_here, '..', 'model_cache'))

import io
import re
import json
import base64
from functools import lru_cache

import requests as http_requests
import numpy as np
from PIL import Image
import fitz
import easyocr
from groq import Groq
import cohere
from rank_bm25 import BM25Okapi
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY environment variable is not set")
COHERE_API_KEY    = os.getenv("COHERE_API_KEY")
SUPABASE_URL      = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY      = os.getenv("SUPABASE_KEY", "")
SUPABASE_DB_URL   = os.getenv("SUPABASE_DB_URL")
GOOGLE_VISION_KEY = os.getenv("GOOGLE_VISION_API_KEY", "")
FRONTEND_URL      = os.getenv("FRONTEND_URL", "http://localhost:3000")

GROQ_MODEL      = "llama-3.3-70b-versatile"
GROQ_MODEL_CHAT = "llama-3.1-8b-instant"

# ملاحظة: e5-large يحتاج حذف chroma_db وإعادة ingest بعد التغيير
EMBED_MODEL = "intfloat/multilingual-e5-large"

app = FastAPI(title="تبيان الطبي API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", FRONTEND_URL, "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def ensure_analyses_table():
    """ينشئ جدول analyses في Supabase تلقائياً إذا لم يكن موجوداً"""
    if not SUPABASE_DB_URL:
        print("[DB] SUPABASE_DB_URL not set — skipping")
        return
    try:
        import psycopg2
        # psycopg2 يستخدم postgresql:// بدون +psycopg
        url = SUPABASE_DB_URL.replace("postgresql+psycopg://", "postgresql://")
        conn = psycopg2.connect(url, sslmode="require")
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
        print("[DB] analyses table ready ✓")
    except Exception as e:
        print(f"[DB] table setup failed: {e}")


@app.on_event("startup")
async def startup():
    load_groq()


@lru_cache(maxsize=1)
def load_groq():
    client = Groq(api_key=GROQ_API_KEY)
    print(f"[INFO] Groq ready | chat={GROQ_MODEL_CHAT}")
    return client


class PGVectorStore:
    """واجهة بحث pgvector عبر Supabase REST — نفس interface ChromaDB"""

    def __init__(self, embeddings, url: str, key: str):
        self._emb = embeddings
        self._url = url
        self._key = key
        self._headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def _embed(self, text: str) -> list:
        return self._emb.embed_query(text)

    def similarity_search_with_relevance_scores(
        self, query: str, k: int = 10, filter: dict = None
    ) -> list:
        vec = self._embed(query)
        payload = {
            "query_embedding": vec,
            "match_threshold": 0.3,
            "match_count": k,
            "filter": filter or {},
        }
        try:
            r = http_requests.post(
                f"{self._url}/rest/v1/rpc/match_documents",
                headers=self._headers,
                json=payload,
                timeout=15,
            )
            r.raise_for_status()
            return [
                (Document(page_content=row["content"], metadata=row.get("metadata") or {}),
                 float(row["similarity"]))
                for row in r.json()
            ]
        except Exception as e:
            print(f"[pgvector] {e}")
            return []

    def count(self) -> int:
        try:
            r = http_requests.get(
                f"{self._url}/rest/v1/documents",
                headers={**self._headers, "Prefer": "count=exact", "Range": "0-0"},
                timeout=10,
            )
            return int(r.headers.get("Content-Range", "0/0").split("/")[-1])
        except Exception:
            return 0


@lru_cache(maxsize=1)
def load_tools():
    reader        = easyocr.Reader(['ar', 'en'], gpu=False)
    embeddings    = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    groq_client   = Groq(api_key=GROQ_API_KEY)
    cohere_client = cohere.ClientV2(api_key=COHERE_API_KEY) if COHERE_API_KEY else None
    db            = PGVectorStore(embeddings, SUPABASE_URL, SUPABASE_KEY)
    print(f"[INFO] Tools loaded | embed={EMBED_MODEL} | DB={db.count()} chunks (pgvector)")
    return reader, embeddings, groq_client, cohere_client, db


# ══════════════════════════════════════════════
# M1 — Google Cloud Vision OCR (مع EasyOCR احتياطاً)
# ══════════════════════════════════════════════

def preprocess_image(image_bytes: bytes) -> "np.ndarray":
    """تحسين جودة صورة التحليل قبل OCR: رفع التباين + تحويل لـ grayscale"""
    from PIL import ImageFilter, ImageEnhance
    img = Image.open(io.BytesIO(image_bytes))
    # تحويل RGBA → RGB
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    # رفع دقة الصورة الصغيرة
    w, h = img.size
    if min(w, h) < 800:
        scale = 800 / min(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    # تحسين التباين والحدة
    img = ImageEnhance.Contrast(img).enhance(1.8)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    return np.array(img)


def extract_text_google_vision(image_bytes: bytes) -> str:
    """OCR دقيق للتحاليل العربية والإنجليزية — GOOGLE_VISION_API_KEY مطلوب في .env"""
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    payload = {
        "requests": [{
            "image": {"content": b64},
            "features": [{"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 1}],
            "imageContext": {"languageHints": ["ar", "en"]},
        }]
    }
    url = f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_VISION_KEY}"
    r = http_requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    text = r.json()["responses"][0].get("fullTextAnnotation", {}).get("text", "")
    print(f"[VISION] Google Cloud Vision: {len(text)} chars")
    return text


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


def is_valid_test(name: str) -> bool:
    ignore = ['page', 'id', 'patient', 'date', 'sex', 'age', 'mrn', 'doctor',
              'physician', 'result', 'unit', 'range', 'validated', 'approved',
              'Interpretation', 'Ref']
    n = str(name).lower()
    return not any(x in n for x in ignore) and len(str(name).strip()) > 1


def get_status(value: str, range_str: str) -> str:
    try:
        nums = re.findall(r"[-+]?\d*\.?\d+", str(range_str))
        val  = float(value)
        if len(nums) >= 2:
            lo, hi = float(nums[0]), float(nums[1])
            if val < lo: return "low"
            if val > hi: return "high"
            return "normal"
    except Exception:
        pass
    return "normal"


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


def cohere_rerank(co_client, results: list, query: str, top_n: int = 5) -> list:
    if not co_client or len(results) <= 1:
        return results
    try:
        docs_text = [doc.page_content for doc, _ in results]
        resp = co_client.rerank(model="rerank-v3.5", query=query, documents=docs_text, top_n=top_n)
        return [(results[r.index][0], r.relevance_score) for r in resp.results]
    except Exception as e:
        print(f"[COHERE] {e} — BM25 fallback")
        return results[:top_n]


def bm25_rerank(results: list, query: str) -> list:
    if len(results) <= 1:
        return results
    docs   = [doc for doc, _ in results]
    vscores = [s for _, s in results]
    tok    = [re.findall(r'\w+', d.page_content.lower()) for d in docs]
    bm25   = BM25Okapi(tok)
    bscores = bm25.get_scores(re.findall(r'\w+', query.lower()))
    mx     = max(bscores) if max(bscores) > 0 else 1
    combined = [(d, vs + (bs / mx) * 0.3) for d, vs, bs in zip(docs, vscores, bscores)]
    return sorted(combined, key=lambda x: x[1], reverse=True)


def get_rag_context(db, query: str, co_client=None, multi_query_client=None, k: int = 10, topic_type: str = None) -> tuple:
    try:
        queries = generate_search_queries(multi_query_client, query) if multi_query_client else [query]
        seen = {}

        # بحث عام
        for q in queries:
            for doc, score in db.similarity_search_with_relevance_scores(q, k=k):
                key = doc.page_content[:80]
                if key not in seen or seen[key][1] < score:
                    seen[key] = (doc, score)

        # بحث مُصفَّى بـ metadata إن حُدِّد نوع (يضيف نتائج إضافية أكثر صلة)
        if topic_type:
            try:
                for q in queries[:2]:
                    for doc, score in db.similarity_search_with_relevance_scores(
                        q, k=k, filter={"topic_type": topic_type}
                    ):
                        key = doc.page_content[:80]
                        boosted = min(score + 0.15, 1.0)   # رفع أولوية النتائج المصفاة
                        if key not in seen or seen[key][1] < boosted:
                            seen[key] = (doc, boosted)
            except Exception:
                pass  # ChromaDB قديم لا يدعم filter، تجاهل

        filtered = [(d, s) for d, s in seen.values() if s >= 0.4]
        if not filtered:
            return "", "لا يوجد"

        top_scores = sorted([s for _, s in filtered], reverse=True)[:5]
        avg = sum(top_scores) / len(top_scores)
        conf = "عالية" if avg > 0.70 else "متوسطة" if avg > 0.45 else "منخفضة"

        top = cohere_rerank(co_client, filtered, query) if co_client else bm25_rerank(filtered, query)[:5]
        context = "\n\n".join([d.page_content for d, _ in top])
        print(f"[RAG] '{query[:40]}' | n={len(filtered)} | conf={conf} ({avg:.2f}) | filter={topic_type}")
        return context, conf
    except Exception as e:
        print(f"[RAG ERROR] {e}")
        return "", "لا يوجد"


# ══════════════════════════════════════════════
# M4 — Supabase: حفظ التحاليل واسترجاعها
# ══════════════════════════════════════════════

def _sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


class SaveAnalysisRequest(BaseModel):
    session_id: str = "anonymous"
    findings:   list
    summary:    str
    report:     dict


@app.post("/api/analyses/save")
async def save_analysis(req: SaveAnalysisRequest):
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
async def list_analyses(session_id: str = "anonymous", profile_name: str = "", limit: int = 20):
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


@app.get("/api/analyses/profiles")
async def list_profiles(session_id: str = "anonymous"):
    """جلب قائمة أفراد العائلة المسجلين لهذا المستخدم"""
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
async def analyze(file: UploadFile = File(...), analysis_type: str = Form("شامل")):
    reader, embeddings, client, co_client, db = load_tools()
    content = await file.read()
    print(f"[ANALYZE] type={analysis_type} | file={file.filename}")

    # استخراج النص
    if file.content_type == "application/pdf":
        doc = fitz.open(stream=content, filetype="pdf")
        all_text = "\n".join([p.get_text() for p in doc])
    elif GOOGLE_VISION_KEY:
        try:
            all_text = extract_text_google_vision(content)
        except Exception as e:
            print(f"[VISION] fallback to EasyOCR ({e})")
            all_text = "\n".join(reader.readtext(preprocess_image(content), detail=0))
    else:
        all_text = "\n".join(reader.readtext(preprocess_image(content), detail=0))

    # استخراج الفحوصات
    pattern = r"([a-zA-Z][a-zA-Z\s#%]{2,})\s+(\d+\.?\d*)\s+([\d\.]+\s*-\s*[\d\.]+)\s*([a-zA-Z0-9^/]+)?"
    findings_raw = [f for f in re.findall(pattern, all_text) if is_valid_test(f[0])]

    if len(findings_raw) < 2:
        try:
            clean = groq_generate(client, f"""حلل النص الطبي واستخرج نتائج التحاليل.
النص: {all_text[:4000]}
أجب بقائمة بايثون فقط: [('Test Name', 'Value', 'Range', 'Unit')]""", max_tokens=1024)
            findings_raw = eval(clean.strip().replace("```python", "").replace("```", ""))
        except Exception:
            pass

    findings = [
        {"name": str(f[0]).strip(), "value": str(f[1]), "range": str(f[2]),
         "unit": str(f[3]) if len(f) > 3 else "", "status": get_status(f[1], f[2])}
        for f in findings_raw if is_valid_test(f[0])
    ]

    abnormal = [f for f in findings if f["status"] != "normal"]
    summary  = ("القيم التي تحتاج انتباهاً: " + "، ".join([f["name"] for f in abnormal[:3]])) if abnormal else "جميع القيم ضمن المعدل الطبيعي ✓"

    type_hint    = ANALYSIS_TYPE_HINTS.get(analysis_type, ANALYSIS_TYPE_HINTS["شامل"])
    search_query = f"{type_hint}: " + ", ".join([f["name"] for f in findings])
    # استخدام metadata filter للتحاليل المحددة
    topic_filter = "lab_definition" if analysis_type != "شامل" else None
    context, conf_label = get_rag_context(db, search_query, co_client, multi_query_client=client, topic_type=topic_filter)

    report_prompt = (
        "أنت طبيب مختبر خبير. أرجع JSON فقط بدون أي نص خارجه. ابدأ بـ { مباشرة.\n"
        "لا HTML ولا markdown. نصوص عربية بسيطة فقط.\n\n"
        f"النتائج: {findings}\nالمراجع: {context or 'لا توجد مراجع'}\n\n"
        '{"تقييم_عام":"جملتان عن الحالة",'
        '"قيم_غير_طبيعية":[{"اسم_الفحص":"","النتيجة":"","المعدل_الطبيعي":"","الحالة":"","الشرح":"","المرجع":""}],'
        '"نصائح":["نصيحة1","نصيحة2","نصيحة3"]}'
    )
    print(f"[ANALYZE] findings={len(findings)}, abnormal={len(abnormal)}, conf={conf_label}")

    def fallback_tips(abn):
        base = ["تناول غذاءً متوازناً غنياً بالخضروات", "اشرب 8 أكواب ماء يومياً",
                "مارس رياضة خفيفة 30 دقيقة يومياً", "احرص على النوم 7-8 ساعات",
                "تجنب التوتر وخصص وقتاً للراحة", "راجع طبيبك لمتابعة التحاليل"]
        extra = {
            "glucose":     ["قلل السكريات والنشويات المكررة", "مارس الرياضة بانتظام"],
            "hemoglobin":  ["تناول أطعمة الحديد كالسبانخ واللحوم", "فيتامين C يحسن امتصاص الحديد"],
            "eosinophils": ["تجنب مسببات الحساسية", "أخبر طبيبك بأي أعراض حساسية"],
        }
        tips = list(base)
        for f in abn:
            for key, sp in extra.items():
                if key in f["name"].lower():
                    tips.extend(sp); break
        return tips[:8]

    report = {}
    try:
        raw = groq_generate(client, report_prompt)
        raw = raw.strip().replace("```json", "").replace("```", "").strip()
        if '{' in raw:
            raw = raw[raw.index('{'):raw.rindex('}') + 1]
        rd = json.loads(raw)
        report = {
            "general": rd.get("تقييم_عام", summary),
            "abnormal_details": rd.get("قيم_غير_طبيعية", []),
            "tips": rd.get("نصائح", []) or fallback_tips(abnormal),
            "rag_confidence": conf_label,
        }
    except Exception as e:
        print(f"[ERROR] JSON parse: {e}")
        report = {
            "general": summary,
            "abnormal_details": [
                {"اسم_الفحص": f["name"], "النتيجة": f["value"], "المعدل_الطبيعي": f["range"],
                 "الحالة": "مرتفع" if f["status"] == "high" else "منخفض",
                 "الشرح": f"قيمة {'مرتفعة' if f['status'] == 'high' else 'منخفضة'} عن المعدل.",
                 "المرجع": "لا يوجد"} for f in abnormal
            ],
            "tips": fallback_tips(abnormal),
            "rag_confidence": conf_label,
        }

    if not report.get("abnormal_details") and abnormal:
        report["abnormal_details"] = [
            {"اسم_الفحص": f["name"], "النتيجة": f["value"], "المعدل_الطبيعي": f["range"],
             "الحالة": "مرتفع" if f["status"] == "high" else "منخفض",
             "الشرح": f"قيمة {'مرتفعة' if f['status'] == 'high' else 'منخفضة'} عن المعدل.",
             "المرجع": "لا يوجد"} for f in abnormal
        ]

    return {"findings": findings, "summary": summary, "report": report}


# ══════════════════════════════════════════════
# M3 — Chat: ذاكرة + ربط التحليل + فلتر ذكي + مصادر
# ══════════════════════════════════════════════

CHAT_SYSTEM = """أنت مساعد طبي ذكي اسمك "تبيان". أجب بشكل واضح ومختصر باللغة العربية.
قواعد صارمة:
1. لا تخترع معلومات — إذا لم تكن متأكداً قل "لا أعلم، استشر طبيبك"
2. اذكر مصدر كل معلومة مهمة (مثال: وفقاً لـ Mayo Clinic | WHO | MedlinePlus)
3. لا تشخّص أمراضاً بشكل قاطع
4. إذا سُئلت عن أعراض، أضف "التحاليل المقترحة:" في النهاية
5. انصح دائماً بمراجعة الطبيب المختص"""

_FALLBACK_WORDS = ["ألم","صداع","تعب","دوخة","حمى","سعال","أعراض","ضغط","سكر","قلب",
                   "معدة","تنفس","التهاب","دواء","علاج","تحليل","دم","فيتامين","نتائج",
                   "فحص","تشخيص","كوليسترول","حديد","هيموجلوبين","كلى","كبد","درقية",
                   "هرمون","بروتين","سمنة","blood","glucose","CBC","hemoglobin"]


def is_medical_query(client, query: str) -> bool:
    """M3 — فلتر ذكي بـ Groq بدل قائمة الكلمات"""
    try:
        r = client.chat.completions.create(
            model=GROQ_MODEL_CHAT,
            messages=[{"role": "user",
                       "content": f"هل هذا السؤال يتعلق بالصحة أو الطب أو التحاليل أو الأدوية؟ أجب بـ نعم أو لا فقط:\n{query}"}],
            temperature=0, max_tokens=5,
        )
        return "نعم" in r.choices[0].message.content
    except Exception:
        return any(w in query for w in _FALLBACK_WORDS)


class ChatRequest(BaseModel):
    query:            str
    history:          list[dict] = []   # [{"role":"user/assistant","content":"..."}]
    analysis_context: str        = ""   # JSON string من آخر تحليل


@app.post("/api/chat")
async def chat_stream(req: ChatRequest):
    client = load_groq()

    if not is_medical_query(client, req.query):
        def nm():
            yield "أنا مساعد طبي متخصص. يسعدني الإجابة على أسئلتك الصحية وتحاليلك الطبية."
        return StreamingResponse(nm(), media_type="text/plain; charset=utf-8")

    system = CHAT_SYSTEM

    # RAG: استرجاع معلومات طبية من قاعدة المعرفة
    try:
        _, _, _, co_client, db = load_tools()
        rag_ctx, _ = get_rag_context(db, req.query, co_client, multi_query_client=client, k=6)
        if rag_ctx:
            system += f"\n\nمعلومات طبية من قاعدة المعرفة (استند إليها):\n{rag_ctx}"
    except Exception:
        pass

    if req.analysis_context:
        try:
            ctx      = json.loads(req.analysis_context)
            findings = ctx.get("findings", [])
            summary  = ctx.get("summary", "")
            abnormal = [f for f in findings if f.get("status") != "normal"]
            normal   = [f for f in findings if f.get("status") == "normal"]

            ctx_lines = [f"ملخص التحليل: {summary}"]
            if abnormal:
                ctx_lines.append("النتائج غير الطبيعية:")
                for f in abnormal:
                    direction = "مرتفع" if f.get("status") == "high" else "منخفض"
                    ctx_lines.append(
                        f"  • {f['name']}: {f['value']} {f.get('unit','')} "
                        f"(المعدل: {f.get('range','')}) — {direction}"
                    )
            if normal:
                ctx_lines.append(f"النتائج الطبيعية: {', '.join(f['name'] for f in normal)}")

            system += "\n\nبيانات تحليل المريض (استند إليها مباشرة عند الإجابة):\n" + "\n".join(ctx_lines)
        except Exception:
            system += f"\n\nنتائج التحليل:\n{req.analysis_context}"

    messages = [{"role": "system", "content": system}]
    for msg in req.history[-10:]:   # آخر 10 رسائل فقط
        if msg.get("role") in ("user", "assistant") and msg.get("content"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": req.query})

    def generate():
        try:
            stream = client.chat.completions.create(
                model=GROQ_MODEL_CHAT,
                messages=messages,
                temperature=0.1,    # M3 — أقل هلوسة
                max_tokens=800,
                stream=True,
            )
            for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if token:
                    yield token
        except Exception as e:
            err = str(e)
            print(f"[CHAT ERROR] {err[:200]}")
            yield "عذراً، الخدمة مشغولة. حاول بعد لحظة." if "429" in err else "حدث خطأ، يرجى المحاولة مرة أخرى."

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")


class EvalRequest(BaseModel):
    question: str
    reference_answer: str = ""


@app.post("/api/evaluate")
async def evaluate_rag(req: EvalRequest):
    """M7 — RAGAS-light: تقييم جودة الـ RAG بـ Groq"""
    client = load_groq()
    _, _, _, co_client, db = load_tools()

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


@app.get("/api/health")
def health():
    return {"status": "ok", "embed_model": EMBED_MODEL}

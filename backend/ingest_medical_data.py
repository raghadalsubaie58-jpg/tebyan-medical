"""
سكريبت جلب بيانات طبية موثوقة وإدراجها في Supabase pgvector
المصادر: MedlinePlus (NIH) + Wikipedia العربية
الأداة: Groq لتنظيف وهيكلة المحتوى بالعربية
"""
import os, json, time, re
import requests as http
from dotenv import load_dotenv
load_dotenv(dotenv_path=r'D:\Project\.env')

os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['HF_HOME'] = r'D:\Project\model_cache'

from groq import Groq
from langchain_huggingface import HuggingFaceEmbeddings

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
EMBED_MODEL  = "intfloat/multilingual-e5-large"

groq   = Groq(api_key=GROQ_API_KEY)
SB_HDR = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}
REST = f"{SUPABASE_URL}/rest/v1"

# ─── قائمة التحاليل ────────────────────────────────────────────────────────
LAB_TESTS = [
    # CBC
    {"ar": "الهيموجلوبين",          "en": "hemoglobin",             "unit": "g/dL",    "normal": "ذكر: 13.5–17.5 | أنثى: 12–15.5"},
    {"ar": "خلايا الدم الحمراء",    "en": "red blood cells RBC",     "unit": "مليون/μL","normal": "ذكر: 4.5–5.9 | أنثى: 4.1–5.1"},
    {"ar": "خلايا الدم البيضاء",    "en": "white blood cells WBC",   "unit": "ألف/μL",  "normal": "4.5–11"},
    {"ar": "الصفائح الدموية",       "en": "platelets PLT",           "unit": "ألف/μL",  "normal": "150–400"},
    {"ar": "الهيماتوكريت",          "en": "hematocrit HCT",          "unit": "%",       "normal": "ذكر: 41–53 | أنثى: 36–46"},
    {"ar": "متوسط حجم الكرية",      "en": "MCV mean corpuscular volume","unit":"fL",    "normal": "80–100"},
    {"ar": "المتعادلات Neutrophils","en": "neutrophils",             "unit": "%",       "normal": "50–70"},
    {"ar": "الليمفاويات",           "en": "lymphocytes",             "unit": "%",       "normal": "20–40"},
    {"ar": "الحمضات Eosinophils",   "en": "eosinophils",             "unit": "%",       "normal": "1–4"},
    {"ar": "الوحيدات Monocytes",    "en": "monocytes",               "unit": "%",       "normal": "2–8"},
    # سكر
    {"ar": "سكر الدم الصائم",       "en": "fasting blood glucose",   "unit": "mg/dL",   "normal": "70–99"},
    {"ar": "الهيموجلوبين السكري HbA1c","en":"hemoglobin A1c HbA1c", "unit": "%",       "normal": "< 5.7"},
    # دهون
    {"ar": "الكوليسترول الكلي",     "en": "total cholesterol",       "unit": "mg/dL",   "normal": "< 200"},
    {"ar": "الدهون الثلاثية",       "en": "triglycerides",           "unit": "mg/dL",   "normal": "< 150"},
    {"ar": "الكوليسترول الجيد HDL", "en": "HDL cholesterol",         "unit": "mg/dL",   "normal": "ذكر: >40 | أنثى: >50"},
    {"ar": "الكوليسترول السيئ LDL", "en": "LDL cholesterol",         "unit": "mg/dL",   "normal": "< 100"},
    # كلى
    {"ar": "الكرياتينين",           "en": "creatinine",              "unit": "mg/dL",   "normal": "ذكر: 0.7–1.3 | أنثى: 0.5–1.1"},
    {"ar": "اليوريا BUN",           "en": "blood urea nitrogen BUN", "unit": "mg/dL",   "normal": "7–20"},
    {"ar": "حمض اليوريك",           "en": "uric acid",               "unit": "mg/dL",   "normal": "ذكر: 3.4–7 | أنثى: 2.4–6"},
    # كبد
    {"ar": "إنزيم ALT",             "en": "alanine aminotransferase ALT","unit":"U/L",  "normal": "7–56"},
    {"ar": "إنزيم AST",             "en": "aspartate aminotransferase AST","unit":"U/L","normal": "10–40"},
    {"ar": "إنزيم ALP",             "en": "alkaline phosphatase ALP","unit": "U/L",     "normal": "44–147"},
    {"ar": "البيليروبين الكلي",     "en": "total bilirubin",         "unit": "mg/dL",   "normal": "0.1–1.2"},
    {"ar": "الألبومين",             "en": "albumin",                 "unit": "g/dL",     "normal": "3.4–5.4"},
    # غدة درقية
    {"ar": "هرمون TSH",             "en": "thyroid stimulating hormone TSH","unit":"mIU/L","normal":"0.4–4.0"},
    {"ar": "هرمون T4 الحر",         "en": "free thyroxine T4",       "unit": "ng/dL",   "normal": "0.8–1.8"},
    {"ar": "هرمون T3 الحر",         "en": "free triiodothyronine T3","unit": "pg/mL",   "normal": "2.3–4.2"},
    # حديد
    {"ar": "الفيريتين",             "en": "ferritin",                "unit": "ng/mL",   "normal": "ذكر: 24–336 | أنثى: 11–307"},
    {"ar": "الحديد في الدم",        "en": "serum iron",              "unit": "μg/dL",   "normal": "60–170"},
    {"ar": "فيتامين د",             "en": "vitamin D 25-hydroxyvitamin D","unit":"ng/mL","normal":"30–100"},
    {"ar": "فيتامين B12",           "en": "vitamin B12 cobalamin",   "unit": "pg/mL",   "normal": "200–900"},
    {"ar": "حمض الفوليك",           "en": "folate folic acid",       "unit": "ng/mL",   "normal": "2.7–17"},
    # التهاب
    {"ar": "بروتين CRP",            "en": "C-reactive protein CRP",  "unit": "mg/L",    "normal": "< 1.0"},
    {"ar": "سرعة ترسب الدم ESR",   "en": "erythrocyte sedimentation rate ESR","unit":"mm/hr","normal":"ذكر:<15 | أنثى:<20"},
    # هرمونات
    {"ar": "هرمون التستوستيرون",    "en": "testosterone",            "unit": "ng/dL",   "normal": "ذكر: 300–1000 | أنثى: 15–70"},
    {"ar": "هرمون TSH الدرقي",      "en": "prolactin",               "unit": "ng/mL",   "normal": "ذكر: 2–18 | أنثى: 2–29"},
    # تخثر
    {"ar": "وقت البروثرومبين PT",   "en": "prothrombin time PT INR", "unit": "ثانية",   "normal": "11–13.5"},
    {"ar": "الصوديوم",              "en": "sodium Na",               "unit": "mEq/L",   "normal": "136–145"},
    {"ar": "البوتاسيوم",            "en": "potassium K",             "unit": "mEq/L",   "normal": "3.5–5.1"},
    {"ar": "الكالسيوم",             "en": "calcium Ca",              "unit": "mg/dL",   "normal": "8.5–10.5"},
]


def groq_call(prompt: str, max_tokens: int = 1200) -> str:
    try:
        r = groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=max_tokens,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        print(f"    [Groq error] {e}")
        time.sleep(10)
        return ""


def get_wikipedia_ar(term_ar: str) -> str:
    try:
        r = http.get(
            "https://ar.wikipedia.org/w/api.php",
            params={"action":"query","titles":term_ar,"prop":"extracts",
                    "format":"json","exintro":1,"explaintext":1,"exsectionformat":"plain"},
            timeout=10,
        )
        pages = r.json().get("query", {}).get("pages", {})
        for p in pages.values():
            extract = p.get("extract", "")
            if extract and len(extract) > 100:
                return extract[:2000]
    except Exception:
        pass
    return ""


def get_medlineplus(term_en: str) -> str:
    try:
        r = http.get(
            "https://wsearch.nlm.nih.gov/ws/query",
            params={"db":"healthTopics","term":term_en,"retmax":"2","rettype":"brief"},
            timeout=10,
        )
        # استخراج النص من XML
        text = re.sub(r'<[^>]+>', ' ', r.text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:2000] if len(text) > 100 else ""
    except Exception:
        return ""


def _extract_json(raw: str) -> dict | None:
    """محاولات متعددة لاستخراج JSON من رد Groq"""
    if not raw:
        return None
    # محاولة 1: استخراج من أول { لآخر }
    try:
        start = raw.index('{')
        end   = raw.rindex('}') + 1
        return json.loads(raw[start:end])
    except Exception:
        pass
    # محاولة 2: إزالة الأسطر المعطوبة وإعادة المحاولة
    try:
        lines = raw.splitlines()
        cleaned = []
        for ln in lines:
            try:
                cleaned.append(ln)
                json.loads('\n'.join(cleaned) + '}' * 4)
            except json.JSONDecodeError as err:
                if err.msg not in ("Unterminated string", "Expecting ',' delimiter"):
                    continue
        joined = '\n'.join(cleaned)
        start = joined.index('{')
        end   = joined.rindex('}') + 1
        return json.loads(joined[start:end])
    except Exception:
        pass
    return None


def build_chunks(test: dict, wiki_ar: str, medline_en: str) -> list:
    prompt = (
        f"You are a medical expert. Write concise Arabic medical info about lab test: {test['en']} ({test['ar']}). "
        f"Unit: {test['unit']}. Normal range: {test['normal']}. "
        "Reply ONLY with valid JSON, no extra text, using this exact format: "
        '{"definition":"one paragraph in Arabic","normal_values":"one paragraph in Arabic",'
        '"abnormal_causes":"one paragraph in Arabic","symptoms_tips":"one paragraph in Arabic"}'
    )

    raw = groq_call(prompt, max_tokens=1200)
    if not raw:
        print("    [!] Groq response empty")
        return []

    data = _extract_json(raw)
    if not data:
        print(f"    [!] JSON parse error | raw[:120]={raw[:120]}")
        return []

    base_meta = {
        "test_name":    test['ar'],
        "test_name_en": test['en'],
        "unit":         test['unit'],
        "normal_range": test['normal'],
        "source":       "MedlinePlus+Wikipedia",
        "language":     "ar",
    }

    chunks = []
    for topic_type, content in [
        ("lab_definition",  data.get("definition", "")),
        ("normal_values",   data.get("normal_values", "")),
        ("abnormal_causes", data.get("abnormal_causes", "")),
        ("symptoms_tips",   data.get("symptoms_tips", "")),
    ]:
        if content and isinstance(content, str) and len(content.strip()) > 50:
            text = f"تحليل: {test['ar']} | {test['en']}\n{content}"
            chunks.append({"content": text, "metadata": {**base_meta, "topic_type": topic_type}})

    return chunks


def insert_chunks(embeddings_model, chunks: list):
    if not chunks:
        return
    rows = []
    for ch in chunks:
        vec = embeddings_model.embed_query(ch["content"])
        rows.append({
            "content":   ch["content"],
            "metadata":  ch["metadata"],
            "embedding": vec,
        })
    r = http.post(f"{REST}/documents", headers=SB_HDR, json=rows, timeout=60)
    if not r.ok:
        print(f"  [DB] خطأ: {r.status_code} — {r.text[:150]}")


def get_existing_test_names() -> set:
    """جلب أسماء التحاليل الموجودة مسبقاً في قاعدة البيانات"""
    try:
        r = http.get(
            f"{REST}/documents",
            headers={**SB_HDR, "Prefer": "return=representation"},
            params={"select": "metadata->test_name_en", "metadata->>source": "eq.MedlinePlus+Wikipedia"},
            timeout=15,
        )
        if r.ok:
            return {row.get("test_name_en") for row in r.json() if row.get("test_name_en")}
    except Exception:
        pass
    return set()


def main():
    print("تحميل نموذج الـ Embeddings...")
    emb = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

    # عدد السجلات الحالية
    r = http.get(f"{REST}/documents", headers={**SB_HDR, "Prefer":"count=exact","Range":"0-0"}, timeout=10)
    current = int(r.headers.get("Content-Range","0/0").split("/")[-1])
    print(f"قاعدة البيانات حالياً: {current} chunk\n")

    existing = get_existing_test_names()
    print(f"تحاليل موجودة مسبقاً: {len(existing)}\n")

    total_added = 0
    for i, test in enumerate(LAB_TESTS):
        if test['en'] in existing:
            print(f"[{i+1}/{len(LAB_TESTS)}] تخطي (موجود): {test['ar']}")
            continue
        print(f"[{i+1}/{len(LAB_TESTS)}] {test['ar']} ({test['en']})")

        wiki_ar   = get_wikipedia_ar(test['ar'])
        medline   = get_medlineplus(test['en'])
        chunks    = build_chunks(test, wiki_ar, medline)

        if chunks:
            insert_chunks(emb, chunks)
            total_added += len(chunks)
            print(f"  + أضفت {len(chunks)} chunks")
        else:
            print(f"  - فشل توليد المحتوى")

        time.sleep(4)  # احترام rate limit Groq

    print(f"\nاكتمل الاستيعاب: أضفنا {total_added} chunk جديد")
    r2 = http.get(f"{REST}/documents", headers={**SB_HDR,"Prefer":"count=exact","Range":"0-0"}, timeout=10)
    final = int(r2.headers.get("Content-Range","0/0").split("/")[-1])
    print(f"إجمالي قاعدة البيانات الآن: {final} chunk")


if __name__ == "__main__":
    main()

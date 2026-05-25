"""
سكريبت استيراد شامل للموسوعة الطبية -> pgvector (Supabase)
يحل محل النسخة القديمة التي كانت تكتب على ChromaDB.

المصادر:
  1. تعاريف التحاليل المخبرية (ثنائي اللغة) — من medical_data.py
  2. MedlinePlus API (مجاني، بدون API key) — 70+ موضوع طبي
  3. توصيات صحية عربية — من medical_data.py

الاستخدام:
  cd backend && python ingest_medlineplus.py
  أو لتنظيف الجداول أولاً: python ingest_medlineplus.py --clear
"""
import os, re, sys, time, hashlib, requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault('HF_HOME', r'D:\Project\model_cache')
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

from langchain_huggingface import HuggingFaceEmbeddings
from medical_data import LAB_DEFINITIONS, HEALTH_RECOMMENDATIONS

EMBED_MODEL  = "intfloat/multilingual-e5-large"
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# ── MedlinePlus topics (search_term, topic_name, topic_type) ──────────────
LAB_TOPICS = [
    ("blood glucose test diabetes", "glucose", "lab_test"),
    ("complete blood count CBC hemoglobin", "CBC", "lab_test"),
    ("hemoglobin anemia iron deficiency", "hemoglobin", "lab_test"),
    ("cholesterol LDL HDL triglycerides", "cholesterol", "lab_test"),
    ("thyroid function TSH T3 T4", "thyroid", "lab_test"),
    ("liver function ALT AST bilirubin", "liver function", "lab_test"),
    ("kidney function creatinine BUN eGFR", "kidney function", "lab_test"),
    ("iron ferritin transferrin anemia", "iron", "lab_test"),
    ("vitamin D deficiency bone", "vitamin D", "lab_test"),
    ("vitamin B12 deficiency anemia", "vitamin B12", "lab_test"),
    ("uric acid gout", "uric acid", "lab_test"),
    ("C-reactive protein CRP inflammation", "CRP", "lab_test"),
    ("HbA1c glycated hemoglobin diabetes", "HbA1c", "lab_test"),
    ("white blood cell WBC leukocytes infection", "WBC", "lab_test"),
    ("platelet count bleeding clotting", "platelets", "lab_test"),
    ("sodium electrolytes hyponatremia", "sodium", "lab_test"),
    ("potassium electrolytes hyperkalemia", "potassium", "lab_test"),
    ("calcium bone osteoporosis", "calcium", "lab_test"),
    ("magnesium deficiency muscle cramp", "magnesium", "lab_test"),
    ("albumin protein liver nutrition", "albumin", "lab_test"),
    ("PSA prostate cancer screening", "PSA", "lab_test"),
    ("vitamin D calcium bone density", "bone health", "lab_test"),
]

SYMPTOM_TOPICS = [
    ("fatigue tiredness exhaustion chronic", "fatigue", "symptom"),
    ("headache migraine pain relief", "headache", "symptom"),
    ("fever temperature infection causes", "fever", "symptom"),
    ("dizziness vertigo balance", "dizziness", "symptom"),
    ("shortness of breath dyspnea", "shortness of breath", "symptom"),
    ("chest pain heart causes", "chest pain", "symptom"),
    ("abdominal pain stomach causes", "abdominal pain", "symptom"),
    ("nausea vomiting causes treatment", "nausea", "symptom"),
    ("back pain lower spine", "back pain", "symptom"),
    ("weight loss unexplained causes", "weight loss", "symptom"),
    ("hair loss alopecia causes", "hair loss", "symptom"),
    ("joint pain arthritis inflammation", "joint pain", "symptom"),
    ("muscle weakness fatigue causes", "muscle weakness", "symptom"),
    ("palpitations heart irregular", "palpitations", "symptom"),
    ("insomnia sleep disorders causes", "insomnia", "symptom"),
    ("anxiety stress mental health", "anxiety", "symptom"),
    ("frequent urination diabetes kidney", "frequent urination", "symptom"),
    ("blurred vision eye causes", "blurred vision", "symptom"),
    ("swollen feet edema causes", "edema", "symptom"),
    ("numbness tingling hands feet neuropathy", "numbness tingling", "symptom"),
]

DISEASE_TOPICS = [
    ("diabetes mellitus type 2 management", "diabetes", "disease"),
    ("hypertension high blood pressure treatment", "hypertension", "disease"),
    ("anemia iron deficiency treatment", "anemia", "disease"),
    ("hypothyroidism underactive thyroid treatment", "hypothyroidism", "disease"),
    ("hyperthyroidism overactive thyroid treatment", "hyperthyroidism", "disease"),
    ("coronary artery disease heart", "heart disease", "disease"),
    ("chronic kidney disease renal failure", "kidney disease", "disease"),
    ("fatty liver hepatic steatosis", "fatty liver", "disease"),
    ("gout uric acid joint treatment", "gout", "disease"),
    ("osteoporosis bone density fracture", "osteoporosis", "disease"),
    ("high cholesterol hyperlipidemia treatment", "high cholesterol", "disease"),
    ("metabolic syndrome insulin resistance", "metabolic syndrome", "disease"),
    ("polycystic ovary syndrome PCOS", "PCOS", "disease"),
    ("vitamin D deficiency treatment", "vitamin D deficiency", "disease"),
    ("vitamin B12 deficiency treatment", "vitamin B12 deficiency", "disease"),
    ("urinary tract infection UTI treatment", "UTI", "disease"),
    ("irritable bowel syndrome IBS", "IBS", "disease"),
    ("GERD acid reflux heartburn", "GERD", "disease"),
    ("rheumatoid arthritis autoimmune joint", "rheumatoid arthritis", "disease"),
    ("celiac disease gluten intolerance", "celiac disease", "disease"),
]

ALL_MEDLINEPLUS_TOPICS = LAB_TOPICS + SYMPTOM_TOPICS + DISEASE_TOPICS


# ══════════════════════════════════════════════════════════════════
# 1. Text Cleaning
# ══════════════════════════════════════════════════════════════════

def clean_text(text: str) -> str:
    """Remove HTML tags, normalize whitespace, normalize Arabic alef variants."""
    text = re.sub(r'<[^>]+>', ' ', text)        # HTML tags
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)    # HTML entities
    text = re.sub(r'\s+', ' ', text).strip()     # excessive whitespace
    # Normalize Arabic alef variants — safe, standard NLP practice
    text = re.sub(r'[إأآ]', 'ا', text)
    return text


# ══════════════════════════════════════════════════════════════════
# 2. Semantic Chunking
# ══════════════════════════════════════════════════════════════════

def make_lab_chunks(lab: dict) -> list[dict]:
    """
    Create 3 semantically distinct chunks per lab test.
    Returns list of {content, chunk_type, chunk_index} dicts.
    """
    name_ar, name_en = lab["name_ar"], lab["name_en"]
    chunks = []

    # Chunk 0 — Definition + normal range
    chunks.append({
        "content": clean_text(f"{name_ar} ({name_en}): {lab['definition']}"),
        "chunk_type": "definition",
        "chunk_index": 0,
    })

    # Chunk 1 — Causes of high and low
    abnormal = (
        f"ارتفاع {name_ar}: {lab['high']}. "
        f"انخفاض {name_ar}: {lab['low']}."
    )
    chunks.append({
        "content": clean_text(abnormal),
        "chunk_type": "values",
        "chunk_index": 1,
    })

    # Chunk 2 — Symptoms (only if content is meaningful)
    symptoms = lab.get("symptoms_low", "").strip()
    if len(symptoms) > 30:
        sym_text = f"الأعراض والعلامات المرتبطة بـ{name_ar}: {symptoms}."
        chunks.append({
            "content": clean_text(sym_text),
            "chunk_type": "symptoms",
            "chunk_index": 2,
        })

    return chunks


def sentence_chunks(text: str, max_chars: int = 800, overlap: int = 1) -> list[dict]:
    """
    Split free-form English/Arabic text at sentence boundaries.
    Returns list of {content, chunk_type, chunk_index}.
    """
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

    chunks, current, current_len = [], [], 0
    for sent in sentences:
        if current_len + len(sent) > max_chars and current:
            body = ' '.join(current)
            chunks.append({"content": body, "chunk_type": _detect_type(body)})
            current = current[-overlap:] if overlap else []
            current_len = sum(len(s) + 1 for s in current)
        current.append(sent)
        current_len += len(sent) + 1

    if current:
        body = ' '.join(current)
        if len(body) > 80:
            chunks.append({"content": body, "chunk_type": _detect_type(body)})

    for i, c in enumerate(chunks):
        c["chunk_index"] = i
    return chunks


def _detect_type(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ['definition', 'what is', 'also called', 'refers to', 'is a test']):
        return 'definition'
    if any(w in t for w in ['normal range', 'normal level', 'mg/dl', 'g/dl', 'mmol', 'ng/ml', 'iu/l']):
        return 'values'
    if any(w in t for w in ['symptom', 'sign', 'can cause', 'may cause', 'causes include']):
        return 'symptoms'
    if any(w in t for w in ['treatment', 'therapy', 'medication', 'manage', 'drug']):
        return 'treatment'
    return 'general'


# ══════════════════════════════════════════════════════════════════
# 3. Metadata helpers
# ══════════════════════════════════════════════════════════════════

_SPECIALTY_MAP = {
    'hematology':   ['hemoglobin', 'rbc', 'wbc', 'platelet', 'cbc', 'hematocrit', 'mcv', 'mch',
                     'mchc', 'rdw', 'neutrophil', 'lymphocyte', 'monocyte', 'eosinophil', 'basophil',
                     'esr', 'd-dimer', 'fibrinogen', 'aptt', 'pt/inr', 'ferritin', 'iron'],
    'endocrinology':['glucose', 'hba1c', 'insulin', 'tsh', 'thyroid', 't3', 't4', 'cortisol',
                     'testosterone', 'estradiol', 'prolactin', 'lh', 'fsh', 'dhea', 'progesterone', 'amh'],
    'cardiology':   ['cholesterol', 'ldl', 'hdl', 'triglyceride', 'troponin', 'bnp', 'ck-mb',
                     'heart', 'cardiac'],
    'nephrology':   ['creatinine', 'egfr', 'bun', 'urea', 'kidney', 'urine protein', 'urine ketone',
                     'urine specific gravity', 'chloride', 'sodium', 'potassium'],
    'hepatology':   ['alt', 'ast', 'bilirubin', 'liver', 'albumin', 'ggt', 'alkaline phosphatase',
                     'total protein', 'hepatitis'],
    'rheumatology': ['crp', 'esr', 'ana', 'rheumatoid', 'uric acid', 'gout', 'anti-tpo'],
    'nutrition':    ['vitamin d', 'vitamin b12', 'folic acid', 'zinc', 'magnesium', 'calcium',
                     'selenium', 'copper', 'phosphorus', 'iron'],
    'immunology':   ['hiv', 'hepatitis b', 'hepatitis c', 'procalcitonin'],
    'reproductive': ['lh', 'fsh', 'progesterone', 'estradiol', 'beta hcg', 'amh', 'semen', 'testosterone', 'prolactin'],
}

def _get_specialty(name: str) -> str:
    name_lower = name.lower()
    for specialty, keywords in _SPECIALTY_MAP.items():
        if any(k in name_lower for k in keywords):
            return specialty
    return 'general'


def _extract_unit(definition: str) -> str | None:
    m = re.search(
        r'\b(g/dL|mg/dL|ng/mL|µg/dL|IU/L|U/L|mEq/L|mmol/L|pg/mL|µIU/mL|mIU/L|mm/hr|ng/dL|µg/L|fL|pg)\b',
        definition
    )
    return m.group(1) if m else None


# ══════════════════════════════════════════════════════════════════
# 4. MedlinePlus API
# ══════════════════════════════════════════════════════════════════

def fetch_medlineplus(search_term: str, retmax: int = 3) -> list[dict]:
    """Fetch free MedlinePlus health topic summaries."""
    url = "https://wsearch.nlm.nih.gov/ws/query"
    params = {"db": "healthTopics", "term": search_term, "retmax": retmax}
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.text)
        results = []
        for doc in root.findall('.//document'):
            title, content = "", ""
            for elem in doc.findall('content'):
                name = elem.get('name', '')
                if name == 'title':
                    title = elem.text or ""
                elif name == 'FullSummary':
                    raw = elem.text or ""
                    content = clean_text(re.sub(r'<[^>]+>', ' ', raw))
            if title and len(content) > 100:
                results.append({"title": title, "content": content})
        return results
    except Exception as e:
        print(f"  [MedlinePlus ERROR] {search_term}: {e}")
        return []


# ══════════════════════════════════════════════════════════════════
# 5. Supabase pgvector Insert
# ══════════════════════════════════════════════════════════════════

def _make_headers(key: str) -> dict:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def insert_batch(batch: list[dict], url: str, key: str) -> bool:
    try:
        r = requests.post(
            f"{url}/rest/v1/documents",
            headers=_make_headers(key),
            json=batch,
            timeout=60,
        )
        if r.status_code not in (200, 201):
            print(f"  [INSERT ERROR] {r.status_code}: {r.text[:300]}")
            return False
        return True
    except Exception as e:
        print(f"  [INSERT EXCEPTION] {e}")
        return False


def clear_source(source: str, url: str, key: str):
    """Delete all documents from a given source before re-ingesting."""
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    r = requests.delete(
        f"{url}/rest/v1/documents",
        headers=headers,
        params={"metadata->>source": f"eq.{source}"},
        timeout=30,
    )
    print(f"  [CLEAR] source={source} -> {r.status_code}")


def embed_and_insert(
    docs: list[dict],
    embeddings: HuggingFaceEmbeddings,
    url: str,
    key: str,
    seen_hashes: set,
    batch_size: int = 50,
) -> int:
    """Embed + deduplicate + batch-insert documents to pgvector."""
    inserted = 0
    batch = []

    for doc in docs:
        content = doc["content"]
        if not content or len(content) < 20:
            continue
        h = hashlib.md5(content.encode()).hexdigest()
        if h in seen_hashes:
            continue
        seen_hashes.add(h)

        try:
            vec = embeddings.embed_query(content)
        except Exception as e:
            print(f"  [EMBED ERROR] {e}")
            continue

        batch.append({
            "content": content,
            "metadata": doc["metadata"],
            "embedding": vec,
        })

        if len(batch) >= batch_size:
            if insert_batch(batch, url, key):
                inserted += len(batch)
            else:
                print(f"  [WARN] Batch of {len(batch)} failed — skipping")
            batch = []

    if batch:
        if insert_batch(batch, url, key):
            inserted += len(batch)

    return inserted


# ══════════════════════════════════════════════════════════════════
# 6. Main
# ══════════════════════════════════════════════════════════════════

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[ERROR] SUPABASE_URL و SUPABASE_KEY غير موجودان في .env")
        sys.exit(1)

    do_clear = "--clear" in sys.argv

    print(f"تحميل نموذج Embeddings: {EMBED_MODEL}...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

    seen_hashes: set = set()
    total_inserted = 0

    # ── 1. Lab definitions (bilingual Arabic/English) ─────────────
    print(f"\n[1/3] استيراد تعاريف التحاليل ({len(LAB_DEFINITIONS)} تحليل)...")
    if do_clear:
        clear_source("TibyanLabs", SUPABASE_URL, SUPABASE_KEY)

    lab_docs = []
    for lab in LAB_DEFINITIONS:
        test_name = lab["name_en"].split("(")[0].strip()
        specialty  = _get_specialty(lab["name_en"] + " " + lab["name_ar"])
        unit       = _extract_unit(lab["definition"])

        for chunk in make_lab_chunks(lab):
            lab_docs.append({
                "content": chunk["content"],
                "metadata": {
                    "source":      "TibyanLabs",
                    "topic_name":  test_name,
                    "topic_type":  "lab_test",
                    "title":       f"{lab['name_ar']} ({lab['name_en']})",
                    "language":    "bilingual",
                    "chunk_index": chunk["chunk_index"],
                    "chunk_type":  chunk["chunk_type"],
                    "specialty":   specialty,
                    "test_name":   test_name,
                    "unit":        unit,
                },
            })

    n = embed_and_insert(lab_docs, embeddings, SUPABASE_URL, SUPABASE_KEY, seen_hashes)
    total_inserted += n
    print(f"  -> {n} chunk مُضاف من تعاريف التحاليل")

    # ── 2. Health recommendations (Arabic) ───────────────────────
    print(f"\n[2/3] استيراد التوصيات الصحية ({len(HEALTH_RECOMMENDATIONS)} موضوع)...")
    rec_docs = []
    for rec in HEALTH_RECOMMENDATIONS:
        content = clean_text(f"{rec['topic']}: {rec['content']}")
        rec_docs.append({
            "content": content,
            "metadata": {
                "source":      "TibyanLabs",
                "topic_name":  rec["topic"],
                "topic_type":  "health_recommendation",
                "title":       rec["topic"],
                "language":    "ar",
                "chunk_index": 0,
                "chunk_type":  "treatment",
                "specialty":   "general",
                "test_name":   None,
                "unit":        None,
            },
        })

    n = embed_and_insert(rec_docs, embeddings, SUPABASE_URL, SUPABASE_KEY, seen_hashes)
    total_inserted += n
    print(f"  -> {n} chunk مُضاف من التوصيات الصحية")

    # ── 3. MedlinePlus API ────────────────────────────────────────
    print(f"\n[3/3] استيراد من MedlinePlus ({len(ALL_MEDLINEPLUS_TOPICS)} موضوع)...")
    if do_clear:
        clear_source("MedlinePlus", SUPABASE_URL, SUPABASE_KEY)

    for i, (search_term, topic_name, topic_type) in enumerate(ALL_MEDLINEPLUS_TOPICS, 1):
        results = fetch_medlineplus(search_term)
        ml_docs = []
        for item in results:
            for chunk in sentence_chunks(item["content"]):
                ml_docs.append({
                    "content": chunk["content"],
                    "metadata": {
                        "source":      "MedlinePlus",
                        "topic_name":  topic_name,
                        "topic_type":  topic_type,
                        "title":       item["title"],
                        "language":    "en",
                        "chunk_index": chunk["chunk_index"],
                        "chunk_type":  chunk["chunk_type"],
                        "specialty":   _get_specialty(topic_name),
                        "test_name":   topic_name if topic_type == "lab_test" else None,
                        "unit":        None,
                    },
                })

        n = embed_and_insert(ml_docs, embeddings, SUPABASE_URL, SUPABASE_KEY, seen_hashes)
        total_inserted += n
        print(f"  [{i}/{len(ALL_MEDLINEPLUS_TOPICS)}] {topic_name} -> {n} chunk")
        time.sleep(0.35)   # rate-limit courtesy

    print(f"\n[ok] اكتمل! إجمالي المُضاف: {total_inserted} chunk في pgvector (Supabase)")


if __name__ == "__main__":
    main()

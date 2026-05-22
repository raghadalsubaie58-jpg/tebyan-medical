"""
سكريبت استيراد الموسوعة الطبية من MedlinePlus (مجاني، بدون API key)
الاستخدام: python ingest_medlineplus.py
"""
import os
import re
import time
import requests
import xml.etree.ElementTree as ET
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

os.environ['HF_HOME'] = r'D:\Project\model_cache'

DB_PATH = r'D:\Project\chroma_db'
EMBEDDINGS_MODEL = "intfloat/multilingual-e5-small"

# ===== تحاليل الدم =====
LAB_TESTS = [
    ("blood glucose test diabetes", "glucose", "lab_test"),
    ("complete blood count CBC hemoglobin", "CBC", "lab_test"),
    ("hemoglobin anemia iron deficiency", "hemoglobin", "lab_test"),
    ("cholesterol LDL HDL triglycerides", "cholesterol", "lab_test"),
    ("thyroid function TSH T3 T4", "thyroid", "lab_test"),
    ("liver function ALT AST bilirubin", "liver function", "lab_test"),
    ("kidney function creatinine BUN", "kidney function", "lab_test"),
    ("iron ferritin transferrin anemia", "iron", "lab_test"),
    ("vitamin D deficiency bone", "vitamin D", "lab_test"),
    ("vitamin B12 deficiency anemia", "vitamin B12", "lab_test"),
    ("uric acid gout", "uric acid", "lab_test"),
    ("C-reactive protein CRP inflammation", "CRP", "lab_test"),
    ("HbA1c glycated hemoglobin diabetes", "HbA1c", "lab_test"),
    ("white blood cell WBC leukocytes infection", "WBC", "lab_test"),
    ("platelet count bleeding clotting", "platelets", "lab_test"),
    ("eosinophils allergy parasites", "eosinophils", "lab_test"),
    ("sodium electrolytes hyponatremia", "sodium", "lab_test"),
    ("potassium electrolytes hyperkalemia", "potassium", "lab_test"),
    ("calcium bone osteoporosis", "calcium", "lab_test"),
    ("magnesium deficiency muscle", "magnesium", "lab_test"),
    ("albumin protein liver nutrition", "albumin", "lab_test"),
    ("PSA prostate cancer screening", "PSA", "lab_test"),
]

# ===== الأعراض الشائعة =====
SYMPTOMS = [
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
    ("weight gain causes treatment", "weight gain", "symptom"),
    ("hair loss alopecia causes", "hair loss", "symptom"),
    ("skin rash allergy dermatitis", "skin rash", "symptom"),
    ("joint pain arthritis inflammation", "joint pain", "symptom"),
    ("muscle weakness fatigue causes", "muscle weakness", "symptom"),
    ("palpitations heart irregular", "palpitations", "symptom"),
    ("insomnia sleep disorders causes", "insomnia", "symptom"),
    ("anxiety stress mental health", "anxiety", "symptom"),
    ("depression mood mental health", "depression", "symptom"),
    ("frequent urination diabetes kidney", "frequent urination", "symptom"),
    ("excessive thirst polydipsia causes", "excessive thirst", "symptom"),
    ("blurred vision eye causes", "blurred vision", "symptom"),
    ("swollen feet edema causes", "swollen feet", "symptom"),
    ("pale skin anemia causes", "pale skin", "symptom"),
    ("night sweats causes fever infection", "night sweats", "symptom"),
    ("cough chronic causes respiratory", "cough", "symptom"),
    ("numbness tingling hands feet", "numbness tingling", "symptom"),
]

# ===== الأمراض الشائعة =====
DISEASES = [
    ("diabetes mellitus type 2 management", "diabetes", "disease"),
    ("hypertension high blood pressure treatment", "hypertension", "disease"),
    ("anemia iron deficiency treatment", "anemia", "disease"),
    ("hypothyroidism underactive thyroid treatment", "hypothyroidism", "disease"),
    ("hyperthyroidism overactive thyroid treatment", "hyperthyroidism", "disease"),
    ("coronary artery disease heart", "heart disease", "disease"),
    ("kidney disease chronic renal failure", "kidney disease", "disease"),
    ("fatty liver hepatic steatosis", "fatty liver", "disease"),
    ("gout uric acid joint", "gout", "disease"),
    ("osteoporosis bone density fracture", "osteoporosis", "disease"),
    ("vitamin D deficiency treatment supplement", "vitamin D deficiency", "disease"),
    ("vitamin B12 deficiency treatment", "vitamin B12 deficiency", "disease"),
    ("high cholesterol hyperlipidemia treatment", "high cholesterol", "disease"),
    ("asthma respiratory treatment inhaler", "asthma", "disease"),
    ("urinary tract infection UTI treatment", "UTI", "disease"),
    ("irritable bowel syndrome IBS treatment", "IBS", "disease"),
    ("GERD acid reflux heartburn treatment", "GERD", "disease"),
    ("polycystic ovary syndrome PCOS treatment", "PCOS", "disease"),
    ("obesity overweight BMI treatment", "obesity", "disease"),
    ("metabolic syndrome insulin resistance", "metabolic syndrome", "disease"),
    ("celiac disease gluten intolerance", "celiac disease", "disease"),
    ("rheumatoid arthritis autoimmune joint", "rheumatoid arthritis", "disease"),
]

ALL_TOPICS = LAB_TESTS + SYMPTOMS + DISEASES


def fetch_medlineplus(search_term: str) -> list[dict]:
    url = "https://wsearch.nlm.nih.gov/ws/query"
    params = {"db": "healthTopics", "term": search_term, "retmax": 3}
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.text)
        results = []
        for doc in root.findall('.//document'):
            title = ""
            content = ""
            for elem in doc.findall('content'):
                name = elem.get('name', '')
                if name == 'title':
                    title = elem.text or ""
                elif name == 'FullSummary':
                    raw = elem.text or ""
                    content = re.sub(r'<[^>]+>', ' ', raw).strip()
                    content = re.sub(r'\s+', ' ', content)
            if title and content and len(content) > 100:
                results.append({"title": title, "content": content})
        return results
    except Exception as e:
        print(f"  [ERROR] {search_term}: {e}")
        return []


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if len(chunk) > 100:
            chunks.append(chunk)
    return chunks


def main():
    print("تحميل نموذج الـ Embeddings...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL)

    print("الاتصال بقاعدة البيانات...")
    db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)

    all_docs = []
    total = len(ALL_TOPICS)
    for i, (search_term, topic_name, topic_type) in enumerate(ALL_TOPICS, 1):
        print(f"[{i}/{total}] {topic_name}...")
        results = fetch_medlineplus(search_term)

        for item in results:
            for idx, chunk in enumerate(chunk_text(item["content"])):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "source": "MedlinePlus",
                        "topic_name": topic_name,
                        "topic_type": topic_type,
                        "title": item["title"],
                        "language": "en",
                        "chunk_index": idx,
                    }
                )
                all_docs.append(doc)

        time.sleep(0.3)

    if all_docs:
        print(f"\nاضافة {len(all_docs)} chunk...")
        db.add_documents(all_docs)
        print(f"[OK] تم! الموسوعة تحتوي {len(all_docs)} chunk من {total} موضوع طبي")
    else:
        print("[ERROR] لم يتم جلب أي بيانات")


if __name__ == "__main__":
    main()

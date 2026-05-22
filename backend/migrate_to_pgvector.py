"""
سكريبت ترحيل البيانات من ChromaDB إلى Supabase pgvector
يستخدم embeddings المحسوبة مسبقاً (لا يعيد الحساب)
"""
import os, sys, json
import requests as http
from dotenv import load_dotenv
load_dotenv(dotenv_path=r'D:\Project\.env')

os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['HF_HOME'] = r'D:\Project\model_cache'

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

EMBED_MODEL  = "intfloat/multilingual-e5-large"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
CHROMA_PATH  = r'D:\Project\chroma_db'
BATCH_SIZE   = 50

print("جاري تحميل النموذج والقاعدة...")
embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
chroma_db  = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)

# استخراج كل البيانات مع الـ embeddings المحسوبة مسبقاً
raw = chroma_db._collection.get(include=["embeddings", "documents", "metadatas"])
docs   = raw["documents"]
metas  = raw["metadatas"]
vecs   = raw["embeddings"]
total  = len(docs)
print(f"وجدت {total} chunk في ChromaDB")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}
REST = f"{SUPABASE_URL}/rest/v1"

# تحقق من الجدول الحالي
r = http.get(f"{REST}/documents", headers={**headers, "Prefer": "count=exact", "Range": "0-0"}, timeout=10)
existing_count = int(r.headers.get("Content-Range", "0/0").split("/")[-1]) if r.ok else 0
print(f"الجدول حالياً يحتوي على {existing_count} سجل")

if existing_count >= total:
    print("البيانات موجودة بالفعل — لا حاجة للترحيل.")
    sys.exit(0)

# مسح البيانات القديمة
if existing_count > 0:
    http.delete(f"{REST}/documents?id=neq.00000000-0000-0000-0000-000000000000", headers=headers, timeout=30)
    print("تم مسح البيانات القديمة")

# إدراج على دفعات
inserted = 0
for i in range(0, total, BATCH_SIZE):
    batch_docs  = docs[i:i+BATCH_SIZE]
    batch_metas = metas[i:i+BATCH_SIZE]
    batch_vecs  = vecs[i:i+BATCH_SIZE]

    rows = []
    for doc, meta, vec in zip(batch_docs, batch_metas, batch_vecs):
        rows.append({
            "content":   doc,
            "metadata":  meta if meta else {},
            "embedding": vec.tolist() if hasattr(vec, "tolist") else list(vec),
        })

    resp = http.post(f"{REST}/documents", headers=headers, json=rows, timeout=60)
    if not resp.ok:
        print(f"  خطأ: {resp.status_code} — {resp.text[:200]}")
        sys.exit(1)
    inserted += len(rows)
    print(f"  [{inserted}/{total}] تم الإدراج")

print(f"\nاكتمل الترحيل: {inserted} chunk في Supabase pgvector")

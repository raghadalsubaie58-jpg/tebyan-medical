import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# 1. الإعدادات
BOOKS_DIR = r'D:\Project\data'
DB_DIR = r'D:\Project\chroma_db'
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
# 2. جلب قائمة الكتب الموجودة تدريجياً (تجنباً لخطأ SQL)
db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
existing_books = set()
chunk_size = 1000
offset = 0

print("🔍 جاري فحص الكتب المسجلة مسبقاً...")
while True:
    res = db._collection.get(include=['metadatas'], limit=chunk_size, offset=offset)
    if not res['metadatas']:
        break
    for m in res['metadatas']:
        if m and 'source' in m:
            book_name = m['source'].split('\\')[-1].split('/')[-1]
            existing_books.add(book_name)
    offset += chunk_size
    if offset > 60000: break # حماية

print(f"📦 الكتب الحالية في القاعدة: {len(existing_books)}")

# 3. البحث عن كتب جديدة في المجلد
all_pdfs = [f for f in os.listdir(BOOKS_DIR) if f.endswith('.pdf')]
new_pdfs = [f for f in all_pdfs if f not in existing_books]

if not new_pdfs:
    print("✅ لا توجد كتب جديدة لإضافتها.")
else:
    print(f"🆕 تم العثور على {len(new_pdfs)} كتب جديدة سيتم إضافتها: {new_pdfs}")
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    
    for pdf in new_pdfs:
        try:
            print(f"📖 جاري معالجة: {pdf}...")
            loader = PyPDFLoader(os.path.join(BOOKS_DIR, pdf))
            pages = loader.load()
            chunks = text_splitter.split_documents(pages)
            
            # إضافة القطع الجديدة
            db.add_documents(chunks)
            print(f"✨ تمت إضافة {pdf} بنجاح!")
        except Exception as e:
            print(f"❌ فشل في معالجة {pdf}: {e}")

    print("\n✅ تم تحديث قاعدة البيانات بنجاح.")
    all_pdfs = [f for f in os.listdir(BOOKS_DIR) if f.endswith('.pdf')]
print(f"👀 الكود يرى هذه الملفات في المجلد حالياً: {all_pdfs}") # أضيفي هذا السطر
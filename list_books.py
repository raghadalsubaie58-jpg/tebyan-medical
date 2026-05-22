import os
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# إعداد الـ Embeddings
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
# مسار قاعدة البيانات
persist_directory = r'D:\Project\chroma_db'

if os.path.exists(persist_directory):
    db = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    
    print("\n" + "🔍" * 15)
    print("جاري فحص قاعدة البيانات العميقة...")
    
    try:
        all_books = set()
        chunk_size = 1000 # نسحب 1000 قطعة في كل مرة لتجنب خطأ SQL
        offset = 0
        
        while True:
            # نسحب فقط الميتا داتا وبكميات محدودة (Paging)
            results = db._collection.get(
                include=['metadatas'], 
                limit=chunk_size, 
                offset=offset
            )
            
            if not results['metadatas']:
                break
                
            for meta in results['metadatas']:
                if meta and 'source' in meta:
                    book_name = meta['source'].split('\\')[-1].split('/')[-1]
                    all_books.add(book_name)
            
            offset += chunk_size
            # إذا سحبنا كمية كبيرة جداً نتوقف (حماية)
            if offset > 50000: 
                break

        if all_books:
            print(f"✅ تم العثور على {len(all_books)} كتب مخزنة فعلياً:")
            for i, book in enumerate(sorted(all_books), 1):
                print(f"   {i}. 📖 {book}")
            print(f"\nإجمالي القطع النصية (Chunks) المفحوصة: {offset}")
        else:
            print("⚠️ لم يتم العثور على أسماء كتب في الميتا داتا.")
            
    except Exception as e:
        print(f"❌ خطأ تقني: {e}")
    
    print("🔍" * 15 + "\n")
else:
    print("❌ المجلد chroma_db غير موجود.")
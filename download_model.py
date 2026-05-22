import os
# إجبار النظام على استخدام القرص D للمساحة المؤقتة أيضاً
os.environ['HF_HOME'] = r'D:\Project\model_cache'
os.environ['TEMP'] = r'D:\Project\temp'
os.environ['TMP'] = r'D:\Project\temp'

from sentence_transformers import SentenceTransformer

# إنشاء مجلدات المؤقتة في D إذا لم تكن موجودة
os.makedirs(r'D:\Project\temp', exist_ok=True)

# موديل صغير جداً وخفيف (22 ميجابايت فقط)
model_name = "paraphrase-MiniLM-L3-v2"

print(f"جاري تحميل الموديل الصغير إلى القرص D...")

try:
    model = SentenceTransformer(model_name)
    print("✅ تم التحميل بنجاح! المساحة لم تعد عائقاً.")
except Exception as e:
    print(f"❌ حدث خطأ: {e}")
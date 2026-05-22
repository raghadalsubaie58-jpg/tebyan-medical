import os
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
import io
import streamlit as st
import google.generativeai as genai
import numpy as np
from PIL import Image
import fitz
import easyocr
import re
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# --- 1. الإعدادات ---
os.environ['HF_HOME'] = r'D:\Project\model_cache'
API_KEY = "AIzaSyDA4UjdmbAAGGgdrYLYRQtJYHrnawYdka4"
genai.configure(api_key=API_KEY)

st.set_page_config(page_title="تبيان الطبي", layout="wide", page_icon="🩺")

# معالجة رسائل الشات في أول الصفحة
_chat_q = st.query_params.get("q", "")
if _chat_q:
    if "chat_msgs" not in st.session_state:
        st.session_state.chat_msgs = [{"role":"bot","text":"مرحباً! أنا مساعدك الطبي 🩺"}]
    st.session_state.chat_msgs.append({"role":"user","text":_chat_q})
    st.query_params.clear()

# --- 2. CSS ---
# إخفاء مساحة iframe الشات
st.markdown("""<style>
div[data-testid="stCustomComponentV1"] {
    height: 0px !important;
    min-height: 0px !important;
    margin: 0 !important;
    padding: 0 !important;
}
</style>""", unsafe_allow_html=True)
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after { font-family: 'Cairo', sans-serif !important; direction: rtl; box-sizing: border-box; }
        .stApp { background-color: #F0F4F8; }
        #MainMenu, footer, header { visibility: hidden; }
        .block-container { padding-top: 0 !important; padding-bottom: 6rem !important; max-width: 1100px !important; min-height: 100vh !important; }

        /* الهيدر */
        .main-header {
            background: rgba(255,255,255,0.97);
            border-bottom: 1px solid #E2E8F0;
            padding: 0 2.5rem;
            height: 64px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: fixed;
            top: 0; left: 0; right: 0;
            z-index: 9999;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            box-shadow: 0 2px 12px rgba(59,130,246,0.07);
        }
        .header-logo { display: flex; align-items: center; gap: 10px; }
        .header-logo-icon {
            width: 38px; height: 38px; 
            background: linear-gradient(135deg,#3B82F6,#2563EB);
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
        }
        .header-logo-text { font-size: 1.3rem; font-weight: 900; color: #0F172A; }
        .header-badge {
            display: flex; align-items: center; gap: 6px;
            background: #EFF6FF; padding: 5px 14px;
            border-radius: 999px; border: 1px solid #BFDBFE;
        }
        .header-badge-dot { width: 7px; height: 7px; background: #3B82F6; border-radius: 50%; }
        .header-badge-text { font-size: 0.78rem; font-weight: 700; color: #2563EB; }

        /* Hero */
        .hero-section { text-align: center; padding: 2rem 1rem 2.5rem; margin-top: 64px; }
        .hero-badge { display: inline-block; background: #EFF6FF; color: #2563EB; border-radius: 999px; padding: 6px 20px; font-size: 13px; font-weight: 700; margin-bottom: 1.2rem; border: 1px solid #BFDBFE; }
        .hero-title { font-size: clamp(1.8rem, 4vw, 2.6rem); font-weight: 900; color: #0F172A; margin: 0 0 1rem; line-height: 1.4; }

        /* Upload */
        div[data-testid="stFileUploader"] {
            background: white !important; border: 2px dashed #CBD5E1 !important;
            border-radius: 1.25rem !important; padding: 3rem 2rem !important;
            text-align: center !important; box-shadow: 0 2px 20px rgba(59,130,246,0.08) !important;
            cursor: pointer !important; transition: all 0.2s !important;
        }
        div[data-testid="stFileUploader"]:hover { border-color: #3B82F6 !important; background: #EFF6FF !important; }
        div[data-testid="stFileUploaderDropzone"] { border: none !important; padding: 0 !important; background: transparent !important; display: flex !important; flex-direction: column !important; align-items: center !important; gap: 0.5rem !important; }
        div[data-testid="stFileUploaderDropzoneInstructions"] { text-align: center !important; }
        div[data-testid="stFileUploaderDropzoneInstructions"] > div > span { font-family: 'Cairo', sans-serif !important; font-size: 1.4rem !important; font-weight: 900 !important; color: #0F172A !important; }
        div[data-testid="stFileUploaderDropzoneInstructions"] > div > span:last-child { display: none !important; }
        div[data-testid="stFileUploaderDropzoneInstructions"] > div > small { font-family: 'Cairo', sans-serif !important; font-size: 0.85rem !important; color: #64748B !important; }
        button[data-testid="stBaseButton-secondary"] { background: linear-gradient(135deg,#3B82F6,#2563EB) !important; color: white !important; border: none !important; border-radius: 12px !important; padding: 12px 36px !important; font-family: 'Cairo', sans-serif !important; font-weight: 700 !important; font-size: 1rem !important; margin-top: 0.5rem !important; }

        /* Feature Cards */
        .feature-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-top: 2.5rem; }
        .feature-card { background: white; border-radius: 1rem; border: 1px solid #E2E8F0; padding: 1.4rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
        .feature-icon-wrap { width: 44px; height: 44px; background: #EFF6FF; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1.3rem; margin-bottom: 0.9rem; }
        .feature-title { font-weight: 800; font-size: 0.95rem; color: #1E293B; margin: 0 0 6px; }
        .feature-text { font-size: 0.85rem; color: #64748B; margin: 0; line-height: 1.7; }

        /* Results */
        .section-title { font-size: 1.1rem; font-weight: 900; color: #0F172A; margin: 2rem 0 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid #EFF6FF; }
        .result-card { background: white; border-radius: 1rem; padding: 1rem 1.2rem; margin-bottom: 0.85rem; border: 1px solid #E2E8F0; border-right: 4px solid; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
        .result-card.status-low    { border-right-color: #F59E0B; }
        .result-card.status-high   { border-right-color: #EF4444; }
        .result-card.status-normal { border-right-color: #10B981; }
        .test-label { font-size: 0.72rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
        .test-value { font-size: 1.3rem; font-weight: 900; color: #0F172A; margin: 4px 0; }
        .test-unit  { font-size: 0.68rem; font-weight: 500; color: #94A3B8; }
        .status-badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.72rem; font-weight: 700; margin-bottom: 6px; }
        .badge-low    { background: #FEF3C7; color: #92400E; }
        .badge-high   { background: #FEE2E2; color: #991B1B; }
        .badge-normal { background: #D1FAE5; color: #065F46; }
        .badge-warning{ background: #EFF6FF; color: #1E40AF; }
        .range-text { font-size: 0.72rem; color: #94A3B8; border-top: 1px dashed #E2E8F0; padding-top: 6px; margin-top: 6px; }

        /* Summary */
        .summary-banner { background: linear-gradient(135deg,#EFF6FF,#F0F9FF); border: 1px solid #BFDBFE; border-radius: 1rem; padding: 1.5rem; display: flex; align-items: flex-start; gap: 1rem; margin-bottom: 1.5rem; }
        .summary-icon  { font-size: 1.8rem; min-width: 40px; }
        .summary-title { font-size: 1.1rem; font-weight: 900; color: #1E3A8A; margin: 0 0 6px; }
        .summary-text  { color: #334155; font-size: 0.9rem; margin: 0; line-height: 1.8; }
        .disclaimer { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 0.75rem; padding: 1rem 1.25rem; font-size: 0.8rem; color: #94A3B8; line-height: 1.7; margin-top: 1.5rem; }

        /* Privacy note */
        .privacy-note { text-align: center; color: #94A3B8; font-size: 0.8rem; margin-top: 0.5rem; }

        /* Buttons */
        .stButton > button { background: linear-gradient(135deg,#3B82F6,#2563EB) !important; color: white !important; border: none !important; border-radius: 10px !important; font-family: 'Cairo', sans-serif !important; font-weight: 700 !important; }
        hr { border: none; border-top: 1px solid #E2E8F0; margin: 2rem 0; }
        /* شريط الشات دايماً شفاف */
        div[data-testid="stBottom"],
        div[data-testid="stBottom"] > div {
            background: transparent !important;
            backdrop-filter: none !important;
            box-shadow: none !important;
            border: none !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 3. الهيدر ---
st.markdown("""
    <div class="main-header">
        <div class="header-logo">
            <div class="header-logo-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            </div>
            <span class="header-logo-text">تبيان الطبي</span>
        </div>
        <div class="header-badge">
            <div class="header-badge-dot"></div>
            <span class="header-badge-text">تحليل ذكي للتقارير الطبية</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 4. Hero ---
st.markdown("""
    <div class="hero-section">
        <div class="hero-badge">🤖 مدعوم بالذكاء الاصطناعي</div>
        <h1 class="hero-title">افهم نتائج تحاليلك بلغة عربية بسيطة</h1>
        <p style="font-size:1rem;color:#64748B;max-width:500px;margin:0 auto;line-height:1.8;text-align:center;">نحوّل المصطلحات الطبية المعقّدة إلى شرح واضح، مع توصيات دقيقة مدعومة بمراجع طبية موثوقة.</p>
    </div>
""", unsafe_allow_html=True)


# --- 5. الدوال --- 
@st.cache_resource
def load_tools():
    reader = easyocr.Reader(['en'], gpu=False)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if 'models/gemini-1.5-flash' in available_models:
            model_name = 'models/gemini-1.5-flash'
        elif 'models/gemini-pro' in available_models:
            model_name = 'models/gemini-pro'
        else:
            model_name = available_models[0]
    except:
        model_name = 'models/gemini-1.5-flash'
    print(f"✅ الموديل المختار: {model_name}")
    return reader, embeddings, genai.GenerativeModel(model_name)

reader, embeddings, model = load_tools()

# رد الشات بعد تحميل الموديل - run_rag 
print(f"DEBUG _chat_q = '{_chat_q}'")
if _chat_q and "chat_msgs" in st.session_state:
    if st.session_state.chat_msgs and st.session_state.chat_msgs[-1]["role"] == "user":
        try:
            # فلتر طبي
            strong_words = ["ألم","صداع","تعب","دوخة","حمى","سعال","غثيان","قيء","أعراض","ضغط","سكر","قلب","معدة","تنفس","التهاب","دواء","علاج"]
            weak_words = ["تحليل","دم","فيتامين","مختبر","نتائج","فحص","تشخيص","كوليسترول","حديد"]
            score = sum(0.6 for w in strong_words if w in _chat_q) + sum(0.3 for w in weak_words if w in _chat_q) + 0.5

            if score < 0.8:
                _ans = "هذا النظام مخصص للأسئلة الطبية فقط."
            else:
                # RAG
                context = ""
                try:
                    if os.path.exists(r'D:\Project\chroma_db'):
                        _db = Chroma(persist_directory=r'D:\Project\chroma_db', embedding_function=embeddings)
                        results = _db.similarity_search_with_relevance_scores(_chat_q, k=3)
                        filtered = [doc for doc, s in results if s >= 0.8]
                        if filtered:
                            context = "\n\n".join([d.page_content for d in filtered])
                            print("✅ تم استخدام RAG")
                except Exception as e:
                    print(f"RAG error: {e}")

                prompt = f"""
أنت مساعد طبي ذكي.

أجب على السؤال الطبي التالي بشكل واضح ومبسط.

إذا كانت الحالة مرتبطة بأعراض أو مشاكل صحية، يجب عليك في نهاية الإجابة إضافة قسم بعنوان:

"التحاليل المقترحة (إن وجدت):"

وتذكر التحاليل المناسبة التي قد يطلبها الطبيب حسب الحالة فقط (إن لزم الأمر).

إذا لم تكن هناك حاجة لتحاليل، لا تذكر هذا القسم.

{("السياق من المراجع:\\n" + context) if context else ""}

السؤال:
{_chat_q}
"""
                _ans = model.generate_content(prompt).text

            st.session_state.chat_msgs.append({"role":"bot","text":_ans})
        except Exception as e:
            st.session_state.chat_msgs.append({"role":"bot","text":f"حدث خطأ: {e}"})
        st.rerun()

def is_valid_test(name):
    ignore = ['page','id','patient','date','sex','age','mrn','doctor','physician','result','unit','range','validated','approved','Interpretation','Ref']
    name_l = str(name).lower()
    return not any(x in name_l for x in ignore) and len(str(name).strip()) > 1

def get_status_color(value, range_str):
    try:
        nums = re.findall(r"[-+]?\d*\.?\d+", str(range_str))
        val = float(value)
        if len(nums) >= 2:
            low, high = float(nums[0]), float(nums[1])
            if val < low or val > high:
                return "status-high", "badge-high", "خارج المعدل"
            return "status-normal", "badge-normal", "ممتاز"
    except:
        pass
    return "status-warning", "badge-warning", "تحليل القيمة"


# --- 6. Upload ---
uploaded_file = st.file_uploader("اسحب ملف التحليل هنا", type=['pdf','png','jpg','jpeg'])
st.markdown('<p class="privacy-note">🔒 ملفاتك محمية ولا تُحفظ على خوادمنا</p>', unsafe_allow_html=True)

if not uploaded_file:
    st.markdown("""
        <div class="feature-grid">
            <div class="feature-card"><div class="feature-icon-wrap">🔬</div><p class="feature-title">استخراج ذكي</p><p class="feature-text">يستخرج نتائج التحاليل تلقائياً من PDF أو صورة بدقة عالية.</p></div>
            <div class="feature-card"><div class="feature-icon-wrap">📚</div><p class="feature-title">مراجع طبية موثوقة</p><p class="feature-text">التقارير مدعومة بمراجع من قاعدة بياناتك الطبية المحلية.</p></div>
            <div class="feature-card"><div class="feature-icon-wrap">🛡️</div><p class="feature-title">خصوصية كاملة</p><p class="feature-text">بياناتك الطبية لا تُحفظ ولا تُشارك مع أي طرف خارجي.</p></div>
        </div>
    """, unsafe_allow_html=True)


# --- 7. المعالجة ---
if uploaded_file:
    with st.spinner("جاري استخراج البيانات الطبية..."):
        if uploaded_file.type == "application/pdf":
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            all_text = "\n".join([page.get_text() for page in doc])
        else:
            img = Image.open(uploaded_file)
            all_text = "\n".join(reader.readtext(np.array(img), detail=0))

    pattern = r"([a-zA-Z][a-zA-Z\s#%]{2,})\s+(\d+\.?\d*)\s+([\d\.]+\s*-\s*[\d\.]+)\s*([a-zA-Z0-9^/]+)?"
    findings = [f for f in re.findall(pattern, all_text) if is_valid_test(f[0])]

    if len(findings) < 2:
        with st.spinner("تنسيق غير تقليدي.. جاري الاستخراج بالذكاء الاصطناعي..."):
            extract_prompt = f"""حلل النص الطبي التالي واستخرج نتائج التحاليل.
النص: {all_text[:4000]}
أجب بتنسيق قائمة بايثون فقط: [('Test Name', 'Value', 'Range', 'Unit')]
لا تكتب أي مقدمات أو شرح، فقط القائمة."""
            try:
                ai_response = model.generate_content(extract_prompt)
                clean_text = ai_response.text.strip().replace("```python","").replace("```","")
                findings = eval(clean_text)
            except:
                pass

    if findings:
        abnormal = [f for f in findings if is_valid_test(f[0]) and get_status_color(f[1], f[2])[0] != "status-normal"]
        abnormal_names = "، ".join([f[0] for f in abnormal[:3]]) if abnormal else "لا توجد قيم خارج المعدل"

        st.markdown(f"""
            <div class="summary-banner">
                <div class="summary-icon">📋</div>
                <div>
                    <p class="summary-title">ملخّص نتائجك</p>
                    <p class="summary-text">تم تحليل <strong>{len(findings)}</strong> فحص طبي.
                    {'القيم التي تحتاج انتباهاً: <strong>' + abnormal_names + '</strong>.' if abnormal else '<strong>جميع القيم ضمن المعدل الطبيعي ✓</strong>'}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<p class="section-title">🔬 نتائج المختبر</p>', unsafe_allow_html=True)
        cols = st.columns(4)
        for i, (name, val, range_val, unit) in enumerate(findings):
            if not is_valid_test(name): continue
            status_class, badge_class, status_label = get_status_color(val, range_val)
            with cols[i % 4]:
                st.markdown(f"""
                    <div class="result-card {status_class}">
                        <div class="test-label">{str(name).strip().upper()}</div>
                        <div class="test-value">{val} <span class="test-unit">{unit}</span></div>
                        <span class="status-badge {badge_class}">{status_label}</span>
                        <div class="range-text">📏 المعدل: {range_val}</div>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<p class="section-title">📖 التقرير التحليلي المدعوم بالمراجع</p>', unsafe_allow_html=True)

        with st.spinner("جاري صياغة التقرير الطبي الموثق..."):
            context = ""
            try:
                if os.path.exists(r'D:\Project\chroma_db'):
                    db_rag = Chroma(persist_directory=r'D:\Project\chroma_db', embedding_function=embeddings)
                    docs = db_rag.similarity_search(f"Clinical pathology: {', '.join([f[0] for f in findings])}", k=4)
                    context_list = []
                    for idx, d in enumerate(docs, 1):
                        src = d.metadata.get('source','Unknown').split('\\')[-1]
                        pg = d.metadata.get('page','?')
                        context_list.append(f"[ref {idx}]: {src} p{pg}\n{d.page_content}")
                        print(f"ref: {src} (p{pg})")
                    context = "\n\n".join(context_list)
            except Exception as e:
                print(f"RAG error: {e}")

            site_prompt = (
                "أنت طبيب مختبر خبير. أرجع JSON فقط بدون أي نص خارجه. ابدأ بـ { مباشرة.\n"
                "لا HTML ولا markdown. نصوص عربية بسيطة فقط.\n\n"
                f"النتائج: {findings}\n"
                f"المراجع: {context if context else 'لا توجد مراجع'}\n\n"
                '{"تقييم_عام":"جملة أو جملتين عن الحالة العامة",'
                '"قيم_غير_طبيعية":[{"اسم_الفحص":"اسم","النتيجة":"قيمة","المعدل_الطبيعي":"مدى","الحالة":"مرتفع او منخفض","الشرح":"شرح طبي","المرجع":"مرجع او لا يوجد"}],'
                '"نصائح":["نصيحة1","نصيحة2","نصيحة3"]}'
            )

            try:
                import json
                raw = model.generate_content(site_prompt).text.strip()
                raw = raw.replace("```json","").replace("```","").strip()
                if '{' in raw:
                    raw = raw[raw.index('{'):raw.rindex('}')+1]
                report_data = json.loads(raw)

                st.markdown(f"""
                    <div style="background:white;border:1px solid #E2E8F0;border-radius:1rem;padding:1.5rem 1.8rem;margin-bottom:1.2rem;direction:rtl;text-align:right;font-family:'Cairo',sans-serif;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                            <div style="width:34px;height:34px;background:#EFF6FF;border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">📋</div>
                            <span style="font-weight:900;font-size:1rem;color:#0F172A;">التقييم العام للحالة</span>
                        </div>
                        <div style="height:1px;background:#F1F5F9;margin-bottom:12px;"></div>
                        <p style="margin:0;line-height:1.9;color:#475569;font-size:0.93rem;">{report_data.get("تقييم_عام","")}</p>
                    </div>
                """, unsafe_allow_html=True)

                abnormal_items = report_data.get("قيم_غير_طبيعية", [])
                if abnormal_items:
                    st.markdown('<p style="font-weight:900;font-size:1rem;color:#0F172A;margin:1.5rem 0 0.8rem;direction:rtl;text-align:right;">🔬 تفصيل القيم غير الطبيعية</p>', unsafe_allow_html=True)

                for item in abnormal_items:
                    حالة = item.get("الحالة","")
                    if "مرتفع" in حالة:
                        dot_color="#EF4444"; badge_bg="#FEE2E2"; badge_color="#991B1B"; badge_text="↑ مرتفع"; bar_color="#EF4444"; bar_pct=85
                    else:
                        dot_color="#F59E0B"; badge_bg="#FEF3C7"; badge_color="#92400E"; badge_text="↓ منخفض"; bar_color="#F59E0B"; bar_pct=18
                    مرجع = item.get("المرجع","")
                    مرجع_html = f'<div style="display:flex;align-items:center;gap:8px;margin-top:12px;padding-top:12px;border-top:1px solid #F1F5F9;"><div style="width:20px;height:20px;background:#EFF6FF;border-radius:5px;display:flex;align-items:center;justify-content:center;font-size:0.65rem;flex-shrink:0;">📖</div><span style="font-size:0.78rem;color:#94A3B8;line-height:1.6;">{مرجع}</span></div>' if مرجع else ""
                    st.markdown(f"""
                        <div style="background:white;border:1px solid #E2E8F0;border-radius:1rem;padding:1.3rem 1.6rem;margin-bottom:0.85rem;direction:rtl;text-align:right;font-family:'Cairo',sans-serif;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                            <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;margin-bottom:10px;">
                                <h3 style="margin:0;font-size:0.95rem;font-weight:900;color:#0F172A;">{item.get("اسم_الفحص","")}</h3>
                                <span style="display:inline-flex;align-items:center;gap:5px;background:{badge_bg};color:{badge_color};border-radius:6px;padding:3px 10px;font-size:0.75rem;font-weight:800;">
                                    <span style="width:6px;height:6px;border-radius:50%;background:{dot_color};display:inline-block;"></span>{badge_text}
                                </span>
                            </div>
                            <div style="display:flex;gap:8px;margin-bottom:10px;">
                                <div style="background:#F8FAFC;border-radius:6px;padding:4px 10px;font-size:0.78rem;"><span style="color:#94A3B8;">القيمة </span><strong style="color:#0F172A;">{item.get("النتيجة","")}</strong></div>
                                <div style="background:#F8FAFC;border-radius:6px;padding:4px 10px;font-size:0.78rem;"><span style="color:#94A3B8;">المعدل </span><strong style="color:#0F172A;">{item.get("المعدل_الطبيعي","")}</strong></div>
                            </div>
                            <div style="height:4px;background:#F1F5F9;border-radius:99px;margin-bottom:12px;overflow:hidden;">
                                <div style="height:100%;width:{bar_pct}%;background:{bar_color};border-radius:99px;"></div>
                            </div>
                            <p style="margin:0;line-height:1.85;color:#475569;font-size:0.88rem;">{item.get("الشرح","")}</p>
                            {مرجع_html}
                        </div>
                    """, unsafe_allow_html=True)

                نصائح = report_data.get("نصائح", [])
                if نصائح:
                    نصائح_html = "".join([f'<div style="display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-bottom:1px solid #F1F5F9;"><div style="width:20px;height:20px;background:#DCFCE7;border-radius:5px;display:flex;align-items:center;justify-content:center;font-size:0.7rem;color:#15803D;flex-shrink:0;margin-top:2px;">✓</div><span style="line-height:1.8;color:#475569;font-size:0.88rem;">{n}</span></div>' for n in نصائح])
                    st.markdown(f"""
                        <div style="background:white;border:1px solid #E2E8F0;border-radius:1rem;padding:1.3rem 1.6rem;margin-top:0.5rem;direction:rtl;text-align:right;font-family:'Cairo',sans-serif;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                            <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
                                <div style="width:34px;height:34px;background:#F0FDF4;border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">💡</div>
                                <span style="font-weight:900;font-size:1rem;color:#0F172A;">نصائح طبية مقترحة</span>
                            </div>
                            {نصائح_html}
                        </div>
                    """, unsafe_allow_html=True)

            except Exception as e:
                st.error("فشل التواصل مع Gemini")
                print(f"ERROR: {e}")

            try:
                import time
                time.sleep(20)
                audit_prompt = f"تقرير فجوات البيانات للمطورة: النتائج {findings}, المراجع {context[:500]}"
                audit_resp = model.generate_content(audit_prompt)
                print("\n=== DATA GAP REPORT ===")
                print(audit_resp.text)
            except Exception as e:
                print(f"AUDIT ERROR: {e}")

        st.markdown("""
            <div class="disclaimer">⚕️ <strong>إخلاء مسؤولية:</strong> هذا التقرير للتوعية الصحية فقط ولا يُعتبر بديلاً عن استشارة الطبيب المختص.</div>
        """, unsafe_allow_html=True)

    else:
        st.markdown("""
            <div class="summary-banner" style="border-color:#FCA5A5;background:linear-gradient(135deg,#FEF2F2,#FFF5F5);">
                <div class="summary-icon">⚠️</div>
                <div><p class="summary-title" style="color:#991B1B;">لم يتم العثور على نتائج</p>
                <p class="summary-text">تأكد أن الملف يحتوي على نتائج تحاليل طبية واضحة وحاول مرة أخرى.</p></div>
            </div>
        """, unsafe_allow_html=True)


# ===== CHATBOT =====
from sklearn.metrics.pairwise import cosine_similarity

@st.cache_resource
def load_chat_db():
    from langchain_community.vectorstores import Chroma as ChromaDB
    emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    try:
        db = ChromaDB(persist_directory=r'D:\Project\chroma_db', embedding_function=emb)
        return emb, db
    except:
        return emb, None

def is_medical(query):
    words = ["ألم","صداع","تعب","دوخة","حمى","سعال","أعراض","ضغط","سكر","قلب","معدة","تنفس","التهاب","دواء","علاج","تحليل","دم","فيتامين","نتائج","فحص","تشخيص","كوليسترول","حديد","مختبر","هيموجلوبين","خلايا"]
    return any(w in query for w in words)

def run_chat(query):
    if not is_medical(query):
        return "هذا النظام مخصص للأسئلة الطبية فقط."
    _, chat_db = load_chat_db()
    context = ""
    used_rag = False
    if chat_db:
        try:
            results = chat_db.similarity_search_with_relevance_scores(query, k=3)
            filtered = [doc for doc, score in results if score >= 0.8]
            if filtered:
                context = "\n\n".join([d.page_content for d in filtered])
                used_rag = True
        except:
            pass
    prompt = f"""أنت مساعد طبي ذكي.

أجب على السؤال الطبي التالي بشكل واضح ومبسط.

إذا كانت الحالة مرتبطة بأعراض أو مشاكل صحية، يجب عليك في نهاية الإجابة إضافة قسم بعنوان:

"التحاليل المقترحة (إن وجدت):"

وتذكر التحاليل المناسبة التي قد يطلبها الطبيب حسب الحالة فقط (إن لزم الأمر).

إذا لم تكن هناك حاجة لتحاليل، لا تذكر هذا القسم.

{("السياق من المراجع:\n" + context) if context else ""}

السؤال:
{query}
"""
    try:
        response = model.generate_content(prompt).text
        if not used_rag:
            response += "\n\n🤖 *هذه الإجابة من Gemini AI*"
        return response
    except Exception as e:
        return f"حدث خطأ: {e}"

# تهيئة الشات
if "chat_msgs" not in st.session_state:
    st.session_state.chat_msgs = [{"role":"bot","text":"مرحباً! أنا مساعدك الطبي الذكي 🩺\nاسألني عن أي تحليل أو حالة صحية."}]
if "chat_open" not in st.session_state:
    st.session_state.chat_open = False

import html as html_lib
import streamlit.components.v1 as components

if "chat_msgs" not in st.session_state:
    st.session_state.chat_msgs = [{"role":"bot","text":"مرحباً! اسألني عن أي تحليل أو حالة صحية 🩺"}]

# إخفاء الشات لما يكون فيه ملف مرفوع
if uploaded_file:
    st.markdown("""<style>
    div[data-testid="stCustomComponentV1"] { opacity:0 !important; pointer-events:none !important; }
    </style>""", unsafe_allow_html=True)

def format_chat_text(text):
    safe = html_lib.escape(str(text))
    safe = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', safe)
    safe = re.sub(r'\*(.+?)\*', r'<em>\1</em>', safe)
    lines = safe.split('\n')
    result_lines = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if re.match(r'^[-•]\s+.+', stripped):
            if not in_list:
                result_lines.append('<ul style="margin:4px 0;padding-right:18px;list-style:disc;">')
                in_list = True
            item_text = re.sub(r'^[-•]\s+', '', stripped)
            result_lines.append(f'<li style="margin:3px 0;">{item_text}</li>')
        else:
            if in_list:
                result_lines.append('</ul>')
                in_list = False
            result_lines.append(line)
    if in_list:
        result_lines.append('</ul>')
    return '<br>'.join(result_lines)

msgs_html = ""
for msg in st.session_state.chat_msgs:
    txt = format_chat_text(msg["text"])
    if msg["role"] == "bot":
        msgs_html += f'<div class="msg-bot">{txt}</div>'
    else:
        msgs_html += f'<div class="msg-user">{txt}</div>'

chat_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:Cairo,sans-serif;}}
html,body{{background:transparent;overflow:hidden;width:100%;height:100%;}}
.fab{{
    position:fixed;bottom:16px;right:16px;
    width:52px;height:52px;
    background:linear-gradient(135deg,#3B82F6,#2563EB);
    border-radius:50%;border:none;cursor:pointer;
    box-shadow:0 4px 16px rgba(59,130,246,0.45);
    font-size:20px;color:white;
    display:flex;align-items:center;justify-content:center;
    z-index:99;
}}
.win{{
    position:fixed;bottom:78px;right:16px;
    width:300px;height:400px;
    background:white;border-radius:14px;
    box-shadow:0 8px 32px rgba(0,0,0,0.18);
    display:none;flex-direction:column;
    border:1px solid #E2E8F0;overflow:hidden;
    direction:rtl;z-index:98;
}}
.win.open{{display:flex;}}
.head{{
    background:linear-gradient(135deg,#3B82F6,#2563EB);
    padding:11px 14px;display:flex;
    justify-content:space-between;align-items:center;
    flex-shrink:0;
}}
.head-t{{color:white;font-weight:900;font-size:13px;}}
.head-s{{color:rgba(255,255,255,0.8);font-size:10px;}}
.x-btn{{
    background:rgba(255,255,255,0.2);border:none;color:white;
    width:22px;height:22px;border-radius:50%;cursor:pointer;font-size:12px;
    display:flex;align-items:center;justify-content:center;
}}
.body{{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:7px;}}
.msg-bot{{background:#F1F5F9;color:#334155;border-radius:3px 11px 11px 11px;padding:8px 11px;font-size:12px;line-height:1.6;max-width:85%;align-self:flex-end;word-break:break-word;}}
.msg-user{{background:#3B82F6;color:white;border-radius:11px 3px 11px 11px;padding:8px 11px;font-size:12px;line-height:1.6;max-width:85%;align-self:flex-start;word-break:break-word;}}
.inp{{padding:9px 10px;border-top:1px solid #E2E8F0;display:flex;gap:7px;background:#F8FAFC;flex-shrink:0;}}
.inp input{{flex:1;border:1px solid #E2E8F0;border-radius:8px;padding:7px 10px;font-size:12px;outline:none;direction:rtl;font-family:Cairo,sans-serif;}}
.inp button{{background:#3B82F6;color:white;border:none;border-radius:8px;padding:7px 12px;font-weight:700;cursor:pointer;font-size:12px;font-family:Cairo,sans-serif;}}
</style></head><body>

<button class="fab" onclick="toggleWin()">💬</button>

<div class="win" id="win">
    <div class="head">
        <div>
            <div class="head-t">🩺 المساعد الطبي</div>
            <div class="head-s">مدعوم بالذكاء الاصطناعي</div>
        </div>
        <button class="x-btn" onclick="toggleWin()">✕</button>
    </div>
    <div class="body" id="body">{msgs_html}</div>
    <div class="inp">
        <input id="inp" type="text" placeholder="اكتب سؤالك الطبي..." onkeydown="if(event.key==='Enter')send()"/>
        <button onclick="send()">إرسال</button>
    </div>
</div>

<script>
function toggleWin(){{
    var w=document.getElementById("win");
    w.classList.toggle("open");
    sc();
}}
function sc(){{
    var b=document.getElementById("body");
    if(b) setTimeout(function(){{b.scrollTop=b.scrollHeight;}},50);
}}
function send(){{
    var inp=document.getElementById("inp");
    var v=inp.value.trim();
    if(!v) return;
    inp.value="";
    var b=document.getElementById("body");
    var u=document.createElement("div");
    u.className="msg-user";u.textContent=v;b.appendChild(u);
    var l=document.createElement("div");
    l.className="msg-bot";l.innerHTML="⏳ جاري التفكير...";
    b.appendChild(l);sc();
    // نكتب في hidden textarea ونضغط زر مخفي
    var ta=window.parent.document.querySelector("textarea[data-testid='stChatInputTextArea']");
    if(ta){{
        var nativeSetter=Object.getOwnPropertyDescriptor(window.parent.HTMLTextAreaElement.prototype,"value").set;
        nativeSetter.call(ta,v);
        ta.dispatchEvent(new Event("input",{{bubbles:true}}));
        setTimeout(function(){{
            var btn=window.parent.document.querySelector("button[data-testid='stChatInputSubmitButton']");
            if(btn) btn.click();
        }},200);
    }}
}}
sc();
</script>
</body></html>"""

components.html(chat_html, height=520, scrolling=False)

# st.chat_input شفاف - يشتغل بس مو مرئي
st.markdown("""<style>
div[data-testid="stBottom"] {
    background: transparent !important;
    backdrop-filter: none !important;
}
div[data-testid="stBottom"] > div {
    background: transparent !important;
}
div[data-testid="stChatInput"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    opacity: 0 !important;
}
div[data-testid="stChatInput"] * {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: transparent !important;
}
</style>""", unsafe_allow_html=True)

user_q = st.chat_input("سؤال")
if user_q:
    st.session_state.chat_msgs.append({"role":"user","text":user_q})
    try:
        strong_words = ["ألم","صداع","تعب","دوخة","حمى","سعال","غثيان","قيء","أعراض","ضغط","سكر","قلب","معدة","تنفس","التهاب","دواء","علاج"]
        weak_words = ["تحليل","دم","فيتامين","مختبر","نتائج","فحص","تشخيص","كوليسترول","حديد"]
        score = sum(0.6 for w in strong_words if w in user_q) + sum(0.3 for w in weak_words if w in user_q) + 0.5
        if score < 0.8:
            ans = "هذا النظام مخصص للأسئلة الطبية فقط."
        else:
            context = ""
            try:
                if os.path.exists(r'D:\Project\chroma_db'):
                    _db = Chroma(persist_directory=r'D:\Project\chroma_db', embedding_function=embeddings)
                    results = _db.similarity_search_with_relevance_scores(user_q, k=3)
                    filtered = [doc for doc, s in results if s >= 0.8]
                    if filtered:
                        context = "\n\n".join([d.page_content for d in filtered])
            except Exception as e:
                print(f"RAG error: {e}")
            prompt = f"""أنت مساعد طبي ذكي.

أجب على السؤال الطبي التالي بشكل واضح ومبسط.

إذا كانت الحالة مرتبطة بأعراض أو مشاكل صحية، يجب عليك في نهاية الإجابة إضافة قسم بعنوان:

"التحاليل المقترحه:"

وتذكر التحاليل المناسبة التي قد يطلبها الطبيب حسب الحالة فقط (إن لزم الأمر).

إذا لم تكن هناك حاجة لتحاليل، لا تذكر هذا القسم.

{("السياق من المراجع:\n" + context) if context else ""}

السؤال:
{user_q}"""
            ans = model.generate_content(prompt).text
    except Exception as e:
        ans = f"حدث خطأ: {e}"
    st.session_state.chat_msgs.append({"role":"bot","text":ans})
    st.rerun()
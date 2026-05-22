import streamlit as st

# --- إعدادات الصفحة ---
st.set_page_config(page_title="تبيان الطبي", layout="wide", initial_sidebar_state="collapsed")

# --- محرك التصميم (CSS & HTML) لنسخ فيجما ---
st.markdown(f"""
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap" rel="stylesheet">
    <style>
        /* إخفاء واجهة ستريمليت الافتراضية بالكامل */
        header, footer, #MainMenu {{visibility: hidden;}}
        .stApp {{ background-color: #FFFFFF; }}
        * {{ font-family: 'Tajawal', sans-serif; direction: rtl; }}

        /* الشريط العلوي (Navbar) - لقطة 724 */
        .nav-container {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 20px 8%; background: white; border-bottom: 1px solid #F1F5F9;
            position: sticky; top: 0; z-index: 1000;
        }}
        .nav-links {{ display: flex; gap: 40px; font-weight: 500; color: #64748B; }}
        .nav-active {{ color: #3B82F6; font-weight: 700; border-bottom: 3px solid #3B82F6; padding-bottom: 5px; }}
        .logo {{ color: #3B82F6; font-size: 2rem; font-weight: 800; }}

        /* قسم النتائج (Grid) - لقطة 725 */
        .results-header {{ text-align: center; margin: 50px 0 30px; }}
        .results-header h1 {{ color: #1E293B; font-weight: 800; font-size: 2.5rem; }}
        
        .cards-wrapper {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 25px; padding: 0 8%; margin-bottom: 50px;
        }}
        
        .custom-card {{
            border-radius: 28px; padding: 30px; border-width: 2px; border-style: solid;
            box-shadow: 0 10px 25px rgba(0,0,0,0.03); transition: transform 0.2s;
        }}
        .custom-card:hover {{ transform: translateY(-5px); }}
        
        /* الألوان الدقيقة من تصميمك */
        .card-green {{ background: #F0FDF4; border-color: #10B981; color: #064E3B; }}
        .card-yellow {{ background: #FFFBEB; border-color: #F59E0B; color: #78350F; }}
        .card-red {{ background: #FEF2F2; border-color: #EF4444; color: #7F1D1D; }}

        .card-label {{ font-size: 1.1rem; font-weight: 600; opacity: 0.8; }}
        .card-value {{ font-size: 2.8rem; font-weight: 800; margin: 15px 0; }}
        .card-status {{ 
            display: inline-block; padding: 6px 18px; border-radius: 50px; 
            background: white; font-weight: 700; font-size: 0.9rem;
        }}

        /* قسم التوصيات (Checklist) - لقطة 728 */
        .rec-container {{
            background: #F8FAFC; border-radius: 35px; padding: 45px;
            margin: 20px 8% 100px; border: 1px solid #E2E8F0;
        }}
        .rec-title {{ color: #1E293B; font-weight: 800; font-size: 1.8rem; margin-bottom: 10px; }}
        .rec-desc {{ color: #64748B; margin-bottom: 35px; }}

        .rec-item {{
            background: white; border: 1px solid #E2E8F0; border-radius: 20px;
            padding: 22px; margin-bottom: 15px; display: flex; align-items: center; gap: 20px;
        }}
        .circle-check {{ 
            width: 28px; height: 28px; border-radius: 50%; border: 2px solid #3B82F6; 
            display: flex; align-items: center; justify-content: center;
        }}
        .circle-check::after {{ content: '✓'; color: #3B82F6; font-weight: bold; }}
        .rec-text {{ font-weight: 700; color: #1E293B; font-size: 1.1rem; }}
        .rec-source {{ font-size: 0.85rem; color: #3B82F6; margin-top: 4px; }}
    </style>
""", unsafe_allow_html=True)

# --- 1. الهيدر (Navbar) ---
st.markdown("""
    <div class="nav-container">
        <div class="nav-links">
            <span>عن الخدمة</span>
            <span class="nav-active">النتائج</span>
            <span>رفع التحاليل</span>
        </div>
        <div class="logo">تبيان الطبي</div>
    </div>
""", unsafe_allow_html=True)

# --- 2. عرض النتائج (Grid) ---
st.markdown('<div class="results-header"><h1>نتائج التحليل</h1></div>', unsafe_allow_html=True)

# محاكاة لبيانات التحليل (هنا نربطها بمخرجات الـ OCR لاحقاً)
data = [
    {"name": "سكر الدم", "val": "95", "unit": "mg/dL", "status": "طبيعي", "type": "card-green"},
    {"name": "فيتامين د", "val": "18.5", "unit": "ng/mL", "status": "يحتاج متابعة", "type": "card-yellow"},
    {"name": "الهيموغلوبين", "val": "11.2", "unit": "g/dL", "status": "يحتاج علاج", "type": "card-red"}
]

st.markdown('<div class="cards-wrapper">', unsafe_allow_html=True)
cols = st.columns(3)
for i, item in enumerate(data):
    with cols[i]:
        st.markdown(f"""
            <div class="custom-card {item['type']}">
                <div class="card-label">{item['name']}</div>
                <div class="card-value">{item['val']} <span style="font-size:1rem;">{item['unit']}</span></div>
                <div class="card-status">{item['status']}</div>
            </div>
        """, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- 3. قسم التوصيات (Checklist) ---
st.markdown("""
    <div class="rec-container">
        <div class="rec-title">توصيات (غذائية وسلوكية)</div>
        <div class="rec-desc">اتبع هذه الخطوات بناءً على نتائج مريضتنا رغد السبيعي لضمان أفضل صحة</div>
        
        <div class="rec-item">
            <div class="circle-check"></div>
            <div>
                <div class="rec-text">تناول اللحوم الحمراء والسبانخ والعدس 3 مرات أسبوعياً</div>
                <div class="rec-source">المصدر: منظمة الصحة العالمية (WHO)</div>
            </div>
        </div>
        
        <div class="rec-item">
            <div class="circle-check"></div>
            <div>
                <div class="rec-text">التعرض لأشعة الشمس 15-20 دقيقة يومياً في الصباح الباكر</div>
                <div class="rec-source">المصدر: جمعية الغذاء والدواء الأمريكية (FDA)</div>
            </div>
        </div>

        <div class="rec-item">
            <div class="circle-check"></div>
            <div>
                <div class="rec-text">شرب لترين من الماء يومياً لتحسين كفاءة التحليل القادم</div>
                <div class="rec-source">المصدر: وزارة الصحة</div>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)
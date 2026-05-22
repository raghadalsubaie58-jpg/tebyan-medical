import os, json
from dotenv import load_dotenv
load_dotenv(dotenv_path=r'D:\Project\.env')
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['HF_HOME'] = r'D:\Project\model_cache'
from groq import Groq

groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))

prompt = (
    "انت خبير طبي. اكتب JSON فقط بالعربية عن تحليل الهيموجلوبين hemoglobin. "
    "المعدل الطبيعي: ذكر 13.5-17.5 g/dL, انثى 12-15.5 g/dL. "
    'اجب بهذا التنسيق حرفيا: {"definition":"...","normal_values":"...","abnormal_causes":"...","symptoms_tips":"..."}'
)

r = groq_client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.2,
    max_tokens=1000,
)
raw = r.choices[0].message.content.strip()
print("RAW len:", len(raw))
print("FIRST 200:", raw[:200])

try:
    start = raw.index('{')
    end   = raw.rindex('}') + 1
    data  = json.loads(raw[start:end])
    print("Keys:", list(data.keys()))
    print("SUCCESS")
except Exception as e:
    print("PARSE ERROR:", e)

"""
M7 — RAGAS-light: تقييم جودة الـ RAG بدون OpenAI
يستخدم Groq بدلاً منه للحفاظ على المجانية
"""
import os
import json
from dotenv import load_dotenv
load_dotenv(dotenv_path=r'D:\Project\.env')
os.environ['HF_HOME'] = r'D:\Project\model_cache'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

from groq import Groq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

GROQ_API_KEY  = os.getenv("GROQ_API_KEY")
EMBED_MODEL   = "intfloat/multilingual-e5-large"
GROQ_MODEL    = "llama-3.1-8b-instant"
DB_PATH       = r'D:\Project\chroma_db'

TEST_QUESTIONS = [
    {"q": "ما هي القيم الطبيعية للهيموجلوبين؟",    "ref": "رجال 13.5-17.5 g/dL نساء 12-15.5 g/dL"},
    {"q": "ماذا يعني ارتفاع الكوليسترول LDL؟",     "ref": "خطر تصلب الشرايين وأمراض القلب"},
    {"q": "ما أعراض نقص فيتامين د؟",               "ref": "آلام العظام وضعف العضلات وضعف المناعة"},
    {"q": "كيف أخفض سكر الدم طبيعياً؟",            "ref": "الرياضة والغذاء الصحي وتقليل النشويات"},
    {"q": "ما سبب ارتفاع إنزيمات الكبد ALT AST؟",  "ref": "التهاب الكبد الكبد الدهني الكحول"},
    {"q": "ما القيم الطبيعية للكرياتينين؟",         "ref": "رجال 0.74-1.35 نساء 0.59-1.04 mg/dL"},
    {"q": "ما أسباب انخفاض خلايا الدم البيضاء؟",   "ref": "أمراض المناعة العلاج الكيميائي أمراض النخاع"},
    {"q": "ما معنى ارتفاع TSH؟",                    "ref": "قصور الغدة الدرقية الغدة خاملة"},
]


def get_rag_answer(client, db, question: str) -> tuple[str, str]:
    results = db.similarity_search_with_relevance_scores(question, k=5)
    filtered = [(d, s) for d, s in results if s >= 0.4]
    context  = "\n\n".join([d.page_content for d, _ in filtered[:3]])

    messages = [
        {"role": "system", "content": "أنت مساعد طبي. أجب باختصار بالعربية مستنداً للسياق."},
        {"role": "user",   "content": f"السياق:\n{context}\n\nالسؤال: {question}"},
    ]
    r = client.chat.completions.create(
        model=GROQ_MODEL, messages=messages, temperature=0.1, max_tokens=300
    )
    return r.choices[0].message.content, context


def evaluate_single(client, answer: str, context: str, question: str, reference: str) -> dict:
    prompt = f"""قيّم الإجابة التالية بدقة. أجب بـ JSON فقط بهذا الشكل:
{{"faithfulness": X, "answer_relevance": X, "context_precision": X, "notes": "..."}}

حيث القيم من 0.0 إلى 1.0:
- faithfulness: هل الإجابة مبنية على السياق المعطى؟
- answer_relevance: هل الإجابة تجيب على السؤال؟
- context_precision: هل السياق يحتوي على معلومات مفيدة؟

السؤال: {question}
المرجع: {reference}
السياق: {context[:1000] if context else 'لا يوجد سياق'}
الإجابة: {answer[:500]}"""

    try:
        r = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0, max_tokens=200,
        )
        raw = r.choices[0].message.content.strip()
        if '{' in raw:
            raw = raw[raw.index('{'):raw.rindex('}') + 1]
        return json.loads(raw)
    except Exception as e:
        return {"faithfulness": 0, "answer_relevance": 0, "context_precision": 0, "notes": str(e)}


def run_evaluation():
    print("=" * 60)
    print("M7 — RAGAS-light Evaluation")
    print("=" * 60)

    client = Groq(api_key=GROQ_API_KEY)
    embed  = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    db     = Chroma(persist_directory=DB_PATH, embedding_function=embed)
    print(f"[DB] {db._collection.count()} chunks loaded\n")

    results  = []
    totals   = {"faithfulness": 0, "answer_relevance": 0, "context_precision": 0}

    for i, item in enumerate(TEST_QUESTIONS, 1):
        print(f"[{i}/{len(TEST_QUESTIONS)}] {item['q'][:50]}...")
        answer, context = get_rag_answer(client, db, item["q"])
        metrics = evaluate_single(client, answer, context, item["q"], item["ref"])

        for k in totals:
            totals[k] += metrics.get(k, 0)

        results.append({
            "question": item["q"],
            "answer":   answer[:150],
            "metrics":  metrics,
        })
        print(f"  faithfulness={metrics.get('faithfulness', 0):.2f} "
              f"| relevance={metrics.get('answer_relevance', 0):.2f} "
              f"| precision={metrics.get('context_precision', 0):.2f}")

    n = len(TEST_QUESTIONS)
    print("\n" + "=" * 60)
    print("النتائج الكلية:")
    print(f"  Faithfulness (أمانة الإجابة):  {totals['faithfulness']/n:.2%}")
    print(f"  Answer Relevance (صلة الإجابة): {totals['answer_relevance']/n:.2%}")
    print(f"  Context Precision (دقة السياق): {totals['context_precision']/n:.2%}")
    print(f"  المتوسط العام:                  {sum(totals.values())/(n*3):.2%}")
    print("=" * 60)

    with open("eval_results.json", "w", encoding="utf-8") as f:
        json.dump({"summary": {k: round(v/n, 3) for k, v in totals.items()}, "details": results}, f, ensure_ascii=False, indent=2)
    print("\nحُفظت النتائج في eval_results.json")


if __name__ == "__main__":
    run_evaluation()

"""
M7 — RAGAS-light: تقييم جودة الـ RAG بدون OpenAI
يستخدم Groq بدلاً منه — pgvector + SemanticSearchService
"""
import os
import json
from dotenv import load_dotenv
load_dotenv(dotenv_path=r'D:\Project\.env')
os.environ.setdefault('HF_HOME', r'D:\Project\model_cache')
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

from groq import Groq
from services.search.semantic_search import SemanticSearchService
from services.rag.retriever import Retriever, RetrievalConfig
from services.rag.context_builder import build_context

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROQ_MODEL   = "llama-3.1-8b-instant"

TEST_QUESTIONS = [
    {"q": "ما هي القيم الطبيعية للهيموجلوبين؟",    "ref": "رجال 13.5-17.5 g/dL نساء 12-15.5 g/dL"},
    {"q": "ماذا يعني ارتفاع الكوليسترول LDL؟",     "ref": "خطر تصلب الشرايين وأمراض القلب"},
    {"q": "ما أعراض نقص فيتامين د؟",               "ref": "آلام العظام وضعف العضلات وضعف المناعة"},
    {"q": "كيف أخفض سكر الدم طبيعياً؟",            "ref": "الرياضة والغذاء الصحي وتقليل النشويات"},
    {"q": "ما سبب ارتفاع إنزيمات الكبد ALT AST؟",  "ref": "التهاب الكبد الكبد الدهني الكحول"},
    {"q": "ما القيم الطبيعية للكرياتينين؟",         "ref": "رجال 0.7-1.3 نساء 0.5-1.1 mg/dL"},
    {"q": "ما أسباب انخفاض خلايا الدم البيضاء؟",   "ref": "أمراض المناعة العلاج الكيميائي أمراض النخاع"},
    {"q": "ما معنى ارتفاع TSH؟",                    "ref": "قصور الغدة الدرقية الغدة خاملة"},
    {"q": "ما أسباب ارتفاع الدهون الثلاثية؟",      "ref": "السكر والكربوهيدرات والسمنة والخمول"},
    {"q": "ما معنى انخفاض eGFR؟",                   "ref": "ضعف وظيفة الكلى ومرض الكلى المزمن"},
]


def get_rag_answer(groq_client: Groq, retriever: Retriever, question: str) -> tuple[str, str]:
    results, _ = retriever.retrieve(question, RetrievalConfig(k=8, top_n=4, use_multi_query=False))
    context    = build_context(results, max_tokens=1200)

    messages = [
        {"role": "system", "content": "أنت مساعد طبي دقيق. أجب باختصار بالعربية مستنداً فقط للسياق المعطى."},
        {"role": "user",   "content": f"السياق:\n{context}\n\nالسؤال: {question}"},
    ]
    r = groq_client.chat.completions.create(
        model=GROQ_MODEL, messages=messages, temperature=0.1, max_tokens=300
    )
    return r.choices[0].message.content, context


def evaluate_single(groq_client: Groq, answer: str, context: str, question: str, reference: str) -> dict:
    prompt = f"""قيّم الإجابة التالية بدقة. أجب بـ JSON فقط بهذا الشكل:
{{"faithfulness": X, "answer_relevance": X, "context_precision": X, "notes": "..."}}

القيم من 0.0 إلى 1.0:
- faithfulness: هل الإجابة مبنية فعلاً على السياق المعطى؟
- answer_relevance: هل الإجابة تجيب على السؤال بشكل مباشر؟
- context_precision: هل السياق يحتوي معلومات مفيدة للسؤال؟

السؤال: {question}
المرجع: {reference}
السياق: {context[:1000] if context else 'لا يوجد سياق'}
الإجابة: {answer[:500]}"""

    try:
        r = groq_client.chat.completions.create(
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
    print("RAGAS-light Evaluation | pgvector + Groq")
    print("=" * 60)

    groq_client = Groq(api_key=GROQ_API_KEY)
    search_svc  = SemanticSearchService(SUPABASE_URL, SUPABASE_KEY)
    retriever   = Retriever(search_svc)

    total_chunks = search_svc.count()
    print(f"[DB] {total_chunks} chunks in pgvector\n")

    results = []
    totals  = {"faithfulness": 0.0, "answer_relevance": 0.0, "context_precision": 0.0}

    for i, item in enumerate(TEST_QUESTIONS, 1):
        print(f"[{i}/{len(TEST_QUESTIONS)}] {item['q'][:55]}...")
        answer, context = get_rag_answer(groq_client, retriever, item["q"])
        metrics = evaluate_single(groq_client, answer, context, item["q"], item["ref"])

        for k in totals:
            totals[k] += metrics.get(k, 0)

        results.append({
            "question": item["q"],
            "answer":   answer[:200],
            "metrics":  metrics,
        })
        print(f"  faithfulness={metrics.get('faithfulness', 0):.2f} "
              f"| relevance={metrics.get('answer_relevance', 0):.2f} "
              f"| precision={metrics.get('context_precision', 0):.2f}"
              f"  — {metrics.get('notes', '')[:60]}")

    n = len(TEST_QUESTIONS)
    avg_f   = totals['faithfulness']    / n
    avg_r   = totals['answer_relevance'] / n
    avg_p   = totals['context_precision'] / n
    overall = (avg_f + avg_r + avg_p) / 3

    print("\n" + "=" * 60)
    print("النتائج الكلية:")
    print(f"  Faithfulness  (امانة الإجابة):  {avg_f:.1%}")
    print(f"  Answer Relevance (صلة الإجابة): {avg_r:.1%}")
    print(f"  Context Precision (دقة السياق): {avg_p:.1%}")
    print(f"  المتوسط العام:                  {overall:.1%}")
    print("=" * 60)

    summary = {
        "faithfulness":     round(avg_f, 3),
        "answer_relevance": round(avg_r, 3),
        "context_precision":round(avg_p, 3),
        "overall":          round(overall, 3),
        "total_chunks":     total_chunks,
        "questions_tested": n,
    }
    output = {"summary": summary, "details": results}

    with open("eval_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("Results saved to eval_results.json")
    return summary


if __name__ == "__main__":
    run_evaluation()

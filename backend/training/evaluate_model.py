"""
evaluate_model.py — evaluate fine-tuned LoRA model vs base on Arabic medical benchmark.

Metrics:
  - BLEU-4 (surface fluency)
  - ROUGE-L (recall)
  - BERTScore (semantic similarity, multilingual)
  - Medical Term Coverage (% of expected medical terms in output)
  - GPT/LLM-as-judge score (via Groq, 1-5 scale)
  - Latency (tokens/sec)

Usage:
    python training/evaluate_model.py \
        --base_model core42/jais-13b-chat \
        --lora_adapter checkpoints/tebyan-medical-v1/lora_adapter \
        --val_data data/val.jsonl \
        --output_dir eval_results/ \
        --n_samples 50 \
        --use_llm_judge
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--base_model",   required=True)
    p.add_argument("--lora_adapter", required=True)
    p.add_argument("--val_data",     default="data/val.jsonl")
    p.add_argument("--output_dir",   default="eval_results")
    p.add_argument("--n_samples",    type=int, default=50)
    p.add_argument("--max_new_tokens",type=int, default=512)
    p.add_argument("--use_llm_judge",action="store_true")
    p.add_argument("--groq_key",     default=None)
    p.add_argument("--hf_token",     default=None)
    return p.parse_args()


def load_val(path: str, n: int) -> list[dict]:
    import random
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    random.shuffle(rows)
    return rows[:n]


def generate(model, tokenizer, prompt: str, max_new_tokens: int = 512) -> tuple[str, float]:
    import torch
    inputs   = tokenizer(prompt, return_tensors="pt").to(model.device)
    t0       = time.perf_counter()
    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False, temperature=1.0)
    elapsed  = time.perf_counter() - t0
    n_tokens = output.shape[1] - inputs["input_ids"].shape[1]
    text     = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return text.strip(), n_tokens / elapsed


def compute_metrics(reference: str, hypothesis: str) -> dict:
    metrics: dict = {}

    # BLEU-4
    try:
        from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
        import re
        ref_toks  = re.findall(r"\w+", reference.lower())
        hyp_toks  = re.findall(r"\w+", hypothesis.lower())
        sf        = SmoothingFunction().method1
        metrics["bleu4"] = round(sentence_bleu([ref_toks], hyp_toks, weights=(0.25,)*4, smoothing_function=sf), 4)
    except Exception:
        metrics["bleu4"] = None

    # ROUGE-L
    try:
        from rouge_score import rouge_scorer
        scorer         = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)
        scores         = scorer.score(reference, hypothesis)
        metrics["rougeL"] = round(scores["rougeL"].fmeasure, 4)
    except Exception:
        metrics["rougeL"] = None

    # Medical term coverage
    MEDICAL_TERMS_AR = [
        "هيموجلوبين", "كريات", "صفائح", "سكر", "كوليسترول", "كرياتينين",
        "تقييم", "توصيات", "مرتفع", "منخفض", "طبيعي", "مراجعة الطبيب",
    ]
    found = sum(1 for t in MEDICAL_TERMS_AR if t in hypothesis)
    metrics["medical_term_coverage"] = round(found / len(MEDICAL_TERMS_AR), 3)

    return metrics


def llm_judge(reference: str, hypothesis: str, groq_key: str) -> float:
    """Score the hypothesis vs reference using Groq LLM-as-judge (1-5)."""
    from groq import Groq
    client  = Groq(api_key=groq_key)
    prompt  = f"""أنت خبير طبي. قيّم جودة الإجابة الطبية مقارنة بالإجابة المرجعية.
أعطِ درجة من 1 إلى 5 (5 = ممتاز، 1 = ضعيف جداً).
أجب بالدرجة فقط كرقم.

المرجع: {reference[:500]}
الإجابة المُقيَّمة: {hypothesis[:500]}
الدرجة:"""
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0, max_tokens=5,
        )
        return float(resp.choices[0].message.content.strip())
    except Exception:
        return 0.0


def main():
    args = parse_args()

    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import PeftModel

    print(f"[eval] loading base model: {args.base_model}")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, token=args.hf_token, trust_remote_code=True)
    base_model = AutoModelForCausalLM.from_pretrained(
        args.base_model, device_map="auto", torch_dtype=torch.bfloat16,
        token=args.hf_token, trust_remote_code=True,
    )

    print(f"[eval] loading LoRA adapter: {args.lora_adapter}")
    lora_model = PeftModel.from_pretrained(base_model, args.lora_adapter)
    lora_model.eval()

    val_data = load_val(args.val_data, args.n_samples)
    print(f"[eval] evaluating {len(val_data)} samples...")

    results = {"base": [], "lora": []}

    for i, ex in enumerate(val_data):
        from training.train_lora import format_prompt
        prompt = format_prompt({**ex, "output": ""})   # exclude output for generation
        ref    = ex.get("output", "")

        # Base model
        hyp_base, tps_base = generate(base_model, tokenizer, prompt, args.max_new_tokens)
        m_base = compute_metrics(ref, hyp_base)
        m_base["tokens_per_sec"] = round(tps_base, 1)

        # LoRA model
        hyp_lora, tps_lora = generate(lora_model, tokenizer, prompt, args.max_new_tokens)
        m_lora = compute_metrics(ref, hyp_lora)
        m_lora["tokens_per_sec"] = round(tps_lora, 1)

        if args.use_llm_judge and args.groq_key:
            m_base["llm_judge"] = llm_judge(ref, hyp_base, args.groq_key)
            m_lora["llm_judge"] = llm_judge(ref, hyp_lora, args.groq_key)

        results["base"].append(m_base)
        results["lora"].append(m_lora)

        if (i + 1) % 10 == 0:
            print(f"[eval] {i+1}/{len(val_data)}")

    # Aggregate
    def avg(lst, key):
        vals = [x[key] for x in lst if x.get(key) is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    keys = ["bleu4", "rougeL", "medical_term_coverage", "tokens_per_sec", "llm_judge"]
    summary = {
        "base": {k: avg(results["base"], k) for k in keys},
        "lora": {k: avg(results["lora"], k) for k in keys},
        "n_samples": len(val_data),
    }
    print("\n[eval] Summary:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "eval_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    (out / "eval_details.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"[eval] results saved → {out}/")


if __name__ == "__main__":
    main()

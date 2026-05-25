"""
prepare_dataset.py — formats Arabic medical reports for LoRA fine-tuning.

Input sources:
  1. Supabase analyses table (via REST API)
  2. Local JSON files in data/raw/
  3. Synthetic examples from few_shot_examples.json

Output: data/train.jsonl, data/val.jsonl (Alpaca-format instruction tuning)

Usage:
    python training/prepare_dataset.py \
        --source supabase \
        --output_dir data/ \
        --val_split 0.1 \
        --min_findings 3
"""
from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path
from typing import Iterator

# ── Instruction templates ──────────────────────────────────────────────────

_SYSTEM_MSG = (
    "أنت طبيب مختبر خبير متخصص في تفسير التحاليل الطبية باللغة العربية. "
    "تقدم تفسيراً دقيقاً وواضحاً للنتائج المختبرية مع التوصيات المناسبة."
)

_INSTRUCTION_TEMPLATE = (
    "فسّر نتائج التحاليل الطبية التالية وقدم تقييماً شاملاً:\n\n"
    "النتائج:\n{findings}\n\n"
    "اشرح:\n1. التقييم العام للحالة\n2. القيم غير الطبيعية وأسبابها المحتملة\n"
    "3. التوصيات العملية للمريض"
)

_OUTPUT_TEMPLATE = (
    "**التقييم العام:**\n{general}\n\n"
    "**القيم غير الطبيعية:**\n{abnormal}\n\n"
    "**التوصيات:**\n{tips}"
)


# ── Data source loaders ────────────────────────────────────────────────────

def load_from_supabase(limit: int = 5000) -> Iterator[dict]:
    """Stream analyses from Supabase REST API."""
    from dotenv import load_dotenv
    load_dotenv()
    url  = os.getenv("SUPABASE_URL", "")
    key  = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        print("[prepare] SUPABASE_URL/KEY not set — skipping Supabase source")
        return

    import requests
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    offset  = 0
    batch   = 100

    while offset < limit:
        r = requests.get(
            f"{url}/rest/v1/analyses",
            headers=headers,
            params={"select": "findings,report,summary", "limit": batch, "offset": offset},
            timeout=15,
        )
        r.raise_for_status()
        rows = r.json()
        if not rows:
            break
        for row in rows:
            yield row
        offset += batch
        print(f"[prepare] loaded {offset} rows from Supabase...")


def load_from_json(data_dir: str) -> Iterator[dict]:
    """Load analyses from local JSON files."""
    for path in Path(data_dir).glob("**/*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                yield from data
            elif isinstance(data, dict):
                yield data
        except Exception as e:
            print(f"[prepare] skip {path}: {e}")


# ── Example formatter ──────────────────────────────────────────────────────

def _format_findings(findings: list[dict]) -> str:
    lines = []
    for f in findings:
        status_ar = {"high": "مرتفع", "low": "منخفض", "normal": "طبيعي"}.get(f.get("status", ""), "")
        line = f"  • {f.get('name','')}: {f.get('value','')} {f.get('unit','')} (المعدل: {f.get('range','')}) — {status_ar}"
        lines.append(line)
    return "\n".join(lines)


def _format_abnormal(details: list[dict]) -> str:
    lines = []
    for d in details:
        lines.append(f"  • {d.get('اسم_الفحص','')}: {d.get('الشرح','')}")
    return "\n".join(lines) if lines else "لا توجد قيم غير طبيعية بارزة"


def _format_tips(tips) -> str:
    if isinstance(tips, list):
        if tips and isinstance(tips[0], dict):
            # tips_categorized
            lines = []
            for cat in tips:
                lines.append(f"**{cat.get('category','')}:**")
                for t in cat.get("tips", []):
                    lines.append(f"  - {t}")
            return "\n".join(lines)
        return "\n".join(f"  - {t}" for t in tips)
    return str(tips)


def row_to_example(row: dict, min_findings: int = 2) -> dict | None:
    """Convert a DB row to an Alpaca-format training example."""
    findings = row.get("findings") or []
    report   = row.get("report") or {}

    if len(findings) < min_findings:
        return None
    if not report.get("general"):
        return None

    abnormal = [f for f in findings if f.get("status") != "normal"]
    details  = report.get("abnormal_details") or []
    tips     = report.get("tips_categorized") or report.get("tips") or []

    instruction = _INSTRUCTION_TEMPLATE.format(findings=_format_findings(findings))
    output      = _OUTPUT_TEMPLATE.format(
        general=report.get("general", ""),
        abnormal=_format_abnormal(details),
        tips=_format_tips(tips),
    )

    return {
        "system":      _SYSTEM_MSG,
        "instruction": instruction,
        "input":       "",
        "output":      output,
        "metadata": {
            "finding_count":  len(findings),
            "abnormal_count": len(abnormal),
        },
    }


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source",      default="json", choices=["supabase", "json", "both"])
    parser.add_argument("--data_dir",    default="data/raw")
    parser.add_argument("--output_dir",  default="data")
    parser.add_argument("--val_split",   type=float, default=0.1)
    parser.add_argument("--min_findings",type=int,   default=2)
    parser.add_argument("--max_examples",type=int,   default=10000)
    parser.add_argument("--seed",        type=int,   default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    examples: list[dict] = []

    if args.source in ("supabase", "both"):
        for row in load_from_supabase(limit=args.max_examples):
            ex = row_to_example(row, args.min_findings)
            if ex:
                examples.append(ex)

    if args.source in ("json", "both"):
        for row in load_from_json(args.data_dir):
            ex = row_to_example(row, args.min_findings)
            if ex:
                examples.append(ex)

    print(f"[prepare] total examples before dedup: {len(examples)}")
    examples = examples[:args.max_examples]
    random.shuffle(examples)

    split     = max(1, int(len(examples) * args.val_split))
    val_data  = examples[:split]
    train_data= examples[split:]

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for name, data in [("train", train_data), ("val", val_data)]:
        path = out / f"{name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for ex in data:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
        print(f"[prepare] wrote {len(data)} examples → {path}")

    # Write dataset stats
    stats = {
        "total": len(examples),
        "train": len(train_data),
        "val":   len(val_data),
        "avg_findings": sum(e["metadata"]["finding_count"] for e in examples) / max(len(examples), 1),
    }
    (out / "dataset_stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False))
    print(f"[prepare] stats: {stats}")


if __name__ == "__main__":
    main()

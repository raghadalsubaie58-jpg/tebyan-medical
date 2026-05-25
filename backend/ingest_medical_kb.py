"""
ingest_medical_kb.py — Ingest medical_kb/schemas/*.json → Supabase pgvector

Creates 3 semantically distinct chunks per lab test:
  chunk 0 (definition)       — name + abbreviations + unit + clinical meaning + patient explanation
  chunk 1 (values)           — normal ranges per gender + severity thresholds + followup tests
  chunk 2 (symptoms_causes)  — high causes + low causes + symptoms_low

Source tag: "TibyanMedicalKB"  (distinct from MedlinePlus "MedlinePlus" or "TibyanLabs")

Usage:
  cd backend
  python ingest_medical_kb.py             # insert new chunks only
  python ingest_medical_kb.py --clear     # delete existing TibyanMedicalKB first
  python ingest_medical_kb.py --dry-run   # print chunks, do NOT insert
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("HF_HOME", r"D:\Project\model_cache")
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

import requests
from langchain_huggingface import HuggingFaceEmbeddings

EMBED_MODEL  = "intfloat/multilingual-e5-large"
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

SCHEMAS_DIR  = Path(__file__).parent / "medical_kb" / "schemas"
SOURCE_TAG   = "TibyanMedicalKB"


# ══════════════════════════════════════════════════════════════════
# 1. Chunk builders
# ══════════════════════════════════════════════════════════════════

def _fmt_range(rng: dict) -> str:
    lo, hi = rng.get("low", "?"), rng.get("high", "?")
    return f"{lo}–{hi}"


def _build_definition_chunk(panel: dict, test_name: str, test: dict) -> str:
    """Chunk 0: identity + what this test measures."""
    name_ar = test.get("name_ar", test_name)
    abbr    = ", ".join(test.get("abbreviations", [])[:5])
    unit    = test.get("unit", "")
    meaning = test.get("clinical_meaning_ar", "")
    explain = test.get("patient_explanation_ar", "")

    parts = [
        f"{name_ar} ({test_name})",
    ]
    if abbr:
        parts.append(f"يُعرف أيضاً بـ: {abbr}")
    if unit:
        parts.append(f"الوحدة: {unit}")
    if meaning:
        parts.append(f"المعنى الطبي: {meaning}")
    if explain:
        parts.append(f"شرح مبسط: {explain}")

    panel_name = panel.get("name_ar", panel.get("panel_code", ""))
    parts.append(f"يُقاس ضمن: {panel_name} ({panel.get('name_en', '')})")

    return " | ".join(parts)


def _build_values_chunk(panel: dict, test_name: str, test: dict) -> str:
    """Chunk 1: normal ranges, severity thresholds, followup tests."""
    name_ar = test.get("name_ar", test_name)
    unit    = test.get("unit", "")
    ranges  = test.get("ranges", {})
    sev     = test.get("severity_thresholds", {})
    followup = test.get("followup_tests", [])

    parts = [f"القيم المرجعية لـ {name_ar}:"]

    range_lines = []
    for gender_key, rng in ranges.items():
        label = {
            "adult_male":     "بالغ ذكر",
            "adult_female":   "بالغة أنثى",
            "adult":          "البالغون",
            "children":       "الأطفال",
            "children_6_12":  "الأطفال 6-12 سنة",
            "pregnant":       "الحوامل",
            "elderly_male":   "كبار السن ذكر",
            "elderly_female": "كبار السن أنثى",
            "neonates":       "حديثو الولادة",
        }.get(gender_key, gender_key)
        range_lines.append(f"{label}: {_fmt_range(rng)} {unit}")
    parts.append(" | ".join(range_lines))

    if sev:
        sev_lines = []
        for k, v in sev.items():
            label = k.replace("_", " ")
            sev_lines.append(f"{label}: {v} {unit}")
        parts.append("عتبات الخطورة: " + " | ".join(sev_lines))

    if followup:
        parts.append("التحاليل التكميلية الموصى بها: " + ", ".join(followup[:6]))

    return " — ".join(parts)


def _build_symptoms_chunk(panel: dict, test_name: str, test: dict) -> str | None:
    """Chunk 2: causes + symptoms. Returns None if empty."""
    name_ar   = test.get("name_ar", test_name)
    high_ar   = test.get("high_causes_ar", [])
    low_ar    = test.get("low_causes_ar", [])
    symp_low  = test.get("symptoms_low_ar", [])

    # Thyroid schemas may use interpretation_matrix instead
    interp    = test.get("interpretation_matrix", {})

    parts = []
    if high_ar:
        parts.append(f"أسباب ارتفاع {name_ar}: " + "، ".join(high_ar))
    if low_ar:
        parts.append(f"أسباب انخفاض {name_ar}: " + "، ".join(low_ar))
    if symp_low:
        parts.append(f"الأعراض عند انخفاض {name_ar}: " + "، ".join(symp_low))
    if interp:
        lines = []
        for pattern, meaning in interp.items():
            lines.append(f"{pattern}: {meaning}")
        parts.append(f"تفسير نتائج {name_ar}: " + " | ".join(lines[:6]))

    if not parts:
        return None
    return " — ".join(parts)


def make_test_chunks(panel: dict, test_name: str, test: dict) -> list[dict]:
    """Return list of {content, chunk_type, chunk_index} for one lab test."""
    chunks = []

    def_text = _build_definition_chunk(panel, test_name, test)
    chunks.append({"content": def_text, "chunk_type": "definition", "chunk_index": 0})

    val_text = _build_values_chunk(panel, test_name, test)
    chunks.append({"content": val_text, "chunk_type": "values", "chunk_index": 1})

    sym_text = _build_symptoms_chunk(panel, test_name, test)
    if sym_text and len(sym_text) > 40:
        chunks.append({"content": sym_text, "chunk_type": "symptoms", "chunk_index": 2})

    return chunks


# ══════════════════════════════════════════════════════════════════
# 2. Schema loading
# ══════════════════════════════════════════════════════════════════

def load_all_schemas() -> list[dict]:
    schemas = []
    for path in sorted(SCHEMAS_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as f:
            schemas.append(json.load(f))
    return schemas


def build_all_docs(schemas: list[dict]) -> list[dict]:
    """Convert all schemas to flat list of documents ready for embedding."""
    docs = []
    for panel in schemas:
        panel_code = panel.get("panel_code", "unknown")
        specialty  = panel.get("specialty", "general")
        panel_name_ar = panel.get("name_ar", panel_code)
        tests      = panel.get("tests", {})

        for test_name, test in tests.items():
            for chunk in make_test_chunks(panel, test_name, test):
                docs.append({
                    "content": chunk["content"],
                    "metadata": {
                        "source":      SOURCE_TAG,
                        "panel_code":  panel_code,
                        "test_name":   test_name,
                        "test_name_ar": test.get("name_ar", test_name),
                        "chunk_type":  chunk["chunk_type"],
                        "chunk_index": chunk["chunk_index"],
                        "specialty":   specialty,
                        "topic_type":  "lab_test",
                        "title":       f"{test.get('name_ar', test_name)} — {panel_name_ar}",
                        "language":    "ar",
                        "unit":        test.get("unit", ""),
                    },
                })

    return docs


# ══════════════════════════════════════════════════════════════════
# 3. Supabase helpers (same pattern as ingest_medlineplus.py)
# ══════════════════════════════════════════════════════════════════

def _headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def clear_kb_source(url: str, key: str):
    r = requests.delete(
        f"{url}/rest/v1/documents",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        params={"metadata->>source": f"eq.{SOURCE_TAG}"},
        timeout=30,
    )
    print(f"  [CLEAR] source={SOURCE_TAG} -> HTTP {r.status_code}")


def insert_batch(batch: list[dict], url: str, key: str) -> bool:
    try:
        r = requests.post(
            f"{url}/rest/v1/documents",
            headers=_headers(),
            json=batch,
            timeout=60,
        )
        if r.status_code not in (200, 201):
            print(f"  [INSERT ERROR] {r.status_code}: {r.text[:300]}")
            return False
        return True
    except Exception as e:
        print(f"  [INSERT EXCEPTION] {e}")
        return False


def embed_and_insert(
    docs: list[dict],
    embeddings: HuggingFaceEmbeddings,
    url: str,
    key: str,
    seen_hashes: set,
    batch_size: int = 30,
) -> int:
    inserted  = 0
    skipped   = 0
    batch     = []

    for doc in docs:
        content = doc["content"].strip()
        if len(content) < 20:
            skipped += 1
            continue

        h = hashlib.md5(content.encode()).hexdigest()
        if h in seen_hashes:
            skipped += 1
            continue
        seen_hashes.add(h)

        try:
            vec = embeddings.embed_query(content)
        except Exception as e:
            print(f"  [EMBED ERROR] {e}")
            continue

        batch.append({
            "content":   content,
            "metadata":  doc["metadata"],
            "embedding": vec,
        })

        if len(batch) >= batch_size:
            if insert_batch(batch, url, key):
                inserted += len(batch)
                print(f"  [BATCH] inserted {len(batch)} | total {inserted}")
            batch = []

    if batch:
        if insert_batch(batch, url, key):
            inserted += len(batch)
            print(f"  [BATCH] inserted {len(batch)} | total {inserted}")

    if skipped:
        print(f"  [SKIP] {skipped} duplicate/short chunks skipped")

    return inserted


# ══════════════════════════════════════════════════════════════════
# 4. Main
# ══════════════════════════════════════════════════════════════════

def main():
    dry_run  = "--dry-run" in sys.argv
    do_clear = "--clear"   in sys.argv

    print("=" * 60)
    print(f"ingest_medical_kb.py | source={SOURCE_TAG}")
    print(f"schemas dir: {SCHEMAS_DIR}")
    print("=" * 60)

    schemas = load_all_schemas()
    if not schemas:
        print(f"[ERROR] لا توجد ملفات JSON في {SCHEMAS_DIR}")
        sys.exit(1)

    print(f"[SCHEMAS] loaded {len(schemas)} panels: {[p.get('panel_code') for p in schemas]}")

    docs = build_all_docs(schemas)
    print(f"[CHUNKS]  {len(docs)} total chunks to insert\n")

    for i, doc in enumerate(docs[:5]):
        meta    = doc["metadata"]
        preview = doc["content"][:120].encode("ascii", errors="replace").decode()
        print(f"  chunk {i} | {meta['panel_code']}.{meta['test_name']} [{meta['chunk_type']}]")
        print(f"    {preview}...")
        print()

    if dry_run:
        print(f"\n[DRY RUN] Would insert {len(docs)} chunks. Exiting.")
        return

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[ERROR] SUPABASE_URL و SUPABASE_KEY غير موجودان في .env")
        sys.exit(1)

    if do_clear:
        print("[CLEAR] حذف السجلات القديمة...")
        clear_kb_source(SUPABASE_URL, SUPABASE_KEY)

    print(f"[EMBED] تحميل نموذج {EMBED_MODEL}...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    print("[EMBED] ready\n")

    seen_hashes: set = set()
    total = embed_and_insert(docs, embeddings, SUPABASE_URL, SUPABASE_KEY, seen_hashes)

    print(f"\n{'=' * 60}")
    print(f"[DONE] إجمالي المُدرج: {total} chunk من {len(docs)}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

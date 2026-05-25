# تبيان الطبي — Agent System

## Overview

The multi-agent pipeline in `backend/services/agents/` processes each medical file through five sequential agents. Each agent reads from and writes to a shared `AgentContext` dataclass, making the full pipeline observable and independently testable.

---

## Base Classes (`agents/base.py`)

### `AgentContext`

Shared state object threaded through all agents. Key fields:

| Field | Type | Set by |
|---|---|---|
| `file_bytes` | `bytes` | Coordinator |
| `file_type` | `"pdf" \| "image"` | Coordinator |
| `raw_text` | `str` | OCRAgent |
| `findings` | `list[dict]` | ExtractionAgent |
| `panel_code` | `str` | ClassificationAgent |
| `rag_context` | `str` | MedicalReasoningAgent |
| `report` | `dict` | MedicalReasoningAgent |
| `logs` | `list[AgentLogEntry]` | All agents |

### `AgentBase`

Abstract base with:
- **Retry logic**: up to `max_retries=2` attempts with `0.3 s × 2^attempt` backoff
- **`_on_failure(ctx, exc)`**: each subclass overrides to provide a safe fallback when all retries fail
- **Timing**: each `run()` call records `duration_ms` in `AgentLogEntry`

---

## Agents

### 1. `OCRAgent`

**File**: `agents/ocr_agent.py`

**Input**: `ctx.file_bytes`, `ctx.file_type`
**Output**: `ctx.raw_text`

**Strategy**:
- PDF: extracts text with PyMuPDF (`fitz`); falls back to EasyOCR page-by-page if text layer is empty
- Image: tries Google Cloud Vision first (higher accuracy for Arabic); falls back to EasyOCR with contrast/sharpness preprocessing

**Failure mode**: sets `raw_text = ""` — downstream agents handle empty text gracefully.

---

### 2. `ExtractionAgent`

**File**: `agents/extraction_agent.py`

**Input**: `ctx.raw_text`
**Output**: `ctx.findings` (list of `{name, value, unit, range, status}`)

**Strategy**:
1. Regex patterns matching common Arabic/English lab report formats
2. LLM extraction via Groq if regex yields < 2 findings
3. Physiological bounds filter (`_validators.py`) removes impossible values (e.g., hemoglobin = 400)
4. Deduplication by normalized test name

**Failure mode**: sets `findings = []`.

---

### 3. `ClassificationAgent`

**File**: `agents/classification_agent.py`

**Input**: `ctx.findings`, `ctx.raw_text`
**Output**: `ctx.panel_code`, `ctx.panel_confidence`

**Strategy**: Uses `services/classifier.py` which scores text against panel-specific keyword sets. Falls back to `detect_panel()` heuristic if primary classifier returns low confidence.

**Panels**: `cbc`, `thyroid`, `liver`, `kidney`, `lipid`, `diabetes`, `urine`, `mixed`

**Failure mode**: sets `panel_code = "mixed"` (general analysis).

---

### 4. `MedicalReasoningAgent`

**File**: `agents/reasoning_agent.py`

**Input**: `ctx.findings`, `ctx.panel_code`, `ctx.analysis_type`
**Output**: `ctx.rag_context`, `ctx.report`

**Strategy**:
1. Checks `rag_cache` (TTL 5 min) for identical query
2. Retrieves relevant medical knowledge via `Retriever` (BM25 + pgvector + Cohere rerank)
3. Selects panel-specific prompt template from `prompts/`
4. Calls Groq `llama-3.3-70b-versatile` with findings + RAG context
5. Parses JSON response into structured report

**Failure mode**: generates a fallback report from raw findings without LLM, appends disclaimer.

---

### 5. `SafetyAgent`

**File**: `agents/safety_agent.py`

**Input**: `ctx.report`
**Output**: `ctx.report` (filtered in-place)

**Strategy**: Applies `services/safety.filter_analysis_report()` which:
- Removes diagnostic certainty claims ("you have diabetes")
- Adds standard medical disclaimer
- Detects emergency patterns (very high/low critical values) and prepends urgent notice

**Failure mode**: appends `DISCLAIMER_AR` manually to ensure minimum safety even if filter itself errors.

---

## `AgentCoordinator` (`agents/coordinator.py`)

Instantiates all five agents and runs them in sequence. Returns `CoordinatorResult`:

```python
@dataclass
class CoordinatorResult:
    findings:   list[dict]
    summary:    str
    report:     dict
    panel_code: str
    logs:       list[dict]   # exposed in dev mode via _agents field
    ok:         bool
    error:      str
    total_ms:   float
```

The coordinator is loaded once via `@lru_cache` and reused across requests. Agent instances are stateless — all state lives in the per-request `AgentContext`.

---

## Adding a New Agent

1. Create `agents/my_agent.py`, subclass `AgentBase`
2. Implement `_execute(self, ctx: AgentContext) -> AgentContext`
3. Implement `_on_failure(self, ctx, exc)` with a safe fallback
4. Add new fields to `AgentContext` if needed
5. Register in `AgentCoordinator.__init__()` agent list at the correct position

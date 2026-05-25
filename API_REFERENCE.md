# تبيان الطبي — API Reference

Base URL: `http://localhost:8000` (dev) / `https://your-domain.com` (prod)

All endpoints return JSON unless noted. Arabic text is UTF-8 encoded.

---

## `POST /api/analyze`

Analyze a medical lab report image or PDF.

**Request**: `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | File | Yes | PDF or image (JPEG/PNG/WEBP/TIFF). Max 20 MB. |
| `analysis_type` | string | No | One of: `شامل`, `دم شامل`, `سكر وكوليسترول`, `كلى وكبد`, `هرمونات`, `بول`. Default: `شامل` |

**Response** `200`
```json
{
  "findings": [
    { "name": "Hemoglobin", "value": "10.2", "unit": "g/dL", "range": "12-16", "status": "low" }
  ],
  "summary": "تُظهر نتائجك انخفاضاً في الهيموجلوبين...",
  "report": {
    "general": "الحالة العامة...",
    "abnormal_details": [{ "اسم_الفحص": "Hemoglobin", "الشرح": "..." }],
    "tips": ["..."],
    "tips_categorized": [{ "category": "التغذية", "tips": ["..."] }]
  }
}
```

**Errors**: `400` bad file, `413` file too large, `415` unsupported type, `422` analysis failed, `429` rate limit (5/min)

---

## `POST /api/chat`

Stream an Arabic medical assistant response.

**Request**: `application/json`
```json
{
  "query": "ماذا يعني انخفاض الهيموجلوبين؟",
  "history": [{ "role": "user", "content": "..." }, { "role": "assistant", "content": "..." }],
  "analysis_context": "{\"findings\": [...], \"summary\": \"...\"}"
}
```

**Response**: `text/plain; charset=utf-8` — streaming text chunks (Server-Sent Events compatible)

**Rate limit**: 30/min per IP

---

## `POST /api/risk`

Assess disease risk from lab findings.

**Request**: `application/json`
```json
{
  "findings": [
    { "name": "Glucose", "value": "126", "unit": "mg/dL", "range": "70-100", "status": "high" }
  ]
}
```

**Response** `200`
```json
{
  "risks": [
    {
      "condition": "diabetes",
      "score": 72,
      "level": "high",
      "confidence": 0.85,
      "label_ar": "السكري",
      "factors": ["ارتفاع سكر الصيام"],
      "recommendation": "استشر طبيبك لإجراء اختبار HbA1c",
      "source": "rule"
    }
  ],
  "top_risk": { ... },
  "overall_ar": "توجد مؤشرات تستوجب المتابعة الطبية",
  "features_used": 12
}
```

**Conditions scored**: `diabetes`, `cardiovascular`, `anemia`, `kidney`, `liver`, `thyroid`

---

## `POST /api/voice/transcribe`

Transcribe Arabic audio to text using Whisper.

**Request**: `multipart/form-data`

| Field | Type | Description |
|---|---|---|
| `audio` | File | Audio file. Formats: WebM, MP4, OGG, WAV, FLAC, M4A. Max 25 MB. |
| `language` | string | Language hint. Default: `ar` |

**Response** `200`
```json
{ "text": "ماذا يعني ارتفاع الكوليسترول؟", "language": "ar" }
```

---

## `POST /api/voice/synthesize`

Convert Arabic text to speech (MP3).

**Request**: `application/json`
```json
{ "text": "نتائج تحليلك تُظهر..." }
```

**Response**: `audio/mpeg` binary (MP3). Max input: 3000 characters.

---

## `POST /api/voice/chat`

Voice-to-voice chat: transcribe audio → chat → synthesize response.

**Request**: `multipart/form-data`

| Field | Type | Description |
|---|---|---|
| `audio` | File | Audio file (same formats as transcribe) |
| `analysis_context` | string | JSON string of last analysis result (optional) |

**Response**: `audio/mpeg` binary — spoken Arabic assistant response.

---

## `POST /api/search`

Semantic search across saved analyses.

**Request**: `application/json`
```json
{
  "query": "ارتفاع الكوليسترول",
  "analyses": [
    { "id": "uuid", "summary": "...", "findings_text": "Hemoglobin Glucose ..." }
  ]
}
```

**Response** `200`
```json
{ "scores": { "uuid-1": 0.82, "uuid-2": 0.31 } }
```

**Rate limit**: 60/min per IP

---

## `POST /api/analyses/save`

Save an analysis result for a session.

**Request**: `application/json`
```json
{
  "session_id": "local_abc123",
  "findings": [...],
  "summary": "...",
  "report": { ... }
}
```

**Response** `200`: `{ "success": true, "data": [...] }`

---

## `GET /api/analyses/list`

List saved analyses for a session.

**Query params**: `session_id`, `profile_name` (optional), `limit` (default 20)

**Response** `200`: `{ "analyses": [...] }`

---

## `GET /health`

System health check.

**Response** `200`
```json
{
  "ok": true,
  "version": "local",
  "environment": "development",
  "uptime_s": 3600,
  "db": { "ok": true, "chunks": 2834, "source": "pgvector/supabase" },
  "model": { "name": "intfloat/multilingual-e5-large", "loaded": true },
  "services": { "groq": true, "cohere": true, "vision": false }
}
```

---

## `GET /api/metrics`

Prometheus-format plaintext metrics.

**Response** `200` `text/plain; version=0.0.4`
```
# HELP tebyan_uptime_seconds Seconds since server start
tebyan_uptime_seconds 3600
# HELP tebyan_requests_total Total HTTP requests per path
tebyan_requests_total{path="/api/analyze"} 42
tebyan_rag_cache_size 18
tebyan_rag_cache_hits 156
```

---

## Error Format

All errors use standard HTTP status codes with a JSON body:

```json
{ "detail": "وصف الخطأ بالعربية أو الإنجليزية" }
```

| Code | Meaning |
|---|---|
| 400 | Bad request (empty file, invalid input) |
| 413 | File too large (> 20 MB) |
| 415 | Unsupported media type |
| 422 | Analysis failed (OCR/LLM error) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
| 503 | External service unavailable |

-- ============================================================
-- Supabase RLS Setup — تبيان الطبي
-- Run this once in the Supabase SQL Editor (Project > SQL Editor)
-- ============================================================

-- ── 1. Enable RLS on protected tables ──────────────────────
ALTER TABLE analyses       ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages  ENABLE ROW LEVEL SECURITY;

-- ── 2. analyses: backend service_role only ─────────────────
-- service_role key bypasses RLS automatically in Supabase.
-- The policies below block all anon/authenticated direct access,
-- forcing all reads/writes through the FastAPI backend.

DROP POLICY IF EXISTS analyses_deny_anon  ON analyses;
CREATE POLICY analyses_deny_anon
    ON analyses
    FOR ALL
    TO anon, authenticated
    USING (false);

-- ── 3. chat_messages: backend service_role only ────────────
DROP POLICY IF EXISTS chat_deny_anon ON chat_messages;
CREATE POLICY chat_deny_anon
    ON chat_messages
    FOR ALL
    TO anon, authenticated
    USING (false);

-- ── 4. documents (KB): allow anon read for pgvector search ─
-- The KB is public knowledge — anon read is fine.
-- Write is blocked (only ingest scripts use service_role).
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS documents_anon_read ON documents;
CREATE POLICY documents_anon_read
    ON documents
    FOR SELECT
    TO anon, authenticated
    USING (true);

-- Also allow the match_documents RPC to execute
-- (RPC security is controlled via SECURITY DEFINER on the function;
--  no extra policy needed if the function uses service_role context)

-- ── 5. Verify ─────────────────────────────────────────────
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE tablename IN ('analyses', 'chat_messages', 'documents');

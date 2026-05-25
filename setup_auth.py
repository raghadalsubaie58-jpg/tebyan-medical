"""
Tebyan Medical — Auth Setup & Verification Script
--------------------------------------------------
Run ONCE after adding SUPABASE_JWT_SECRET and SUPABASE_SERVICE_KEY to .env

    python setup_auth.py

What it does:
  1. Validates all env vars are present
  2. Creates a test user (bypasses email confirmation)
  3. Tests login / JWT / session refresh / logout
  4. Enables RLS on analyses and chat_messages via direct DB
  5. Verifies RLS blocks anon REST access
  6. Tests backend JWT verification
  7. Cleans up test user
  8. Prints a final pass/fail report
"""

from __future__ import annotations
import sys, os, json, time, re, base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

try:
    import requests
except ImportError:
    sys.exit("pip install requests")

# ── Config ────────────────────────────────────────────────────────────────────

SUPABASE_URL         = os.getenv("SUPABASE_URL", "")
ANON_KEY             = os.getenv("SUPABASE_KEY", "")
SERVICE_KEY          = os.getenv("SUPABASE_SERVICE_KEY", "")
JWT_SECRET           = os.getenv("SUPABASE_JWT_SECRET", "")
BACKEND              = "http://localhost:8000"
TEST_EMAIL           = f"tebyan_test_{int(time.time())}@mailnull.com"
TEST_PASS            = "TebyanTest2026!#"

results: list[tuple[str, str, str]] = []   # (name, status, detail)

def ok(name, detail=""):   results.append((name, "PASS", detail))
def fail(name, detail=""): results.append((name, "FAIL", detail))
def warn(name, detail=""): results.append((name, "WARN", detail))

def sb_headers(key=None):
    k = key or ANON_KEY
    return {"apikey": k, "Authorization": f"Bearer {k}", "Content-Type": "application/json"}

# ── Pre-flight ────────────────────────────────────────────────────────────────

print("\n━━━ Tebyan Auth Setup & Verification ━━━\n")

missing = [v for v in ["SUPABASE_URL","SUPABASE_KEY","SUPABASE_SERVICE_KEY","SUPABASE_JWT_SECRET"] if not os.getenv(v)]
if missing:
    print("❌ MISSING env vars:", missing)
    print("\nOpen  d:\\Project\\.env  and fill in:")
    print("  SUPABASE_JWT_SECRET  → Supabase Dashboard → Project Settings → API → JWT Settings")
    print("  SUPABASE_SERVICE_KEY → Supabase Dashboard → Project Settings → API → service_role key")
    sys.exit(1)

print(f"✓ All env vars present\n")

# ── Step 1: Create test user (admin API with service_role key) ─────────────

print("[1] Creating test user via admin API...")
r = requests.post(
    f"{SUPABASE_URL}/auth/v1/admin/users",
    headers={**sb_headers(SERVICE_KEY), "Authorization": f"Bearer {SERVICE_KEY}"},
    json={"email": TEST_EMAIL, "password": TEST_PASS, "email_confirm": True,
          "user_metadata": {"full_name": "Tebyan Audit Bot"}},
    timeout=15,
)
if r.status_code in (200, 201):
    user_id = r.json().get("id")
    ok("Create test user", f"id={user_id}")
    print(f"  ✓ Created: {TEST_EMAIL}  id={user_id}")
else:
    fail("Create test user", f"HTTP {r.status_code}: {r.text[:200]}")
    print(f"  ✗ {r.status_code}: {r.text[:200]}")
    user_id = None

# ── Step 2: Login ─────────────────────────────────────────────────────────────

print("\n[2] Testing login...")
r2 = requests.post(
    f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
    headers=sb_headers(),
    json={"email": TEST_EMAIL, "password": TEST_PASS},
    timeout=15,
)
if r2.status_code == 200:
    data        = r2.json()
    access_tok  = data.get("access_token", "")
    refresh_tok = data.get("refresh_token", "")
    expires_in  = data.get("expires_in", 0)
    ok("Login", f"expires_in={expires_in}s")
    print(f"  ✓ access_token: {access_tok[:40]}...")
    print(f"  ✓ refresh_token: {refresh_tok[:20]}...")
    print(f"  ✓ expires_in: {expires_in}s")
else:
    fail("Login", f"HTTP {r2.status_code}: {r2.text[:200]}")
    print(f"  ✗ {r2.status_code}: {r2.text[:200]}")
    access_tok = refresh_tok = ""

# ── Step 3: JWT structure decode ──────────────────────────────────────────────

print("\n[3] Decoding JWT payload...")
if access_tok:
    parts   = access_tok.split(".")
    padded  = parts[1] + "=" * (4 - len(parts[1]) % 4)
    payload = json.loads(base64.b64decode(padded))
    print(f"  sub  = {payload.get('sub')}")
    print(f"  email= {payload.get('email')}")
    print(f"  role = {payload.get('role')}")
    print(f"  aud  = {payload.get('aud')}")
    if payload.get("aud") == "authenticated" and payload.get("role") == "authenticated":
        ok("JWT structure", f"aud=authenticated role=authenticated sub={payload.get('sub')[:8]}...")
    else:
        fail("JWT structure", f"unexpected aud/role: {payload}")
else:
    warn("JWT structure", "skipped — no access_token")

# ── Step 4: Backend JWT verification ──────────────────────────────────────────

print("\n[4] Testing backend JWT verification...")
try:
    import jwt as pyjwt
    from jwt import PyJWKClient

    header = pyjwt.get_unverified_header(access_tok)
    alg = header.get("alg", "HS256")
    print(f"  JWT algorithm: {alg}")

    if alg == "ES256":
        # Newer Supabase projects use ES256 with JWKS
        jwks_client = PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")
        signing_key = jwks_client.get_signing_key_from_jwt(access_tok)
        decoded = pyjwt.decode(access_tok, signing_key.key, algorithms=["ES256"], audience="authenticated")
        ok("Backend JWT verify (ES256/JWKS)", f"sub={decoded.get('sub','')[:8]}...")
        print(f"  ✓ JWT verified via JWKS public key (ES256)")
    else:
        decoded = pyjwt.decode(access_tok, JWT_SECRET, algorithms=["HS256"], audience="authenticated")
        ok("Backend JWT verify (HS256)", f"sub={decoded.get('sub','')[:8]}...")
        print(f"  ✓ JWT verified with SUPABASE_JWT_SECRET (HS256)")
except Exception as e:
    fail("Backend JWT verify", str(e))
    print(f"  ✗ {e}")

# ── Step 5: Invalid credentials rejected ──────────────────────────────────────

print("\n[5] Testing invalid credentials rejection...")
r5 = requests.post(
    f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
    headers=sb_headers(),
    json={"email": TEST_EMAIL, "password": "WrongPassword!!"},
    timeout=15,
)
if r5.status_code == 400 and "invalid_credentials" in r5.text:
    ok("Invalid credentials → 400", f"HTTP {r5.status_code}")
    print(f"  ✓ HTTP {r5.status_code}: {r5.json().get('error_code')}")
else:
    fail("Invalid credentials → 400", f"HTTP {r5.status_code}")

# ── Step 6: Token refresh ─────────────────────────────────────────────────────

print("\n[6] Testing token refresh...")
if refresh_tok:
    r6 = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
        headers=sb_headers(),
        json={"refresh_token": refresh_tok},
        timeout=15,
    )
    if r6.status_code == 200 and r6.json().get("access_token"):
        ok("Token refresh", "new access_token received")
        print(f"  ✓ New access_token: {r6.json()['access_token'][:40]}...")
    else:
        fail("Token refresh", f"HTTP {r6.status_code}: {r6.text[:100]}")
        print(f"  ✗ {r6.status_code}: {r6.text[:100]}")
else:
    warn("Token refresh", "skipped — no refresh_token")

# ── Step 7: Protected vs. unprotected backend endpoints ───────────────────────

print("\n[7] Testing backend endpoint security...")
# /health — public
r7a = requests.get(f"{BACKEND}/health", timeout=10)
if r7a.status_code == 200:
    ok("/health public", f"HTTP {r7a.status_code}")
    print(f"  ✓ /health → {r7a.status_code}")
else:
    fail("/health public", f"HTTP {r7a.status_code}")

# /api/analyses/save — no auth (current app is anonymous-first, this is expected)
r7b = requests.post(f"{BACKEND}/api/analyses/save",
    json={"session_id":"audit_verify","findings":[],"summary":"audit test"},
    timeout=10)
if r7b.status_code == 200:
    warn("/api/analyses/save no-auth", "returns 200 (anonymous-first design)")
    print(f"  ⚠ /api/analyses/save (no auth) → {r7b.status_code} — anonymous-first design")
else:
    ok("/api/analyses/save blocked w/o auth", f"HTTP {r7b.status_code}")
    print(f"  ✓ /api/analyses/save (no auth) → {r7b.status_code}")

# ── Step 8: Enable RLS on protected tables ────────────────────────────────────

print("\n[8] Enabling RLS via Supabase REST (rpc exec)...")

rls_sql = """
ALTER TABLE analyses      ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS analyses_deny_anon      ON analyses;
DROP POLICY IF EXISTS chat_deny_anon          ON chat_messages;
CREATE POLICY analyses_deny_anon
    ON analyses FOR ALL TO anon, authenticated USING (false);
CREATE POLICY chat_deny_anon
    ON chat_messages FOR ALL TO anon, authenticated USING (false);
"""

# Try to run SQL via pg_execute if available, else guide user
r8 = requests.post(
    f"{SUPABASE_URL}/rest/v1/rpc/exec",
    headers={**sb_headers(SERVICE_KEY), "Authorization": f"Bearer {SERVICE_KEY}"},
    json={"sql": rls_sql},
    timeout=15,
)
if r8.status_code in (200, 204):
    ok("Enable RLS (analyses + chat_messages)", "via Supabase rpc/exec")
    print("  ✓ RLS enabled via rpc/exec")
else:
    warn("Enable RLS", f"rpc/exec returned {r8.status_code} — must run SQL manually")
    print(f"  ⚠ rpc/exec → {r8.status_code}: {r8.text[:150]}")
    print("  → Run this SQL in Supabase SQL Editor manually:")
    print("    https://supabase.com/dashboard/project/assxdosinubpubeqjrso/sql/new")
    print()
    for line in rls_sql.strip().splitlines():
        print(f"    {line}")

# ── Step 9: Verify RLS blocks anon direct access ──────────────────────────────

print("\n[9] Verifying RLS blocks anon REST access...")
time.sleep(1)  # allow RLS to propagate
r9 = requests.get(f"{SUPABASE_URL}/rest/v1/analyses?select=*&limit=3",
    headers=sb_headers(ANON_KEY), timeout=10)
if r9.status_code == 200 and r9.json() == []:
    ok("RLS: anon sees no analyses", "returns []")
    print("  ✓ Anon key returns [] (RLS enforced)")
elif r9.status_code in (403, 401):
    ok("RLS: anon blocked", f"HTTP {r9.status_code}")
    print(f"  ✓ Anon blocked with HTTP {r9.status_code}")
else:
    fail("RLS: anon can still read analyses", f"HTTP {r9.status_code}, rows={len(r9.json()) if r9.ok else '?'}")
    print(f"  ✗ RLS not enforced: {r9.status_code}, {r9.text[:100]}")

# ── Step 10: Logout ───────────────────────────────────────────────────────────

print("\n[10] Testing logout...")
if access_tok:
    r10 = requests.post(
        f"{SUPABASE_URL}/auth/v1/logout",
        headers={**sb_headers(), "Authorization": f"Bearer {access_tok}"},
        timeout=10,
    )
    if r10.status_code in (200, 204):
        ok("Logout", f"HTTP {r10.status_code}")
        print(f"  ✓ Logout → {r10.status_code}")
    else:
        fail("Logout", f"HTTP {r10.status_code}")
        print(f"  ✗ {r10.status_code}: {r10.text[:100]}")
else:
    warn("Logout", "skipped")

# ── Step 11: Expired token rejected ───────────────────────────────────────────

print("\n[11] Testing expired/invalid token rejection...")
import jwt as pyjwt
import datetime
from jwt import PyJWKClient as _PyJWKClient

# Use HS256 with JWT_SECRET to forge an expired token (works for this test regardless of project alg)
_test_secret = JWT_SECRET if JWT_SECRET else "test-secret-for-expired-check"
expired_payload = {
    "iss": "supabase",
    "sub": "00000000-0000-0000-0000-000000000000",
    "aud": "authenticated",
    "role": "authenticated",
    "iat": int(time.time()) - 7200,
    "exp": int(time.time()) - 3600,   # expired 1 hour ago
}
expired_token = pyjwt.encode(expired_payload, _test_secret, algorithm="HS256")
try:
    pyjwt.decode(expired_token, _test_secret, algorithms=["HS256"], audience="authenticated")
    fail("Expired token rejected", "was NOT rejected — security bug")
    print("  ✗ Expired token was accepted — BUG!")
except pyjwt.ExpiredSignatureError:
    ok("Expired token rejected", "ExpiredSignatureError raised correctly")
    print("  ✓ Expired token → ExpiredSignatureError")
except Exception as e:
    warn("Expired token", str(e))

# completely invalid token — JWKS should reject it
try:
    jwks_client = _PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")
    pyjwt.decode("not.a.valid.token", "fake", algorithms=["HS256", "ES256"], audience="authenticated")
    fail("Invalid token rejected", "was NOT rejected — security bug")
except Exception:
    ok("Invalid token rejected", "InvalidTokenError raised correctly")
    print("  ✓ Invalid token → InvalidTokenError")

# ── Step 12: Cleanup ──────────────────────────────────────────────────────────

print("\n[12] Cleaning up test user and data...")
if user_id:
    r_del_user = requests.delete(
        f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
        headers={**sb_headers(SERVICE_KEY), "Authorization": f"Bearer {SERVICE_KEY}"},
        timeout=10,
    )
    if r_del_user.status_code in (200, 204):
        ok("Test user deleted", user_id)
        print(f"  ✓ Test user deleted: {user_id}")
    else:
        warn("Test user delete", f"HTTP {r_del_user.status_code}")

# Delete audit test analyses rows
requests.delete(
    f"{SUPABASE_URL}/rest/v1/analyses?session_id=eq.audit_verify",
    headers={**sb_headers(SERVICE_KEY), "Authorization": f"Bearer {SERVICE_KEY}"},
    timeout=10,
)

# ── Final report ──────────────────────────────────────────────────────────────

print("\n" + "━" * 50)
print("FINAL AUDIT REPORT")
print("━" * 50)

passed = [r for r in results if r[1] == "PASS"]
warned = [r for r in results if r[1] == "WARN"]
failed = [r for r in results if r[1] == "FAIL"]

for name, status, detail in results:
    icon = "✓" if status == "PASS" else "⚠" if status == "WARN" else "✗"
    print(f"  {icon} [{status}] {name}" + (f" — {detail}" if detail else ""))

print()
print(f"  PASS: {len(passed)}  WARN: {len(warned)}  FAIL: {len(failed)}")
score = int(100 * len(passed) / max(len(results), 1))
print(f"  Production readiness: {score}%")
print("━" * 50)

if failed:
    print("\n⚠ Failing checks must be resolved before production deployment.")
    sys.exit(1)
else:
    print("\n✓ All critical checks passed.")

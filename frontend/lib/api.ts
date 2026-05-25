import { createClient } from "./supabase"

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000"

/** Returns fetch headers including Bearer token when the user is logged in. */
async function authHeaders(extra?: Record<string, string>): Promise<Record<string, string>> {
  const supabase = createClient()
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  }
}

export async function apiGet(path: string, params?: Record<string, string | number>) {
  const headers = await authHeaders({ "Content-Type": "application/json" })
  const url = new URL(`${BACKEND}${path}`)
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)))
  }
  return fetch(url.toString(), { headers })
}

export async function apiPost(path: string, body: unknown) {
  const headers = await authHeaders()
  return fetch(`${BACKEND}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  })
}

export async function apiDelete(path: string, params?: Record<string, string>) {
  const headers = await authHeaders()
  const url = new URL(`${BACKEND}${path}`)
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))
  }
  return fetch(url.toString(), { method: "DELETE", headers })
}

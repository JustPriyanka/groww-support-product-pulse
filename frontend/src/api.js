/**
 * API client. Local dev: /api is proxied to :8000. Production: VITE_API_URL = Railway URL.
 */
// Trim + drop trailing slashes: a stray space pasted into the Vercel env var broke every request.
const BASE_URL = (import.meta.env.VITE_API_URL ?? '').trim().replace(/\/+$/, '')

let passcode = sessionStorage.getItem('reviewerPasscode') || ''
export const setPasscode = (p) => { passcode = p; sessionStorage.setItem('reviewerPasscode', p) }

async function req(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (passcode) headers['X-Reviewer-Passcode'] = passcode
  const res = await fetch(`${BASE_URL}${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = new Error(typeof data.detail === 'string' ? data.detail : `Request failed (${res.status})`)
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}

export const api = {
  health: () => req('/api/health'),
  meta: () => req('/api/meta'),
  stats: () => req('/api/stats'),
  questions: () => req('/api/questions'),
  question: (id) => req(`/api/questions/${id}`),
  ask: (text, channel) => req('/api/questions', { method: 'POST', body: { text, channel } }),
  refine: (id, feedback) => req(`/api/questions/${id}/refine`, { method: 'POST', body: { feedback } }),
  editDraft: (id, reply) => req(`/api/drafts/${id}/edit`, { method: 'POST', body: { reply } }),
  approveDraft: (id) => req(`/api/drafts/${id}/approve`, { method: 'POST' }),
  rejectDraft: (id, reason) => req(`/api/drafts/${id}/reject`, { method: 'POST', body: { reason } }),
  proposeLog: (id) => req(`/api/drafts/${id}/propose-log`, { method: 'POST' }),
  runPulse: (window_days) => req('/api/pulse/run', { method: 'POST', body: { window_days } }),
  pulseRuns: () => req('/api/pulse/runs'),
  pulseRun: (id) => req(`/api/pulse/runs/${id}`),
  actions: (status) => req(`/api/actions${status ? `?status=${status}` : ''}`),
  approveAction: (id, payload_sha256) => req(`/api/actions/${id}/approve`, { method: 'POST', body: { payload_sha256, confirm: true } }),
  rejectAction: (id) => req(`/api/actions/${id}/reject`, { method: 'POST' }),
  canonical: () => req('/api/canonical'),
  sources: () => req('/api/sources'),
  sentences: (ids) => req(`/api/sources/sentences?ids=${encodeURIComponent(ids.join(','))}`),
  reviews: (ids) => req(`/api/reviews?ids=${encodeURIComponent(ids.join(','))}`),
  workspace: () => req('/api/workspace'),
  agentRuns: () => req('/api/agent-runs'),
}

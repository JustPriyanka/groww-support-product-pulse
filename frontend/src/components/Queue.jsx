import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { Empty, ErrorNote, Reply, Section, SourceList, Status, Tag, fmtTime } from './ui'

export default function Queue({ selectedId, onSelect, refreshKey }) {
  const [list, setList] = useState([])
  const [filter, setFilter] = useState('all')
  useEffect(() => { api.questions().then((d) => setList(d.questions)).catch(() => {}) }, [refreshKey, selectedId])
  const shown = list.filter((q) => filter === 'all' || q.status === filter)
  const counts = list.reduce((a, q) => ({ ...a, [q.status]: (a[q.status] || 0) + 1 }), {})

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(280px,380px)_1fr]">
      <div className="space-y-3">
        <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Filter questions">
          {['all', 'ready', 'blocked', 'approved', 'rejected'].map((f) => (
            <button key={f} role="tab" aria-selected={filter === f} onClick={() => setFilter(f)}
              className={`rounded-md px-2.5 py-1 text-xs border ${filter === f ? 'border-ink bg-ink text-paper' : 'border-rule bg-white text-ink-soft'}`}>
              {f === 'all' ? `All ${list.length}` : `${f[0].toUpperCase() + f.slice(1)} ${counts[f] || 0}`}
            </button>
          ))}
        </div>
        {!shown.length && <Empty>No questions here yet. Ask one from the Ask tab.</Empty>}
        <ul className="space-y-2">
          {shown.map((q) => (
            <li key={q.id}>
              <button onClick={() => onSelect(q.id)}
                className={`w-full rounded-lg border px-3 py-2.5 text-left ${selectedId === q.id ? 'border-ink bg-white' : 'border-rule bg-white/60 hover:bg-white'}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="id">Q{q.id} · {q.channel}</span>
                  <Status value={q.status} />
                </div>
                <div className="mt-1 line-clamp-2 text-sm">{q.text_redacted}</div>
                <div className="mt-1.5 flex flex-wrap gap-1">
                  <Tag>{q.intent.replaceAll('_', ' ')}</Tag>
                  {q.routing?.priority && <Tag tone={q.routing.priority === 'P1' ? 'bad' : q.routing.priority === 'P2' ? 'warn' : 'plain'}>{q.routing.priority}</Tag>}
                  {q.origin === 'canonical' && <Tag tone="good">canonical answer</Tag>}
                  {(q.pii_types || []).length > 0 && <Tag tone="bad">PII redacted</Tag>}
                </div>
              </button>
            </li>
          ))}
        </ul>
      </div>
      <div>{selectedId ? <QuestionDetail id={selectedId} /> : <Empty>Select a question to review its draft, citations, routing and reviewer result.</Empty>}</div>
    </div>
  )
}

function QuestionDetail({ id }) {
  const [q, setQ] = useState(null)
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState('')
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState('')
  const [feedback, setFeedback] = useState('')
  const [rejectOpen, setRejectOpen] = useState(false)

  const load = () => api.question(id).then(setQ).catch(setErr)
  useEffect(() => { setQ(null); setErr(null); setEditing(false); load() }, [id])

  async function act(name, fn) {
    setBusy(name); setErr(null)
    try { const r = await fn(); if (r && r.id === id) setQ(r); else await load() } catch (e) { setErr(e) } finally { setBusy('') }
  }
  if (!q) return err ? <ErrorNote error={err} /> : <div className="text-sm text-ink-soft">Loading…</div>
  const d = q.current_draft
  const review = d?.review || {}
  const flags = review.flags || []
  const agents = d?.agents || {}

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="id">Q{q.id}</span><Status value={q.status} />
          <Tag>{q.intent.replaceAll('_', ' ')}</Tag>
          {q.scheme && <Tag>{q.scheme.replaceAll('_', ' ')}</Tag>}
          <span className="text-xs text-ink-faint">round {q.round} of 5 · {fmtTime(q.created_at)}</span>
        </div>
        <p className="text-base">{q.text_redacted}</p>
        {q.pii_types?.length > 0 && (
          <p className="text-xs text-blocked">Personal details ({q.pii_types.join(', ')}) were redacted before storage and before any agent saw this message.</p>
        )}
      </header>

      {d && (
        <div className={`panel border-l-4 p-5 ${d.passed ? 'border-l-verified' : 'border-l-blocked'}`}>
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-ink-soft">
            <span>Customer reply draft v{d.version}</span>
            {d.origin === 'canonical' && <Tag tone="good">reused approved canonical explainer #{d.canonical_id}</Tag>}
            {d.origin === 'correction' && <Tag tone="warn">{d.correction_name}</Tag>}
            {d.origin === 'human_edit' && <Tag>edited by reviewer</Tag>}
          </div>
          {editing ? (
            <div className="space-y-2">
              <textarea className="field font-serif text-[15px]" rows={5} value={editText} onChange={(e) => setEditText(e.target.value)} aria-label="Edit reply" />
              <p className="text-xs text-ink-soft">Keep the [n] markers next to each factual sentence. Your edit is reviewed again before it replaces the draft.</p>
              <div className="flex gap-2">
                <button className="btn-primary" disabled={!!busy} onClick={() => act('edit', async () => { const r = await api.editDraft(d.id, editText); setEditing(false); return r })}>Save edit</button>
                <button className="btn-quiet" onClick={() => setEditing(false)}>Cancel</button>
              </div>
            </div>
          ) : (
            <Reply text={d.reply} citations={d.citations} />
          )}
          <p className="mt-3 text-xs text-ink-soft">Last checked: {d.last_checked}</p>

          <div className="mt-4 flex flex-wrap gap-2">
            <button className="btn-approve" disabled={!q.approval_enabled || !!busy} onClick={() => act('approve', () => api.approveDraft(d.id))}
              title={q.approval_enabled ? '' : 'Approval is disabled until a draft passes review'}>Approve reply</button>
            <button className="btn-quiet" disabled={q.status !== 'ready' || !!busy} onClick={() => { setEditText(d.reply); setEditing(true) }}>Edit</button>
            <button className="btn-danger" disabled={['approved', 'rejected'].includes(q.status) || !!busy} onClick={() => setRejectOpen(true)}>Reject</button>
            {q.status === 'approved' && (
              <button className="btn-quiet" disabled={!!busy} onClick={() => act('log', () => api.proposeLog(d.id))}>Propose adding to support answers log</button>
            )}
          </div>
          {rejectOpen && (
            <div className="mt-3 flex gap-2">
              <button className="btn-danger" onClick={() => { setRejectOpen(false); act('reject', () => api.rejectDraft(d.id, '')) }}>Confirm reject</button>
              <button className="btn-quiet" onClick={() => setRejectOpen(false)}>Keep draft</button>
            </div>
          )}
          {busy && <p className="mt-2 text-xs text-pending">Working: {busy}…</p>}
        </div>
      )}
      <ErrorNote error={err} />

      <div className="grid gap-6 xl:grid-cols-2">
        <Section title="Reviewer">
          {flags.length === 0 ? (
            <p className="text-sm text-verified">Passed every hard check: citations resolve, numbers grounded, no advice, no performance figures, no personal data, within 3 sentences.</p>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-blocked">Approval is disabled. The draft failed review after the one allowed correction.</p>
              <ul className="space-y-1 text-sm">
                {flags.map((f, i) => (
                  <li key={i}><Tag tone="bad">{f.code}</Tag> <span className="text-ink-soft">{f.detail}</span>{f.sentence && <div className="ml-2 mt-0.5 font-serif text-xs italic">“{f.sentence}”</div>}</li>
                ))}
              </ul>
            </div>
          )}
        </Section>
        <Section title="Routing note (internal)">
          {d?.routing && (
            <div className="space-y-2 text-sm">
              <p><strong>{d.routing.team}</strong>{d.routing.also_notify?.length > 0 && <> + {d.routing.also_notify.join(', ')}</>} · <Tag tone={d.routing.priority === 'P1' ? 'bad' : d.routing.priority === 'P2' ? 'warn' : 'plain'}>{d.routing.priority}</Tag></p>
              {d.routing.disagreements?.map((x, i) => <p key={i} className="rounded-md bg-pending-tint px-3 py-2 text-pending">{x}</p>)}
              <ul className="list-disc pl-5 text-ink-soft">{d.routing.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
            </div>
          )}
        </Section>
      </div>

      {d?.citations?.length > 0 && (
        <Section title="Sources for this reply"><SourceList citations={d.citations} lastChecked={d.last_checked} /></Section>
      )}

      <AgentPanels agents={agents} />

      {['ready', 'blocked'].includes(q.status) && (
        <Section title="Ask for a revision" aside={<span className="text-xs text-ink-faint">{5 - q.round} of 5 rounds left</span>}>
          <div className="flex gap-2">
            <input className="field" value={feedback} onChange={(e) => setFeedback(e.target.value)} placeholder="e.g. Shorter, or: also mention the charge below ₹100" aria-label="Revision feedback" />
            <button className="btn-primary" disabled={!feedback.trim() || !!busy || q.round >= 5}
              onClick={() => act('revise', async () => { const r = await api.refine(q.id, feedback); setFeedback(''); return r })}>Revise</button>
          </div>
          <p className="text-xs text-ink-soft">Wording feedback reruns only the orchestrator and reviewer; feedback asking for more facts also reruns the Facts Agent.</p>
        </Section>
      )}

      <Section title="Draft history and agent runs">
        <div className="grid gap-4 xl:grid-cols-2">
          <ol className="space-y-2 text-sm">
            {q.drafts.map((x) => (
              <li key={x.id} className="rounded-md border border-rule bg-white px-3 py-2">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="id">v{x.version}</span><span>round {x.round}</span><Tag>{x.origin}</Tag>
                  <Tag tone={x.passed ? 'good' : 'bad'}>{x.passed ? 'passed' : 'failed'}</Tag>
                  {x.correction_name && <span className="id">{x.correction_name}</span>}
                </div>
                <p className="mt-1 font-serif text-[13px] text-ink-soft">{x.reply}</p>
              </li>
            ))}
          </ol>
          <table className="w-full text-left text-xs">
            <thead className="text-ink-faint"><tr><th className="py-1">Round</th><th>Agent</th><th>Status</th><th>ms</th><th>Output summary</th></tr></thead>
            <tbody>
              {q.agent_runs.map((r) => (
                <tr key={r.id} className="border-t border-rule align-top">
                  <td className="py-1">{r.round}</td><td>{r.agent}</td><td>{r.status}</td><td>{r.duration_ms}</td>
                  <td className="id break-all">{JSON.stringify(r.output_summary)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-ink-faint">Agent runs store a hash of the redacted input and a structured summary, never the message itself.</p>
      </Section>
    </div>
  )
}

function AgentPanels({ agents }) {
  const f = agents.facts, p = agents.pattern, c = agents.compliance
  if (!f) return null
  return (
    <Section title="What each agent found">
      <div className="grid gap-3 lg:grid-cols-3">
        <div className="panel p-4 text-sm">
          <h3 className="mb-1">Facts</h3>
          <p className={f.status === 'covered' ? 'text-verified' : 'text-pending'}>{f.status === 'covered' ? `${f.facts.length} verified fact(s)` : 'Not covered by official sources'}</p>
          {f.status !== 'covered' && (
            <p className="mt-1 text-xs text-ink-soft">Searched {f.searched?.corpus_size} official sources for: {(f.searched?.query_terms || []).slice(0, 12).join(', ')}. Closest sources: {(f.searched?.sources_considered || []).join(', ') || 'none'}.</p>
          )}
          {f.mode !== 'llm' && <p className="mt-1 text-xs text-pending">Mode: {f.mode}</p>}
        </div>
        <div className="panel p-4 text-sm">
          <h3 className="mb-1">Pattern</h3>
          <p className={p.classification === 'isolated' ? '' : 'text-pending'}>{p.classification[0].toUpperCase() + p.classification.slice(1)}</p>
          <p className="mt-1 text-xs text-ink-soft">{p.question_count_7d} similar question(s) in the last 7 days ({p.question_count_prev_7d} the week before). {p.review_count} matching reviews between {p.review_window?.start} and {p.review_window?.end}; {p.recent_review_count} in the last 4 weeks.</p>
          {p.matched_themes?.length > 0 && <p className="mt-1 text-xs">Pulse theme: {p.matched_themes.map((t) => `${t.theme} (${t.matching_reviews})`).join(', ')}</p>}
          {p.sample_review_ids?.length > 0 && <p className="mt-1 id">{p.sample_review_ids.join(', ')}</p>}
        </div>
        <div className="panel p-4 text-sm">
          <h3 className="mb-1">Compliance</h3>
          {c.flags.length ? <div className="flex flex-wrap gap-1">{c.flags.map((x) => <Tag key={x} tone="bad">{x}</Tag>)}</div> : <p className="text-verified">No policy flags</p>}
          <p className="mt-1 text-xs text-ink-soft">Scope: {c.allowed_scope.replaceAll('_', ' ')}{c.llm_used ? ' · rules + model check' : ' · rules only'}</p>
        </div>
      </div>
    </Section>
  )
}

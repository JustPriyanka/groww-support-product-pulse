import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { Empty, ErrorNote, Status, fmtTime } from './ui'

const KIND = {
  doc_append: 'Document append',
  email_draft: 'Email draft (never sent)',
  canonical_publish: 'Canonical answer',
}

export default function Approvals({ onChange }) {
  const [actions, setActions] = useState([])
  const [err, setErr] = useState(null)
  const load = () => api.actions().then((d) => setActions(d.actions)).catch(setErr)
  useEffect(() => { load() }, [])
  const pending = actions.filter((a) => a.status === 'pending')
  const done = actions.filter((a) => a.status !== 'pending')

  return (
    <div className="space-y-6">
      <div>
        <h1>Approvals</h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-soft">Each action shows exactly what will be written and where. Approving one runs that one action only, through the workspace MCP tool. Email is only ever saved as a draft.</p>
      </div>
      <ErrorNote error={err} />
      {!pending.length && <Empty>Nothing is waiting for approval.</Empty>}
      <div className="space-y-5">
        {pending.map((a) => <Receipt key={a.id} action={a} onDone={() => { load(); onChange?.() }} />)}
      </div>
      {done.length > 0 && (
        <section className="space-y-2">
          <h2>Decided</h2>
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-ink-faint"><tr><th className="py-1">Action</th><th>Status</th><th>Decided</th><th>Result</th></tr></thead>
            <tbody>
              {done.map((a) => (
                <tr key={a.id} className="border-t border-rule align-top">
                  <td className="py-1.5"><span className="id">A{a.id}</span> {a.title}</td>
                  <td><Status value={a.status} /></td>
                  <td className="text-xs">{fmtTime(a.decided_at)}</td>
                  <td className="id break-all">{a.result ? JSON.stringify(a.result) : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  )
}

function Receipt({ action: a, onDone }) {
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const p = a.payload

  async function run(fn) {
    setBusy(true); setErr(null)
    try { await fn(); onDone() } catch (e) { setErr(e) } finally { setBusy(false); setConfirming(false) }
  }

  return (
    <article className="panel overflow-hidden" aria-labelledby={`a${a.id}`}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule bg-pending-tint/60 px-5 py-3">
        <div>
          <h3 id={`a${a.id}`}>{a.title}</h3>
          <p className="text-xs text-ink-soft">{KIND[a.kind]} · proposed {fmtTime(a.created_at)} · from {a.source_type.replace('_', ' ')} {a.source_id}</p>
        </div>
        <Status value={a.status} />
      </div>
      <dl className="grid gap-x-6 gap-y-3 px-5 py-4 md:grid-cols-[140px_1fr]">
        <dt className="text-sm text-ink-soft">Where</dt>
        <dd className="text-sm font-medium">{a.target}</dd>
        {a.kind === 'doc_append' && (<><dt className="text-sm text-ink-soft">Entry title</dt><dd className="text-sm">{p.title}</dd></>)}
        {a.kind === 'email_draft' && (<><dt className="text-sm text-ink-soft">To</dt><dd className="text-sm">{p.to}</dd><dt className="text-sm text-ink-soft">Subject</dt><dd className="text-sm">{p.subject}</dd></>)}
        {a.kind === 'canonical_publish' && (<><dt className="text-sm text-ink-soft">Reused for</dt><dd className="text-sm">Customer questions about <strong>{p.fee_type.replaceAll('_', ' ')}</strong>{p.scheme_scope ? ` for ${p.scheme_scope}` : ' (any scheme / platform-wide)'}, only while sources {p.source_ids.join(', ')} are unchanged</dd></>)}
        <dt className="text-sm text-ink-soft">Exact content</dt>
        <dd>
          {a.kind === 'canonical_publish' ? (
            <div className="rounded-md border border-rule bg-paper p-3 font-serif text-[14px] leading-6">
              <p className="font-sans font-semibold">{p.title}</p>
              <ul className="mt-1 space-y-1">{p.bullets.map((b, i) => <li key={i}>• {b.text} {b.cites.map((n) => `[${n}]`).join('')}</li>)}</ul>
              <p className="mt-2 font-sans text-xs text-ink-soft">{p.citations.map((c) => `[${c.n}] ${c.url}`).join('  ')} · Last checked {p.last_checked}</p>
            </div>
          ) : (
            <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md border border-rule bg-paper p-3 font-serif text-[13px] leading-6">{p.body}</pre>
          )}
        </dd>
        <dt className="text-sm text-ink-soft">Fingerprint</dt>
        <dd className="id break-all">sha256 {a.payload_sha256}</dd>
      </dl>
      <div className="flex flex-wrap items-center gap-2 border-t border-rule px-5 py-3">
        {!confirming ? (
          <>
            <button className="btn-approve" disabled={busy} onClick={() => setConfirming(true)}>Approve this action</button>
            <button className="btn-danger" disabled={busy} onClick={() => run(() => api.rejectAction(a.id))}>Reject</button>
          </>
        ) : (
          <>
            <span className="text-sm">Write exactly this content to {a.kind === 'canonical_publish' ? 'the canonical answer store' : 'the workspace'}?</span>
            <button className="btn-approve" disabled={busy} onClick={() => run(() => api.approveAction(a.id, a.payload_sha256))}>{busy ? 'Writing…' : 'Yes, approve'}</button>
            <button className="btn-quiet" disabled={busy} onClick={() => setConfirming(false)}>Cancel</button>
          </>
        )}
      </div>
      {err && <div className="px-5 pb-4"><ErrorNote error={err} /></div>}
    </article>
  )
}

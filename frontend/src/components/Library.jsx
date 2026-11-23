import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { Empty, ErrorNote, MiniMarkdown, Section, SourceList, Status, Tag, fmtTime } from './ui'

export function Canonical({ openQuestion }) {
  const [rows, setRows] = useState(null)
  const [err, setErr] = useState(null)
  useEffect(() => { api.canonical().then((d) => setRows(d.canonical)).catch(setErr) }, [])
  return (
    <div className="space-y-6">
      <div>
        <h1>Canonical fee explainers</h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-soft">An explainer becomes the canonical answer only after its publish action is approved. It is reused for a new question only when the fee, scheme and official sources still match, and every reuse still passes the reviewer.</p>
      </div>
      <ErrorNote error={err} />
      {rows && !rows.length && <Empty>No canonical explainer yet. Approve a “Publish fee explainer” action on the Approvals screen.</Empty>}
      {rows?.map((c) => (
        <article key={c.id} className="panel space-y-4 p-5">
          <div className="flex flex-wrap items-center gap-2">
            <h2>{c.title}</h2>
            <Tag tone={c.active ? 'good' : 'plain'}>{c.active ? 'active' : 'superseded'}</Tag>
            <Tag>{c.fee_type.replaceAll('_', ' ')}</Tag><Tag>{c.scheme_scope || 'all schemes / platform-wide'}</Tag>
          </div>
          <ul className="space-y-1.5 font-serif text-[15px] leading-6">
            {c.bullets.map((b, i) => <li key={i}>• {b.text} {b.cites.map((n) => <sup key={n} className="font-sans text-verified">[{n}]</sup>)}</li>)}
          </ul>
          <SourceList citations={c.citations} lastChecked={c.last_checked} />
          <p className="text-xs text-ink-soft">Approved via action A{c.action_id} on {fmtTime(c.created_at)} · from pulse run {c.pulse_run_id} · last checked {c.last_checked}</p>
          <Section title={`Reused in ${c.reuses.length} repl${c.reuses.length === 1 ? 'y' : 'ies'}`}>
            {c.reuses.length ? (
              <ul className="space-y-1 text-sm">
                {c.reuses.map((r) => (
                  <li key={r.id}><button className="underline" onClick={() => openQuestion(r.question_id)}>Q{r.question_id}</button> · {r.text_redacted} <Status value={r.status} /></li>
                ))}
              </ul>
            ) : <p className="text-sm text-ink-soft">Not reused yet. Ask a matching question to see it used.</p>}
          </Section>
        </article>
      ))}
    </div>
  )
}

export function Sources() {
  const [rows, setRows] = useState([])
  useEffect(() => { api.sources().then((d) => setRows(d.sources)) }, [])
  const groups = rows.reduce((g, s) => ({ ...g, [s.publisher]: [...(g[s.publisher] || []), s] }), {})
  return (
    <div className="space-y-6">
      <div>
        <h1>Official sources</h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-soft">Every factual claim in a reply or explainer must cite a sentence from one of these {rows.length} public pages. Nothing else counts as evidence: no blogs, app screens or model memory.</p>
      </div>
      {Object.entries(groups).map(([pub, list]) => (
        <Section key={pub} title={`${pub} (${list.length})`}>
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-ink-faint"><tr><th className="py-1">Page</th><th>Type</th><th>Sentences</th><th>Last checked</th></tr></thead>
            <tbody>
              {list.map((s) => (
                <tr key={s.id} className="border-t border-rule">
                  <td className="py-1.5 pr-3"><a className="underline decoration-rule underline-offset-2 hover:decoration-ink" href={s.url} target="_blank" rel="noreferrer">{s.title}</a><div className="id">{s.id}</div></td>
                  <td>{s.type}</td><td>{s.sentences}</td><td>{s.fetched_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      ))}
    </div>
  )
}

export function Workspace() {
  const [w, setW] = useState(null)
  const [err, setErr] = useState(null)
  useEffect(() => { api.workspace().then(setW).catch(setErr) }, [])
  return (
    <div className="space-y-6">
      <div>
        <h1>Workspace</h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-soft">Documents and email drafts written by the workspace MCP server. Only approved actions appear here. The server has no tool to send email.</p>
      </div>
      <ErrorNote error={err} />
      {!w && !err && <p className="text-sm text-ink-soft">Loading from MCP server…</p>}
      {w && (
        <>
          {w.documents.map((d) => (
            <Section key={d.document} title={`${d.title} (${d.entries})`}>
              {w.contents[d.document].entries.length ? w.contents[d.document].entries.map((e) => (
                <article key={e.id} className="panel p-4">
                  <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-ink-soft"><strong className="text-sm text-ink">{e.title}</strong> · entry {e.id} · action A{e.action_id} · {fmtTime(e.created_at)}</div>
                  <MiniMarkdown text={e.body} />
                </article>
              )) : <Empty>No entries yet.</Empty>}
            </Section>
          ))}
          <Section title={`Email drafts (${w.email_drafts.length})`}>
            {w.email_drafts.length ? w.email_drafts.map((m) => (
              <article key={m.id} className="panel p-4">
                <div className="text-xs text-ink-soft">To: {m.to_label} · <Tag tone="warn">{m.status}, not sent</Tag> · action A{m.action_id} · {fmtTime(m.created_at)}</div>
                <h3 className="mt-1">{m.subject}</h3>
                <pre className="mt-2 whitespace-pre-wrap font-serif text-[13px] leading-6">{m.body}</pre>
              </article>
            )) : <Empty>No email drafts yet.</Empty>}
          </Section>
        </>
      )}
    </div>
  )
}

export function AgentRuns() {
  const [runs, setRuns] = useState([])
  useEffect(() => { api.agentRuns().then((d) => setRuns(d.runs)) }, [])
  return (
    <div className="space-y-4">
      <div>
        <h1>Agent runs</h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-soft">Which agents ran, in which round, and what they returned. Inputs are recorded only as a hash of the redacted text.</p>
      </div>
      <table className="w-full text-left text-xs">
        <thead className="text-ink-faint"><tr><th className="py-1">Run</th><th>Question</th><th>Round</th><th>Agent</th><th>Status</th><th>ms</th><th>Input hash</th><th>Output summary</th></tr></thead>
        <tbody>
          {runs.map((r) => (
            <tr key={r.id} className="border-t border-rule align-top">
              <td className="py-1">{r.id}</td><td>Q{r.question_id}</td><td>{r.round}</td><td>{r.agent}</td><td>{r.status}</td><td>{r.duration_ms}</td>
              <td className="id">{r.input_sha256?.slice(0, 12)}…</td><td className="id break-all">{JSON.stringify(r.output_summary)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

import React, { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { Empty, ErrorNote, MiniMarkdown, Section, SourceList, Status, Tag, fmtTime } from './ui'

export default function Pulse({ goApprovals }) {
  const [runs, setRuns] = useState([])
  const [runId, setRunId] = useState(null)
  const [run, setRun] = useState(null)
  const [err, setErr] = useState(null)
  const [days, setDays] = useState(7)
  const poll = useRef(null)

  const loadRuns = () => api.pulseRuns().then((d) => {
    setRuns(d.runs)
    if (!runId && d.runs.length) setRunId((d.runs.find((r) => r.status === 'completed') || d.runs[0]).id)
  })
  useEffect(() => { loadRuns().catch(setErr) }, [])
  useEffect(() => {
    clearInterval(poll.current)
    if (!runId) return
    const load = () => api.pulseRun(runId).then((r) => { setRun(r); if (r.status !== 'running') { clearInterval(poll.current); loadRuns() } })
    load()
    poll.current = setInterval(load, 4000)
    return () => clearInterval(poll.current)
  }, [runId])

  async function trigger() {
    setErr(null)
    try { const r = await api.runPulse(days); setRunId(r.run_id); loadRuns() } catch (e) { setErr(e) }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1>Weekly product pulse</h1>
          <p className="mt-1 max-w-2xl text-sm text-ink-soft">Runs every Monday at 09:00 IST, or now on demand. Analysis and drafts finish on their own; nothing is published until each action is approved.</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-ink-soft" htmlFor="days">Window</label>
          <select id="days" className="field w-auto" value={days} onChange={(e) => setDays(+e.target.value)}>
            <option value={7}>7 days</option><option value={14}>14 days</option><option value={28}>28 days</option>
          </select>
          <button className="btn-primary" onClick={trigger} disabled={run?.status === 'running'}>Run pulse now</button>
        </div>
      </div>
      <ErrorNote error={err} />
      {runs.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {runs.map((r) => (
            <button key={r.id} onClick={() => setRunId(r.id)} className={`rounded-md border px-2.5 py-1 text-xs ${runId === r.id ? 'border-ink bg-white' : 'border-rule'}`}>
              Run {r.id} · {r.trigger} · {r.window_start ? `${r.window_start} → ${r.window_end}` : fmtTime(r.created_at)} <Status value={r.status} />
            </button>
          ))}
        </div>
      )}
      {!run && <Empty>No pulse has run yet. Run one now to cluster this week's reviews.</Empty>}
      {run && <RunView run={run} goApprovals={goApprovals} />}
    </div>
  )
}

function RunView({ run, goApprovals }) {
  const [openTheme, setOpenTheme] = useState(null)
  const [reviews, setReviews] = useState({})
  const themes = run.themes?.themes || []
  const quotes = run.themes?.quotes || []
  const conf = run.fee_confusion || {}
  const exp = run.explainer?.draft
  const expReview = run.explainer?.review

  async function showReviews(t) {
    setOpenTheme(openTheme === t.id ? null : t.id)
    if (!reviews[t.id]) {
      const d = await api.reviews(t.review_ids.slice(0, 40))
      setReviews((r) => ({ ...r, [t.id]: d.reviews }))
    }
  }

  return (
    <div className="space-y-8">
      <Section title="Run steps">
        <ol className="flex flex-wrap gap-2 text-xs">
          {run.steps.map((s, i) => (
            <li key={i} className={`rounded-md border px-2 py-1 ${s.status === 'fail' ? 'border-blocked/40 text-blocked' : s.status === 'warn' ? 'border-pending/40 text-pending' : 'border-rule'}`}
              title={JSON.stringify(s.detail)}>{i + 1}. {s.step.replaceAll('_', ' ')}</li>
          ))}
        </ol>
        {run.status === 'running' && <p className="text-sm text-pending">Running… this page refreshes on its own.</p>}
        {run.error && <p className="text-sm text-blocked">{run.error}</p>}
      </Section>

      {run.status === 'completed' && (
        <>
          <div className="grid gap-6 xl:grid-cols-[1.1fr_1fr]">
            <Section title="Pulse draft" aside={<span className="text-xs text-ink-faint">{run.pulse.words} / 250 words</span>}>
              <div className="panel p-5"><MiniMarkdown text={run.pulse.markdown} /></div>
              <ReviewLine review={run.pulse.review} />
            </Section>
            <Section title="Fee explainer draft" aside={exp && <span className="text-xs text-ink-faint">{exp.bullets.length} / 6 bullets</span>}>
              {exp ? (
                <div className="panel space-y-4 p-5">
                  <h3>{exp.title}</h3>
                  <ul className="space-y-1.5 font-serif text-[15px] leading-6">
                    {exp.bullets.map((b, i) => <li key={i} className="flex gap-2"><span className="text-ink-faint">•</span><span>{b.text} {b.cites.map((n) => <sup key={n} className="font-sans text-verified">[{n}]</sup>)}</span></li>)}
                  </ul>
                  <SourceList citations={exp.citations} lastChecked={exp.last_checked} />
                  <p className="text-xs text-ink-soft">Last checked: {exp.last_checked}</p>
                </div>
              ) : <Empty>No explainer: {JSON.stringify(expReview?.flags || [])}</Empty>}
              {expReview && <ReviewLine review={expReview} />}
            </Section>
          </div>

          <Section title={`Themes · ${run.window_start} → ${run.window_end}`} aside={<span className="text-xs text-ink-faint">{run.stats.reviews_in_window} reviews, {run.stats.substantive} substantive · clustering: {run.themes.method}</span>}>
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-ink-faint"><tr><th className="py-1.5">Theme</th><th>Reviews</th><th>Avg rating</th><th>Evidence</th></tr></thead>
              <tbody>
                {themes.map((t, i) => (
                  <React.Fragment key={t.id}>
                    <tr className="border-t border-rule align-top">
                      <td className="py-2 pr-3"><span className="font-medium">{t.name}</span>{i < 3 && <Tag tone="good">top {i + 1}</Tag>}<div className="text-xs text-ink-soft">{t.description}</div></td>
                      <td>{t.count}</td><td>{t.avg_rating}★</td>
                      <td><button className="text-xs underline" onClick={() => showReviews(t)}>{openTheme === t.id ? 'Hide' : 'Show'} {t.review_ids.length} review IDs</button></td>
                    </tr>
                    {openTheme === t.id && (
                      <tr><td colSpan={4} className="pb-3">
                        <p className="id mb-2 break-all">{t.review_ids.join(', ')}</p>
                        <ul className="max-h-72 space-y-1 overflow-auto text-xs">
                          {(reviews[t.id] || []).map((r) => <li key={r.review_id}><a className="id underline" href={r.source_url} target="_blank" rel="noreferrer">{r.review_id}</a> {r.date} {r.rating}★ — {r.text}</li>)}
                        </ul>
                      </td></tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </Section>

          <div className="grid gap-6 xl:grid-cols-2">
            <Section title="Quotes (verbatim, de-identified)">
              <ul className="space-y-3">
                {quotes.map((q) => (
                  <li key={q.review_id}>
                    <blockquote className="font-serif italic">“{q.quote}”</blockquote>
                    <div className="mt-0.5 text-xs text-ink-soft"><a className="id underline" href={q.source_url} target="_blank" rel="noreferrer">{q.review_id}</a> · {q.rating}★ · {q.date} · {q.theme}</div>
                  </li>
                ))}
              </ul>
            </Section>
            <Section title="Fee confusion found in reviews">
              {conf.fee_type ? (
                <div className="space-y-2 text-sm">
                  <p><strong>{conf.label}</strong>: {conf.statement}</p>
                  <p className="text-xs text-ink-soft">{conf.count} reviews, {conf.window.start} → {conf.window.end}. Counts by fee: {Object.entries(conf.all_fee_counts).map(([k, v]) => `${k} ${v}`).join(', ')}</p>
                  <p className="id break-all">{conf.review_ids.join(', ')}</p>
                </div>
              ) : <Empty>No fee confusion detected in this window.</Empty>}
              <h3 className="pt-2">Repeated customer questions (5+ in a week)</h3>
              {run.signals?.length ? (
                <ul className="text-sm">{run.signals.map((s) => <li key={s.intent}><strong>{s.label}</strong> asked {s.count} times ({s.window.start} → {s.window.end}) · {s.team}</li>)}</ul>
              ) : <p className="text-sm text-ink-soft">No intent reached 5 questions in the last 7 days.</p>}
            </Section>
          </div>

          <Section title="Actions waiting for approval" aside={<button className="btn-quiet" onClick={goApprovals}>Open approvals</button>}>
            <ul className="space-y-1 text-sm">
              {run.actions.map((a) => <li key={a.id} className="flex items-center gap-2"><span className="id">A{a.id}</span>{a.title}<Status value={a.status} /></li>)}
            </ul>
          </Section>
        </>
      )}
    </div>
  )
}

function ReviewLine({ review }) {
  if (!review) return null
  return review.passed
    ? <p className="text-xs text-verified">Reviewer: passed ({Object.entries(review.checks || {}).map(([k, v]) => `${k} ${v}`).join(', ')})</p>
    : <p className="text-xs text-blocked">Reviewer flags: {review.flags.map((f) => `${f.code} (${f.detail})`).join('; ')}</p>
}

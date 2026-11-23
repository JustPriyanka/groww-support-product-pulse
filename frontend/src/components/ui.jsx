import React from 'react'

const STATUS = {
  ready: ['Ready for review', 'text-verified bg-verified-tint'],
  approved: ['Approved', 'text-white bg-verified'],
  blocked: ['Blocked by reviewer', 'text-blocked bg-blocked-tint'],
  rejected: ['Rejected', 'text-ink-soft bg-rule/60'],
  processing: ['Processing', 'text-pending bg-pending-tint'],
  pending: ['Waiting for approval', 'text-pending bg-pending-tint'],
  executed: ['Done', 'text-verified bg-verified-tint'],
  failed: ['Failed', 'text-blocked bg-blocked-tint'],
  running: ['Running', 'text-pending bg-pending-tint'],
  completed: ['Completed', 'text-verified bg-verified-tint'],
  interrupted: ['Interrupted', 'text-blocked bg-blocked-tint'],
}

export function Status({ value }) {
  const [label, cls] = STATUS[value] || [value, 'bg-rule text-ink']
  return <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${cls}`}>{label}</span>
}

export function Tag({ children, tone = 'plain' }) {
  const tones = {
    plain: 'border-rule text-ink-soft',
    warn: 'border-pending/40 text-pending',
    bad: 'border-blocked/40 text-blocked',
    good: 'border-verified/40 text-verified',
  }
  return <span className={`inline-block rounded border px-1.5 py-0.5 text-xs ${tones[tone]}`}>{children}</span>
}

export function ErrorNote({ error }) {
  if (!error) return null
  return (
    <div role="alert" className="rounded-md border border-blocked/30 bg-blocked-tint px-3 py-2 text-sm text-blocked">
      {error.message || String(error)}
      {error.data?.flags && (
        <ul className="mt-1 list-disc pl-5">
          {error.data.flags.map((f, i) => <li key={i}>{f.code}: {f.detail}</li>)}
        </ul>
      )}
    </div>
  )
}

export function Empty({ children }) {
  return <div className="rounded-lg border border-dashed border-rule px-5 py-8 text-center text-sm text-ink-soft">{children}</div>
}

/** Customer-facing reply: serif, citation markers become links to the official source. */
export function Reply({ text, citations = [] }) {
  const byN = Object.fromEntries(citations.map((c) => [c.n, c]))
  const parts = text.split(/(\[\d+\])/g)
  return (
    <p className="reply">
      {parts.map((p, i) => {
        const m = p.match(/^\[(\d+)\]$/)
        if (m && byN[m[1]]) {
          return (
            <a key={i} href={byN[m[1]].url} target="_blank" rel="noreferrer"
               className="mx-0.5 align-super text-[11px] font-sans font-medium text-verified underline decoration-dotted"
               title={`${byN[m[1]].publisher} — ${byN[m[1]].title}`}>{m[1]}</a>
          )
        }
        return <span key={i}>{p}</span>
      })}
    </p>
  )
}

/** Sources panel for factual claims: source, quoted sentence(s), last checked. */
export function SourceList({ citations = [], lastChecked }) {
  if (!citations.length) return null
  return (
    <ol className="space-y-3">
      {citations.map((c) => (
        <li key={c.n} className="flex gap-3">
          <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-verified-tint text-center text-xs font-semibold leading-5 text-verified">{c.n}</span>
          <div className="min-w-0">
            <a href={c.url} target="_blank" rel="noreferrer" className="text-sm font-medium underline decoration-rule underline-offset-2 hover:decoration-ink">
              {c.title}
            </a>
            <div className="text-xs text-ink-soft">{c.publisher} · last checked {c.last_checked || lastChecked}</div>
            {c.quotes?.slice(0, 3).map((q, i) => (
              <blockquote key={i} className="mt-1 border-l-2 border-rule pl-2 text-xs text-ink-soft">{q}</blockquote>
            ))}
          </div>
        </li>
      ))}
    </ol>
  )
}

/** Tiny renderer for the pulse/explainer markdown we generate (bold, quotes, lists). */
export function MiniMarkdown({ text }) {
  const inline = (s) => s.split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
    p.startsWith('**') ? <strong key={i} className="font-semibold">{p.slice(2, -2)}</strong> : <span key={i}>{p}</span>)
  return (
    <div className="space-y-1.5 text-sm leading-6">
      {text.split('\n').map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-1" />
        if (line.startsWith('### ')) return <h3 key={i} className="pt-1">{line.slice(4)}</h3>
        if (line.startsWith('> ')) return <blockquote key={i} className="border-l-2 border-verified/50 pl-3 font-serif italic text-ink">{inline(line.slice(2))}</blockquote>
        if (line.startsWith('- ')) return <div key={i} className="flex gap-2"><span className="text-ink-faint">•</span><span>{inline(line.slice(2))}</span></div>
        return <p key={i}>{inline(line)}</p>
      })}
    </div>
  )
}

export function Section({ title, children, aside }) {
  return (
    <section className="space-y-3">
      <div className="flex items-baseline justify-between gap-4">
        <h2>{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  )
}

export const fmtTime = (iso) => (iso ? new Date(iso).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '')

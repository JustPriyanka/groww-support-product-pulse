import React, { useEffect, useState } from 'react'
import { api, setPasscode } from './api'
import Ask from './components/Ask'
import Approvals from './components/Approvals'
import { AgentRuns, Canonical, Sources, Workspace } from './components/Library'
import Pulse from './components/Pulse'
import Queue from './components/Queue'

const VIEWS = [
  ['queue', 'Question queue'],
  ['ask', 'Ask'],
  ['pulse', 'Weekly pulse'],
  ['approvals', 'Approvals'],
  ['canonical', 'Canonical explainers'],
  ['sources', 'Sources'],
  ['workspace', 'Workspace'],
  ['runs', 'Agent runs'],
]

function readHash() {
  const [view, id] = window.location.hash.replace('#', '').split('/')
  return { view: VIEWS.some(([v]) => v === view) ? view : 'queue', id: id ? Number(id) : null }
}

export default function App() {
  const [{ view, id }, setRoute] = useState(readHash())
  const [meta, setMeta] = useState(null)
  const [stats, setStats] = useState(null)
  const [down, setDown] = useState(false)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const on = () => setRoute(readHash())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  useEffect(() => { api.meta().then(setMeta).catch(() => setDown(true)) }, [])
  useEffect(() => { api.stats().then(setStats).catch(() => {}) }, [view, tick])

  const go = (v, qid) => { window.location.hash = qid ? `${v}/${qid}` : v }
  const pending = stats?.actions?.pending || 0

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[232px_1fr]">
      <aside className="border-b border-rule bg-white lg:sticky lg:top-0 lg:h-screen lg:border-b-0 lg:border-r">
        <div className="px-5 pb-4 pt-6">
          <div className="text-[17px] font-semibold leading-tight">Groww support<br />& product pulse</div>
          <p className="mt-1 text-xs text-ink-soft">Internal review console</p>
        </div>
        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-col lg:overflow-visible">
          {VIEWS.map(([v, label]) => (
            <a key={v} href={`#${v}`} aria-current={view === v ? 'page' : undefined}
              className={`flex items-center justify-between whitespace-nowrap rounded-md px-3 py-2 text-sm ${view === v ? 'bg-ink text-paper' : 'text-ink hover:bg-paper'}`}>
              {label}
              {v === 'approvals' && pending > 0 && <span className={`ml-2 rounded px-1.5 text-xs ${view === v ? 'bg-paper text-ink' : 'bg-pending text-white'}`}>{pending}</span>}
            </a>
          ))}
        </nav>
        {meta && (
          <div className="hidden space-y-1 border-t border-rule px-5 py-4 text-xs text-ink-soft lg:block">
            <p>{meta.amc}: {Object.values(meta.schemes).length} schemes</p>
            <p>{meta.corpus.sources} official sources · checked {meta.corpus.last_checked}</p>
            <p>{meta.reviews.count.toLocaleString('en-IN')} Play Store reviews, {meta.reviews.window.start} → {meta.reviews.window.end}</p>
            <p>Next scheduled pulse: {meta.schedule.next_run ? new Date(meta.schedule.next_run).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '—'}</p>
            {meta.passcode_required && (
              <input className="field mt-2" type="password" placeholder="Reviewer passcode" aria-label="Reviewer passcode" onChange={(e) => setPasscode(e.target.value)} />
            )}
          </div>
        )}
      </aside>
      <main className="mx-auto w-full max-w-[1200px] px-5 py-8 lg:px-10">
        {down && (
          <div role="alert" className="mb-6 rounded-md border border-blocked/30 bg-blocked-tint px-4 py-3 text-sm text-blocked">
            The backend is not reachable. If it was asleep, wait a few seconds and reload.
          </div>
        )}
        {view === 'queue' && <Queue selectedId={id} onSelect={(q) => go('queue', q)} refreshKey={tick} />}
        {view === 'ask' && <Ask onCreated={(q) => { setTick((t) => t + 1); go('queue', q) }} />}
        {view === 'pulse' && <Pulse goApprovals={() => go('approvals')} />}
        {view === 'approvals' && <Approvals onChange={() => setTick((t) => t + 1)} />}
        {view === 'canonical' && <Canonical openQuestion={(q) => go('queue', q)} />}
        {view === 'sources' && <Sources />}
        {view === 'workspace' && <Workspace />}
        {view === 'runs' && <AgentRuns />}
      </main>
    </div>
  )
}

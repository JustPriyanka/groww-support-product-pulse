import React, { useState } from 'react'
import { api } from '../api'
import { useVoice } from '../voice/useVoice'
import { ErrorNote } from './ui'

const EXAMPLES = [
  'Why was a DP charge deducted when I sold my shares?',
  'Is there an exit load on HDFC Mid Cap Fund if I redeem after 6 months?',
  'How much brokerage does Groww charge per order?',
  'Should I buy HDFC Small Cap Fund now?',
]
const COMMAND = /^\s*(please\s+)?(approve|reject|publish|send|confirm|delete)\b/i

export default function Ask({ onCreated }) {
  const [text, setText] = useState('')
  const [channel, setChannel] = useState('typed')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const voice = useVoice()

  async function submit() {
    setBusy(true); setErr(null)
    try {
      const q = await api.ask(text, channel)
      setText(''); setChannel('typed')
      onCreated(q.id)
    } catch (e) { setErr(e) } finally { setBusy(false) }
  }

  const fromVoice = channel === 'voice'
  const looksLikeCommand = COMMAND.test(text)

  return (
    <div className="max-w-2xl space-y-5">
      <div>
        <h1>Ask a customer question</h1>
        <p className="mt-1 text-sm text-ink-soft">Type or dictate a question as a customer would ask it. Three agents check facts, patterns and compliance in parallel, then a reviewer checks the draft before you see it.</p>
      </div>

      <div className="panel space-y-3 p-4">
        <label htmlFor="q" className="text-sm font-medium">{fromVoice ? 'Review the transcript, fix any mistakes, then submit' : 'Question'}</label>
        <textarea id="q" className={`field ${fromVoice ? 'border-pending' : ''}`} rows={4} value={text} maxLength={2000}
          onChange={(e) => setText(e.target.value)} placeholder="e.g. Why was ₹20 deducted when I sold shares?" />
        {looksLikeCommand && (
          <p className="text-sm text-blocked">Voice and chat can't approve, reject or send anything. Use the buttons on the Approvals screen.</p>
        )}
        <div className="flex flex-wrap items-center gap-2">
          <button className="btn-primary" disabled={!text.trim() || busy || looksLikeCommand} onClick={submit}>
            {busy ? 'Running agents…' : 'Submit question'}
          </button>
          {voice.state === 'recording' ? (
            <button className="btn-danger" onClick={voice.stop}><span className="h-2 w-2 animate-pulse rounded-full bg-blocked" aria-hidden />Stop recording</button>
          ) : (
            <button className="btn-quiet" disabled={busy || voice.state === 'transcribing'}
              onClick={() => voice.start((t) => { setText(t); setChannel('voice') })}>
              {voice.state === 'transcribing' ? 'Transcribing on this device…' : 'Dictate with microphone'}
            </button>
          )}
          {voice.state === 'recording' && <span className="text-xs text-ink-soft">Recording (max {voice.maxSeconds}s)…</span>}
          {voice.progress != null && voice.state === 'transcribing' && voice.progress < 100 && <span className="text-xs text-ink-soft">Loading speech model {voice.progress}%</span>}
        </div>
        {voice.error && <p className="text-sm text-blocked">{voice.error}</p>}
        <p className="text-xs text-ink-faint">
          Speech is transcribed by a Whisper model running inside your browser. Audio never leaves this device and is discarded after transcription;
          the server only receives the text you submit, and redacts personal details before storing it. First use downloads the model (about 40 MB). English only.
        </p>
      </div>
      <ErrorNote error={err} />

      <div className="space-y-2">
        <p className="text-sm text-ink-soft">Try one:</p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((e) => <button key={e} className="btn-quiet text-left" onClick={() => { setText(e); setChannel('typed') }}>{e}</button>)}
        </div>
      </div>
    </div>
  )
}

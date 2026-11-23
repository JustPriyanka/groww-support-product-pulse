import { useEffect, useRef, useState } from 'react'

const MAX_SECONDS = 30

/** Records from the mic, decodes to 16 kHz mono PCM in memory, transcribes in a worker.
 *  Nothing is persisted: buffers are dropped as soon as the transcript is produced. */
export function useVoice() {
  const [state, setState] = useState('idle') // idle | loading-model | recording | transcribing | error
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState('')
  const worker = useRef(null)
  const rec = useRef(null)
  const timer = useRef(null)
  const onText = useRef(null)

  useEffect(() => () => { worker.current?.terminate(); clearTimeout(timer.current) }, [])

  function getWorker() {
    if (!worker.current) {
      worker.current = new Worker(new URL('./whisperWorker.js', import.meta.url), { type: 'module' })
      worker.current.onmessage = (e) => {
        const m = e.data
        if (m.type === 'progress' && m.progress != null) setProgress(Math.round(m.progress))
        if (m.type === 'ready') setState('idle')
        if (m.type === 'result') { setState('idle'); onText.current?.(m.text) }
        if (m.type === 'error') { setState('error'); setError(`Transcription failed: ${m.message}`) }
      }
    }
    return worker.current
  }

  async function start(cb) {
    onText.current = cb
    setError('')
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setState('error'); setError('This browser cannot record audio. Type your question instead.'); return
    }
    let stream
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }) } catch {
      setState('error'); setError('Microphone permission was denied. Allow it in the browser, or type your question.'); return
    }
    getWorker().postMessage({ type: 'load' }) // warm the model while recording
    const chunks = []
    const mr = new MediaRecorder(stream)
    mr.ondataavailable = (e) => e.data.size && chunks.push(e.data)
    mr.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop())
      setState('transcribing')
      try {
        const blob = new Blob(chunks, { type: mr.mimeType })
        chunks.length = 0
        const ctx = new AudioContext({ sampleRate: 16000 })
        const decoded = await ctx.decodeAudioData(await blob.arrayBuffer())
        const pcm = decoded.getChannelData(0).slice()
        ctx.close()
        getWorker().postMessage({ type: 'transcribe', audio: pcm }, [pcm.buffer])
      } catch (err) { setState('error'); setError('Could not read the recording. Try again or type instead.') }
    }
    rec.current = mr
    mr.start()
    setState('recording')
    timer.current = setTimeout(stop, MAX_SECONDS * 1000)
  }

  function stop() {
    clearTimeout(timer.current)
    if (rec.current && rec.current.state === 'recording') rec.current.stop()
  }

  return { state, progress, error, start, stop, maxSeconds: MAX_SECONDS }
}

/**
 * In-browser speech-to-text (Whisper tiny.en via transformers.js / ONNX in WASM/WebGPU).
 * Audio is processed entirely on this device: it is never uploaded, stored, or logged.
 * Only model weights are downloaded (once, then cached by the browser).
 */
import { pipeline, env } from '@huggingface/transformers'

env.allowLocalModels = false
let asr = null

async function load() {
  if (!asr) {
    asr = await pipeline('automatic-speech-recognition', 'Xenova/whisper-tiny.en', {
      progress_callback: (p) => self.postMessage({ type: 'progress', status: p.status, progress: p.progress ?? null, file: p.file }),
    })
  }
  return asr
}

self.onmessage = async (e) => {
  const { type, audio } = e.data
  try {
    if (type === 'load') {
      await load()
      self.postMessage({ type: 'ready' })
    } else if (type === 'transcribe') {
      const model = await load()
      const out = await model(audio, { chunk_length_s: 30 })
      self.postMessage({ type: 'result', text: (out.text || '').trim() })
    }
  } catch (err) {
    self.postMessage({ type: 'error', message: String(err && err.message ? err.message : err) })
  }
}

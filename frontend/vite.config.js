import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // Local dev: proxy /api to FastAPI on :8000 (same as the Zomato project)
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
  },
  worker: { format: 'es' },
  optimizeDeps: { exclude: ['@huggingface/transformers'] },
})

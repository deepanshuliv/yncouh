import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In development the FastAPI backend runs on :8000; in production it serves this build.
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: { output: { manualChunks: { charts: ['recharts'] } } },
    chunkSizeWarningLimit: 600,
  },
  server: {
    proxy: { '/api': 'http://localhost:8000' },
  },
})

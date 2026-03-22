import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:3025',
      '/downloads': 'http://localhost:3025',
      '/uploads': 'http://localhost:3025',
    },
  },
  build: {
    outDir: '../frontend-dist',
    emptyOutDir: true,
  },
})

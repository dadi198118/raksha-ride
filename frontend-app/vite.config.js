import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/riders': { target: 'http://localhost:8000', changeOrigin: true },
      '/pricing': { target: 'http://localhost:8000', changeOrigin: true },
      '/alerts':  { target: 'http://localhost:8000', changeOrigin: true },
      '/claims':  { target: 'http://localhost:8000', changeOrigin: true },
      '/cities':  { target: 'http://localhost:8000', changeOrigin: true },
      '/health':  { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
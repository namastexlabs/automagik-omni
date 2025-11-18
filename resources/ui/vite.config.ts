import path from "path"
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 9882,
    proxy: {
      '/api': {
        target: 'http://localhost:8882',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8882',
        changeOrigin: true,
      },
    },
  },
})

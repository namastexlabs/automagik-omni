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
    host: process.env.UI_HOST || '0.0.0.0',
    port: parseInt(process.env.UI_PORT || '9882', 10),
    strictPort: false, // Allow Vite to use a different port if the specified one is busy
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8882',
        changeOrigin: true,
      },
      '/health': {
        target: process.env.VITE_API_URL || 'http://localhost:8882',
        changeOrigin: true,
      },
    },
  },
})

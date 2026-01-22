import path from "path"
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import packageJson from './package.json'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(packageJson.version),
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: process.env.UI_HOST || '0.0.0.0',
    port: parseInt(process.env.UI_PORT || '9882', 10),
    strictPort: true, // Let Gateway handle port conflicts via PortRegistry
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

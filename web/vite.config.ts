import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'BoiAI — Gestão Bovina',
        short_name: 'BoiAI',
        theme_color: '#1a3a1a',
        background_color: '#ffffff',
        display: 'standalone',
        icons: [],
      },
    }),
  ],
  server: {
    proxy: {
      // Em dev, as chamadas da API vão para o backend local
      '/api': { target: 'http://localhost:8000', rewrite: (p) => p.replace(/^\/api/, '') },
    },
  },
})

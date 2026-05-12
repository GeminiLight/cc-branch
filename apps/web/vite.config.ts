import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import svgr from 'vite-plugin-svgr'

// https://vite.dev/config/
const apiTarget = process.env.CC_BRANCH_API_TARGET || 'http://127.0.0.1:5193'

export default defineConfig({
  plugins: [react(), tailwindcss(), svgr()],
  base: './',
  server: {
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})

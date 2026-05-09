import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import svgr from 'vite-plugin-svgr'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), svgr()],
  base: './',
  server: {
    proxy: process.env.CC_BRANCH_API_TARGET
      ? {
          '/api': {
            target: process.env.CC_BRANCH_API_TARGET,
            changeOrigin: true,
          },
        }
      : undefined,
  },
})

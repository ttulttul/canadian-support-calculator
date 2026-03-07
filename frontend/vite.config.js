import process from 'node:process'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(() => {
  const backendPort = process.env.BACKEND_PORT ?? '5001'

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': `http://127.0.0.1:${backendPort}`,
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: './src/test/setup.js',
    },
  }
})

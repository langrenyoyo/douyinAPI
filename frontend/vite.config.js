import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 8010,
    proxy: {
      '/health': 'http://127.0.0.1:8081',
      '/dashboard': 'http://127.0.0.1:8081',
      '/leads': 'http://127.0.0.1:8081',
      '/conversations': 'http://127.0.0.1:8081',
      '/quick-replies': 'http://127.0.0.1:8081',
      '/events': 'http://127.0.0.1:8081',
      '/api-call-logs': 'http://127.0.0.1:8081',
      '/auth-callback-records': 'http://127.0.0.1:8081',
      '/auth-token-records': 'http://127.0.0.1:8081',
      '/auth-status': 'http://127.0.0.1:8081',
      '/douyin': 'http://127.0.0.1:8081',
    },
  },
})

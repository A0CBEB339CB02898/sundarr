import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '')
  const apiTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8080'

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/health': apiTarget,
        '/search': apiTarget,
        '/discover': apiTarget,
        '/configuration': apiTarget,
        '/plugins': apiTarget,
        '/resources': apiTarget,
        '/resource-links': apiTarget,
        '/transfers': apiTarget,
        '/sources': apiTarget,
        '/settings': apiTarget,
        '/storage': apiTarget,
        '/media-libraries': apiTarget,
        '/remote-media-libraries': apiTarget,
        '/sync': apiTarget,
        '/download-to-local': apiTarget,
        '/worker': apiTarget,
      }
    }
  }
})

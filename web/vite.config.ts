import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/health': 'http://localhost:8080',
      '/search': 'http://localhost:8080',
      '/discover': 'http://localhost:8080',
      '/configuration': 'http://localhost:8080',
      '/plugins': 'http://localhost:8080',
      '/resources': 'http://localhost:8080',
      '/resource-links': 'http://localhost:8080',
      '/transfers': 'http://localhost:8080',
      '/sources': 'http://localhost:8080',
      '/settings': 'http://localhost:8080',
      '/storage': 'http://localhost:8080',
      '/media-libraries': 'http://localhost:8080',
      '/remote-media-libraries': 'http://localhost:8080',
      '/sync': 'http://localhost:8080',
      '/download-to-local': 'http://localhost:8080',
      '/worker': 'http://localhost:8080',
    }
  }
})

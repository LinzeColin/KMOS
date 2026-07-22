import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const shellModuleMarker = {
  name: 'kmfa-shell-module-marker',
  enforce: 'post',
  transformIndexHtml(html) {
    if (html.includes('id="kmfa-app-module"')) return html
    const marked = html.replace('<script type="module"', '<script id="kmfa-app-module" type="module"')
    if (marked === html) throw new Error('KMFA public shell module script is missing')
    return marked
  },
}

export default defineConfig({
  plugins: [react(), shellModuleMarker],
  base: '/',
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/public-api': 'http://127.0.0.1:8000',
      '/healthz': 'http://127.0.0.1:8000',
    },
  },
})

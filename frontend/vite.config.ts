import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    visualizer({
      filename: './dist/stats.html',
      open: false,
      gzipSize: true,
      brotliSize: true,
    }),
  ],
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            // Core React libraries
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router-dom')) {
              return 'vendor-react'
            }
            // React Query
            if (id.includes('@tanstack/react-query')) {
              return 'vendor-query'
            }
            // UI libraries
            if (id.includes('lucide-react') || id.includes('@ionic/react')) {
              return 'vendor-ui'
            }
            // QR libraries (heavy)
            if (id.includes('html5-qrcode') || id.includes('qrcode')) {
              return 'vendor-qr'
            }
          }
        },
      },
    },
    chunkSizeWarningLimit: 500,
    cssCodeSplit: true,
  },
  server: {
    host: true,
    port: 3000,
    strictPort: false,
    proxy: {
      '/api': 'http://localhost:8000',
      '/media': 'http://localhost:8000',
    },
  }
})

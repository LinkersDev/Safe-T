import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    // NOTE: Simplified - defer chunk optimization until profiling shows benefit
    // Premature manualChunks can increase mobile startup overhead
  },
  server: {
    port: 3000,
    strictPort: false
  }
})

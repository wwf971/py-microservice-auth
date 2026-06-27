import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const dirCurrent = dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [react()],
  resolve: {
    dedupe: ['react', 'react-dom'],
    alias: {
      react: resolve(dirCurrent, 'node_modules/react'),
      'react-dom': resolve(dirCurrent, 'node_modules/react-dom'),
      'react/jsx-runtime': resolve(dirCurrent, 'node_modules/react/jsx-runtime.js'),
      'react/jsx-dev-runtime': resolve(dirCurrent, 'node_modules/react/jsx-dev-runtime.js'),
    },
  },
  build: {
    outDir: 'build',
  },
  base: '/manage/',
})

import { defineConfig } from 'vitest/config'

// Test config kept separate from vite.config.ts so the production `tsc -b`
// build does not need vitest's types. esbuild's automatic JSX runtime is set
// explicitly so .tsx test files don't need a React import (and don't depend on
// the app's Vite plugin pipeline under the test runner).
export default defineConfig({
  esbuild: { jsx: 'automatic' },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['tests/**/*.test.{ts,tsx}'],
    setupFiles: './tests/setup.ts',
    css: false,
  },
})

import { defineConfig } from 'vite';

export default defineConfig({
  base: './',
  server: {
    port: 5188,
    // photo → VRM jobs run in the local Python pipeline (template/server.py)
    proxy: { '/api': 'http://127.0.0.1:5189' },
  },
});

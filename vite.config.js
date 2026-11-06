import { defineConfig } from 'vite';
export default defineConfig({ build: { assetsInlineLimit: 0 }, server: { proxy: { '/api': 'http://127.0.0.1:4321' } } });

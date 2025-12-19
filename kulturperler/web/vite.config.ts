import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		port: 4242
	},
	preview: {
		port: 4243
	},
	optimizeDeps: {
		exclude: ['sql.js']
	},
	build: {
		target: 'esnext'
	}
});

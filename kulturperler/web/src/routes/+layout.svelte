<script lang="ts">
	import { onMount } from 'svelte';
	import { initDatabase } from '$lib/db';

	let loading = true;
	let error: string | null = null;

	onMount(async () => {
		try {
			await initDatabase();
			loading = false;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load database';
			loading = false;
		}
	});
</script>

<svelte:head>
	<link rel="preconnect" href="https://gfx.nrk.no" />
</svelte:head>

<div class="app">
	<header>
		<nav>
			<a href="/" class="logo">Kulturperler</a>
			<span class="tagline">NRK Fjernsynsteatret 1960-1999</span>
		</nav>
	</header>

	<main>
		{#if loading}
			<div class="loading">
				<p>Laster database...</p>
			</div>
		{:else if error}
			<div class="error">
				<p>Feil: {error}</p>
			</div>
		{:else}
			<slot />
		{/if}
	</main>

	<footer>
		<p>
			Data fra <a href="https://tv.nrk.no" target="_blank" rel="noopener">NRK TV</a>.
			Beriket med data fra <a href="https://sceneweb.no" target="_blank" rel="noopener">Sceneweb</a>
			og <a href="https://www.wikidata.org" target="_blank" rel="noopener">Wikidata</a>.
		</p>
	</footer>
</div>

<style>
	:global(*) {
		box-sizing: border-box;
		margin: 0;
		padding: 0;
	}

	:global(body) {
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
		line-height: 1.6;
		color: #333;
		background: #f5f5f5;
	}

	.app {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	header {
		background: #1a1a2e;
		color: white;
		padding: 1rem 2rem;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	}

	nav {
		max-width: 1400px;
		margin: 0 auto;
		display: flex;
		align-items: baseline;
		gap: 1rem;
	}

	.logo {
		font-size: 1.5rem;
		font-weight: bold;
		color: white;
		text-decoration: none;
	}

	.logo:hover {
		color: #e94560;
	}

	.tagline {
		font-size: 0.9rem;
		opacity: 0.7;
	}

	main {
		flex: 1;
		max-width: 1400px;
		margin: 0 auto;
		padding: 2rem;
		width: 100%;
	}

	.loading, .error {
		text-align: center;
		padding: 4rem;
	}

	.error {
		color: #e94560;
	}

	footer {
		background: #1a1a2e;
		color: white;
		padding: 1rem 2rem;
		text-align: center;
		font-size: 0.85rem;
	}

	footer a {
		color: #e94560;
	}

	@media (max-width: 768px) {
		nav {
			flex-direction: column;
			gap: 0.25rem;
		}

		main {
			padding: 1rem;
		}
	}
</style>

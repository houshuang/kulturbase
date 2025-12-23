<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { initDatabase } from '$lib/db';
	import SearchBox from '$lib/components/SearchBox.svelte';

	let loading = true;
	let error: string | null = null;
	let dbReady = false;

	$: currentPath = $page.url.pathname;

	// Navigation items with content-type organization
	const navItems = [
		{ href: '/', label: 'Hjem', exact: true },
		{ href: '/teater', label: 'Teater' },
		{ href: '/opera', label: 'Opera/Ballett' },
		{ href: '/dramaserier', label: 'Dramaserier' },
		{ href: '/kulturprogrammer', label: 'Kulturprogrammer' },
		{ href: '/konserter', label: 'Konserter' },
		{ href: '/forfattere', label: 'Personer' }
	];

	function isActive(href: string, exact = false): boolean {
		if (exact) return currentPath === href;
		return currentPath === href || currentPath.startsWith(href + '/');
	}

	onMount(async () => {
		try {
			await initDatabase();
			dbReady = true;
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
		<div class="header-content">
			<a href="/" class="logo">Kulturbase.no</a>
			<nav class="main-nav">
				{#each navItems as item}
					<a
						href={item.href}
						class="nav-link"
						class:active={isActive(item.href, item.exact)}
					>
						{item.label}
					</a>
				{/each}
			</nav>
			<div class="header-spacer"></div>
			<a href="/om" class="nav-link nav-link-secondary" class:active={currentPath === '/om'}>Om</a>
			{#if dbReady}
				<SearchBox placeholder="Søk..." />
			{/if}
		</div>
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
		padding: 0.75rem 2rem;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
		position: sticky;
		top: 0;
		z-index: 100;
	}

	.header-content {
		max-width: 1400px;
		margin: 0 auto;
		display: flex;
		align-items: center;
		gap: 2rem;
	}

	.logo {
		font-size: 1.25rem;
		font-weight: bold;
		color: white;
		text-decoration: none;
		white-space: nowrap;
	}

	.logo:hover {
		color: #e94560;
	}

	.main-nav {
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	.header-spacer {
		flex: 1;
	}

	.nav-link {
		color: rgba(255, 255, 255, 0.8);
		text-decoration: none;
		padding: 0.5rem 1rem;
		border-radius: 6px;
		font-size: 0.95rem;
		font-weight: 500;
		transition: all 0.15s;
	}

	.nav-link:hover {
		color: white;
		background: rgba(255, 255, 255, 0.1);
	}

	.nav-link.active {
		color: white;
		background: #e94560;
	}

	.nav-link-secondary {
		color: rgba(255, 255, 255, 0.6);
	}

	.nav-link-secondary:hover {
		color: rgba(255, 255, 255, 0.9);
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

	@media (max-width: 900px) {
		header {
			padding: 0.5rem 1rem;
		}

		.header-content {
			flex-wrap: wrap;
			gap: 0.5rem;
		}

		.header-spacer {
			display: none;
		}

		.main-nav {
			flex-wrap: wrap;
			gap: 0.25rem;
			order: 3;
			width: 100%;
		}

		.nav-link {
			padding: 0.4rem 0.75rem;
			font-size: 0.85rem;
		}

		main {
			padding: 1rem;
		}
	}
</style>

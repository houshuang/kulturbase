<script lang="ts">
	import { onMount } from 'svelte';
	import { getDb } from '$lib/db';
	import type { ExternalResource } from '$lib/types';

	let concerts: ExternalResource[] = [];
	let loading = true;
	let composerFilter = '';
	let composers: string[] = [];

	onMount(async () => {
		const db = getDb();
		if (!db) return;

		// Get all concert resources
		const results = db.exec(`
			SELECT id, url, title, type, description, added_date, is_working
			FROM external_resources
			WHERE type = 'bergenphilive'
			ORDER BY title
		`);

		if (results.length > 0) {
			concerts = results[0].values.map((row: any[]) => ({
				id: row[0],
				url: row[1],
				title: row[2],
				type: row[3],
				description: row[4],
				added_date: row[5],
				is_working: row[6]
			}));

			// Extract unique composers from titles (format: "Composer: Work")
			const composerSet = new Set<string>();
			concerts.forEach(c => {
				if (c.title.includes(':')) {
					const composer = c.title.split(':')[0].trim();
					if (composer) composerSet.add(composer);
				}
			});
			composers = Array.from(composerSet).sort();
		}

		loading = false;
	});

	$: filteredConcerts = composerFilter
		? concerts.filter(c => c.title.toLowerCase().startsWith(composerFilter.toLowerCase()))
		: concerts;
</script>

<svelte:head>
	<title>Konserter | Kulturbase.no</title>
</svelte:head>

<div class="konserter-page">
	<header class="page-header">
		<h1>Konserter</h1>
		<p class="subtitle">Konserter fra Bergen Filharmoniske Orkester og andre</p>
	</header>

	{#if loading}
		<div class="loading">Laster konserter...</div>
	{:else}
		<div class="filters">
			<div class="filter-group">
				<label for="composer">Komponist</label>
				<select id="composer" bind:value={composerFilter}>
					<option value="">Alle komponister</option>
					{#each composers as composer}
						<option value={composer}>{composer}</option>
					{/each}
				</select>
			</div>
		</div>

		<div class="stats">
			<span class="stat">{filteredConcerts.length} konserter</span>
			{#if composerFilter}
				<button class="clear-filter" on:click={() => composerFilter = ''}>Nullstill filter</button>
			{/if}
		</div>

		<div class="concerts-grid">
			{#each filteredConcerts as concert}
				<a href={concert.url} target="_blank" rel="noopener" class="concert-card">
					<div class="card-icon">Konsert</div>
					<div class="card-content">
						<h3>{concert.title}</h3>
						{#if concert.description}
							<p class="description">{concert.description}</p>
						{/if}
						<div class="meta">
							<span class="source">Bergen Filharmoniske</span>
							<span class="external">Se konsert ↗</span>
						</div>
					</div>
				</a>
			{/each}
		</div>
	{/if}
</div>

<style>
	.konserter-page {
		max-width: 1400px;
		margin: 0 auto;
	}

	.page-header {
		margin-bottom: 1.5rem;
	}

	.page-header h1 {
		font-size: 2rem;
		margin-bottom: 0.5rem;
	}

	.subtitle {
		color: #666;
		font-size: 1.1rem;
	}

	.filters {
		background: white;
		padding: 1rem;
		border-radius: 8px;
		margin-bottom: 1.5rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.filter-group {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.filter-group label {
		font-weight: 500;
		color: #333;
	}

	.filter-group select {
		padding: 0.5rem 1rem;
		border: 1px solid #ddd;
		border-radius: 6px;
		font-size: 0.95rem;
		min-width: 200px;
	}

	.stats {
		margin-bottom: 1.5rem;
		color: #666;
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.stat {
		background: #e8e8e8;
		padding: 0.25rem 0.75rem;
		border-radius: 4px;
		font-size: 0.9rem;
	}

	.clear-filter {
		background: none;
		border: none;
		color: #e94560;
		cursor: pointer;
		font-size: 0.9rem;
	}

	.clear-filter:hover {
		text-decoration: underline;
	}

	.loading {
		text-align: center;
		padding: 4rem;
		color: #666;
	}

	.concerts-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
		gap: 1rem;
	}

	.concert-card {
		background: white;
		border-radius: 8px;
		overflow: hidden;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
		display: flex;
	}

	.concert-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
	}

	.card-icon {
		width: 80px;
		min-height: 80px;
		background: linear-gradient(135deg, #1a1a2e, #16213e);
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
		font-weight: bold;
		font-size: 0.85rem;
	}

	.card-content {
		padding: 0.75rem 1rem;
		flex: 1;
		display: flex;
		flex-direction: column;
	}

	.card-content h3 {
		font-size: 0.95rem;
		margin-bottom: 0.25rem;
		line-height: 1.3;
	}

	.description {
		color: #666;
		font-size: 0.8rem;
		margin-bottom: 0.5rem;
		flex: 1;
	}

	.meta {
		display: flex;
		gap: 0.75rem;
		font-size: 0.75rem;
		color: #888;
	}

	.source {
		background: #f0f0f0;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
	}

	.external {
		color: #e94560;
	}
</style>

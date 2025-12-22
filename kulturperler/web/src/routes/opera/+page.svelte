<script lang="ts">
	import { onMount } from 'svelte';
	import { getDb } from '$lib/db';
	import type { ExternalResource } from '$lib/types';

	let resources: ExternalResource[] = [];
	let loading = true;

	onMount(async () => {
		const db = getDb();
		if (!db) return;

		// Get opera resources from external_resources
		const results = db.exec(`
			SELECT id, url, title, type, description, added_date, is_working
			FROM external_resources
			WHERE type = 'operavision'
			ORDER BY title
		`);

		if (results.length > 0) {
			resources = results[0].values.map((row: any[]) => ({
				id: row[0],
				url: row[1],
				title: row[2],
				type: row[3],
				description: row[4],
				added_date: row[5],
				is_working: row[6]
			}));
		}

		loading = false;
	});
</script>

<svelte:head>
	<title>Opera | Kulturbase.no</title>
</svelte:head>

<div class="opera-page">
	<header class="page-header">
		<h1>Opera</h1>
		<p class="subtitle">Operaopptak fra OperaVision og andre kilder</p>
	</header>

	{#if loading}
		<div class="loading">Laster operaer...</div>
	{:else}
		<div class="stats">
			<span class="stat">{resources.length} operaer</span>
		</div>

		{#if resources.length === 0}
			<div class="empty-state">
				<p>Ingen operaer i arkivet ennå.</p>
				<p class="hint">Vi jobber med å legge til operainnhold fra OperaVision og andre kilder.</p>
			</div>
		{:else}
			<div class="resources-grid">
				{#each resources as resource}
					<a href={resource.url} target="_blank" rel="noopener" class="resource-card">
						<div class="card-icon">Opera</div>
						<div class="card-content">
							<h3>{resource.title}</h3>
							{#if resource.description}
								<p class="description">{resource.description}</p>
							{/if}
							<div class="meta">
								<span class="source">{resource.type}</span>
								<span class="external">Ekstern lenke ↗</span>
							</div>
						</div>
					</a>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<style>
	.opera-page {
		max-width: 1400px;
		margin: 0 auto;
	}

	.page-header {
		margin-bottom: 2rem;
	}

	.page-header h1 {
		font-size: 2rem;
		margin-bottom: 0.5rem;
	}

	.subtitle {
		color: #666;
		font-size: 1.1rem;
	}

	.stats {
		margin-bottom: 1.5rem;
		color: #666;
	}

	.stat {
		background: #e8e8e8;
		padding: 0.25rem 0.75rem;
		border-radius: 4px;
		font-size: 0.9rem;
	}

	.loading {
		text-align: center;
		padding: 4rem;
		color: #666;
	}

	.empty-state {
		text-align: center;
		padding: 4rem;
		background: white;
		border-radius: 8px;
		color: #666;
	}

	.hint {
		font-size: 0.9rem;
		margin-top: 1rem;
	}

	.resources-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 1.5rem;
	}

	.resource-card {
		background: white;
		border-radius: 8px;
		overflow: hidden;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
		display: flex;
	}

	.resource-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
	}

	.card-icon {
		width: 100px;
		min-height: 100px;
		background: linear-gradient(135deg, #8b0000, #4a0000);
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
		font-weight: bold;
	}

	.card-content {
		padding: 1rem;
		flex: 1;
	}

	.card-content h3 {
		font-size: 1rem;
		margin-bottom: 0.5rem;
		line-height: 1.3;
	}

	.description {
		color: #666;
		font-size: 0.85rem;
		margin-bottom: 0.5rem;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.meta {
		display: flex;
		gap: 0.75rem;
		font-size: 0.8rem;
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

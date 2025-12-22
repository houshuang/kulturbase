<script lang="ts">
	import { onMount } from 'svelte';
	import { getDb } from '$lib/db';
	import type { PerformanceWithDetails } from '$lib/types';

	let performances: PerformanceWithDetails[] = [];
	let loading = true;

	onMount(async () => {
		const db = getDb();
		if (!db) return;

		// Get all theater performances (teaterstykke + nrk_teaterstykke)
		const results = db.exec(`
			SELECT DISTINCT
				p.id,
				p.work_id,
				p.year,
				p.title as performance_title,
				p.description,
				p.venue,
				p.total_duration,
				p.image_url,
				p.medium,
				w.title as work_title,
				w.work_type,
				w.category,
				author.name as playwright_name,
				author.id as playwright_id,
				director.name as director_name,
				(SELECT COUNT(*) FROM episodes e WHERE e.performance_id = p.id) as media_count
			FROM performances p
			LEFT JOIN works w ON p.work_id = w.id
			LEFT JOIN persons author ON w.playwright_id = author.id
			LEFT JOIN performance_persons pp ON pp.performance_id = p.id AND pp.role = 'director'
			LEFT JOIN persons director ON pp.person_id = director.id
			WHERE w.category = 'teater' OR w.work_type IN ('teaterstykke', 'nrk_teaterstykke')
			ORDER BY p.year DESC, w.title
		`);

		if (results.length > 0) {
			performances = results[0].values.map((row: any[]) => ({
				id: row[0],
				work_id: row[1],
				year: row[2],
				title: row[3],
				description: row[4],
				venue: row[5],
				total_duration: row[6],
				image_url: row[7],
				medium: row[8],
				work_title: row[9],
				work_type: row[10],
				category: row[11],
				playwright_name: row[12],
				playwright_id: row[13],
				director_name: row[14],
				media_count: row[15]
			}));
		}

		loading = false;
	});

	function formatDuration(seconds: number | null): string {
		if (!seconds) return '';
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		if (hours > 0) return `${hours}t ${minutes}m`;
		return `${minutes}m`;
	}
</script>

<svelte:head>
	<title>Teater | Kulturbase.no</title>
</svelte:head>

<div class="teater-page">
	<header class="page-header">
		<h1>Teater</h1>
		<p class="subtitle">Teaterstykker fra NRK Fjernsynsteatret og Radioteatret</p>
	</header>

	{#if loading}
		<div class="loading">Laster teateropptak...</div>
	{:else}
		<div class="stats">
			<span class="stat">{performances.length} opptak</span>
		</div>

		<div class="performances-grid">
			{#each performances as perf}
				<a href="/performance/{perf.id}" class="performance-card">
					{#if perf.image_url}
						<img src={perf.image_url} alt={perf.work_title || perf.title || ''} />
					{:else}
						<div class="no-image">Teater</div>
					{/if}
					<div class="card-content">
						<h3>{perf.work_title || perf.title}</h3>
						{#if perf.playwright_name}
							<p class="playwright">{perf.playwright_name}</p>
						{/if}
						<div class="meta">
							{#if perf.year}
								<span class="year">{perf.year}</span>
							{/if}
							{#if perf.medium}
								<span class="medium">{perf.medium === 'tv' ? 'TV' : 'Radio'}</span>
							{/if}
							{#if perf.total_duration}
								<span class="duration">{formatDuration(perf.total_duration)}</span>
							{/if}
						</div>
					</div>
				</a>
			{/each}
		</div>
	{/if}
</div>

<style>
	.teater-page {
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

	.performances-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
		gap: 1.5rem;
	}

	.performance-card {
		background: white;
		border-radius: 8px;
		overflow: hidden;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.performance-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
	}

	.performance-card img {
		width: 100%;
		height: 160px;
		object-fit: cover;
	}

	.no-image {
		width: 100%;
		height: 160px;
		background: linear-gradient(135deg, #1a1a2e, #16213e);
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.2rem;
	}

	.card-content {
		padding: 1rem;
	}

	.card-content h3 {
		font-size: 1rem;
		margin-bottom: 0.25rem;
		line-height: 1.3;
	}

	.playwright {
		color: #666;
		font-size: 0.9rem;
		margin-bottom: 0.5rem;
	}

	.meta {
		display: flex;
		gap: 0.5rem;
		font-size: 0.8rem;
		color: #888;
	}

	.medium {
		background: #f0f0f0;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
	}
</style>

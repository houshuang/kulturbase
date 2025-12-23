<script lang="ts">
	import { onMount } from 'svelte';
	import { getDb } from '$lib/db';
	import type { PerformanceWithDetails } from '$lib/types';

	let performances: PerformanceWithDetails[] = [];
	let loading = true;
	let selectedType = 'all';
	let selectedMedium = 'all';

	const programTypes = [
		{ value: 'all', label: 'Alle typer' },
		{ value: 'bokprogram', label: 'Bokprogram' },
		{ value: 'kulturmagasin', label: 'Kulturmagasin' },
		{ value: 'lyrikk', label: 'Lyrikk' },
		{ value: 'dokumentar', label: 'Dokumentar' }
	];

	const mediumOptions = [
		{ value: 'all', label: 'Alle medier' },
		{ value: 'tv', label: 'TV' },
		{ value: 'radio', label: 'Radio' }
	];

	onMount(async () => {
		const db = getDb();
		if (!db) return;

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
				p.series_id,
				w.title as work_title,
				w.work_type,
				w.category,
				(SELECT COUNT(*) FROM episodes e WHERE e.performance_id = p.id) as media_count
			FROM performances p
			LEFT JOIN works w ON p.work_id = w.id
			WHERE w.category = 'kulturprogram'
			ORDER BY w.title, p.year DESC
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
				series_id: row[9],
				work_title: row[10],
				work_type: row[11],
				category: row[12],
				media_count: row[13]
			}));
		}

		loading = false;
	});

	$: filteredPerformances = performances.filter(p => {
		if (selectedMedium !== 'all' && p.medium !== selectedMedium) return false;
		if (selectedType !== 'all' && p.work_type !== selectedType) return false;
		return true;
	});

	function formatDuration(seconds: number | null): string {
		if (!seconds) return '';
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		if (hours > 0) return `${hours}t ${minutes}m`;
		return `${minutes}m`;
	}

	function getProgramTypeLabel(type: string | null): string {
		switch (type) {
			case 'bokprogram': return 'Bokprogram';
			case 'kulturmagasin': return 'Kulturmagasin';
			case 'lyrikk': return 'Lyrikk';
			case 'dokumentar': return 'Dokumentar';
			default: return 'Kulturprogram';
		}
	}
</script>

<svelte:head>
	<title>Kulturprogrammer | Kulturbase.no</title>
</svelte:head>

<div class="kulturprogrammer-page">
	<header class="page-header">
		<h1>Kulturprogrammer</h1>
		<p class="subtitle">Litteratur- og kulturprogrammer fra NRK-arkivet</p>
	</header>

	{#if loading}
		<div class="loading">Laster kulturprogrammer...</div>
	{:else}
		<div class="filters">
			<div class="filter-group">
				<label for="type-filter">Type:</label>
				<select id="type-filter" bind:value={selectedType}>
					{#each programTypes as type}
						<option value={type.value}>{type.label}</option>
					{/each}
				</select>
			</div>
			<div class="filter-group">
				<label for="medium-filter">Medium:</label>
				<select id="medium-filter" bind:value={selectedMedium}>
					{#each mediumOptions as medium}
						<option value={medium.value}>{medium.label}</option>
					{/each}
				</select>
			</div>
		</div>

		<div class="stats">
			<span class="stat">{filteredPerformances.length} programmer</span>
		</div>

		{#if filteredPerformances.length === 0}
			<div class="empty-state">
				<p>Ingen kulturprogrammer funnet.</p>
				<p class="hint">Programmer blir lagt til fortløpende.</p>
			</div>
		{:else}
			<div class="performances-grid">
				{#each filteredPerformances as perf}
					<a href="/opptak/{perf.id}" class="performance-card">
						{#if perf.image_url}
							<img src={perf.image_url} alt={perf.work_title || perf.title || ''} />
						{:else}
							<div class="no-image">{getProgramTypeLabel(perf.work_type)}</div>
						{/if}
						<div class="card-content">
							<h3>{perf.title || perf.work_title}</h3>
							<div class="meta">
								{#if perf.year}
									<span class="year">{perf.year}</span>
								{/if}
								{#if perf.medium}
									<span class="medium" class:tv={perf.medium === 'tv'} class:radio={perf.medium === 'radio'}>
										{perf.medium === 'tv' ? 'TV' : 'Radio'}
									</span>
								{/if}
								{#if perf.work_type}
									<span class="type-badge">{getProgramTypeLabel(perf.work_type)}</span>
								{/if}
								{#if perf.media_count && perf.media_count > 1}
									<span class="episodes">{perf.media_count} episoder</span>
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
	{/if}
</div>

<style>
	.kulturprogrammer-page {
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

	.filters {
		display: flex;
		gap: 1.5rem;
		margin-bottom: 1.5rem;
		flex-wrap: wrap;
	}

	.filter-group {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.filter-group label {
		color: #666;
		font-size: 0.9rem;
	}

	.filter-group select {
		padding: 0.4rem 0.8rem;
		border: 1px solid #ddd;
		border-radius: 4px;
		background: white;
		font-size: 0.9rem;
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

	.empty-state .hint {
		font-size: 0.9rem;
		margin-top: 0.5rem;
		opacity: 0.7;
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
		background: linear-gradient(135deg, #1a5f7a, #57c5b6);
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1rem;
	}

	.card-content {
		padding: 1rem;
		display: flex;
		flex-direction: column;
		min-height: 100px;
	}

	.card-content h3 {
		font-size: 1rem;
		margin-bottom: 0.5rem;
		line-height: 1.3;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		font-size: 0.8rem;
		color: #888;
		margin-top: auto;
	}

	.episodes {
		background: #1a5f7a;
		color: white;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
	}

	.type-badge {
		background: #e8e8e8;
		color: #555;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
	}

	.medium {
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
	}

	.medium.tv {
		background: #e94560;
		color: white;
	}

	.medium.radio {
		background: #6b5ce7;
		color: white;
	}
</style>

<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getDb } from '$lib/db';

	interface OperaPerformance {
		id: number;
		work_id: number | null;
		year: number | null;
		title: string | null;
		description: string | null;
		total_duration: number | null;
		image_url: string | null;
		work_title: string | null;
		work_type: string | null;
		composer_name: string | null;
		composer_id: number | null;
		librettist_name: string | null;
	}

	interface FilterCounts {
		types: Record<string, number>;
		composers: Record<string, { id: number; count: number }>;
	}

	let allPerformances: OperaPerformance[] = [];
	let filteredPerformances: OperaPerformance[] = [];
	let loading = true;
	let filterCounts: FilterCounts = { types: {}, composers: {} };

	// Filter state
	let selectedType: string = 'all';
	let selectedComposer: string = 'all';
	let sortBy: 'year-desc' | 'year-asc' | 'composer' | 'title' = 'year-desc';
	let showFilters = false;

	// Get unique types and composers
	$: types = Object.entries(filterCounts.types).sort((a, b) => b[1] - a[1]);
	$: composers = Object.entries(filterCounts.composers)
		.map(([name, data]) => ({ name, ...data }))
		.sort((a, b) => b.count - a.count);

	// Read filters from URL
	$: {
		const urlType = $page.url.searchParams.get('type');
		const urlComposer = $page.url.searchParams.get('composer');
		const urlSort = $page.url.searchParams.get('sort');

		selectedType = urlType || 'all';
		selectedComposer = urlComposer || 'all';

		if (urlSort === 'year-asc' || urlSort === 'composer' || urlSort === 'title') sortBy = urlSort;
		else sortBy = 'year-desc';
	}

	// Apply filters
	$: {
		let result = [...allPerformances];

		if (selectedType !== 'all') {
			result = result.filter(p => p.work_type === selectedType);
		}

		if (selectedComposer !== 'all') {
			result = result.filter(p => p.composer_name === selectedComposer);
		}

		// Sort
		if (sortBy === 'year-desc') {
			result.sort((a, b) => (b.year || 0) - (a.year || 0));
		} else if (sortBy === 'year-asc') {
			result.sort((a, b) => (a.year || 0) - (b.year || 0));
		} else if (sortBy === 'composer') {
			result.sort((a, b) => (a.composer_name || '').localeCompare(b.composer_name || '', 'no'));
		} else if (sortBy === 'title') {
			result.sort((a, b) => (a.work_title || a.title || '').localeCompare(b.work_title || b.title || '', 'no'));
		}

		filteredPerformances = result;
	}

	function updateUrl() {
		const params = new URLSearchParams();
		if (selectedType !== 'all') params.set('type', selectedType);
		if (selectedComposer !== 'all') params.set('composer', selectedComposer);
		if (sortBy !== 'year-desc') params.set('sort', sortBy);

		const query = params.toString();
		goto(`/opera${query ? '?' + query : ''}`, { replaceState: true, noScroll: true });
	}

	function setFilter(type: 'type' | 'composer', value: string) {
		if (type === 'type') selectedType = value;
		else if (type === 'composer') selectedComposer = value;
		updateUrl();
	}

	function resetFilters() {
		selectedType = 'all';
		selectedComposer = 'all';
		goto('/opera', { replaceState: true, noScroll: true });
	}

	$: hasActiveFilters = selectedType !== 'all' || selectedComposer !== 'all';

	onMount(async () => {
		const db = getDb();
		if (!db) return;

		// Get all opera/ballet performances
		const results = db.exec(`
			SELECT DISTINCT
				p.id,
				p.work_id,
				p.year,
				p.title as performance_title,
				p.description,
				p.total_duration,
				p.image_url,
				w.title as work_title,
				w.work_type,
				composer.name as composer_name,
				composer.id as composer_id,
				librettist.name as librettist_name
			FROM performances p
			LEFT JOIN works w ON p.work_id = w.id
			LEFT JOIN persons composer ON w.composer_id = composer.id
			LEFT JOIN persons librettist ON w.librettist_id = librettist.id
			WHERE w.work_type IN ('opera', 'operetta', 'ballet') OR w.category = 'opera'
			ORDER BY p.year DESC, w.title
		`);

		if (results.length > 0) {
			allPerformances = results[0].values.map((row: any[]) => ({
				id: row[0],
				work_id: row[1],
				year: row[2],
				title: row[3],
				description: row[4],
				total_duration: row[5],
				image_url: row[6],
				work_title: row[7],
				work_type: row[8],
				composer_name: row[9],
				composer_id: row[10],
				librettist_name: row[11]
			}));

			// Calculate filter counts
			const typeCounts: Record<string, number> = {};
			const composerCounts: Record<string, { id: number; count: number }> = {};

			for (const perf of allPerformances) {
				if (perf.work_type) {
					typeCounts[perf.work_type] = (typeCounts[perf.work_type] || 0) + 1;
				}
				if (perf.composer_name && perf.composer_id) {
					if (!composerCounts[perf.composer_name]) {
						composerCounts[perf.composer_name] = { id: perf.composer_id, count: 0 };
					}
					composerCounts[perf.composer_name].count++;
				}
			}

			filterCounts = { types: typeCounts, composers: composerCounts };
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

	function getImageUrl(url: string | null, width = 400): string {
		if (!url) return '';
		if (url.includes('gfx.nrk.no')) {
			return url.replace(/\/\d+$/, `/${width}`);
		}
		return url;
	}

	function getTypeLabel(type: string): string {
		const labels: Record<string, string> = {
			opera: 'Opera',
			operetta: 'Operette',
			ballet: 'Ballett'
		};
		return labels[type] || type;
	}
</script>

<svelte:head>
	<title>Opera & Ballett | Kulturbase.no</title>
</svelte:head>

<div class="opera-page">
	<header class="page-header">
		<h1>Opera & Ballett</h1>
		<p class="subtitle">Opera, operette og ballett fra NRK-arkivet</p>
	</header>

	{#if loading}
		<div class="loading">Laster opptak...</div>
	{:else}
		<div class="browse-layout">
			<!-- Filters sidebar -->
			<aside class="filters-sidebar" class:open={showFilters}>
				<div class="filters-header">
					<h2>Filter</h2>
					<button class="close-filters" on:click={() => showFilters = false}>×</button>
				</div>

				<!-- Type filter -->
				<div class="filter-group">
					<h3>Type</h3>
					<label class="filter-option">
						<input type="radio" name="type" checked={selectedType === 'all'} on:change={() => setFilter('type', 'all')} />
						<span>Alle</span>
						<span class="count">{allPerformances.length}</span>
					</label>
					{#each types as [type, count]}
						<label class="filter-option">
							<input type="radio" name="type" checked={selectedType === type} on:change={() => setFilter('type', type)} />
							<span>{getTypeLabel(type)}</span>
							<span class="count">{count}</span>
						</label>
					{/each}
				</div>

				<!-- Composer filter -->
				<div class="filter-group">
					<h3>Komponist</h3>
					<label class="filter-option">
						<input type="radio" name="composer" checked={selectedComposer === 'all'} on:change={() => setFilter('composer', 'all')} />
						<span>Alle</span>
						<span class="count">{allPerformances.length}</span>
					</label>
					<div class="scrollable-options">
						{#each composers as composer}
							<label class="filter-option">
								<input type="radio" name="composer" checked={selectedComposer === composer.name} on:change={() => setFilter('composer', composer.name)} />
								<span>{composer.name}</span>
								<span class="count">{composer.count}</span>
							</label>
						{/each}
					</div>
				</div>

				{#if hasActiveFilters}
					<button class="reset-filters" on:click={resetFilters}>
						Nullstill filter
					</button>
				{/if}
			</aside>

			<!-- Main content -->
			<main class="browse-content">
				<div class="browse-toolbar">
					<button class="filter-toggle" on:click={() => showFilters = !showFilters}>
						Filter {hasActiveFilters ? '(aktive)' : ''}
					</button>

					<div class="results-info">
						<span class="result-count">{filteredPerformances.length} opptak</span>
						{#if hasActiveFilters}
							<button class="clear-link" on:click={resetFilters}>Fjern filter</button>
						{/if}
					</div>

					<div class="sort-control">
						<label for="sort">Sorter:</label>
						<select id="sort" bind:value={sortBy} on:change={() => updateUrl()}>
							<option value="year-desc">Nyeste forst</option>
							<option value="year-asc">Eldste forst</option>
							<option value="composer">Komponist A-A</option>
							<option value="title">Tittel A-A</option>
						</select>
					</div>
				</div>

				<div class="opera-grid">
					{#each filteredPerformances as perf}
						<a href="/opptak/{perf.id}" class="opera-card">
							{#if perf.image_url}
								<img src={getImageUrl(perf.image_url)} alt={perf.work_title || perf.title || ''} loading="lazy" />
							{:else}
								<div class="no-image">
									<span class="icon">{getTypeLabel(perf.work_type || 'opera')}</span>
								</div>
							{/if}
							<div class="card-content">
								<h3>{perf.work_title || perf.title}</h3>
								{#if perf.composer_name}
									<p class="composer">{perf.composer_name}</p>
								{/if}
								<div class="meta">
									{#if perf.year}
										<span class="year">{perf.year}</span>
									{/if}
									{#if perf.work_type}
										<span class="type" class:opera={perf.work_type === 'opera'} class:ballet={perf.work_type === 'ballet'}>
											{getTypeLabel(perf.work_type)}
										</span>
									{/if}
									{#if perf.total_duration}
										<span class="duration">{formatDuration(perf.total_duration)}</span>
									{/if}
								</div>
							</div>
						</a>
					{/each}
				</div>

				{#if filteredPerformances.length === 0}
					<div class="no-results">
						<p>Ingen opptak matcher filtrene dine.</p>
						<button on:click={resetFilters}>Fjern filter</button>
					</div>
				{/if}
			</main>
		</div>
	{/if}
</div>

<!-- Backdrop for mobile filters -->
{#if showFilters}
	<button class="filters-backdrop" on:click={() => showFilters = false} aria-label="Lukk filter"></button>
{/if}

<style>
	.opera-page {
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

	.loading {
		text-align: center;
		padding: 4rem;
		color: #666;
	}

	/* Browse layout */
	.browse-layout {
		display: grid;
		grid-template-columns: 240px 1fr;
		gap: 2rem;
	}

	/* Filters sidebar */
	.filters-sidebar {
		background: white;
		border-radius: 8px;
		padding: 1.5rem;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
		height: fit-content;
		position: sticky;
		top: 1rem;
	}

	.filters-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.filters-header h2 {
		font-size: 1.1rem;
		margin: 0;
	}

	.close-filters {
		display: none;
		background: none;
		border: none;
		font-size: 1.5rem;
		cursor: pointer;
		color: #666;
	}

	.filter-group {
		margin-bottom: 1.5rem;
	}

	.filter-group h3 {
		font-size: 0.85rem;
		text-transform: uppercase;
		color: #888;
		margin-bottom: 0.75rem;
		letter-spacing: 0.5px;
	}

	.filter-option {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0;
		cursor: pointer;
		font-size: 0.95rem;
	}

	.filter-option input {
		accent-color: #8b0000;
	}

	.filter-option span:first-of-type {
		flex: 1;
	}

	.filter-option .count {
		color: #999;
		font-size: 0.85rem;
	}

	.scrollable-options {
		max-height: 300px;
		overflow-y: auto;
	}

	.reset-filters {
		width: 100%;
		padding: 0.75rem;
		background: #f5f5f5;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		font-size: 0.9rem;
		color: #666;
		transition: background 0.15s;
	}

	.reset-filters:hover {
		background: #8b0000;
		color: white;
	}

	/* Browse content */
	.browse-content {
		min-width: 0;
	}

	.browse-toolbar {
		display: flex;
		align-items: center;
		gap: 1rem;
		margin-bottom: 1.5rem;
		flex-wrap: wrap;
	}

	.filter-toggle {
		display: none;
		padding: 0.5rem 1rem;
		background: white;
		border: 1px solid #ddd;
		border-radius: 4px;
		cursor: pointer;
		font-size: 0.9rem;
	}

	.results-info {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex: 1;
	}

	.result-count {
		background: #e8e8e8;
		padding: 0.35rem 0.75rem;
		border-radius: 4px;
		font-size: 0.9rem;
	}

	.clear-link {
		background: none;
		border: none;
		color: #8b0000;
		cursor: pointer;
		font-size: 0.85rem;
		padding: 0;
	}

	.clear-link:hover {
		text-decoration: underline;
	}

	.sort-control {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.sort-control label {
		font-size: 0.9rem;
		color: #666;
	}

	.sort-control select {
		padding: 0.4rem 0.75rem;
		border: 1px solid #ddd;
		border-radius: 4px;
		font-size: 0.9rem;
		background: white;
	}

	/* Grid */
	.opera-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: 1.25rem;
	}

	.opera-card {
		background: white;
		border-radius: 8px;
		overflow: hidden;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.opera-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
	}

	.opera-card img {
		width: 100%;
		height: 140px;
		object-fit: cover;
	}

	.no-image {
		width: 100%;
		height: 140px;
		background: linear-gradient(135deg, #8b0000, #4a0000);
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.no-image .icon {
		font-size: 1rem;
		opacity: 0.8;
	}

	.card-content {
		padding: 0.875rem;
	}

	.card-content h3 {
		font-size: 0.95rem;
		margin-bottom: 0.25rem;
		line-height: 1.3;
	}

	.composer {
		color: #8b0000;
		font-size: 0.85rem;
		margin-bottom: 0.5rem;
		font-weight: 500;
	}

	.meta {
		display: flex;
		gap: 0.5rem;
		font-size: 0.8rem;
		color: #888;
		flex-wrap: wrap;
	}

	.year {
		font-weight: 500;
	}

	.type {
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
		background: #f0f0f0;
	}

	.type.opera {
		background: #8b0000;
		color: white;
	}

	.type.ballet {
		background: #9370db;
		color: white;
	}

	.no-results {
		text-align: center;
		padding: 3rem;
		color: #666;
	}

	.no-results button {
		margin-top: 1rem;
		padding: 0.5rem 1.5rem;
		background: #8b0000;
		color: white;
		border: none;
		border-radius: 4px;
		cursor: pointer;
	}

	.filters-backdrop {
		display: none;
	}

	/* Mobile styles */
	@media (max-width: 800px) {
		.browse-layout {
			grid-template-columns: 1fr;
		}

		.filters-sidebar {
			position: fixed;
			top: 0;
			left: 0;
			right: 0;
			bottom: 0;
			z-index: 100;
			border-radius: 0;
			overflow-y: auto;
			transform: translateX(-100%);
			transition: transform 0.3s ease;
		}

		.filters-sidebar.open {
			transform: translateX(0);
		}

		.close-filters {
			display: block;
		}

		.filter-toggle {
			display: block;
		}

		.filters-backdrop {
			display: block;
			position: fixed;
			inset: 0;
			background: rgba(0, 0, 0, 0.5);
			z-index: 99;
			border: none;
			cursor: pointer;
		}

		.opera-grid {
			grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
			gap: 1rem;
		}

		.opera-card img, .no-image {
			height: 120px;
		}
	}
</style>

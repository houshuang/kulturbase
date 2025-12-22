<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getDb } from '$lib/db';

	interface ConcertWork {
		id: number;
		title: string;
		work_type: string | null;
		composer_name: string | null;
		composer_id: number | null;
		performance_count: number;
		image_url: string | null;
	}

	interface FilterCounts {
		types: Record<string, number>;
		composers: Record<string, { id: number; count: number }>;
	}

	let allWorks: ConcertWork[] = [];
	let filteredWorks: ConcertWork[] = [];
	let loading = true;
	let filterCounts: FilterCounts = { types: {}, composers: {} };

	// Filter state
	let selectedType: string = 'all';
	let selectedComposer: string = 'all';
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

		selectedType = urlType || 'all';
		selectedComposer = urlComposer || 'all';
	}

	// Apply filters (sort: images first, then by performance_count)
	$: {
		let result = [...allWorks];

		if (selectedType !== 'all') {
			result = result.filter(w => w.work_type === selectedType);
		}

		if (selectedComposer !== 'all') {
			result = result.filter(w => w.composer_name === selectedComposer);
		}

		// Sort: entries with images first, then by performance_count
		result.sort((a, b) => {
			const aHasImage = a.image_url ? 1 : 0;
			const bHasImage = b.image_url ? 1 : 0;
			if (aHasImage !== bHasImage) return bHasImage - aHasImage;
			return b.performance_count - a.performance_count;
		});

		filteredWorks = result;
	}

	function updateUrl() {
		const params = new URLSearchParams();
		if (selectedType !== 'all') params.set('type', selectedType);
		if (selectedComposer !== 'all') params.set('composer', selectedComposer);

		const query = params.toString();
		goto(`/konserter${query ? '?' + query : ''}`, { replaceState: true, noScroll: true });
	}

	function setFilter(type: 'type' | 'composer', value: string) {
		if (type === 'type') selectedType = value;
		else if (type === 'composer') selectedComposer = value;
		updateUrl();
	}

	function resetFilters() {
		selectedType = 'all';
		selectedComposer = 'all';
		goto('/konserter', { replaceState: true, noScroll: true });
	}

	$: hasActiveFilters = selectedType !== 'all' || selectedComposer !== 'all';

	onMount(async () => {
		const db = getDb();
		if (!db) return;

		// Get all concert works with performance counts, sorted by performance count
		const results = db.exec(`
			SELECT
				w.id,
				w.title,
				w.work_type,
				composer.name as composer_name,
				composer.id as composer_id,
				(SELECT COUNT(*) FROM performances p WHERE p.work_id = w.id) as performance_count,
				(SELECT p.image_url FROM performances p WHERE p.work_id = w.id AND p.image_url IS NOT NULL LIMIT 1) as image_url
			FROM works w
			LEFT JOIN persons composer ON w.composer_id = composer.id
			WHERE w.category = 'konsert' OR w.work_type IN ('konsert', 'orchestral', 'symphony', 'concerto', 'chamber', 'choral')
			ORDER BY performance_count DESC, w.title
		`);

		if (results.length > 0) {
			allWorks = results[0].values.map((row: any[]) => ({
				id: row[0],
				title: row[1],
				work_type: row[2],
				composer_name: row[3],
				composer_id: row[4],
				performance_count: row[5],
				image_url: row[6]
			}));

			// Calculate filter counts
			const typeCounts: Record<string, number> = {};
			const composerCounts: Record<string, { id: number; count: number }> = {};

			for (const work of allWorks) {
				if (work.work_type) {
					typeCounts[work.work_type] = (typeCounts[work.work_type] || 0) + 1;
				}
				if (work.composer_name && work.composer_id) {
					if (!composerCounts[work.composer_name]) {
						composerCounts[work.composer_name] = { id: work.composer_id, count: 0 };
					}
					composerCounts[work.composer_name].count++;
				}
			}

			filterCounts = { types: typeCounts, composers: composerCounts };
		}

		loading = false;
	});

	function getImageUrl(url: string | null, width = 400): string {
		if (!url) return '';
		if (url.includes('gfx.nrk.no')) {
			return url.replace(/\/\d+$/, `/${width}`);
		}
		return url;
	}

	function getTypeLabel(type: string): string {
		const labels: Record<string, string> = {
			orchestral: 'Orkesterverk',
			symphony: 'Symfoni',
			concerto: 'Konsert (solist)',
			chamber: 'Kammermusikk',
			choral: 'Korverk'
		};
		return labels[type] || type;
	}
</script>

<svelte:head>
	<title>Konserter | Kulturbase.no</title>
</svelte:head>

<div class="konserter-page">
	<header class="page-header">
		<h1>Klassisk musikk</h1>
		<p class="subtitle">Konserter fra Bergen Filharmoniske Orkester og andre</p>
	</header>

	{#if loading}
		<div class="loading">Laster konserter...</div>
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
						<span class="count">{allWorks.length}</span>
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
						<span class="count">{allWorks.length}</span>
					</label>
					<div class="scrollable-options">
						{#each composers.slice(0, 30) as composer}
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
						<span class="result-count">{filteredWorks.length} verk</span>
						{#if hasActiveFilters}
							<button class="clear-link" on:click={resetFilters}>Fjern filter</button>
						{/if}
					</div>
				</div>

				<div class="concerts-grid">
					{#each filteredWorks as work}
						<a href="/verk/{work.id}" class="concert-card">
							{#if work.image_url}
								<img src={getImageUrl(work.image_url)} alt={work.title} loading="lazy" />
							{:else}
								<div class="no-image">
									<span class="icon">Klassisk</span>
								</div>
							{/if}
							<div class="card-content">
								<h3>{work.title}</h3>
								{#if work.composer_name}
									<p class="composer">{work.composer_name}</p>
								{/if}
								<div class="meta">
									{#if work.performance_count > 0}
										<span class="count-badge">{work.performance_count} opptak</span>
									{/if}
									{#if work.work_type}
										<span class="type">{getTypeLabel(work.work_type)}</span>
									{/if}
								</div>
							</div>
						</a>
					{/each}
				</div>

				{#if filteredWorks.length === 0}
					<div class="no-results">
						<p>Ingen konserter matcher filtrene dine.</p>
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
		accent-color: #667eea;
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
		background: #667eea;
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
		color: #667eea;
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
	.concerts-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: 1.25rem;
	}

	.concert-card {
		background: white;
		border-radius: 8px;
		overflow: hidden;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.concert-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
	}

	.concert-card img {
		width: 100%;
		height: 140px;
		object-fit: cover;
	}

	.no-image {
		width: 100%;
		height: 140px;
		background: linear-gradient(135deg, #667eea, #764ba2);
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
		color: #667eea;
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
		margin-bottom: 0.25rem;
	}

	.year {
		font-weight: 500;
	}

	.type {
		background: #f0f0f0;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
	}

	.count-badge {
		background: #667eea;
		color: white;
		padding: 0.1rem 0.5rem;
		border-radius: 3px;
		font-weight: 500;
	}

	.no-results {
		text-align: center;
		padding: 3rem;
		color: #666;
	}

	.no-results button {
		margin-top: 1rem;
		padding: 0.5rem 1.5rem;
		background: #667eea;
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

		.concerts-grid {
			grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
			gap: 1rem;
		}

		.concert-card img, .no-image {
			height: 120px;
		}
	}
</style>

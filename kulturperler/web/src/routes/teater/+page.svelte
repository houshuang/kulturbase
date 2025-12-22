<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getDb } from '$lib/db';
	import type { PerformanceWithDetails } from '$lib/types';

	interface FilterCounts {
		mediums: { tv: number; radio: number };
		decades: Record<number, number>;
		types: { classic: number; nrk: number };
	}

	let allPerformances: PerformanceWithDetails[] = [];
	let filteredPerformances: PerformanceWithDetails[] = [];
	let loading = true;
	let filterCounts: FilterCounts = { mediums: { tv: 0, radio: 0 }, decades: {}, types: { classic: 0, nrk: 0 } };

	// Filter state
	let selectedMedium: 'all' | 'tv' | 'radio' = 'all';
	let selectedDecade: number | null = null;
	let selectedType: 'all' | 'classic' | 'nrk' = 'all';
	let sortBy: 'year-desc' | 'year-asc' | 'title' = 'year-desc';
	let showFilters = false;

	// Get unique decades
	$: decades = Object.keys(filterCounts.decades).map(Number).sort((a, b) => b - a);

	// Read filters from URL
	$: {
		const urlMedium = $page.url.searchParams.get('medium');
		const urlDecade = $page.url.searchParams.get('decade');
		const urlType = $page.url.searchParams.get('type');
		const urlSort = $page.url.searchParams.get('sort');

		if (urlMedium === 'tv' || urlMedium === 'radio') selectedMedium = urlMedium;
		else selectedMedium = 'all';

		selectedDecade = urlDecade ? parseInt(urlDecade) : null;

		if (urlType === 'classic' || urlType === 'nrk') selectedType = urlType;
		else selectedType = 'all';

		if (urlSort === 'year-asc' || urlSort === 'title') sortBy = urlSort;
		else sortBy = 'year-desc';
	}

	// Apply filters
	$: {
		let result = [...allPerformances];

		if (selectedMedium !== 'all') {
			result = result.filter(p => p.medium === selectedMedium);
		}

		if (selectedDecade !== null) {
			const decadeStart = selectedDecade;
			const decadeEnd = selectedDecade + 9;
			result = result.filter(p => p.year && p.year >= decadeStart && p.year <= decadeEnd);
		}

		if (selectedType === 'classic') {
			result = result.filter(p => p.work_type === 'teaterstykke');
		} else if (selectedType === 'nrk') {
			result = result.filter(p => p.work_type === 'nrk_teaterstykke');
		}

		// Sort
		if (sortBy === 'year-desc') {
			// Prioritize TV with images first for better visual presentation
			result.sort((a, b) => {
				const aHasImage = a.medium === 'tv' && a.image_url ? 1 : 0;
				const bHasImage = b.medium === 'tv' && b.image_url ? 1 : 0;
				if (bHasImage !== aHasImage) return bHasImage - aHasImage;
				return (b.year || 0) - (a.year || 0);
			});
		} else if (sortBy === 'year-asc') {
			result.sort((a, b) => (a.year || 0) - (b.year || 0));
		} else if (sortBy === 'title') {
			result.sort((a, b) => (a.work_title || a.title || '').localeCompare(b.work_title || b.title || '', 'no'));
		}

		filteredPerformances = result;
	}

	function updateUrl() {
		const params = new URLSearchParams();
		if (selectedMedium !== 'all') params.set('medium', selectedMedium);
		if (selectedDecade !== null) params.set('decade', selectedDecade.toString());
		if (selectedType !== 'all') params.set('type', selectedType);
		if (sortBy !== 'year-desc') params.set('sort', sortBy);

		const query = params.toString();
		goto(`/teater${query ? '?' + query : ''}`, { replaceState: true, noScroll: true });
	}

	function setFilter(type: 'medium' | 'decade' | 'type', value: any) {
		if (type === 'medium') selectedMedium = value;
		else if (type === 'decade') selectedDecade = value;
		else if (type === 'type') selectedType = value;
		updateUrl();
	}

	function setSort(value: typeof sortBy) {
		sortBy = value;
		updateUrl();
	}

	function resetFilters() {
		selectedMedium = 'all';
		selectedDecade = null;
		selectedType = 'all';
		goto('/teater', { replaceState: true, noScroll: true });
	}

	$: hasActiveFilters = selectedMedium !== 'all' || selectedDecade !== null || selectedType !== 'all';

	onMount(async () => {
		const db = getDb();
		if (!db) return;

		// Get all theater performances
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
			allPerformances = results[0].values.map((row: any[]) => ({
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

			// Calculate filter counts
			filterCounts = {
				mediums: {
					tv: allPerformances.filter(p => p.medium === 'tv').length,
					radio: allPerformances.filter(p => p.medium === 'radio').length
				},
				decades: {},
				types: {
					classic: allPerformances.filter(p => p.work_type === 'teaterstykke').length,
					nrk: allPerformances.filter(p => p.work_type === 'nrk_teaterstykke').length
				}
			};

			// Calculate decade counts
			for (const perf of allPerformances) {
				if (perf.year) {
					const decade = Math.floor(perf.year / 10) * 10;
					filterCounts.decades[decade] = (filterCounts.decades[decade] || 0) + 1;
				}
			}
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
		<div class="browse-layout">
			<!-- Filters sidebar -->
			<aside class="filters-sidebar" class:open={showFilters}>
				<div class="filters-header">
					<h2>Filter</h2>
					<button class="close-filters" on:click={() => showFilters = false}>×</button>
				</div>

				<!-- Medium filter -->
				<div class="filter-group">
					<h3>Medium</h3>
					<label class="filter-option">
						<input type="radio" name="medium" checked={selectedMedium === 'all'} on:change={() => setFilter('medium', 'all')} />
						<span>Alle</span>
						<span class="count">{allPerformances.length}</span>
					</label>
					<label class="filter-option">
						<input type="radio" name="medium" checked={selectedMedium === 'tv'} on:change={() => setFilter('medium', 'tv')} />
						<span>TV</span>
						<span class="count">{filterCounts.mediums.tv}</span>
					</label>
					<label class="filter-option">
						<input type="radio" name="medium" checked={selectedMedium === 'radio'} on:change={() => setFilter('medium', 'radio')} />
						<span>Radio</span>
						<span class="count">{filterCounts.mediums.radio}</span>
					</label>
				</div>

				<!-- Type filter -->
				<div class="filter-group">
					<h3>Type</h3>
					<label class="filter-option">
						<input type="radio" name="type" checked={selectedType === 'all'} on:change={() => setFilter('type', 'all')} />
						<span>Alle</span>
						<span class="count">{allPerformances.length}</span>
					</label>
					<label class="filter-option">
						<input type="radio" name="type" checked={selectedType === 'classic'} on:change={() => setFilter('type', 'classic')} />
						<span>Klassisk dramatikk</span>
						<span class="count">{filterCounts.types.classic}</span>
					</label>
					<label class="filter-option">
						<input type="radio" name="type" checked={selectedType === 'nrk'} on:change={() => setFilter('type', 'nrk')} />
						<span>NRK-produksjon</span>
						<span class="count">{filterCounts.types.nrk}</span>
					</label>
				</div>

				<!-- Decade filter -->
				<div class="filter-group">
					<h3>Tiar</h3>
					<label class="filter-option">
						<input type="radio" name="decade" checked={selectedDecade === null} on:change={() => setFilter('decade', null)} />
						<span>Alle</span>
						<span class="count">{allPerformances.length}</span>
					</label>
					{#each decades as decade}
						<label class="filter-option">
							<input type="radio" name="decade" checked={selectedDecade === decade} on:change={() => setFilter('decade', decade)} />
							<span>{decade}-tallet</span>
							<span class="count">{filterCounts.decades[decade] || 0}</span>
						</label>
					{/each}
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
							<option value="title">Tittel A-A</option>
						</select>
					</div>
				</div>

				<div class="performances-grid">
					{#each filteredPerformances as perf}
						<a href="/opptak/{perf.id}" class="performance-card">
							{#if perf.image_url}
								<img src={getImageUrl(perf.image_url)} alt={perf.work_title || perf.title || ''} loading="lazy" />
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
										<span class="medium" class:tv={perf.medium === 'tv'} class:radio={perf.medium === 'radio'}>
											{perf.medium === 'tv' ? 'TV' : 'Radio'}
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
	.teater-page {
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
		accent-color: #e94560;
	}

	.filter-option span:first-of-type {
		flex: 1;
	}

	.filter-option .count {
		color: #999;
		font-size: 0.85rem;
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
		background: #e94560;
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
		color: #e94560;
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
	.performances-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: 1.25rem;
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
		height: 140px;
		object-fit: cover;
	}

	.no-image {
		width: 100%;
		height: 140px;
		background: linear-gradient(135deg, #1a1a2e, #16213e);
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1rem;
	}

	.card-content {
		padding: 0.875rem;
	}

	.card-content h3 {
		font-size: 0.95rem;
		margin-bottom: 0.25rem;
		line-height: 1.3;
	}

	.playwright {
		color: #666;
		font-size: 0.85rem;
		margin-bottom: 0.5rem;
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

	.no-results {
		text-align: center;
		padding: 3rem;
		color: #666;
	}

	.no-results button {
		margin-top: 1rem;
		padding: 0.5rem 1.5rem;
		background: #e94560;
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

		.performances-grid {
			grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
			gap: 1rem;
		}

		.performance-card img, .no-image {
			height: 120px;
		}
	}
</style>

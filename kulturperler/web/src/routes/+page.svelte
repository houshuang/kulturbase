<script lang="ts">
	import { searchPerformances, getYearRange, getPersonsByRole, getPerformanceCount, getPlaywrightsWithCounts, searchAuthors, getMediumCounts, getAllPlays, getAllPlaywrights, getPlayCount, getAuthorCount, type PlaywrightWithCount, type PlayWithDetails, type PlaywrightWithDetails } from '$lib/db';
	import type { PerformanceWithDetails, Person, SearchFilters } from '$lib/types';
	import { onMount } from 'svelte';
	import { page as pageStore } from '$app/stores';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';

	type Tab = 'opptak' | 'skuespill' | 'forfattere';
	let activeTab: Tab = 'opptak';

	// Opptak tab state
	let performances: PerformanceWithDetails[] = [];
	let matchingAuthors: (Person & { play_count?: number })[] = [];
	let directors: Person[] = [];
	let playwrights: Person[] = [];
	let playwrightsWithCounts: PlaywrightWithCount[] = [];
	let yearRange = { min: 1960, max: 2016 };
	let mediumCounts = { tv: 0, radio: 0 };
	let showTv = true;
	let showRadio = true;
	let filters: SearchFilters = {
		query: '',
		yearFrom: undefined,
		yearTo: undefined,
		playwrightId: undefined,
		directorId: undefined,
		tagIds: [],
		mediums: undefined
	};
	let totalCount = 0;
	let page = 0;
	const pageSize = 24;

	// Skuespill tab state
	let plays: PlayWithDetails[] = [];
	let playsSortBy: 'title' | 'year' | 'playwright' = 'title';
	let playsFilter = '';
	let playCount = 0;

	// Forfattere tab state
	let authors: PlaywrightWithDetails[] = [];
	let authorsSortBy: 'name' | 'plays' | 'birth' = 'name';
	let authorsFilter = '';
	let authorCount = 0;

	// Track if we're initializing from URL (to avoid double-updating)
	let initialized = false;

	// Update URL with current state
	function updateUrl(params: Record<string, string | number | undefined>, replace = true) {
		if (!browser) return;
		const url = new URL(window.location.href);
		for (const [key, value] of Object.entries(params)) {
			if (value === undefined || value === '' || value === 0) {
				url.searchParams.delete(key);
			} else {
				url.searchParams.set(key, String(value));
			}
		}
		goto(url.toString(), { replaceState: replace, noScroll: true, keepFocus: true });
	}

	// Read state from URL params
	function readUrlParams() {
		const params = $pageStore.url.searchParams;

		// Tab
		const tab = params.get('tab');
		if (tab === 'skuespill' || tab === 'forfattere') {
			activeTab = tab;
		} else {
			activeTab = 'opptak';
		}

		// Opptak filters
		filters.query = params.get('q') || '';
		filters.yearFrom = params.get('yearFrom') ? parseInt(params.get('yearFrom')!) : undefined;
		filters.yearTo = params.get('yearTo') ? parseInt(params.get('yearTo')!) : undefined;
		filters.playwrightId = params.get('playwright') ? parseInt(params.get('playwright')!) : undefined;
		filters.directorId = params.get('director') ? parseInt(params.get('director')!) : undefined;
		page = params.get('page') ? parseInt(params.get('page')!) : 0;

		// Medium filter
		const medium = params.get('medium');
		if (medium === 'tv') {
			showTv = true;
			showRadio = false;
			filters.mediums = ['tv'];
		} else if (medium === 'radio') {
			showTv = false;
			showRadio = true;
			filters.mediums = ['radio'];
		} else {
			showTv = true;
			showRadio = true;
			filters.mediums = undefined;
		}

		// Skuespill tab
		const playsSort = params.get('playsSort');
		if (playsSort === 'year' || playsSort === 'playwright') {
			playsSortBy = playsSort;
		} else {
			playsSortBy = 'title';
		}
		playsFilter = params.get('playsFilter') || '';

		// Forfattere tab
		const authorsSort = params.get('authorsSort');
		if (authorsSort === 'plays' || authorsSort === 'birth') {
			authorsSortBy = authorsSort;
		} else {
			authorsSortBy = 'name';
		}
		authorsFilter = params.get('authorsFilter') || '';
	}

	onMount(() => {
		try {
			yearRange = getYearRange();
			directors = getPersonsByRole('director');
			playwrights = getPersonsByRole('playwright');
			playwrightsWithCounts = getPlaywrightsWithCounts();
			mediumCounts = getMediumCounts();
			playCount = getPlayCount();
			authorCount = getAuthorCount();

			// Read URL params on mount
			readUrlParams();

			// Load data based on active tab
			if (activeTab === 'skuespill') {
				loadPlays();
			} else if (activeTab === 'forfattere') {
				loadAuthors();
			}
			loadPerformances();

			initialized = true;
		} catch (e) {
			console.error('Failed to load initial data:', e);
		}
	});

	// React to URL changes (browser back/forward)
	$: if (browser && initialized && $pageStore.url) {
		readUrlParams();
		if (activeTab === 'opptak') {
			loadPerformances();
		} else if (activeTab === 'skuespill') {
			loadPlays();
		} else if (activeTab === 'forfattere') {
			loadAuthors();
		}
	}

	function switchTab(tab: Tab) {
		activeTab = tab;
		if (tab === 'skuespill' && plays.length === 0) {
			loadPlays();
		}
		if (tab === 'forfattere' && authors.length === 0) {
			loadAuthors();
		}
		// Update URL with new tab (push new history entry)
		updateUrl({ tab: tab === 'opptak' ? undefined : tab }, false);
	}

	function loadPlays() {
		plays = getAllPlays(playsSortBy);
	}

	function loadAuthors() {
		const all = getAllPlaywrights();
		if (authorsSortBy === 'plays') {
			authors = [...all].sort((a, b) => b.performance_count - a.performance_count);
		} else if (authorsSortBy === 'birth') {
			authors = [...all].sort((a, b) => (a.birth_year || 0) - (b.birth_year || 0));
		} else {
			authors = all;
		}
	}

	$: filteredPlays = plays.filter(p =>
		!playsFilter ||
		p.title.toLowerCase().includes(playsFilter.toLowerCase()) ||
		(p.playwright_name && p.playwright_name.toLowerCase().includes(playsFilter.toLowerCase()))
	);

	$: filteredAuthors = authors.filter(a =>
		!authorsFilter ||
		a.name.toLowerCase().includes(authorsFilter.toLowerCase())
	);

	$: timelineAuthors = filteredAuthors.filter(a => a.birth_year);

	function updateMediumFilter() {
		if (showTv && showRadio) {
			filters.mediums = undefined;
		} else if (showTv) {
			filters.mediums = ['tv'];
		} else if (showRadio) {
			filters.mediums = ['radio'];
		} else {
			filters.mediums = [];
		}
		search();
	}

	function search() {
		page = 0;
		loadPerformances();
		// Update URL with search filters
		updateUrl({
			q: filters.query || undefined,
			yearFrom: filters.yearFrom,
			yearTo: filters.yearTo,
			playwright: filters.playwrightId,
			director: filters.directorId,
			medium: showTv && showRadio ? undefined : (showTv ? 'tv' : (showRadio ? 'radio' : undefined)),
			page: undefined
		});
	}

	function loadPerformances() {
		const cleanFilters: SearchFilters = {
			...filters,
			query: filters.query?.trim() || undefined,
			yearFrom: filters.yearFrom || undefined,
			yearTo: filters.yearTo || undefined,
			playwrightId: filters.playwrightId || undefined,
			directorId: filters.directorId || undefined,
			tagIds: filters.tagIds?.length ? filters.tagIds : undefined,
			mediums: filters.mediums
		};

		if (cleanFilters.query && cleanFilters.query.length >= 2) {
			matchingAuthors = searchAuthors(cleanFilters.query);
		} else {
			matchingAuthors = [];
		}

		performances = searchPerformances(cleanFilters, pageSize, page * pageSize);
		totalCount = getPerformanceCount(cleanFilters);
	}

	function clearFilters() {
		filters = {
			query: '',
			yearFrom: undefined,
			yearTo: undefined,
			playwrightId: undefined,
			directorId: undefined,
			tagIds: [],
			mediums: undefined
		};
		showTv = true;
		showRadio = true;
		page = 0;
		loadPerformances();
		// Clear all filter params from URL
		updateUrl({
			q: undefined,
			yearFrom: undefined,
			yearTo: undefined,
			playwright: undefined,
			director: undefined,
			medium: undefined,
			page: undefined
		});
	}

	function nextPage() {
		if ((page + 1) * pageSize < totalCount) {
			page++;
			loadPerformances();
			updateUrl({ page: page > 0 ? page : undefined });
		}
	}

	function prevPage() {
		if (page > 0) {
			page--;
			loadPerformances();
			updateUrl({ page: page > 0 ? page : undefined });
		}
	}

	function formatDuration(seconds: number | null): string {
		if (!seconds) return '';
		const h = Math.floor(seconds / 3600);
		const m = Math.floor((seconds % 3600) / 60);
		if (h > 0) return `${h}t ${m}m`;
		return `${m} min`;
	}

	function getImageUrl(url: string | null): string {
		if (!url) return '/placeholder.jpg';
		return url;
	}

	function handlePlaysSortChange() {
		loadPlays();
		updateUrl({ playsSort: playsSortBy === 'title' ? undefined : playsSortBy });
	}

	function handleAuthorsSortChange() {
		loadAuthors();
		updateUrl({ authorsSort: authorsSortBy === 'name' ? undefined : authorsSortBy });
	}

	function handlePlaysFilterChange() {
		updateUrl({ playsFilter: playsFilter || undefined });
	}

	function handleAuthorsFilterChange() {
		updateUrl({ authorsFilter: authorsFilter || undefined });
	}
</script>

<div class="page-container">
	<nav class="tabs">
		<button class:active={activeTab === 'opptak'} on:click={() => switchTab('opptak')}>
			Opptak <span class="count">({mediumCounts.tv + mediumCounts.radio})</span>
		</button>
		<button class:active={activeTab === 'skuespill'} on:click={() => switchTab('skuespill')}>
			Skuespill <span class="count">({playCount})</span>
		</button>
		<button class:active={activeTab === 'forfattere'} on:click={() => switchTab('forfattere')}>
			Forfattere <span class="count">({authorCount})</span>
		</button>
	</nav>

	{#if activeTab === 'opptak'}
		<div class="browse-page">
			<aside class="filters">
				<h2>Filtrer</h2>

				<div class="filter-group">
					<label for="search">Fritekst</label>
					<input
						type="search"
						id="search"
						bind:value={filters.query}
						on:input={search}
						placeholder="Tittel, beskrivelse..."
					/>
				</div>

				<div class="filter-group">
					<span class="filter-label">År ({yearRange.min} - {yearRange.max})</span>
					<div class="year-range">
						<input
							type="number"
							bind:value={filters.yearFrom}
							on:change={search}
							placeholder="Fra"
							min={yearRange.min}
							max={yearRange.max}
						/>
						<span>-</span>
						<input
							type="number"
							bind:value={filters.yearTo}
							on:change={search}
							placeholder="Til"
							min={yearRange.min}
							max={yearRange.max}
						/>
					</div>
				</div>

				{#if playwrights.length > 0}
					<div class="filter-group">
						<label for="playwright">Dramatiker</label>
						<select id="playwright" bind:value={filters.playwrightId} on:change={search}>
							<option value={undefined}>Alle</option>
							{#each playwrights as p}
								<option value={p.id}>{p.name}</option>
							{/each}
						</select>
					</div>
				{/if}

				{#if directors.length > 0}
					<div class="filter-group">
						<label for="director">Regissør</label>
						<select id="director" bind:value={filters.directorId} on:change={search}>
							<option value={undefined}>Alle</option>
							{#each directors as d}
								<option value={d.id}>{d.name}</option>
							{/each}
						</select>
					</div>
				{/if}

				<div class="filter-group">
					<span class="filter-label">Medium</span>
					<div class="medium-checkboxes">
						<label class="checkbox-label">
							<input type="checkbox" bind:checked={showTv} on:change={updateMediumFilter} />
							<span class="medium-icon tv">TV</span>
							Fjernsynsteater
							{#if mediumCounts.tv > 0}<span class="count">({mediumCounts.tv})</span>{/if}
						</label>
						<label class="checkbox-label">
							<input type="checkbox" bind:checked={showRadio} on:change={updateMediumFilter} />
							<span class="medium-icon radio">R</span>
							Radioteater
							{#if mediumCounts.radio > 0}<span class="count">({mediumCounts.radio})</span>{/if}
						</label>
					</div>
				</div>

				<button class="clear-btn" on:click={clearFilters}>Nullstill filter</button>
			</aside>

			<section class="results">
				{#if matchingAuthors.length > 0}
					<div class="author-results">
						<h3>Dramatikere</h3>
						<div class="author-cards">
							{#each matchingAuthors as author}
								<a href="/person/{author.id}" class="author-card">
									<div class="author-card-info">
										<span class="author-card-name">{author.name}</span>
										{#if author.birth_year}
											<span class="author-card-dates">{author.birth_year}–{author.death_year || ''}</span>
										{/if}
										<span class="author-card-count">{author.play_count} stykker</span>
									</div>
								</a>
							{/each}
						</div>
					</div>
				{/if}

				<div class="results-header">
					<h2>{totalCount} opptak</h2>
					{#if totalCount > pageSize}
						<div class="pagination">
							<button on:click={prevPage} disabled={page === 0}>Forrige</button>
							<span>Side {page + 1} av {Math.ceil(totalCount / pageSize)}</span>
							<button on:click={nextPage} disabled={(page + 1) * pageSize >= totalCount}>Neste</button>
						</div>
					{/if}
				</div>

				<div class="performances-grid">
					{#each performances as perf}
						<a href="/performance/{perf.id}" class="performance-card">
							<div class="performance-image">
								<img
									src={getImageUrl(perf.image_url)}
									alt={perf.title || ''}
									loading="lazy"
								/>
								{#if perf.total_duration}
									<span class="duration">{formatDuration(perf.total_duration)}</span>
								{/if}
								{#if perf.media_count && perf.media_count > 1}
									<span class="parts-badge">{perf.media_count} deler</span>
								{/if}
								{#if perf.medium === 'radio'}
									<span class="medium-badge radio">Radio</span>
								{/if}
							</div>
							<div class="performance-info">
								<h3>{perf.work_title || perf.title || 'Ukjent tittel'}</h3>
								{#if perf.year}
									<span class="year">{perf.year}</span>
								{/if}
								{#if perf.director_name}
									<span class="director">Regi: {perf.director_name}</span>
								{/if}
							</div>
						</a>
					{/each}
				</div>

				{#if performances.length === 0}
					<div class="no-results">
						<p>Ingen opptak funnet med disse filtrene.</p>
					</div>
				{/if}

				{#if totalCount > pageSize}
					<div class="pagination bottom">
						<button on:click={prevPage} disabled={page === 0}>Forrige</button>
						<span>Side {page + 1} av {Math.ceil(totalCount / pageSize)}</span>
						<button on:click={nextPage} disabled={(page + 1) * pageSize >= totalCount}>Neste</button>
					</div>
				{/if}
			</section>
		</div>
	{:else if activeTab === 'skuespill'}
		<div class="plays-page">
			<div class="plays-header">
				<div class="plays-controls">
					<input
						type="search"
						bind:value={playsFilter}
						on:input={handlePlaysFilterChange}
						placeholder="Søk i skuespill..."
						class="plays-search"
					/>
					<select bind:value={playsSortBy} on:change={handlePlaysSortChange}>
						<option value="title">Alfabetisk</option>
						<option value="playwright">Etter forfatter</option>
						<option value="year">Etter år skrevet</option>
					</select>
				</div>
				<p class="plays-count">{filteredPlays.length} skuespill</p>
			</div>

			<div class="plays-list">
				{#each filteredPlays as play}
					<a href="/play/{play.id}" class="play-item">
						<span class="play-title">{play.title}</span>
						{#if play.playwright_name}
							<span class="play-author">({play.playwright_name})</span>
						{/if}
						{#if play.year_written}
							<span class="play-year">{play.year_written}</span>
						{/if}
						<span class="play-count">{play.performance_count} {play.performance_count === 1 ? 'opptak' : 'opptak'}</span>
					</a>
				{/each}
			</div>
		</div>
	{:else if activeTab === 'forfattere'}
		<div class="authors-page">
			<div class="authors-header">
				<div class="authors-controls">
					<input
						type="search"
						bind:value={authorsFilter}
						on:input={handleAuthorsFilterChange}
						placeholder="Søk i forfattere..."
						class="authors-search"
					/>
					<select bind:value={authorsSortBy} on:change={handleAuthorsSortChange}>
						<option value="name">Alfabetisk</option>
						<option value="plays">Etter antall stykker</option>
						<option value="birth">Etter fødselsår</option>
					</select>
				</div>
				<p class="authors-count">{filteredAuthors.length} forfattere</p>
			</div>

			{#if authorsSortBy === 'birth' && timelineAuthors.length > 0}
				<div class="timeline">
					<h3>Tidslinje</h3>
					<div class="timeline-container">
						{#each timelineAuthors as author}
							<a href="/person/{author.id}" class="timeline-item" title="{author.name} ({author.birth_year}–{author.death_year || ''})">
								<span class="timeline-year">{author.birth_year}</span>
								<span class="timeline-name">{author.name}</span>
								{#if author.death_year && author.birth_year}
									<span class="timeline-lifespan">({author.death_year - author.birth_year} år)</span>
								{/if}
							</a>
						{/each}
					</div>
				</div>
			{:else}
				<div class="authors-grid">
					{#each filteredAuthors as author}
						<a href="/person/{author.id}" class="author-card-large">
							<div class="author-info">
								<h3>{author.name}</h3>
								{#if author.birth_year}
									<span class="author-dates">{author.birth_year}–{author.death_year || ''}</span>
								{/if}
								<span class="author-stats">{author.play_count} stykker, {author.performance_count} opptak</span>
							</div>
						</a>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.page-container {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.tabs {
		display: flex;
		gap: 0.5rem;
		background: white;
		padding: 0.5rem;
		border-radius: 8px;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.tabs button {
		padding: 0.75rem 1.5rem;
		border: none;
		background: transparent;
		border-radius: 6px;
		cursor: pointer;
		font-size: 1rem;
		font-weight: 500;
		color: #666;
		transition: all 0.2s;
	}

	.tabs button:hover {
		background: #f5f5f5;
	}

	.tabs button.active {
		background: #e94560;
		color: white;
	}

	.tabs .count {
		font-weight: normal;
		opacity: 0.8;
	}

	/* Opptak tab styles */
	.browse-page {
		display: grid;
		grid-template-columns: 280px 1fr;
		gap: 2rem;
	}

	.filters {
		background: white;
		padding: 1.5rem;
		border-radius: 8px;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
		height: fit-content;
		position: sticky;
		top: 1rem;
	}

	.filters h2 {
		margin-bottom: 1rem;
		font-size: 1.25rem;
	}

	.filter-group {
		margin-bottom: 1.25rem;
	}

	.filter-group label,
	.filter-label {
		display: block;
		font-weight: 500;
		margin-bottom: 0.5rem;
		font-size: 0.9rem;
	}

	.filter-group input[type="search"],
	.filter-group input[type="number"],
	.filter-group select {
		width: 100%;
		padding: 0.5rem;
		border: 1px solid #ddd;
		border-radius: 4px;
		font-size: 0.95rem;
	}

	.year-range {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.year-range input {
		width: 80px;
	}

	.clear-btn {
		width: 100%;
		padding: 0.5rem;
		background: #f5f5f5;
		border: 1px solid #ddd;
		border-radius: 4px;
		cursor: pointer;
		font-size: 0.9rem;
	}

	.clear-btn:hover {
		background: #eee;
	}

	.author-results {
		margin-bottom: 1.5rem;
		padding-bottom: 1.5rem;
		border-bottom: 1px solid #eee;
	}

	.author-results h3 {
		font-size: 0.9rem;
		color: #888;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-bottom: 0.75rem;
	}

	.author-cards {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
	}

	.author-card {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		background: white;
		border-radius: 8px;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
		text-decoration: none;
		color: inherit;
		transition: transform 0.15s, box-shadow 0.15s;
	}

	.author-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
	}

	.author-thumb {
		width: 48px;
		height: 48px;
		border-radius: 50%;
		object-fit: cover;
	}

	.author-thumb.placeholder {
		background: #ddd;
	}

	.author-card-info {
		display: flex;
		flex-direction: column;
	}

	.author-card-name {
		font-weight: 600;
		font-size: 0.95rem;
		color: #e94560;
	}

	.author-card-dates {
		font-size: 0.8rem;
		color: #888;
	}

	.author-card-count {
		font-size: 0.8rem;
		color: #666;
	}

	.results-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.results-header h2 {
		font-size: 1.1rem;
		font-weight: 500;
	}

	.pagination {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.pagination button {
		padding: 0.5rem 1rem;
		background: white;
		border: 1px solid #ddd;
		border-radius: 4px;
		cursor: pointer;
	}

	.pagination button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.pagination.bottom {
		margin-top: 2rem;
		justify-content: center;
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
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.performance-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
	}

	.performance-image {
		position: relative;
		aspect-ratio: 16/9;
		background: #eee;
	}

	.performance-image img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.duration {
		position: absolute;
		bottom: 0.5rem;
		right: 0.5rem;
		background: rgba(0, 0, 0, 0.8);
		color: white;
		padding: 0.2rem 0.5rem;
		border-radius: 4px;
		font-size: 0.8rem;
	}

	.parts-badge {
		position: absolute;
		top: 0.5rem;
		left: 0.5rem;
		background: #1a1a2e;
		color: white;
		padding: 0.25rem 0.6rem;
		border-radius: 4px;
		font-size: 0.75rem;
		font-weight: 500;
	}

	.performance-info {
		padding: 1rem;
	}

	.performance-info h3 {
		font-size: 1rem;
		font-weight: 600;
		margin-bottom: 0.5rem;
		line-height: 1.3;
	}

	.performance-info .year {
		display: inline-block;
		background: #e94560;
		color: white;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
		font-size: 0.75rem;
		margin-right: 0.5rem;
	}

	.performance-info .director {
		display: block;
		font-size: 0.85rem;
		color: #666;
		margin-top: 0.25rem;
	}

	.no-results {
		text-align: center;
		padding: 4rem;
		color: #666;
	}

	.medium-checkboxes {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.checkbox-label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
		font-size: 0.9rem;
	}

	.checkbox-label input[type="checkbox"] {
		width: auto;
		margin: 0;
	}

	.checkbox-label .count {
		color: #888;
		font-size: 0.85rem;
	}

	.medium-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 18px;
		border-radius: 3px;
		font-size: 0.65rem;
		font-weight: 600;
		color: white;
	}

	.medium-icon.tv {
		background: #e94560;
	}

	.medium-icon.radio {
		background: #6b5ce7;
	}

	.medium-badge {
		position: absolute;
		top: 0.5rem;
		right: 0.5rem;
		padding: 0.2rem 0.5rem;
		border-radius: 4px;
		font-size: 0.7rem;
		font-weight: 600;
		color: white;
	}

	.medium-badge.radio {
		background: #6b5ce7;
	}

	/* Skuespill tab styles */
	.plays-page {
		background: white;
		border-radius: 8px;
		padding: 1.5rem;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.plays-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.plays-controls {
		display: flex;
		gap: 1rem;
	}

	.plays-search,
	.authors-search {
		padding: 0.5rem 1rem;
		border: 1px solid #ddd;
		border-radius: 4px;
		font-size: 0.95rem;
		width: 250px;
	}

	.plays-controls select,
	.authors-controls select {
		padding: 0.5rem 1rem;
		border: 1px solid #ddd;
		border-radius: 4px;
		font-size: 0.95rem;
	}

	.plays-count,
	.authors-count {
		color: #666;
		font-size: 0.95rem;
	}

	.plays-list {
		display: flex;
		flex-direction: column;
	}

	.play-item {
		display: flex;
		align-items: baseline;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		border-bottom: 1px solid #f0f0f0;
		text-decoration: none;
		color: inherit;
		transition: background 0.15s;
	}

	.play-item:hover {
		background: #f8f9fa;
	}

	.play-title {
		font-weight: 500;
		color: #333;
	}

	.play-author {
		color: #666;
		font-size: 0.9rem;
	}

	.play-year {
		color: #888;
		font-size: 0.85rem;
	}

	.play-count {
		margin-left: auto;
		color: #888;
		font-size: 0.85rem;
	}

	/* Forfattere tab styles */
	.authors-page {
		background: white;
		border-radius: 8px;
		padding: 1.5rem;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.authors-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.authors-controls {
		display: flex;
		gap: 1rem;
	}

	.authors-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: 1rem;
	}

	.author-card-large {
		display: block;
		padding: 1rem 1.25rem;
		background: #f8f9fa;
		border-radius: 8px;
		text-decoration: none;
		color: inherit;
		transition: background 0.15s, transform 0.15s;
	}

	.author-card-large:hover {
		background: #f0f0f0;
		transform: translateY(-1px);
	}

	.author-info h3 {
		font-size: 1rem;
		margin-bottom: 0.25rem;
		color: #333;
	}

	.author-dates {
		display: block;
		font-size: 0.85rem;
		color: #666;
	}

	.author-stats {
		display: block;
		font-size: 0.85rem;
		color: #888;
	}

	/* Timeline */
	.timeline {
		margin-bottom: 2rem;
	}

	.timeline h3 {
		font-size: 1rem;
		margin-bottom: 1rem;
		color: #666;
	}

	.timeline-container {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.timeline-item {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 0.5rem 1rem;
		text-decoration: none;
		color: inherit;
		border-left: 3px solid #e94560;
		transition: background 0.15s;
	}

	.timeline-item:hover {
		background: #f8f9fa;
	}

	.timeline-year {
		font-weight: 600;
		color: #e94560;
		min-width: 50px;
	}

	.timeline-name {
		font-weight: 500;
	}

	.timeline-lifespan {
		color: #888;
		font-size: 0.85rem;
	}

	@media (max-width: 900px) {
		.browse-page {
			grid-template-columns: 1fr;
		}

		.filters {
			position: static;
		}

		.tabs {
			flex-wrap: wrap;
		}

		.plays-controls,
		.authors-controls {
			flex-direction: column;
			width: 100%;
		}

		.plays-search,
		.authors-search {
			width: 100%;
		}
	}
</style>

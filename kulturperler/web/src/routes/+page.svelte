<script lang="ts">
	import { searchPerformances, getYearRange, getPersonsByRole, getPerformanceCount, getPlaywrightsWithCounts, searchAuthors, type PlaywrightWithCount } from '$lib/db';
	import type { PerformanceWithDetails, Person, SearchFilters } from '$lib/types';
	import { onMount } from 'svelte';

	let performances: PerformanceWithDetails[] = [];
	let matchingAuthors: (Person & { play_count?: number })[] = [];
	let directors: Person[] = [];
	let playwrights: Person[] = [];
	let playwrightsWithCounts: PlaywrightWithCount[] = [];
	let yearRange = { min: 1960, max: 1999 };

	let filters: SearchFilters = {
		query: '',
		yearFrom: undefined,
		yearTo: undefined,
		playwrightId: undefined,
		directorId: undefined,
		tagIds: []
	};

	let totalCount = 0;
	let page = 0;
	const pageSize = 24;

	onMount(() => {
		try {
			yearRange = getYearRange();
			directors = getPersonsByRole('director');
			playwrights = getPersonsByRole('playwright');
			playwrightsWithCounts = getPlaywrightsWithCounts();
			search();
		} catch (e) {
			console.error('Failed to load initial data:', e);
		}
	});

	function search() {
		page = 0;
		loadPerformances();
	}

	function loadPerformances() {
		const cleanFilters: SearchFilters = {
			...filters,
			query: filters.query?.trim() || undefined,
			yearFrom: filters.yearFrom || undefined,
			yearTo: filters.yearTo || undefined,
			playwrightId: filters.playwrightId || undefined,
			directorId: filters.directorId || undefined,
			tagIds: filters.tagIds?.length ? filters.tagIds : undefined
		};

		// Search for matching authors
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
			tagIds: []
		};
		search();
	}

	function nextPage() {
		if ((page + 1) * pageSize < totalCount) {
			page++;
			loadPerformances();
		}
	}

	function prevPage() {
		if (page > 0) {
			page--;
			loadPerformances();
		}
	}

	function formatDuration(seconds: number | null): string {
		if (!seconds) return '';
		const h = Math.floor(seconds / 3600);
		const m = Math.floor((seconds % 3600) / 60);
		if (h > 0) return `${h}t ${m}m`;
		return `${m} min`;
	}

	function getImageUrl(url: string | null, width = 480): string {
		if (!url) return '/placeholder.jpg';
		if (url.includes('gfx.nrk.no')) {
			return url.replace(/\/\d+$/, `/${width}`);
		}
		return url;
	}
</script>

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
				<label for="director">Regissor</label>
				<select id="director" bind:value={filters.directorId} on:change={search}>
					<option value={undefined}>Alle</option>
					{#each directors as d}
						<option value={d.id}>{d.name}</option>
					{/each}
				</select>
			</div>
		{/if}

		<button class="clear-btn" on:click={clearFilters}>Nullstill filter</button>

		{#if playwrightsWithCounts.length > 0}
			<div class="playwrights-section">
				<h3>Dramatikere</h3>
				<ul class="playwrights-list">
					{#each playwrightsWithCounts.slice(0, 15) as pw}
						<li>
							<a href="/person/{pw.id}" class="playwright-link">
								{pw.name}
								<span class="count">({pw.episode_count})</span>
							</a>
						</li>
					{/each}
				</ul>
				{#if playwrightsWithCounts.length > 15}
					<a href="/persons" class="more-link">+ {playwrightsWithCounts.length - 15} flere</a>
				{/if}
			</div>
		{/if}
	</aside>

	<section class="results">
		{#if matchingAuthors.length > 0}
			<div class="author-results">
				<h3>Dramatikere</h3>
				<div class="author-cards">
					{#each matchingAuthors as author}
						<a href="/person/{author.id}" class="author-card">
							{#if author.image_url}
								<img src={author.image_url} alt={author.name} class="author-thumb" />
							{:else}
								<div class="author-thumb placeholder"></div>
							{/if}
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
			<h2>{totalCount} {totalCount === 1 ? 'opptak' : 'opptak'}</h2>
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
					</div>
					<div class="performance-info">
						<h3>{perf.work_title || perf.title || 'Ukjent tittel'}</h3>
						{#if perf.year}
							<span class="year">{perf.year}</span>
						{/if}
						{#if perf.playwright_name}
							<span class="playwright">{perf.playwright_name}</span>
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

<style>
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

	.playwrights-section {
		margin-top: 1.5rem;
		padding-top: 1.5rem;
		border-top: 1px solid #eee;
	}

	.playwrights-section h3 {
		font-size: 1rem;
		font-weight: 600;
		margin-bottom: 0.75rem;
	}

	.playwrights-list {
		list-style: none;
	}

	.playwrights-list li {
		margin-bottom: 0.25rem;
	}

	.playwright-link {
		display: flex;
		justify-content: space-between;
		padding: 0.35rem 0.5rem;
		border-radius: 4px;
		text-decoration: none;
		color: #333;
		font-size: 0.9rem;
		transition: background-color 0.15s;
	}

	.playwright-link:hover {
		background: #f0f0f0;
	}

	.playwright-link .count {
		color: #888;
		font-size: 0.85rem;
	}

	.more-link {
		font-size: 0.85rem;
		color: #888;
		text-align: center;
		margin-top: 0.5rem;
	}

	/* Author search results */
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

	.performance-info .playwright,
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

	@media (max-width: 900px) {
		.browse-page {
			grid-template-columns: 1fr;
		}

		.filters {
			position: static;
		}
	}
</style>

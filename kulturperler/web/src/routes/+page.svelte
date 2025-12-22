<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { getRandomClassicalPlays, getPlaysByPlaywright, getRecentConcerts, getClassicalPerformanceCount, getBergenPhilConcertCount, getDatabase, type RandomPerformance } from '$lib/db';
	import type { PerformanceWithDetails, ExternalResource } from '$lib/types';

	interface TopCreator {
		id: number;
		name: string;
		performance_count: number;
	}

	interface SearchResult {
		type: 'person' | 'work';
		id: number;
		title: string;
		subtitle: string | null;
		count: number;
		image_url: string | null;
	}

	let featuredPerformances: RandomPerformance[] = [];
	let ibsenPlays: PerformanceWithDetails[] = [];
	let topCreators: TopCreator[] = [];
	let concerts: ExternalResource[] = [];

	let stats = {
		theater: 0,
		concerts: 0,
		opera: 0,
		persons: 0
	};

	let loading = true;
	let searchQuery = '';
	let searchResults: SearchResult[] = [];
	let showResults = false;
	let searchTimeout: ReturnType<typeof setTimeout> | null = null;
	const IBSEN_ID = 1;

	function handleSearchInput() {
		if (searchTimeout) clearTimeout(searchTimeout);

		if (searchQuery.trim().length < 2) {
			searchResults = [];
			showResults = false;
			return;
		}

		searchTimeout = setTimeout(() => {
			performSearch();
		}, 120);
	}

	function performSearch() {
		const query = searchQuery.trim().toLowerCase();
		if (query.length < 2) return;

		const db = getDatabase();
		const results: SearchResult[] = [];

		// Search persons with performance count and image
		const personStmt = db.prepare(`
			SELECT
				p.id,
				p.name,
				p.image_url,
				(SELECT COUNT(DISTINCT pf.id) FROM works w
				 JOIN performances pf ON pf.work_id = w.id
				 WHERE w.playwright_id = p.id OR w.composer_id = p.id) as perf_count
			FROM persons p
			WHERE LOWER(p.name) LIKE ?
			ORDER BY perf_count DESC, p.name
			LIMIT 4
		`);
		personStmt.bind([`%${query}%`]);
		while (personStmt.step()) {
			const row = personStmt.getAsObject() as { id: number; name: string; image_url: string | null; perf_count: number };
			results.push({
				type: 'person',
				id: row.id,
				title: row.name,
				subtitle: row.perf_count > 0 ? `${row.perf_count} opptak` : null,
				count: row.perf_count,
				image_url: row.image_url
			});
		}
		personStmt.free();

		// Search works with performance count and image
		const workStmt = db.prepare(`
			SELECT
				w.id,
				w.title,
				p.name as playwright_name,
				(SELECT COUNT(*) FROM performances pf WHERE pf.work_id = w.id) as perf_count,
				(SELECT e.image_url FROM episodes e
				 JOIN performances pf ON e.performance_id = pf.id
				 WHERE pf.work_id = w.id LIMIT 1) as image_url
			FROM works w
			LEFT JOIN persons p ON w.playwright_id = p.id
			WHERE LOWER(w.title) LIKE ?
			ORDER BY perf_count DESC, w.title
			LIMIT 4
		`);
		workStmt.bind([`%${query}%`]);
		while (workStmt.step()) {
			const row = workStmt.getAsObject() as { id: number; title: string; playwright_name: string | null; perf_count: number; image_url: string | null };
			results.push({
				type: 'work',
				id: row.id,
				title: row.title,
				subtitle: row.playwright_name,
				count: row.perf_count,
				image_url: row.image_url
			});
		}
		workStmt.free();

		searchResults = results;
		showResults = results.length > 0;
	}

	function selectResult(result: SearchResult) {
		showResults = false;
		searchQuery = '';
		if (result.type === 'person') {
			goto(`/person/${result.id}`);
		} else {
			goto(`/verk/${result.id}`);
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && searchQuery.trim()) {
			goto(`/sok?q=${encodeURIComponent(searchQuery.trim())}`);
		} else if (e.key === 'Escape') {
			showResults = false;
		}
	}

	function handleBlur() {
		setTimeout(() => { showResults = false; }, 200);
	}

	onMount(() => {
		try {
			const db = getDatabase();

			// Get featured performances (with images)
			featuredPerformances = getRandomClassicalPlays(8);

			// Get Ibsen plays
			ibsenPlays = getPlaysByPlaywright(IBSEN_ID, 8);

			// Get top creators
			const creatorsStmt = db.prepare(`
				SELECT
					p.id,
					p.name,
					COUNT(DISTINCT pf.id) as performance_count
				FROM persons p
				JOIN works w ON w.playwright_id = p.id OR w.composer_id = p.id
				JOIN performances pf ON pf.work_id = w.id
				GROUP BY p.id
				ORDER BY performance_count DESC
				LIMIT 6
			`);
			topCreators = [];
			while (creatorsStmt.step()) {
				topCreators.push(creatorsStmt.getAsObject() as TopCreator);
			}
			creatorsStmt.free();

			// Get concerts
			concerts = getRecentConcerts(6);

			// Get stats
			stats.theater = getClassicalPerformanceCount();
			stats.concerts = getBergenPhilConcertCount();

			const personResult = db.exec('SELECT COUNT(*) FROM persons');
			if (personResult.length > 0) {
				stats.persons = personResult[0].values[0][0] as number;
			}
			const operaResult = db.exec("SELECT COUNT(*) FROM performances p JOIN works w ON p.work_id = w.id WHERE w.work_type IN ('opera', 'operetta', 'ballet')");
			if (operaResult.length > 0) {
				stats.opera = operaResult[0].values[0][0] as number;
			}

			loading = false;
		} catch (e) {
			console.error('Failed to load landing page data:', e);
			loading = false;
		}
	});

	function formatDuration(seconds: number | null): string {
		if (!seconds) return '';
		const h = Math.floor(seconds / 3600);
		const m = Math.floor((seconds % 3600) / 60);
		if (h > 0) return `${h}t ${m}m`;
		return `${m} min`;
	}
</script>

<svelte:head>
	<title>Kulturbase.no - Norsk scenekunst</title>
	<meta name="description" content="Utforsk klassisk norsk teater, opera og konserter fra NRK-arkivet." />
</svelte:head>

{#if loading}
	<div class="loading">Laster...</div>
{:else}
	<div class="landing">
		<!-- Search -->
		<section class="search-section">
			<div class="search-container">
				<input
					type="text"
					placeholder="Søk etter stykker, personer..."
					bind:value={searchQuery}
					on:input={handleSearchInput}
					on:keydown={handleKeydown}
					on:focus={() => searchResults.length > 0 && (showResults = true)}
					on:blur={handleBlur}
				/>
				{#if showResults}
					<div class="search-results">
						{#each searchResults as result}
							<button class="result-item" on:click={() => selectResult(result)}>
								<div class="result-image">
									{#if result.image_url}
										<img src={result.image_url} alt="" />
									{:else}
										<div class="result-placeholder" data-type={result.type}>
											{result.type === 'person' ? '👤' : '🎭'}
										</div>
									{/if}
								</div>
								<div class="result-info">
									<span class="result-title">{result.title}</span>
									{#if result.subtitle}
										<span class="result-subtitle">{result.subtitle}</span>
									{/if}
								</div>
								{#if result.count > 0}
									<span class="result-count">{result.count}</span>
								{/if}
							</button>
						{/each}
						<a href="/sok?q={encodeURIComponent(searchQuery)}" class="result-all">
							Alle resultater →
						</a>
					</div>
				{/if}
			</div>
			<nav class="quick-stats">
				<a href="/teater">{stats.theater} teateropptak</a>
				<a href="/konserter">{stats.concerts} konserter</a>
				<a href="/opera">{stats.opera} opera & ballett</a>
				<a href="/persons">{stats.persons} skapere</a>
			</nav>
		</section>

		<!-- Featured grid -->
		{#if featuredPerformances.length > 0}
			<section class="featured">
				<h2>Utvalgte klassikere</h2>
				<div class="grid">
					{#each featuredPerformances as perf}
						<a href="/opptak/{perf.id}" class="card">
							<div class="card-image">
								{#if perf.image_url}
									<img src={perf.image_url} alt="" />
								{:else}
									<div class="placeholder"></div>
								{/if}
								{#if perf.medium}
									<span class="badge">{perf.medium === 'tv' ? 'TV' : 'Radio'}</span>
								{/if}
							</div>
							<div class="card-body">
								<h3>{perf.work_title || perf.title}</h3>
								{#if perf.playwright_name}
									<p class="author">{perf.playwright_name}</p>
								{/if}
								{#if perf.year}
									<p class="meta">{perf.year}</p>
								{/if}
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Creators -->
		{#if topCreators.length > 0}
			<section class="creators">
				<div class="section-header">
					<h2>Skapere</h2>
					<a href="/persons" class="link">Alle →</a>
				</div>
				<div class="creator-list">
					{#each topCreators as creator}
						<a href="/person/{creator.id}" class="creator">
							{creator.name}
						</a>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Ibsen -->
		{#if ibsenPlays.length > 0}
			<section class="row-section">
				<div class="section-header">
					<h2>Henrik Ibsen</h2>
					<a href="/person/{IBSEN_ID}" class="link">Alle →</a>
				</div>
				<div class="row">
					{#each ibsenPlays as perf}
						<a href="/opptak/{perf.id}" class="row-card">
							{#if perf.image_url}
								<img src={perf.image_url} alt="" />
							{:else}
								<div class="row-placeholder"></div>
							{/if}
							<span class="row-title">{perf.work_title || perf.title}</span>
							{#if perf.year}<span class="row-year">{perf.year}</span>{/if}
						</a>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Concerts -->
		{#if concerts.length > 0}
			<section class="row-section">
				<div class="section-header">
					<h2>Konserter</h2>
					<a href="/konserter" class="link">Alle →</a>
				</div>
				<div class="row">
					{#each concerts as concert}
						<a href={concert.url} target="_blank" rel="noopener" class="row-card concert">
							<div class="concert-icon">♪</div>
							<span class="row-title">{concert.title}</span>
						</a>
					{/each}
				</div>
			</section>
		{/if}
	</div>
{/if}

<style>
	.loading {
		text-align: center;
		padding: 4rem;
		color: #888;
	}

	.landing {
		display: flex;
		flex-direction: column;
		gap: 3rem;
	}

	/* Search section */
	.search-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
		padding: 1.5rem 0;
	}

	.search-container {
		position: relative;
		width: 100%;
		max-width: 480px;
	}

	.search-container input {
		width: 100%;
		padding: 0.875rem 1.25rem;
		font-size: 1rem;
		border: 2px solid #e0e0e0;
		border-radius: 8px;
		outline: none;
		transition: border-color 0.15s, box-shadow 0.15s;
	}

	.search-container input:focus {
		border-color: #e94560;
		box-shadow: 0 0 0 3px rgba(233, 69, 96, 0.1);
	}

	.search-container input::placeholder {
		color: #999;
	}

	.search-results {
		position: absolute;
		top: calc(100% + 6px);
		left: 0;
		right: 0;
		background: white;
		border-radius: 12px;
		box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
		z-index: 100;
		overflow: hidden;
	}

	.result-item {
		display: flex;
		align-items: center;
		gap: 1rem;
		width: 100%;
		padding: 0.75rem 1rem;
		border: none;
		background: none;
		text-align: left;
		cursor: pointer;
		transition: background 0.1s;
	}

	.result-item:hover {
		background: #f5f5f5;
	}

	.result-image {
		width: 56px;
		height: 56px;
		border-radius: 6px;
		overflow: hidden;
		flex-shrink: 0;
	}

	.result-image img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.result-placeholder {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		background: #f0f0f0;
		font-size: 1.25rem;
	}

	.result-placeholder[data-type="person"] {
		border-radius: 50%;
	}

	.result-info {
		flex: 1;
		min-width: 0;
	}

	.result-title {
		display: block;
		font-weight: 500;
		color: #333;
	}

	.result-subtitle {
		display: block;
		font-size: 0.85rem;
		color: #666;
	}

	.result-count {
		background: #e94560;
		color: white;
		font-size: 0.75rem;
		font-weight: 600;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		flex-shrink: 0;
	}

	.result-all {
		display: block;
		padding: 0.75rem 1rem;
		text-align: center;
		color: #e94560;
		text-decoration: none;
		font-size: 0.9rem;
		border-top: 1px solid #eee;
	}

	.result-all:hover {
		background: #fdf2f4;
	}

	.quick-stats {
		display: flex;
		gap: 1.5rem;
	}

	.quick-stats a {
		color: #888;
		text-decoration: none;
		font-size: 0.85rem;
	}

	.quick-stats a:hover {
		color: #e94560;
	}

	/* Section headers */
	.section-header {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		margin-bottom: 1rem;
	}

	.section-header h2 {
		font-size: 1.25rem;
		font-weight: 600;
	}

	.link {
		color: #e94560;
		text-decoration: none;
		font-size: 0.9rem;
	}

	.link:hover {
		text-decoration: underline;
	}

	/* Featured grid */
	.featured h2 {
		font-size: 1.25rem;
		font-weight: 600;
		margin-bottom: 1rem;
	}

	.grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 1.5rem;
	}

	.card {
		text-decoration: none;
		color: inherit;
	}

	.card-image {
		position: relative;
		aspect-ratio: 16/10;
		border-radius: 8px;
		overflow: hidden;
		background: #f0f0f0;
		margin-bottom: 0.75rem;
	}

	.card-image img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		transition: transform 0.2s;
	}

	.card:hover .card-image img {
		transform: scale(1.03);
	}

	.card-image .placeholder {
		width: 100%;
		height: 100%;
		background: linear-gradient(135deg, #2d3748, #1a202c);
	}

	.card-image .badge {
		position: absolute;
		top: 0.5rem;
		left: 0.5rem;
		background: rgba(0,0,0,0.7);
		color: white;
		font-size: 0.7rem;
		padding: 0.2rem 0.5rem;
		border-radius: 3px;
	}

	.card-body h3 {
		font-size: 0.95rem;
		font-weight: 500;
		line-height: 1.3;
		margin-bottom: 0.25rem;
	}

	.card-body .author {
		font-size: 0.85rem;
		color: #666;
	}

	.card-body .meta {
		font-size: 0.8rem;
		color: #999;
	}

	/* Creators */
	.creator-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
	}

	.creator {
		padding: 0.5rem 1rem;
		background: white;
		border: 1px solid #e0e0e0;
		border-radius: 4px;
		text-decoration: none;
		color: #333;
		font-size: 0.9rem;
	}

	.creator:hover {
		border-color: #e94560;
		color: #e94560;
	}

	/* Horizontal rows */
	.row {
		display: flex;
		gap: 1rem;
		overflow-x: auto;
		padding-bottom: 0.5rem;
	}

	.row::-webkit-scrollbar {
		height: 4px;
	}

	.row::-webkit-scrollbar-thumb {
		background: #ddd;
		border-radius: 2px;
	}

	.row-card {
		flex: 0 0 160px;
		text-decoration: none;
		color: inherit;
	}

	.row-card img {
		width: 100%;
		height: 90px;
		object-fit: cover;
		border-radius: 6px;
		margin-bottom: 0.5rem;
	}

	.row-placeholder {
		width: 100%;
		height: 90px;
		background: linear-gradient(135deg, #2d3748, #1a202c);
		border-radius: 6px;
		margin-bottom: 0.5rem;
	}

	.row-card.concert {
		background: #f8f9fa;
		border-radius: 6px;
		padding: 1rem;
		display: flex;
		flex-direction: column;
		height: 130px;
	}

	.concert-icon {
		font-size: 1.5rem;
		color: #667eea;
		margin-bottom: 0.5rem;
	}

	.row-title {
		font-size: 0.85rem;
		font-weight: 500;
		line-height: 1.3;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.row-year {
		font-size: 0.75rem;
		color: #999;
	}

	/* Responsive */
	@media (max-width: 1000px) {
		.grid {
			grid-template-columns: repeat(3, 1fr);
		}
	}

	@media (max-width: 768px) {
		.grid {
			grid-template-columns: repeat(2, 1fr);
			gap: 1rem;
		}

		.stats-bar {
			flex-wrap: wrap;
			gap: 1rem;
		}
	}

	@media (max-width: 500px) {
		.grid {
			grid-template-columns: 1fr;
		}

		.row-card {
			flex: 0 0 140px;
		}
	}
</style>

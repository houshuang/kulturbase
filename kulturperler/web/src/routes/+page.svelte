<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { getRandomClassicalPlays, getPlaysByPlaywright, getRecentConcerts, getClassicalPlayCount, getClassicalPerformanceCount, getBergenPhilConcertCount, getPerformanceCount, getDatabase, type RandomPerformance } from '$lib/db';
	import type { PerformanceWithDetails, ExternalResource } from '$lib/types';

	interface TopCreator {
		id: number;
		name: string;
		work_count: number;
		performance_count: number;
	}

	interface TopWork {
		id: number;
		title: string;
		playwright_name: string | null;
		playwright_id: number | null;
		performance_count: number;
		image_url: string | null;
	}

	interface SearchResult {
		type: 'person' | 'work' | 'performance';
		id: number;
		title: string;
		subtitle: string | null;
	}

	let heroPerformance: RandomPerformance | null = null;
	let ibsenPlays: PerformanceWithDetails[] = [];
	let topCreators: TopCreator[] = [];
	let topWorks: TopWork[] = [];
	let concerts: ExternalResource[] = [];
	let moreClassics: RandomPerformance[] = [];

	let stats = {
		classicalPlays: 0,
		classicalPerformances: 0,
		totalPerformances: 0,
		concerts: 0,
		persons: 0,
		operaBallett: 0
	};

	let loading = true;
	let searchQuery = '';
	let searchResults: SearchResult[] = [];
	let showResults = false;
	let searchTimeout: ReturnType<typeof setTimeout> | null = null;

	const IBSEN_ID = 1;

	function handleSearch() {
		if (searchQuery.trim()) {
			goto(`/sok?q=${encodeURIComponent(searchQuery.trim())}`);
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			handleSearch();
		} else if (e.key === 'Escape') {
			showResults = false;
		}
	}

	function handleInput() {
		if (searchTimeout) clearTimeout(searchTimeout);

		if (searchQuery.trim().length < 2) {
			searchResults = [];
			showResults = false;
			return;
		}

		searchTimeout = setTimeout(() => {
			performSearch();
		}, 150);
	}

	function performSearch() {
		const query = searchQuery.trim().toLowerCase();
		if (query.length < 2) return;

		const db = getDatabase();
		const results: SearchResult[] = [];

		// Search persons
		const personStmt = db.prepare(`
			SELECT id, name FROM persons
			WHERE LOWER(name) LIKE ?
			ORDER BY
				CASE WHEN LOWER(name) LIKE ? THEN 0 ELSE 1 END,
				name
			LIMIT 5
		`);
		personStmt.bind([`%${query}%`, `${query}%`]);
		while (personStmt.step()) {
			const row = personStmt.getAsObject() as { id: number; name: string };
			results.push({
				type: 'person',
				id: row.id,
				title: row.name,
				subtitle: null
			});
		}
		personStmt.free();

		// Search works
		const workStmt = db.prepare(`
			SELECT w.id, w.title, p.name as playwright_name
			FROM works w
			LEFT JOIN persons p ON w.playwright_id = p.id
			WHERE LOWER(w.title) LIKE ?
			ORDER BY
				CASE WHEN LOWER(w.title) LIKE ? THEN 0 ELSE 1 END,
				w.title
			LIMIT 5
		`);
		workStmt.bind([`%${query}%`, `${query}%`]);
		while (workStmt.step()) {
			const row = workStmt.getAsObject() as { id: number; title: string; playwright_name: string | null };
			results.push({
				type: 'work',
				id: row.id,
				title: row.title,
				subtitle: row.playwright_name
			});
		}
		workStmt.free();

		searchResults = results;
		showResults = results.length > 0;
	}

	function selectResult(result: SearchResult) {
		showResults = false;
		if (result.type === 'person') {
			goto(`/person/${result.id}`);
		} else if (result.type === 'work') {
			goto(`/verk/${result.id}`);
		}
	}

	function handleBlur() {
		setTimeout(() => {
			showResults = false;
		}, 200);
	}

	onMount(() => {
		try {
			const db = getDatabase();

			// Get random classical plays for hero and more section
			const randomPlays = getRandomClassicalPlays(7);
			if (randomPlays.length > 0) {
				heroPerformance = randomPlays[0];
				moreClassics = randomPlays.slice(1);
			}

			// Get Ibsen plays
			ibsenPlays = getPlaysByPlaywright(IBSEN_ID, 8);

			// Get top creators (by number of performances of their works)
			const creatorsStmt = db.prepare(`
				SELECT
					p.id,
					p.name,
					COUNT(DISTINCT w.id) as work_count,
					COUNT(DISTINCT pf.id) as performance_count
				FROM persons p
				JOIN works w ON w.playwright_id = p.id OR w.composer_id = p.id
				JOIN performances pf ON pf.work_id = w.id
				GROUP BY p.id
				ORDER BY performance_count DESC
				LIMIT 8
			`);
			topCreators = [];
			while (creatorsStmt.step()) {
				topCreators.push(creatorsStmt.getAsObject() as TopCreator);
			}
			creatorsStmt.free();

			// Get works with most recordings
			const worksStmt = db.prepare(`
				SELECT
					w.id,
					w.title,
					p.name as playwright_name,
					p.id as playwright_id,
					COUNT(pf.id) as performance_count,
					(SELECT e.image_url FROM episodes e
					 JOIN performances pf2 ON e.performance_id = pf2.id
					 WHERE pf2.work_id = w.id LIMIT 1) as image_url
				FROM works w
				LEFT JOIN persons p ON w.playwright_id = p.id
				JOIN performances pf ON pf.work_id = w.id
				GROUP BY w.id
				HAVING performance_count > 1
				ORDER BY performance_count DESC
				LIMIT 8
			`);
			topWorks = [];
			while (worksStmt.step()) {
				topWorks.push(worksStmt.getAsObject() as TopWork);
			}
			worksStmt.free();

			// Get random concerts
			concerts = getRecentConcerts(8);

			// Get stats
			stats.classicalPlays = getClassicalPlayCount();
			stats.classicalPerformances = getClassicalPerformanceCount();
			stats.totalPerformances = getPerformanceCount();
			stats.concerts = getBergenPhilConcertCount();

			const personResult = db.exec('SELECT COUNT(*) FROM persons');
			if (personResult.length > 0) {
				stats.persons = personResult[0].values[0][0] as number;
			}
			const operaResult = db.exec("SELECT COUNT(*) FROM performances p JOIN works w ON p.work_id = w.id WHERE w.work_type IN ('opera', 'operetta', 'ballet')");
			if (operaResult.length > 0) {
				stats.operaBallett = operaResult[0].values[0][0] as number;
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
	<title>Kulturbase.no - Klassisk norsk scenekunst</title>
	<meta name="description" content="Utforsk klassisk norsk teater, opera og konserter fra NRK-arkivet. Ibsen, Bjørnson, Grieg og mer." />
</svelte:head>

{#if loading}
	<div class="loading">
		<p>Laster...</p>
	</div>
{:else}
	<div class="landing-page">
		<!-- Search Section -->
		<section class="search-section">
			<h1>Kulturbase.no</h1>
			<p class="tagline">Norsk scenekunst og klassisk musikk</p>
			<div class="search-wrapper">
				<div class="search-box">
					<svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<circle cx="11" cy="11" r="8"/>
						<path d="M21 21l-4.35-4.35"/>
					</svg>
					<input
						type="text"
						placeholder="Søk etter stykker, personer, opptak..."
						bind:value={searchQuery}
						on:keydown={handleKeydown}
						on:input={handleInput}
						on:focus={() => searchResults.length > 0 && (showResults = true)}
						on:blur={handleBlur}
					/>
				</div>
				{#if showResults && searchResults.length > 0}
					<div class="search-results">
						{#each searchResults as result}
							<button class="search-result" on:click={() => selectResult(result)}>
								<span class="result-type">{result.type === 'person' ? 'Person' : 'Verk'}</span>
								<span class="result-title">{result.title}</span>
								{#if result.subtitle}
									<span class="result-subtitle">{result.subtitle}</span>
								{/if}
							</button>
						{/each}
						<a href="/sok?q={encodeURIComponent(searchQuery)}" class="search-all">
							Vis alle resultater for «{searchQuery}»
						</a>
					</div>
				{/if}
			</div>
			<div class="quick-links">
				<a href="/teater" class="quick-link">Teater</a>
				<a href="/konserter" class="quick-link">Klassisk</a>
				<a href="/opera" class="quick-link">Opera & Ballett</a>
				<a href="/persons" class="quick-link">Skapere</a>
			</div>
		</section>

		<!-- Top Creators -->
		{#if topCreators.length > 0}
			<section class="discovery-row">
				<div class="row-header">
					<h2>Mest i arkivet</h2>
					<a href="/persons" class="see-more">Alle skapere</a>
				</div>
				<div class="creators-row">
					{#each topCreators as creator}
						<a href="/person/{creator.id}" class="creator-chip">
							<span class="creator-name">{creator.name}</span>
							<span class="creator-count">{creator.performance_count}</span>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Top Works -->
		{#if topWorks.length > 0}
			<section class="discovery-row">
				<div class="row-header">
					<h2>Flest innspillinger</h2>
					<a href="/teater" class="see-more">Alle verk</a>
				</div>
				<div class="row-scroll">
					{#each topWorks as work}
						<a href="/verk/{work.id}" class="perf-card">
							{#if work.image_url}
								<img src={work.image_url} alt={work.title} loading="lazy" />
							{:else}
								<div class="card-placeholder">Teater</div>
							{/if}
							<div class="card-info">
								<h3>{work.title}</h3>
								<div class="card-meta">
									{#if work.playwright_name}
										<span class="author">{work.playwright_name}</span>
									{/if}
									<span class="count">{work.performance_count} opptak</span>
								</div>
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Featured Performance -->
		{#if heroPerformance}
			<section class="hero">
				<div class="hero-content">
					<div class="hero-image">
						{#if heroPerformance.image_url}
							<img src={heroPerformance.image_url} alt={heroPerformance.work_title || ''} />
						{:else}
							<div class="hero-placeholder">
								<span>Klassisk teater</span>
							</div>
						{/if}
					</div>
					<div class="hero-info">
						<span class="hero-label">Tilfeldig klassiker</span>
						<h2>{heroPerformance.work_title || heroPerformance.title}</h2>
						{#if heroPerformance.playwright_name}
							<p class="hero-author">
								<a href="/person/{heroPerformance.playwright_id}">{heroPerformance.playwright_name}</a>
							</p>
						{/if}
						<div class="hero-meta">
							{#if heroPerformance.year}
								<span class="year">{heroPerformance.year}</span>
							{/if}
							{#if heroPerformance.director_name}
								<span class="director">Regi: {heroPerformance.director_name}</span>
							{/if}
							{#if heroPerformance.total_duration}
								<span class="duration">{formatDuration(heroPerformance.total_duration)}</span>
							{/if}
							{#if heroPerformance.medium}
								<span class="medium">{heroPerformance.medium === 'tv' ? 'TV' : 'Radio'}</span>
							{/if}
						</div>
						{#if heroPerformance.work_synopsis}
							<p class="hero-synopsis">{heroPerformance.work_synopsis}</p>
						{/if}
						<a href="/opptak/{heroPerformance.id}" class="hero-cta">Se opptak</a>
					</div>
				</div>
			</section>
		{/if}

		<!-- Ibsen -->
		{#if ibsenPlays.length > 0}
			<section class="discovery-row">
				<div class="row-header">
					<h2>Ibsen i arkivet</h2>
					<a href="/person/{IBSEN_ID}" class="see-more">Alle Ibsen-opptak</a>
				</div>
				<div class="row-scroll">
					{#each ibsenPlays as perf}
						<a href="/opptak/{perf.id}" class="perf-card">
							{#if perf.image_url}
								<img src={perf.image_url} alt={perf.work_title || ''} loading="lazy" />
							{:else}
								<div class="card-placeholder">Teater</div>
							{/if}
							<div class="card-info">
								<h3>{perf.work_title || perf.title}</h3>
								{#if perf.year}<span class="year">{perf.year}</span>{/if}
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		{#if concerts.length > 0}
			<section class="discovery-row">
				<div class="row-header">
					<h2>Bergen Filharmoniske Orkester</h2>
					<a href="/konserter" class="see-more">Alle konserter</a>
				</div>
				<div class="row-scroll">
					{#each concerts as concert}
						<a href={concert.url} target="_blank" rel="noopener" class="concert-card">
							<div class="concert-placeholder">
								<svg viewBox="0 0 24 24" fill="currentColor">
									<path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
								</svg>
							</div>
							<div class="card-info">
								<h3>{concert.title}</h3>
								<span class="external">bergenphilive.no</span>
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		{#if moreClassics.length > 0}
			<section class="discovery-row">
				<div class="row-header">
					<h2>Flere klassikere</h2>
					<a href="/teater" class="see-more">Utforsk teater</a>
				</div>
				<div class="row-scroll">
					{#each moreClassics as perf}
						<a href="/opptak/{perf.id}" class="perf-card">
							{#if perf.image_url}
								<img src={perf.image_url} alt={perf.work_title || ''} loading="lazy" />
							{:else}
								<div class="card-placeholder">Teater</div>
							{/if}
							<div class="card-info">
								<h3>{perf.work_title || perf.title}</h3>
								{#if perf.playwright_name}<span class="author">{perf.playwright_name}</span>{/if}
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Stats Section -->
		<section class="stats-section">
			<h2>Arkivet i tall</h2>
			<div class="stats-grid">
				<a href="/teater" class="stat-item clickable">
					<span class="stat-value">{stats.classicalPerformances}</span>
					<span class="stat-label">teateropptak</span>
				</a>
				<a href="/konserter" class="stat-item clickable">
					<span class="stat-value">{stats.concerts}</span>
					<span class="stat-label">konserter</span>
				</a>
				<a href="/opera" class="stat-item clickable">
					<span class="stat-value">{stats.operaBallett}</span>
					<span class="stat-label">opera & ballett</span>
				</a>
				<a href="/persons" class="stat-item clickable">
					<span class="stat-value">{stats.persons}</span>
					<span class="stat-label">skapere</span>
				</a>
			</div>
		</section>
	</div>
{/if}

<style>
	.loading {
		text-align: center;
		padding: 4rem;
		color: #666;
	}

	.landing-page {
		display: flex;
		flex-direction: column;
		gap: 2.5rem;
	}

	/* Search Section - Light design */
	.search-section {
		text-align: center;
		padding: 2rem 1rem;
	}

	.search-section h1 {
		font-size: 2rem;
		font-weight: 700;
		margin-bottom: 0.25rem;
		color: #1a1a2e;
	}

	.search-section .tagline {
		font-size: 1rem;
		color: #666;
		margin-bottom: 1.5rem;
	}

	.search-wrapper {
		position: relative;
		max-width: 500px;
		margin: 0 auto 1rem;
	}

	.search-box {
		display: flex;
		align-items: center;
		background: white;
		border: 2px solid #e0e0e0;
		border-radius: 8px;
		overflow: hidden;
		transition: border-color 0.2s, box-shadow 0.2s;
	}

	.search-box:focus-within {
		border-color: #e94560;
		box-shadow: 0 0 0 3px rgba(233, 69, 96, 0.1);
	}

	.search-icon {
		width: 20px;
		height: 20px;
		margin-left: 1rem;
		color: #999;
		flex-shrink: 0;
	}

	.search-box input {
		flex: 1;
		padding: 0.875rem 1rem;
		border: none;
		font-size: 1rem;
		color: #333;
		outline: none;
		background: transparent;
	}

	.search-box input::placeholder {
		color: #999;
	}

	.search-results {
		position: absolute;
		top: 100%;
		left: 0;
		right: 0;
		background: white;
		border: 1px solid #e0e0e0;
		border-radius: 8px;
		margin-top: 4px;
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
		z-index: 100;
		overflow: hidden;
	}

	.search-result {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		width: 100%;
		padding: 0.75rem 1rem;
		border: none;
		background: none;
		text-align: left;
		cursor: pointer;
		transition: background 0.15s;
	}

	.search-result:hover {
		background: #f5f5f5;
	}

	.result-type {
		font-size: 0.7rem;
		text-transform: uppercase;
		background: #e0e0e0;
		color: #666;
		padding: 0.15rem 0.4rem;
		border-radius: 3px;
		flex-shrink: 0;
	}

	.result-title {
		font-weight: 500;
		color: #333;
	}

	.result-subtitle {
		color: #888;
		font-size: 0.9rem;
	}

	.search-all {
		display: block;
		padding: 0.75rem 1rem;
		text-align: center;
		color: #e94560;
		text-decoration: none;
		font-size: 0.9rem;
		border-top: 1px solid #eee;
	}

	.search-all:hover {
		background: #fdf2f4;
	}

	.quick-links {
		display: flex;
		justify-content: center;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.quick-link {
		padding: 0.4rem 0.875rem;
		background: #f5f5f5;
		color: #555;
		text-decoration: none;
		border-radius: 20px;
		font-size: 0.85rem;
		transition: background 0.2s, color 0.2s;
	}

	.quick-link:hover {
		background: #e94560;
		color: white;
	}

	/* Creators Row */
	.creators-row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.creator-chip {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0.875rem;
		background: white;
		border: 1px solid #e0e0e0;
		border-radius: 20px;
		text-decoration: none;
		color: #333;
		font-size: 0.9rem;
		transition: border-color 0.2s, background 0.2s;
	}

	.creator-chip:hover {
		border-color: #e94560;
		background: #fdf2f4;
	}

	.creator-name {
		font-weight: 500;
	}

	.creator-count {
		background: #e94560;
		color: white;
		font-size: 0.75rem;
		padding: 0.1rem 0.4rem;
		border-radius: 10px;
		font-weight: 600;
	}

	/* Hero Section */
	.hero {
		background: white;
		border-radius: 12px;
		overflow: hidden;
		box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
	}

	.hero-content {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 2rem;
	}

	.hero-image {
		aspect-ratio: 16/10;
		overflow: hidden;
	}

	.hero-image img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.hero-placeholder {
		width: 100%;
		height: 100%;
		background: linear-gradient(135deg, #1a1a2e, #16213e);
		display: flex;
		align-items: center;
		justify-content: center;
		color: rgba(255, 255, 255, 0.5);
		font-size: 1.5rem;
	}

	.hero-info {
		padding: 2rem;
		display: flex;
		flex-direction: column;
		justify-content: center;
	}

	.hero-label {
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: #e94560;
		margin-bottom: 0.5rem;
	}

	.hero-info h2 {
		font-size: 1.75rem;
		margin-bottom: 0.5rem;
		line-height: 1.2;
	}

	.hero-author {
		font-size: 1rem;
		color: #666;
		margin-bottom: 1rem;
	}

	.hero-author a {
		color: #e94560;
		text-decoration: none;
	}

	.hero-author a:hover {
		text-decoration: underline;
	}

	.hero-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		font-size: 0.85rem;
		color: #666;
		margin-bottom: 1rem;
	}

	.hero-meta .year {
		background: #e94560;
		color: white;
		padding: 0.1rem 0.4rem;
		border-radius: 4px;
	}

	.hero-meta .medium {
		background: #1a1a2e;
		color: white;
		padding: 0.1rem 0.4rem;
		border-radius: 4px;
	}

	.hero-synopsis {
		color: #555;
		line-height: 1.6;
		margin-bottom: 1.5rem;
		display: -webkit-box;
		-webkit-line-clamp: 3;
		-webkit-box-orient: vertical;
		overflow: hidden;
		font-size: 0.95rem;
	}

	.hero-cta {
		display: inline-block;
		background: #e94560;
		color: white;
		padding: 0.625rem 1.25rem;
		border-radius: 6px;
		text-decoration: none;
		font-weight: 500;
		font-size: 0.9rem;
		transition: background 0.2s;
		align-self: flex-start;
	}

	.hero-cta:hover {
		background: #d63d56;
	}

	/* Discovery Rows */
	.discovery-row {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.row-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.row-header h2 {
		font-size: 1.1rem;
		font-weight: 600;
	}

	.see-more {
		color: #e94560;
		text-decoration: none;
		font-size: 0.85rem;
	}

	.see-more:hover {
		text-decoration: underline;
	}

	.row-scroll {
		display: flex;
		gap: 0.875rem;
		overflow-x: auto;
		padding-bottom: 0.5rem;
		scroll-snap-type: x mandatory;
		-webkit-overflow-scrolling: touch;
	}

	.row-scroll::-webkit-scrollbar {
		height: 6px;
	}

	.row-scroll::-webkit-scrollbar-track {
		background: #f0f0f0;
		border-radius: 3px;
	}

	.row-scroll::-webkit-scrollbar-thumb {
		background: #ccc;
		border-radius: 3px;
	}

	.perf-card, .concert-card {
		flex: 0 0 180px;
		background: white;
		border-radius: 8px;
		overflow: hidden;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
		scroll-snap-align: start;
	}

	.perf-card:hover, .concert-card:hover {
		transform: translateY(-3px);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
	}

	.perf-card img {
		width: 100%;
		height: 100px;
		object-fit: cover;
	}

	.card-placeholder {
		width: 100%;
		height: 100px;
		background: linear-gradient(135deg, #1a1a2e, #16213e);
		display: flex;
		align-items: center;
		justify-content: center;
		color: rgba(255, 255, 255, 0.5);
		font-size: 0.85rem;
	}

	.concert-placeholder {
		width: 100%;
		height: 100px;
		background: linear-gradient(135deg, #1a365d, #2a4365);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.concert-placeholder svg {
		width: 36px;
		height: 36px;
		color: rgba(255, 255, 255, 0.5);
	}

	.card-info {
		padding: 0.625rem;
	}

	.card-info h3 {
		font-size: 0.85rem;
		font-weight: 500;
		margin-bottom: 0.25rem;
		line-height: 1.3;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.card-info .year {
		font-size: 0.75rem;
		color: #e94560;
	}

	.card-info .author {
		font-size: 0.75rem;
		color: #666;
	}

	.card-info .external {
		font-size: 0.7rem;
		color: #888;
	}

	.card-meta {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		flex-wrap: wrap;
	}

	.card-meta .count {
		font-size: 0.7rem;
		background: #e94560;
		color: white;
		padding: 0.1rem 0.35rem;
		border-radius: 3px;
	}

	/* Stats Section */
	.stats-section {
		background: white;
		border-radius: 12px;
		padding: 1.5rem;
		text-align: center;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
	}

	.stats-section h2 {
		font-size: 1rem;
		margin-bottom: 1rem;
		color: #666;
	}

	.stats-grid {
		display: flex;
		justify-content: center;
		gap: 2rem;
	}

	.stat-item {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
		text-decoration: none;
	}

	.stat-item.clickable {
		padding: 0.75rem 1rem;
		border-radius: 8px;
		transition: background 0.2s;
	}

	.stat-item.clickable:hover {
		background: #f5f5f5;
	}

	.stat-value {
		font-size: 1.5rem;
		font-weight: bold;
		color: #1a1a2e;
	}

	.stat-label {
		font-size: 0.8rem;
		color: #666;
	}

	/* Responsive */
	@media (max-width: 900px) {
		.hero-content {
			grid-template-columns: 1fr;
		}

		.hero-image {
			aspect-ratio: 16/9;
		}

		.hero-info {
			padding: 1.5rem;
		}

		.hero-info h2 {
			font-size: 1.4rem;
		}

		.stats-grid {
			flex-wrap: wrap;
			gap: 1rem;
		}
	}

	@media (max-width: 600px) {
		.landing-page {
			gap: 2rem;
		}

		.search-section h1 {
			font-size: 1.5rem;
		}

		.perf-card, .concert-card {
			flex: 0 0 150px;
		}

		.perf-card img, .card-placeholder, .concert-placeholder {
			height: 85px;
		}

		.stats-grid {
			gap: 0.5rem;
		}

		.stat-value {
			font-size: 1.25rem;
		}

		.creators-row {
			overflow-x: auto;
			flex-wrap: nowrap;
			padding-bottom: 0.5rem;
		}

		.creator-chip {
			flex-shrink: 0;
		}
	}
</style>

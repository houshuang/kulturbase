<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { getRandomClassicalPlays, getPlaysByPlaywright, getTheaterPerformanceCount, getConcertPerformanceCount, getOperaPerformanceCount, getCreatorCount, getDatabase, initDatabase, type RandomPerformance } from '$lib/db';
	import type { PerformanceWithDetails } from '$lib/types';

	let featuredPerformances: RandomPerformance[] = [];
	let ibsenPlays: PerformanceWithDetails[] = [];

	// Category showcases
	interface CategoryShowcase {
		id: number;
		title: string;
		subtitle: string | null;
		image_url: string | null;
		count: number;
		link: string;
	}
	let showcaseTeater: CategoryShowcase | null = null;
	let showcaseDrama: CategoryShowcase | null = null;
	let showcaseOpera: CategoryShowcase | null = null;
	let showcaseKonsert: CategoryShowcase | null = null;
	let showcasePerson: CategoryShowcase | null = null;

	let stats = {
		theater: 0,
		concerts: 0,
		opera: 0,
		persons: 0
	};

	let loading = true;
	let searchQuery = '';
	let searchTimeout: ReturnType<typeof setTimeout> | null = null;
	const IBSEN_ID = 1;

	function handleSearchInput() {
		if (searchTimeout) clearTimeout(searchTimeout);

		const trimmed = searchQuery.trim();
		if (trimmed.length < 2) {
			return;
		}

		// Debounce navigation to search page (400ms)
		searchTimeout = setTimeout(() => {
			goto(`/sok?q=${encodeURIComponent(trimmed)}`);
		}, 400);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && searchQuery.trim()) {
			if (searchTimeout) clearTimeout(searchTimeout);
			goto(`/sok?q=${encodeURIComponent(searchQuery.trim())}`);
		}
	}

	onMount(async () => {
		try {
			// Ensure database is initialized (waits if already loading)
			await initDatabase();
			const db = getDatabase();

			// Get featured performances (with images)
			featuredPerformances = getRandomClassicalPlays(8);

			// Get Ibsen plays
			ibsenPlays = getPlaysByPlaywright(IBSEN_ID, 8);

			// Get stats
			stats = {
				theater: getTheaterPerformanceCount(),
				concerts: getConcertPerformanceCount(),
				opera: getOperaPerformanceCount(),
				persons: getCreatorCount()
			};

			// Get category showcases - one random item from each category (with image and multiple performances)
			// Teater - use subquery to filter by image
			const teaterStmt = db.prepare(`
				SELECT * FROM (
					SELECT w.id, w.title, p.name as subtitle,
						(SELECT e.image_url FROM episodes e JOIN performances pf ON e.performance_id = pf.id WHERE pf.work_id = w.id AND e.image_url IS NOT NULL LIMIT 1) as image_url,
						COUNT(DISTINCT pf.id) as count
					FROM works w
					LEFT JOIN persons p ON w.playwright_id = p.id
					JOIN performances pf ON pf.work_id = w.id
					WHERE w.category = 'teater'
					GROUP BY w.id
					HAVING count > 1
				) WHERE image_url IS NOT NULL
				ORDER BY RANDOM()
				LIMIT 1
			`);
			if (teaterStmt.step()) {
				const row = teaterStmt.getAsObject() as any;
				showcaseTeater = { ...row, link: `/verk/${row.id}` };
			}
			teaterStmt.free();

			// Dramaserier (use count >= 1 since drama series typically have single performances)
			const dramaStmt = db.prepare(`
				SELECT * FROM (
					SELECT w.id, w.title, p.name as subtitle,
						(SELECT e.image_url FROM episodes e JOIN performances pf ON e.performance_id = pf.id WHERE pf.work_id = w.id AND e.image_url IS NOT NULL LIMIT 1) as image_url,
						COUNT(DISTINCT pf.id) as count
					FROM works w
					LEFT JOIN persons p ON w.playwright_id = p.id
					JOIN performances pf ON pf.work_id = w.id
					WHERE w.category = 'dramaserie'
					GROUP BY w.id
					HAVING count >= 1
				) WHERE image_url IS NOT NULL
				ORDER BY RANDOM()
				LIMIT 1
			`);
			if (dramaStmt.step()) {
				const row = dramaStmt.getAsObject() as any;
				showcaseDrama = { ...row, link: `/verk/${row.id}` };
			}
			dramaStmt.free();

			// Opera/Ballett
			const operaStmt = db.prepare(`
				SELECT * FROM (
					SELECT w.id, w.title, p.name as subtitle,
						(SELECT e.image_url FROM episodes e JOIN performances pf ON e.performance_id = pf.id WHERE pf.work_id = w.id AND e.image_url IS NOT NULL LIMIT 1) as image_url,
						COUNT(DISTINCT pf.id) as count
					FROM works w
					LEFT JOIN persons p ON w.composer_id = p.id
					JOIN performances pf ON pf.work_id = w.id
					WHERE w.category = 'opera'
					GROUP BY w.id
					HAVING count > 1
				) WHERE image_url IS NOT NULL
				ORDER BY RANDOM()
				LIMIT 1
			`);
			if (operaStmt.step()) {
				const row = operaStmt.getAsObject() as any;
				showcaseOpera = { ...row, link: `/verk/${row.id}` };
			}
			operaStmt.free();

			// Konsert
			const konsertStmt = db.prepare(`
				SELECT * FROM (
					SELECT w.id, w.title, p.name as subtitle,
						(SELECT e.image_url FROM episodes e JOIN performances pf ON e.performance_id = pf.id WHERE pf.work_id = w.id AND e.image_url IS NOT NULL LIMIT 1) as image_url,
						COUNT(DISTINCT pf.id) as count
					FROM works w
					LEFT JOIN persons p ON w.composer_id = p.id
					JOIN performances pf ON pf.work_id = w.id
					WHERE w.category = 'konsert'
					GROUP BY w.id
					HAVING count > 1
				) WHERE image_url IS NOT NULL
				ORDER BY RANDOM()
				LIMIT 1
			`);
			if (konsertStmt.step()) {
				const row = konsertStmt.getAsObject() as any;
				showcaseKonsert = { ...row, link: `/verk/${row.id}` };
			}
			konsertStmt.free();

			// Person (random playwright or composer with multiple works, fetch image from their performances)
			const personStmt = db.prepare(`
				SELECT * FROM (
					SELECT p.id, p.name as title,
						(CASE WHEN COUNT(DISTINCT wp.id) > 0 THEN 'Dramatiker' ELSE 'Komponist' END) as subtitle,
						COUNT(DISTINCT wp.id) + COUNT(DISTINCT wc.id) as count,
						(SELECT e.image_url FROM episodes e
						 JOIN performances pf ON e.performance_id = pf.id
						 JOIN works w ON pf.work_id = w.id
						 WHERE (w.playwright_id = p.id OR w.composer_id = p.id) AND e.image_url IS NOT NULL
						 LIMIT 1) as image_url
					FROM persons p
					LEFT JOIN works wp ON wp.playwright_id = p.id
					LEFT JOIN works wc ON wc.composer_id = p.id
					GROUP BY p.id
					HAVING count > 1
				) WHERE image_url IS NOT NULL
				ORDER BY RANDOM()
				LIMIT 1
			`);
			if (personStmt.step()) {
				const row = personStmt.getAsObject() as any;
				showcasePerson = { ...row, link: `/person/${row.id}` };
			}
			personStmt.free();

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
				/>
			</div>
			<nav class="quick-stats">
				<a href="/teater">{stats.theater} teateropptak</a>
				<a href="/konserter">{stats.concerts} konserter</a>
				<a href="/opera">{stats.opera} opera & ballett</a>
				<a href="/forfattere">{stats.persons} forfattere</a>
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

		<!-- Category showcase -->
		<section class="showcase-section">
			<h2>Utforsk kategorier</h2>
			<div class="showcase-grid">
				<div class="showcase-card">
					<a href={showcaseTeater?.link || '/teater'} class="showcase-main">
						<div class="showcase-image">
							{#if showcaseTeater?.image_url}
								<img src={showcaseTeater.image_url} alt="" />
							{:else}
								<div class="showcase-placeholder">🎭</div>
							{/if}
						</div>
						<div class="showcase-info">
							<span class="showcase-category">Teater</span>
							<span class="showcase-title">{showcaseTeater?.title || 'Teaterstykker'}</span>
						</div>
					</a>
					<a href="/teater" class="showcase-all">{stats.theater} opptak →</a>
				</div>
				<div class="showcase-card">
					<a href={showcaseDrama?.link || '/dramaserier'} class="showcase-main">
						<div class="showcase-image">
							{#if showcaseDrama?.image_url}
								<img src={showcaseDrama.image_url} alt="" />
							{:else}
								<div class="showcase-placeholder">📺</div>
							{/if}
						</div>
						<div class="showcase-info">
							<span class="showcase-category">Dramaserier</span>
							<span class="showcase-title">{showcaseDrama?.title || 'Dramaserier'}</span>
						</div>
					</a>
					<a href="/dramaserier" class="showcase-all">Se alle →</a>
				</div>
				<div class="showcase-card">
					<a href={showcaseOpera?.link || '/opera'} class="showcase-main">
						<div class="showcase-image">
							{#if showcaseOpera?.image_url}
								<img src={showcaseOpera.image_url} alt="" />
							{:else}
								<div class="showcase-placeholder">🩰</div>
							{/if}
						</div>
						<div class="showcase-info">
							<span class="showcase-category">Opera & Ballett</span>
							<span class="showcase-title">{showcaseOpera?.title || 'Opera og ballett'}</span>
						</div>
					</a>
					<a href="/opera" class="showcase-all">{stats.opera} opptak →</a>
				</div>
				<div class="showcase-card">
					<a href={showcaseKonsert?.link || '/konserter'} class="showcase-main">
						<div class="showcase-image">
							{#if showcaseKonsert?.image_url}
								<img src={showcaseKonsert.image_url} alt="" />
							{:else}
								<div class="showcase-placeholder">🎵</div>
							{/if}
						</div>
						<div class="showcase-info">
							<span class="showcase-category">Konserter</span>
							<span class="showcase-title">{showcaseKonsert?.title || 'Klassisk musikk'}</span>
						</div>
					</a>
					<a href="/konserter" class="showcase-all">{stats.concerts} opptak →</a>
				</div>
				<div class="showcase-card">
					<a href={showcasePerson?.link || '/forfattere'} class="showcase-main">
						<div class="showcase-image">
							{#if showcasePerson?.image_url}
								<img src={showcasePerson.image_url} alt="" />
							{:else}
								<div class="showcase-placeholder person">👤</div>
							{/if}
						</div>
						<div class="showcase-info">
							<span class="showcase-category">Personer</span>
							<span class="showcase-title">{showcasePerson?.title || 'Forfattere & komponister'}</span>
						</div>
					</a>
					<a href="/forfattere" class="showcase-all">{stats.persons} personer →</a>
				</div>
			</div>
		</section>

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

	.row-placeholder.music {
		background: linear-gradient(135deg, #667eea, #764ba2);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 2rem;
		color: rgba(255,255,255,0.5);
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

	.row-composer {
		font-size: 0.75rem;
		color: #666;
	}

	.row-count {
		font-size: 0.7rem;
		color: #e94560;
		margin-top: 0.25rem;
	}

	/* Showcase section */
	.showcase-section {
		margin-top: 1rem;
	}

	.showcase-section h2 {
		font-size: 1.25rem;
		font-weight: 600;
		margin-bottom: 1rem;
	}

	.showcase-grid {
		display: grid;
		grid-template-columns: repeat(5, 1fr);
		gap: 1rem;
	}

	.showcase-card {
		display: flex;
		flex-direction: column;
		background: white;
		border-radius: 10px;
		overflow: hidden;
		box-shadow: 0 2px 8px rgba(0,0,0,0.08);
		transition: box-shadow 0.2s;
	}

	.showcase-card:hover {
		box-shadow: 0 4px 16px rgba(0,0,0,0.12);
	}

	.showcase-main {
		display: block;
		text-decoration: none;
		color: inherit;
		flex: 1;
	}

	.showcase-main:hover .showcase-image img {
		transform: scale(1.03);
	}

	.showcase-image {
		aspect-ratio: 16/10;
		overflow: hidden;
	}

	.showcase-image img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		transition: transform 0.2s;
	}

	.showcase-placeholder {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		background: linear-gradient(135deg, #1a1a2e, #16213e);
		font-size: 2rem;
	}

	.showcase-placeholder.person {
		background: linear-gradient(135deg, #667eea, #764ba2);
	}

	.showcase-info {
		padding: 0.75rem;
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
	}

	.showcase-category {
		font-size: 0.7rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: #e94560;
	}

	.showcase-title {
		font-weight: 500;
		font-size: 0.85rem;
		line-height: 1.3;
		color: #333;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.showcase-all {
		display: block;
		text-align: center;
		padding: 0.6rem;
		font-size: 0.8rem;
		color: #e94560;
		text-decoration: none;
		border-top: 1px solid #f0f0f0;
		transition: background 0.15s;
	}

	.showcase-all:hover {
		background: #fdf2f4;
	}

	/* Responsive */
	@media (max-width: 1000px) {
		.grid {
			grid-template-columns: repeat(3, 1fr);
		}

		.showcase-grid {
			grid-template-columns: repeat(3, 1fr);
		}
	}

	@media (max-width: 768px) {
		.grid {
			grid-template-columns: repeat(2, 1fr);
			gap: 1rem;
		}

		.showcase-grid {
			grid-template-columns: repeat(2, 1fr);
		}

		.quick-stats {
			flex-wrap: wrap;
			justify-content: center;
			gap: 0.75rem 1.25rem;
		}
	}

	@media (max-width: 500px) {
		.grid {
			grid-template-columns: 1fr;
		}

		.showcase-grid {
			grid-template-columns: repeat(2, 1fr);
			gap: 0.75rem;
		}

		.showcase-card {
			border-radius: 8px;
		}

		.showcase-info {
			padding: 0.5rem;
		}

		.showcase-title {
			font-size: 0.8rem;
		}

		.row-card {
			flex: 0 0 140px;
		}

		.search-container input {
			padding: 0.75rem 1rem;
			font-size: 0.95rem;
		}
	}
</style>

<script lang="ts">
	import { onMount } from 'svelte';
	import { getRandomClassicalPlays, getPlaysByPlaywright, getPerformancesByDecade, getRecentConcerts, getClassicalPlayCount, getClassicalPerformanceCount, getBergenPhilConcertCount, getPerformanceCount, type RandomPerformance } from '$lib/db';
	import type { PerformanceWithDetails, ExternalResource } from '$lib/types';

	let heroPerformance: RandomPerformance | null = null;
	let ibsenPlays: PerformanceWithDetails[] = [];
	let seventiesClassics: PerformanceWithDetails[] = [];
	let concerts: ExternalResource[] = [];
	let moreClassics: RandomPerformance[] = [];

	let stats = {
		classicalPlays: 0,
		classicalPerformances: 0,
		totalPerformances: 0,
		concerts: 0
	};

	let loading = true;

	// Known Ibsen ID (we'll find it dynamically)
	const IBSEN_ID = 1; // Typically Ibsen is ID 1

	onMount(() => {
		try {
			// Get random classical plays for hero and more section
			const randomPlays = getRandomClassicalPlays(7);
			if (randomPlays.length > 0) {
				heroPerformance = randomPlays[0];
				moreClassics = randomPlays.slice(1);
			}

			// Get Ibsen plays (playwright ID 1 is typically Ibsen)
			ibsenPlays = getPlaysByPlaywright(IBSEN_ID, 8);

			// Get classics from the 70s
			seventiesClassics = getPerformancesByDecade(1970, 1979, 8);

			// Get random concerts
			concerts = getRecentConcerts(8);

			// Get stats
			stats.classicalPlays = getClassicalPlayCount();
			stats.classicalPerformances = getClassicalPerformanceCount();
			stats.totalPerformances = getPerformanceCount();
			stats.concerts = getBergenPhilConcertCount();

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
		<!-- Hero Section -->
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
						<h1>{heroPerformance.work_title || heroPerformance.title}</h1>
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
						<a href="/performance/{heroPerformance.id}" class="hero-cta">Se opptak</a>
					</div>
				</div>
			</section>
		{/if}

		<!-- Discovery Rows -->
		{#if ibsenPlays.length > 0}
			<section class="discovery-row">
				<div class="row-header">
					<h2>Ibsen i arkivet</h2>
					<a href="/skapere" class="see-more">Se alle skapere</a>
				</div>
				<div class="row-scroll">
					{#each ibsenPlays as perf}
						<a href="/performance/{perf.id}" class="perf-card">
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

		{#if seventiesClassics.length > 0}
			<section class="discovery-row">
				<div class="row-header">
					<h2>Fra 1970-tallet</h2>
					<a href="/teater" class="see-more">Utforsk alle opptak</a>
				</div>
				<div class="row-scroll">
					{#each seventiesClassics as perf}
						<a href="/performance/{perf.id}" class="perf-card">
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
						<a href="/performance/{perf.id}" class="perf-card">
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
			<div class="stats-grid">
				<div class="stat-item">
					<span class="stat-value">{stats.classicalPlays}</span>
					<span class="stat-label">klassiske stykker</span>
				</div>
				<div class="stat-item">
					<span class="stat-value">{stats.totalPerformances}</span>
					<span class="stat-label">opptak totalt</span>
				</div>
				<div class="stat-item">
					<span class="stat-value">{stats.concerts}</span>
					<span class="stat-label">konserter</span>
				</div>
			</div>
			<div class="stats-links">
				<a href="/teater">Utforsk teater</a>
				<a href="/konserter">Konserter</a>
				<a href="/skapere">Skapere</a>
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
		gap: 3rem;
	}

	/* Hero Section */
	.hero {
		background: white;
		border-radius: 12px;
		overflow: hidden;
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
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
		font-size: 0.8rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: #e94560;
		margin-bottom: 0.5rem;
	}

	.hero-info h1 {
		font-size: 2rem;
		margin-bottom: 0.5rem;
		line-height: 1.2;
	}

	.hero-author {
		font-size: 1.1rem;
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
		gap: 1rem;
		font-size: 0.9rem;
		color: #666;
		margin-bottom: 1rem;
	}

	.hero-meta .year {
		background: #e94560;
		color: white;
		padding: 0.15rem 0.5rem;
		border-radius: 4px;
	}

	.hero-meta .medium {
		background: #1a1a2e;
		color: white;
		padding: 0.15rem 0.5rem;
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
	}

	.hero-cta {
		display: inline-block;
		background: #e94560;
		color: white;
		padding: 0.75rem 1.5rem;
		border-radius: 6px;
		text-decoration: none;
		font-weight: 500;
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
		gap: 1rem;
	}

	.row-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.row-header h2 {
		font-size: 1.25rem;
		font-weight: 600;
	}

	.see-more {
		color: #e94560;
		text-decoration: none;
		font-size: 0.9rem;
	}

	.see-more:hover {
		text-decoration: underline;
	}

	.row-scroll {
		display: flex;
		gap: 1rem;
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
		flex: 0 0 200px;
		background: white;
		border-radius: 8px;
		overflow: hidden;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
		scroll-snap-align: start;
	}

	.perf-card:hover, .concert-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
	}

	.perf-card img {
		width: 100%;
		height: 120px;
		object-fit: cover;
	}

	.card-placeholder {
		width: 100%;
		height: 120px;
		background: linear-gradient(135deg, #1a1a2e, #16213e);
		display: flex;
		align-items: center;
		justify-content: center;
		color: rgba(255, 255, 255, 0.5);
		font-size: 0.9rem;
	}

	.concert-placeholder {
		width: 100%;
		height: 120px;
		background: linear-gradient(135deg, #1a365d, #2a4365);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.concert-placeholder svg {
		width: 40px;
		height: 40px;
		color: rgba(255, 255, 255, 0.5);
	}

	.card-info {
		padding: 0.75rem;
	}

	.card-info h3 {
		font-size: 0.9rem;
		font-weight: 500;
		margin-bottom: 0.25rem;
		line-height: 1.3;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.card-info .year {
		font-size: 0.8rem;
		color: #e94560;
	}

	.card-info .author {
		font-size: 0.8rem;
		color: #666;
	}

	.card-info .external {
		font-size: 0.75rem;
		color: #888;
	}

	/* Stats Section */
	.stats-section {
		background: white;
		border-radius: 12px;
		padding: 2rem;
		text-align: center;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.stats-grid {
		display: flex;
		justify-content: center;
		gap: 3rem;
		margin-bottom: 1.5rem;
	}

	.stat-item {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.stat-value {
		font-size: 2rem;
		font-weight: bold;
		color: #1a1a2e;
	}

	.stat-label {
		font-size: 0.85rem;
		color: #666;
	}

	.stats-links {
		display: flex;
		justify-content: center;
		gap: 1.5rem;
	}

	.stats-links a {
		color: #e94560;
		text-decoration: none;
		font-weight: 500;
	}

	.stats-links a:hover {
		text-decoration: underline;
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

		.hero-info h1 {
			font-size: 1.5rem;
		}

		.stats-grid {
			flex-direction: column;
			gap: 1.5rem;
		}

		.stats-links {
			flex-wrap: wrap;
			gap: 1rem;
		}
	}

	@media (max-width: 600px) {
		.landing-page {
			gap: 2rem;
		}

		.perf-card, .concert-card {
			flex: 0 0 160px;
		}

		.perf-card img, .card-placeholder, .concert-placeholder {
			height: 100px;
		}
	}
</style>

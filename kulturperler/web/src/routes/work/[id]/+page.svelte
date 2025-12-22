<script lang="ts">
	import { page } from '$app/stores';
	import { getWork, getWorkPerformancesByMedium, getPerformanceMedia, getWorkExternalLinks, getPerson, getPlaysByPlaywright } from '$lib/db';
	import type { Work, WorkExternalLink, PerformanceWithDetails, Episode, Person } from '$lib/types';
	import { onMount } from 'svelte';

	interface PerformanceWithMedia extends PerformanceWithDetails {
		media: Episode[];
	}

	let work: (Work & { playwright_name?: string }) | null = null;
	let playwright: Person | null = null;
	let composer: Person | null = null;
	let tvPerformances: PerformanceWithMedia[] = [];
	let radioPerformances: PerformanceWithMedia[] = [];
	let externalLinks: WorkExternalLink[] = [];
	let moreByAuthor: PerformanceWithDetails[] = [];
	let loading = true;
	let error: string | null = null;

	$: workId = parseInt($page.params.id || '0');

	onMount(() => {
		loadWork();
	});

	function loadWork() {
		try {
			work = getWork(workId);
			if (work) {
				// Get playwright details
				if (work.playwright_id) {
					playwright = getPerson(work.playwright_id);
					// Get more works by this playwright (excluding current)
					const authorWorks = getPlaysByPlaywright(work.playwright_id, 10);
					moreByAuthor = authorWorks.filter(w => w.work_id !== workId);
				}

				// Get composer details
				if (work.composer_id) {
					composer = getPerson(work.composer_id);
				}

				// Get TV performances
				const tvPerfs = getWorkPerformancesByMedium(workId, 'tv');
				tvPerformances = tvPerfs.map(perf => ({
					...perf,
					media: getPerformanceMedia(perf.id).filter(m => !m.is_introduction)
				}));

				// Get Radio performances
				const radioPerfs = getWorkPerformancesByMedium(workId, 'radio');
				radioPerformances = radioPerfs.map(perf => ({
					...perf,
					media: getPerformanceMedia(perf.id).filter(m => !m.is_introduction)
				}));

				// Load external links
				externalLinks = getWorkExternalLinks(workId);
			} else {
				error = 'Verk ikke funnet';
			}
			loading = false;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Ukjent feil';
			loading = false;
		}
	}

	function formatDuration(seconds: number | null): string {
		if (!seconds) return '';
		const h = Math.floor(seconds / 3600);
		const m = Math.floor((seconds % 3600) / 60);
		if (h > 0) return `${h}t ${m}m`;
		return `${m} min`;
	}

	function getImageUrl(url: string | null, width = 400): string {
		if (!url) return '';
		if (url.includes('gfx.nrk.no')) {
			return url.replace(/\/\d+$/, `/${width}`);
		}
		return url;
	}

	function getWorkTypeLabel(type: string | null): string {
		const labels: Record<string, string> = {
			teaterstykke: 'Klassisk dramatikk',
			nrk_teaterstykke: 'NRK-produksjon',
			dramaserie: 'Dramaserie',
			opera: 'Opera',
			konsert: 'Konsert'
		};
		return labels[type || ''] || type || '';
	}

	$: totalPerformances = tvPerformances.length + radioPerformances.length;
</script>

<svelte:head>
	{#if work}
		<title>{work.title} - Kulturbase.no</title>
		<meta name="description" content="{work.synopsis?.slice(0, 160) || `${work.title} av ${work.playwright_name || 'ukjent'}`}" />
	{/if}
</svelte:head>

{#if loading}
	<div class="loading">Laster...</div>
{:else if error}
	<div class="error">{error}</div>
{:else if work}
	<article class="work-detail">
		<a href="/teater" class="back-link">&larr; Tilbake til teater</a>

		<header class="work-header">
			<div class="header-content">
				<div class="header-text">
					<h1>{work.title}</h1>

					<p class="work-meta">
						{#if playwright}
							<a href="/person/{playwright.id}" class="author-link">{playwright.name}</a>
							{#if playwright.birth_year || playwright.death_year}
								<span class="author-dates">({playwright.birth_year || '?'}–{playwright.death_year || ''})</span>
							{/if}
						{/if}
						{#if work.year_written}
							<span class="separator">·</span>
							<span class="year-written">skrevet {work.year_written}</span>
						{/if}
					</p>

					{#if work.original_title && work.original_title !== work.title}
						<p class="original-title">Originaltittel: {work.original_title}</p>
					{/if}

					{#if work.work_type}
						<span class="work-type-badge">{getWorkTypeLabel(work.work_type)}</span>
					{/if}

					{#if work.synopsis}
						<p class="work-synopsis">{work.synopsis}</p>
					{/if}
				</div>
			</div>
		</header>

		<!-- Stats -->
		<section class="work-stats">
			<div class="stats-grid">
				<div class="stat-item">
					<span class="stat-value">{totalPerformances}</span>
					<span class="stat-label">opptak</span>
				</div>
				{#if tvPerformances.length > 0}
					<div class="stat-item">
						<span class="stat-value">{tvPerformances.length}</span>
						<span class="stat-label">TV</span>
					</div>
				{/if}
				{#if radioPerformances.length > 0}
					<div class="stat-item">
						<span class="stat-value">{radioPerformances.length}</span>
						<span class="stat-label">Radio</span>
					</div>
				{/if}
			</div>
		</section>

		{#if externalLinks.length > 0}
			<section class="external-sources">
				<h2>Les og se mer</h2>
				<div class="sources-grid">
					{#each externalLinks.filter(l => l.type === 'bokselskap') as link}
						<a href={link.url} target="_blank" rel="noopener" class="source-card bokselskap">
							<div class="source-info">
								<span class="source-title">Les hele teksten</span>
								<span class="source-subtitle">{link.title}</span>
							</div>
							<span class="arrow">→</span>
						</a>
					{/each}
					{#each externalLinks.filter(l => l.type === 'streaming') as link}
						<a href={link.url} target="_blank" rel="noopener" class="source-card streaming">
							<div class="source-info">
								<span class="source-title">{link.title}</span>
								{#if link.description}
									<span class="source-note">{link.description}</span>
								{/if}
								{#if link.access_note}
									<span class="source-note">{link.access_note}</span>
								{/if}
							</div>
							<span class="arrow">→</span>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		{#if tvPerformances.length > 0}
			<section class="performances tv-section">
				<h2>
					<span class="medium-icon tv">TV</span>
					Fjernsynsteater
					{#if tvPerformances.length > 1}<span class="count">({tvPerformances.length})</span>{/if}
				</h2>

				<div class="performances-grid">
					{#each tvPerformances as perf}
						<a href="/performance/{perf.id}" class="performance-card">
							<div class="perf-image">
								{#if perf.image_url}
									<img src={getImageUrl(perf.image_url)} alt={perf.title || work?.title || ''} loading="lazy" />
								{:else}
									<div class="perf-placeholder">TV Teater</div>
								{/if}
								{#if perf.total_duration}
									<span class="duration-badge">{formatDuration(perf.total_duration)}</span>
								{/if}
								{#if perf.media.length > 1}
									<span class="parts-badge">{perf.media.length} deler</span>
								{/if}
							</div>
							<div class="perf-info">
								{#if perf.year}
									<span class="perf-year">{perf.year}</span>
								{/if}
								{#if perf.director_name}
									<p class="perf-director">Regi: {perf.director_name}</p>
								{/if}
								{#if perf.description}
									<p class="perf-desc">{perf.description.slice(0, 150)}{perf.description.length > 150 ? '...' : ''}</p>
								{/if}
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		{#if radioPerformances.length > 0}
			<section class="performances radio-section">
				<h2>
					<span class="medium-icon radio">R</span>
					Radioteater
					{#if radioPerformances.length > 1}<span class="count">({radioPerformances.length})</span>{/if}
				</h2>

				<div class="performances-grid">
					{#each radioPerformances as perf}
						<a href="/performance/{perf.id}" class="performance-card">
							<div class="perf-image radio-image">
								{#if perf.image_url}
									<img src={getImageUrl(perf.image_url)} alt={perf.title || work?.title || ''} loading="lazy" />
								{:else}
									<div class="perf-placeholder radio">Radioteater</div>
								{/if}
								{#if perf.total_duration}
									<span class="duration-badge">{formatDuration(perf.total_duration)}</span>
								{/if}
								{#if perf.media.length > 1}
									<span class="parts-badge">{perf.media.length} deler</span>
								{/if}
							</div>
							<div class="perf-info">
								{#if perf.year}
									<span class="perf-year radio">{perf.year}</span>
								{/if}
								{#if perf.director_name}
									<p class="perf-director">Regi: {perf.director_name}</p>
								{/if}
								{#if perf.description}
									<p class="perf-desc">{perf.description.slice(0, 150)}{perf.description.length > 150 ? '...' : ''}</p>
								{/if}
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		{#if moreByAuthor.length > 0 && playwright}
			<section class="more-by-author">
				<div class="section-header">
					<h2>Mer av {playwright.name}</h2>
					<a href="/person/{playwright.id}" class="see-all">Se alle verk →</a>
				</div>
				<div class="author-works-scroll">
					{#each moreByAuthor as perf}
						<a href="/performance/{perf.id}" class="author-work-card">
							{#if perf.image_url}
								<img src={getImageUrl(perf.image_url, 240)} alt={perf.work_title || ''} loading="lazy" />
							{:else}
								<div class="author-work-placeholder">Teater</div>
							{/if}
							<div class="author-work-info">
								<h3>{perf.work_title || perf.title}</h3>
								{#if perf.year}
									<span class="author-work-year">{perf.year}</span>
								{/if}
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		{#if work.sceneweb_url || work.wikipedia_url}
			<footer class="work-footer">
				<span class="footer-label">Lenker:</span>
				{#if work.sceneweb_url}
					<a href={work.sceneweb_url} target="_blank" rel="noopener" class="footer-link">Sceneweb</a>
				{/if}
				{#if work.wikipedia_url}
					<a href={work.wikipedia_url} target="_blank" rel="noopener" class="footer-link">Wikipedia</a>
				{/if}
			</footer>
		{/if}
	</article>
{/if}

<style>
	.loading, .error {
		text-align: center;
		padding: 4rem;
	}

	.error {
		color: #e94560;
	}

	.back-link {
		display: inline-block;
		margin-bottom: 1rem;
		color: #666;
		text-decoration: none;
		font-size: 0.9rem;
	}

	.back-link:hover {
		color: #e94560;
	}

	.work-detail {
		background: white;
		border-radius: 8px;
		padding: 2rem;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.work-header {
		margin-bottom: 1.5rem;
		padding-bottom: 1.5rem;
		border-bottom: 1px solid #eee;
	}

	.header-content {
		display: flex;
		gap: 1.25rem;
		align-items: flex-start;
	}

	.header-text {
		flex: 1;
		min-width: 0;
	}

	.work-header h1 {
		font-size: 1.75rem;
		margin: 0 0 0.5rem 0;
		line-height: 1.2;
	}

	.work-meta {
		margin: 0 0 0.5rem 0;
		font-size: 0.95rem;
		color: #555;
	}

	.author-link {
		color: #e94560;
		text-decoration: none;
		font-weight: 500;
	}

	.author-link:hover {
		text-decoration: underline;
	}

	.author-dates {
		color: #888;
		font-size: 0.85rem;
	}

	.separator {
		margin: 0 0.4rem;
		color: #ccc;
	}

	.year-written {
		color: #666;
	}

	.original-title {
		font-style: italic;
		color: #888;
		font-size: 0.85rem;
		margin: 0 0 0.5rem 0;
	}

	.work-type-badge {
		display: inline-block;
		background: #f0f0f0;
		color: #666;
		padding: 0.25rem 0.75rem;
		border-radius: 4px;
		font-size: 0.8rem;
		margin-bottom: 0.75rem;
	}

	.work-synopsis {
		margin: 0;
		font-size: 0.95rem;
		color: #555;
		line-height: 1.6;
	}

	/* Stats */
	.work-stats {
		background: #f8f9fa;
		border-radius: 8px;
		padding: 1rem 1.5rem;
		margin-bottom: 1.5rem;
	}

	.stats-grid {
		display: flex;
		justify-content: center;
		gap: 2.5rem;
	}

	.stat-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.15rem;
	}

	.stat-value {
		font-size: 1.5rem;
		font-weight: bold;
		color: #1a1a2e;
	}

	.stat-label {
		font-size: 0.8rem;
		color: #666;
		text-transform: uppercase;
	}

	/* External sources */
	.external-sources {
		margin-bottom: 2rem;
	}

	.external-sources h2 {
		font-size: 1.1rem;
		margin-bottom: 1rem;
	}

	.sources-grid {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
	}

	.source-card {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		border-radius: 8px;
		text-decoration: none;
		transition: transform 0.15s, box-shadow 0.15s;
		min-width: 200px;
	}

	.source-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
	}

	.source-card.bokselskap {
		background: linear-gradient(135deg, #2d5016, #4a7c2d);
		color: white;
	}

	.source-card.streaming {
		background: linear-gradient(135deg, #667eea, #764ba2);
		color: white;
	}

	.source-info {
		display: flex;
		flex-direction: column;
		flex: 1;
	}

	.source-title {
		font-weight: 600;
		font-size: 0.95rem;
	}

	.source-subtitle, .source-note {
		font-size: 0.8rem;
		opacity: 0.9;
	}

	.source-card .arrow {
		font-size: 1.1rem;
		opacity: 0.8;
	}

	/* Performances */
	.performances {
		margin-bottom: 2rem;
	}

	.performances h2 {
		font-size: 1.25rem;
		margin-bottom: 1rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.performances h2 .count {
		font-weight: 400;
		color: #888;
		font-size: 0.9em;
	}

	.medium-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 20px;
		border-radius: 3px;
		font-size: 0.7rem;
		font-weight: 600;
		color: white;
	}

	.medium-icon.tv {
		background: #e94560;
	}

	.medium-icon.radio {
		background: #6b5ce7;
	}

	.performances-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: 1.5rem;
	}

	.performance-card {
		background: #f9f9f9;
		border-radius: 8px;
		overflow: hidden;
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.performance-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
	}

	.perf-image {
		position: relative;
		aspect-ratio: 16/9;
		background: #eee;
	}

	.perf-image img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.perf-placeholder {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		background: linear-gradient(135deg, #1a1a2e, #16213e);
		color: rgba(255, 255, 255, 0.5);
		font-size: 0.9rem;
	}

	.perf-placeholder.radio {
		background: linear-gradient(135deg, #5b4cdb, #6b5ce7);
	}

	.duration-badge {
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
		padding: 0.2rem 0.5rem;
		border-radius: 4px;
		font-size: 0.75rem;
	}

	.perf-info {
		padding: 1rem;
	}

	.perf-year {
		display: inline-block;
		background: #e94560;
		color: white;
		padding: 0.15rem 0.5rem;
		border-radius: 4px;
		font-size: 0.85rem;
		font-weight: 600;
		margin-bottom: 0.5rem;
	}

	.perf-year.radio {
		background: #6b5ce7;
	}

	.perf-director {
		font-size: 0.9rem;
		color: #666;
		margin: 0 0 0.5rem 0;
	}

	.perf-desc {
		font-size: 0.85rem;
		color: #555;
		margin: 0;
		line-height: 1.5;
	}

	.tv-section {
		margin-bottom: 2rem;
	}

	.radio-section {
		border-top: 1px solid #eee;
		padding-top: 1.5rem;
	}

	/* More by author */
	.more-by-author {
		margin-top: 2rem;
		padding-top: 1.5rem;
		border-top: 1px solid #eee;
	}

	.section-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.section-header h2 {
		font-size: 1.25rem;
		margin: 0;
	}

	.see-all {
		color: #e94560;
		text-decoration: none;
		font-size: 0.9rem;
	}

	.see-all:hover {
		text-decoration: underline;
	}

	.author-works-scroll {
		display: flex;
		gap: 1rem;
		overflow-x: auto;
		padding-bottom: 0.5rem;
		-webkit-overflow-scrolling: touch;
	}

	.author-works-scroll::-webkit-scrollbar {
		height: 6px;
	}

	.author-works-scroll::-webkit-scrollbar-track {
		background: #f0f0f0;
		border-radius: 3px;
	}

	.author-works-scroll::-webkit-scrollbar-thumb {
		background: #ccc;
		border-radius: 3px;
	}

	.author-work-card {
		flex: 0 0 180px;
		background: #f9f9f9;
		border-radius: 8px;
		overflow: hidden;
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.author-work-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
	}

	.author-work-card img {
		width: 100%;
		height: 100px;
		object-fit: cover;
	}

	.author-work-placeholder {
		width: 100%;
		height: 100px;
		background: linear-gradient(135deg, #1a1a2e, #16213e);
		display: flex;
		align-items: center;
		justify-content: center;
		color: rgba(255, 255, 255, 0.5);
		font-size: 0.85rem;
	}

	.author-work-info {
		padding: 0.75rem;
	}

	.author-work-info h3 {
		font-size: 0.9rem;
		margin: 0 0 0.25rem 0;
		line-height: 1.3;
	}

	.author-work-year {
		font-size: 0.8rem;
		color: #e94560;
	}

	/* Footer */
	.work-footer {
		margin-top: 2rem;
		padding-top: 1rem;
		border-top: 1px solid #eee;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.75rem;
	}

	.footer-label {
		color: #888;
		font-size: 0.85rem;
	}

	.footer-link {
		padding: 0.35rem 0.75rem;
		background: #f0f0f0;
		border-radius: 4px;
		text-decoration: none;
		color: #555;
		font-size: 0.85rem;
		transition: background-color 0.15s;
	}

	.footer-link:hover {
		background: #e0e0e0;
	}

	@media (max-width: 600px) {
		.performances-grid {
			grid-template-columns: 1fr;
		}

		.stats-grid {
			gap: 1.5rem;
		}

		.sources-grid {
			flex-direction: column;
		}

		.source-card {
			width: 100%;
		}
	}
</style>

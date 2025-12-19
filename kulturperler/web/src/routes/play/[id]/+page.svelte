<script lang="ts">
	import { page } from '$app/stores';
	import { getPlay, getWorkPerformancesByMedium, getPerformanceMedia, getPlayExternalLinks, getPerson } from '$lib/db';
	import type { Play, PlayExternalLink, PerformanceWithDetails, Episode, Person } from '$lib/types';
	import { onMount } from 'svelte';

	interface PerformanceWithMedia extends PerformanceWithDetails {
		media: Episode[];
	}

	let play: (Play & { playwright_name?: string }) | null = null;
	let playwright: Person | null = null;
	let tvPerformances: PerformanceWithMedia[] = [];
	let radioPerformances: PerformanceWithMedia[] = [];
	let externalLinks: PlayExternalLink[] = [];
	let loading = true;
	let error: string | null = null;

	$: playId = parseInt($page.params.id || '0');

	onMount(() => {
		loadPlay();
	});

	function loadPlay() {
		try {
			play = getPlay(playId);
			if (play) {
				// Get playwright details
				if (play.playwright_id) {
					playwright = getPerson(play.playwright_id);
				}

				// Get TV performances
				const tvPerfs = getWorkPerformancesByMedium(playId, 'tv');
				tvPerformances = tvPerfs.map(perf => ({
					...perf,
					media: getPerformanceMedia(perf.id).filter(m => !m.is_introduction)
				}));

				// Get Radio performances
				const radioPerfs = getWorkPerformancesByMedium(playId, 'radio');
				radioPerformances = radioPerfs.map(perf => ({
					...perf,
					media: getPerformanceMedia(perf.id).filter(m => !m.is_introduction)
				}));

				// Load external links
				externalLinks = getPlayExternalLinks(playId);
			} else {
				error = 'Stykke ikke funnet';
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

	function getImageUrl(url: string | null): string {
		if (!url) return '/placeholder.jpg';
		return url;
	}
</script>

<svelte:head>
	{#if play}
		<title>{play.title} - Kulturperler</title>
	{/if}
</svelte:head>

{#if loading}
	<div class="loading">Laster...</div>
{:else if error}
	<div class="error">{error}</div>
{:else if play}
	<article class="play-detail">
		<a href="/" class="back-link">&larr; Tilbake til oversikt</a>

		<header class="play-header">
			<div class="header-content">
				<div class="header-text">
					<h1>{play.title}</h1>
					<p class="play-meta">
						{#if playwright}
							<a href="/person/{playwright.id}" class="author-link">{playwright.name}</a>
							{#if playwright.birth_year || playwright.death_year}
								<span class="author-dates">({playwright.birth_year || '?'}–{playwright.death_year || ''})</span>
							{/if}
						{/if}
						{#if play.year_written}
							<span class="separator">·</span>
							<span class="year-written">skrevet {play.year_written}</span>
						{/if}
					</p>
					{#if play.original_title && play.original_title !== play.title}
						<p class="original-title">Originaltittel: {play.original_title}</p>
					{/if}
					{#if play.synopsis}
						<p class="play-synopsis">{play.synopsis}</p>
					{/if}
				</div>
			</div>
		</header>

		{#if externalLinks.length > 0}
			<section class="external-sources">
				{#each externalLinks.filter(l => l.type === 'bokselskap') as link}
					<a href={link.url} target="_blank" rel="noopener" class="source-card bokselskap">
						<span class="source-icon">📖</span>
						<div class="source-info">
							<span class="source-title">Les hele teksten</span>
							<span class="source-subtitle">{link.title}</span>
						</div>
						<span class="arrow">→</span>
					</a>
				{/each}
				{#each externalLinks.filter(l => l.type === 'streaming') as link}
					<a href={link.url} target="_blank" rel="noopener" class="source-card streaming">
						<span class="source-icon">▶</span>
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
			</section>
		{/if}

		{#if tvPerformances.length > 0}
			<section class="performances tv-section">
				<h2>
					<span class="medium-icon tv">TV</span>
					Fjernsynsteater
					{#if tvPerformances.length > 1}<span class="count">({tvPerformances.length})</span>{/if}
				</h2>

				{#if tvPerformances.length === 1}
					{@const perf = tvPerformances[0]}
					<a href="/performance/{perf.id}" class="single-perf-card">
						<div class="single-perf-image">
							<img src={getImageUrl(perf.image_url)} alt={perf.title || play?.title || ''} />
							<div class="play-overlay">
								<span class="play-icon">▶</span>
							</div>
						</div>
						<div class="single-perf-info">
							<div class="single-perf-meta">
								{#if perf.year}
									<span class="perf-year">{perf.year}</span>
								{/if}
								{#if perf.total_duration}
									<span class="perf-duration">{formatDuration(perf.total_duration)}</span>
								{/if}
								{#if perf.media.length > 1}
									<span class="perf-parts">{perf.media.length} deler</span>
								{/if}
							</div>
							{#if perf.director_name}
								<p class="single-perf-director">Regi: {perf.director_name}</p>
							{/if}
							{#if perf.description}
								<p class="single-perf-desc">{perf.description.slice(0, 200)}{perf.description.length > 200 ? '...' : ''}</p>
							{/if}
						</div>
					</a>
				{:else}
					<div class="performances-grid">
					{#each tvPerformances as perf}
						<a href="/performance/{perf.id}" class="performance-card-link">
							<div class="performance-group">
								<div class="perf-header">
									{#if perf.year}
										<span class="perf-year">{perf.year}</span>
									{/if}
									{#if perf.director_name}
										<span class="perf-director">Regi: {perf.director_name}</span>
									{/if}
									{#if perf.total_duration}
										<span class="perf-duration">{formatDuration(perf.total_duration)}</span>
									{/if}
									{#if perf.media.length > 1}
										<span class="perf-parts">{perf.media.length} deler</span>
									{/if}
								</div>

								<div class="perf-content">
									{#if perf.image_url}
										<div class="perf-thumb">
											<img src={getImageUrl(perf.image_url)} alt={perf.title || play?.title || ''} loading="lazy" />
										</div>
									{/if}

									{#if perf.description}
										<p class="perf-description">{perf.description}</p>
									{/if}
								</div>
							</div>
						</a>
					{/each}
					</div>
				{/if}
			</section>
		{/if}

		{#if radioPerformances.length > 0}
			<section class="performances radio-section">
				<h2>
					<span class="medium-icon radio">R</span>
					Radioteater
					{#if radioPerformances.length > 1}<span class="count">({radioPerformances.length})</span>{/if}
				</h2>

				{#if radioPerformances.length === 1}
					{@const perf = radioPerformances[0]}
					<a href="/performance/{perf.id}" class="single-perf-card">
						<div class="single-perf-image">
							<img src={getImageUrl(perf.image_url)} alt={perf.title || play?.title || ''} />
							<div class="play-overlay">
								<span class="play-icon">▶</span>
							</div>
						</div>
						<div class="single-perf-info">
							<div class="single-perf-meta">
								{#if perf.year}
									<span class="perf-year">{perf.year}</span>
								{/if}
								{#if perf.total_duration}
									<span class="perf-duration">{formatDuration(perf.total_duration)}</span>
								{/if}
								{#if perf.media.length > 1}
									<span class="perf-parts">{perf.media.length} deler</span>
								{/if}
							</div>
							{#if perf.director_name}
								<p class="single-perf-director">Regi: {perf.director_name}</p>
							{/if}
							{#if perf.description}
								<p class="single-perf-desc">{perf.description.slice(0, 200)}{perf.description.length > 200 ? '...' : ''}</p>
							{/if}
						</div>
					</a>
				{:else}
					<div class="performances-grid">
					{#each radioPerformances as perf}
						<a href="/performance/{perf.id}" class="performance-card-link">
							<div class="performance-group">
								<div class="perf-header">
									{#if perf.year}
										<span class="perf-year">{perf.year}</span>
									{/if}
									{#if perf.director_name}
										<span class="perf-director">Regi: {perf.director_name}</span>
									{/if}
									{#if perf.total_duration}
										<span class="perf-duration">{formatDuration(perf.total_duration)}</span>
									{/if}
									{#if perf.media.length > 1}
										<span class="perf-parts">{perf.media.length} deler</span>
									{/if}
								</div>

								<div class="perf-content">
									{#if perf.image_url}
										<div class="perf-thumb">
											<img src={getImageUrl(perf.image_url)} alt={perf.title || play?.title || ''} loading="lazy" />
										</div>
									{/if}

									{#if perf.description}
										<p class="perf-description">{perf.description}</p>
									{/if}
								</div>
							</div>
						</a>
					{/each}
					</div>
				{/if}
			</section>
		{/if}

		{#if play.sceneweb_url}
			<footer class="play-footer">
				<span class="footer-label">Lenker:</span>
				<a href={play.sceneweb_url} target="_blank" rel="noopener" class="footer-link">Sceneweb</a>
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

	.play-detail {
		background: white;
		border-radius: 8px;
		padding: 2rem;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.play-header {
		margin-bottom: 1.5rem;
		padding-bottom: 1.5rem;
		border-bottom: 1px solid #eee;
	}

	.header-content {
		display: flex;
		gap: 1.25rem;
		align-items: flex-start;
	}

	.author-portrait {
		flex-shrink: 0;
		width: 80px;
		height: 80px;
		border-radius: 50%;
		overflow: hidden;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
	}

	.author-portrait img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.header-text {
		flex: 1;
		min-width: 0;
	}

	.play-header h1 {
		font-size: 1.75rem;
		margin: 0 0 0.3rem 0;
		line-height: 1.2;
	}

	.play-meta {
		margin: 0;
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
		margin: 0.3rem 0 0 0;
	}

	.play-synopsis {
		margin: 0.6rem 0 0 0;
		font-size: 0.9rem;
		color: #555;
		line-height: 1.5;
	}

	/* External sources */
	.external-sources {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		margin-bottom: 1.5rem;
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
		background: linear-gradient(135deg, #2d5016 0%, #4a7c2d 100%);
		color: white;
	}

	.source-card.streaming {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
	}

	.source-icon {
		font-size: 1.25rem;
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

	.source-subtitle {
		font-size: 0.8rem;
		opacity: 0.9;
	}

	.source-note {
		font-size: 0.75rem;
		opacity: 0.85;
	}

	.source-card .arrow {
		font-size: 1.1rem;
		opacity: 0.8;
	}

	/* Footer links */
	.play-footer {
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

	/* Single performance layout */
	.single-performance h2 {
		font-size: 1.1rem;
		color: #666;
		margin-bottom: 1rem;
	}

	.single-perf-card {
		display: grid;
		grid-template-columns: 280px 1fr;
		gap: 1.25rem;
		text-decoration: none;
		color: inherit;
		background: #f9f9f9;
		border-radius: 8px;
		overflow: hidden;
		padding: 1rem;
		transition: box-shadow 0.2s;
	}

	.single-perf-card:hover {
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
	}

	.single-perf-image {
		position: relative;
		aspect-ratio: 16/9;
		background: #ddd;
		border-radius: 6px;
		overflow: hidden;
	}

	.single-perf-image img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.play-overlay {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(0, 0, 0, 0.3);
		opacity: 0;
		transition: opacity 0.2s;
	}

	.single-perf-card:hover .play-overlay {
		opacity: 1;
	}

	.play-icon {
		width: 64px;
		height: 64px;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.95);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.5rem;
		color: #e94560;
		padding-left: 4px;
	}

	.single-perf-info {
		display: flex;
		flex-direction: column;
		justify-content: center;
	}

	.single-perf-meta {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 0.5rem;
	}

	.single-perf-director {
		font-size: 0.9rem;
		color: #666;
		margin: 0 0 0.5rem 0;
	}

	.single-perf-desc {
		font-size: 0.9rem;
		color: #555;
		margin: 0;
		line-height: 1.5;
	}

	.performances h2 {
		font-size: 1.3rem;
		margin-bottom: 1.5rem;
	}

	.performances-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 1rem;
	}

	.performance-card-link {
		display: block;
		text-decoration: none;
		color: inherit;
	}

	.performance-group {
		background: #f9f9f9;
		border-radius: 8px;
		padding: 1.25rem;
		transition: background-color 0.2s, box-shadow 0.2s;
	}

	.performance-card-link:hover .performance-group {
		background: #f0f0f0;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.perf-header {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		align-items: center;
		margin-bottom: 1rem;
	}

	.perf-year {
		font-size: 1.25rem;
		font-weight: 600;
		color: #e94560;
	}

	.perf-director {
		color: #555;
		font-size: 0.95rem;
	}

	.perf-duration {
		color: #666;
		font-size: 0.9rem;
	}

	.perf-parts {
		background: #1a1a2e;
		color: white;
		padding: 0.2rem 0.6rem;
		border-radius: 4px;
		font-size: 0.8rem;
		font-weight: 500;
	}

	.perf-content {
		display: flex;
		gap: 1.25rem;
	}

	.perf-thumb {
		width: 200px;
		flex-shrink: 0;
		border-radius: 6px;
		overflow: hidden;
	}

	.perf-thumb img {
		width: 100%;
		aspect-ratio: 16/9;
		object-fit: cover;
	}

	.perf-parts-preview {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.5rem;
		flex: 1;
	}

	.mini-thumb {
		position: relative;
		border-radius: 4px;
		overflow: hidden;
	}

	.mini-thumb img {
		width: 100%;
		aspect-ratio: 16/9;
		object-fit: cover;
	}

	.mini-badge {
		position: absolute;
		bottom: 0.25rem;
		left: 0.25rem;
		background: rgba(0, 0, 0, 0.75);
		color: white;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
		font-size: 0.7rem;
	}

	.more-parts {
		display: flex;
		align-items: center;
		justify-content: center;
		background: #ddd;
		border-radius: 4px;
		font-weight: 600;
		color: #666;
	}

	.perf-description {
		flex: 1;
		font-size: 0.95rem;
		color: #555;
		line-height: 1.5;
		margin: 0;
	}

	/* Medium section styles */
	.performances h2 {
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

	.tv-section {
		margin-bottom: 2rem;
	}

	.radio-section {
		border-top: 1px solid #eee;
		padding-top: 1.5rem;
	}

</style>

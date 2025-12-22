<script lang="ts">
	import { page } from '$app/stores';
	import { getPerformance, getPerformanceContributors, getPerformanceMedia, getOtherPerformances, getPlay } from '$lib/db';
	import type { PerformanceWithDetails, PerformancePerson, Episode, Play } from '$lib/types';

	let performance: PerformanceWithDetails | null = null;
	let work: (Play & { playwright_name?: string }) | null = null;
	let contributors: (PerformancePerson & { person_name: string })[] = [];
	let media: Episode[] = [];
	let otherPerformances: PerformanceWithDetails[] = [];
	let loading = true;
	let error: string | null = null;

	$: performanceId = parseInt($page.params.id || '0');

	$: if (performanceId) {
		loadPerformance();
	}

	function loadPerformance() {
		loading = true;
		error = null;
		work = null;
		otherPerformances = [];

		try {
			performance = getPerformance(performanceId);
			if (performance) {
				contributors = getPerformanceContributors(performanceId);
				media = getPerformanceMedia(performanceId);

				if (performance.work_id) {
					work = getPlay(performance.work_id);
					otherPerformances = getOtherPerformances(performance.work_id, performanceId);
				}
			} else {
				error = 'Opptak ikke funnet';
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

	function formatDurationLong(seconds: number | null): string {
		if (!seconds) return '';
		const h = Math.floor(seconds / 3600);
		const m = Math.floor((seconds % 3600) / 60);
		if (h > 0) return `${h} time${h > 1 ? 'r' : ''} ${m} min`;
		return `${m} minutter`;
	}

	function hasImage(url: string | null | undefined): boolean {
		return !!url && url.length > 0;
	}

	function getRoleLabel(role: string | null): string {
		const labels: Record<string, string> = {
			director: 'Regi',
			actor: 'Skuespillere',
			playwright: 'Manus',
			composer: 'Komponist',
			set_designer: 'Scenografi',
			costume_designer: 'Kostymer',
			producer: 'Produsent',
			other: 'Annet'
		};
		return labels[role || ''] || role || 'Ukjent rolle';
	}

	function groupContributors(contribs: typeof contributors) {
		const groups: Record<string, typeof contributors> = {};
		for (const c of contribs) {
			const role = c.role || 'other';
			if (!groups[role]) groups[role] = [];
			groups[role].push(c);
		}
		return groups;
	}

	function getDirectorName(): string | null {
		const director = contributors.find(c => c.role === 'director');
		return director?.person_name || null;
	}

	$: contributorGroups = groupContributors(contributors);
	$: directorName = getDirectorName();
</script>

<svelte:head>
	{#if performance}
		<title>{performance.title || work?.title || 'Opptak'} ({performance.year}) - Kulturperler</title>
	{/if}
</svelte:head>

{#if loading}
	<div class="loading">Laster...</div>
{:else if error}
	<div class="error">{error}</div>
{:else if performance}
	<article class="performance-detail">
		<a href="/" class="back-link">&larr; Tilbake til oversikt</a>

		<div class="performance-header">
			{#if media.length === 1}
				<a
					href={media[0].nrk_url || `https://tv.nrk.no/se?v=${media[0].prf_id}`}
					target="_blank"
					rel="noopener"
					class="performance-image playable"
				>
					{#if hasImage(performance.image_url)}
						<img src={performance.image_url} alt={performance.title || ''} />
					{:else}
						<div class="image-placeholder">
							<svg viewBox="0 0 24 24" fill="currentColor" class="placeholder-icon">
								<path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z"/>
							</svg>
						</div>
					{/if}
					<div class="header-play-icon">
						<svg viewBox="0 0 24 24" fill="currentColor">
							<path d="M8 5v14l11-7z"/>
						</svg>
					</div>
					{#if media[0].duration_seconds}
						<span class="header-duration">{formatDuration(media[0].duration_seconds)}</span>
					{/if}
				</a>
			{:else}
				<div class="performance-image">
					{#if hasImage(performance.image_url)}
						<img src={performance.image_url} alt={performance.title || ''} />
					{:else}
						<div class="image-placeholder">
							<svg viewBox="0 0 24 24" fill="currentColor" class="placeholder-icon">
								<path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z"/>
							</svg>
						</div>
					{/if}
				</div>
			{/if}

			<div class="performance-info">
				<h1>
					{performance.title || work?.title || 'Ukjent tittel'}
					{#if performance.medium === 'radio'}
						<span class="medium-badge radio">Radioteater</span>
					{:else}
						<span class="medium-badge tv">Fjernsynsteater</span>
					{/if}
				</h1>

				<div class="meta-line">
					{#if performance.year}
						<span class="year">{performance.year}</span>
					{/if}
					{#if performance.total_duration}
						<span class="duration">{formatDurationLong(performance.total_duration)}</span>
					{/if}
					{#if directorName}
						<span class="director">Regi: {directorName}</span>
					{/if}
				</div>

				{#if work}
					<div class="work-preview">
						<div class="work-preview-header">
							<span class="label">Fra stykket ({otherPerformances.length + 1} opptak)</span>
							<a href="/work/{work.id}" class="work-link">Se mer &rarr;</a>
						</div>
						<h2>
							<a href="/work/{work.id}">{work.title}</a>
							{#if work.year_written}
								<span class="year-written">({work.year_written})</span>
							{/if}
						</h2>
						{#if performance.playwright_name}
							<p class="playwright">av <a href="/person/{performance.playwright_id}">{performance.playwright_name}</a></p>
						{/if}
					</div>
				{/if}

				{#if performance.description}
					<p class="description">{performance.description}</p>
				{/if}
			</div>
		</div>

		<!-- Media/Parts section (only shown for multi-part recordings) -->
		{#if media.length > 1}
			<section class="media-section">
				<h2>Se alle deler ({media.length})</h2>
				<div class="media-grid">
					{#each media as item}
						<a
							href={item.nrk_url || `https://tv.nrk.no/se?v=${item.prf_id}`}
							target="_blank"
							rel="noopener"
							class="media-card"
						>
							<div class="media-thumbnail">
								{#if hasImage(item.image_url)}
									<img src={item.image_url} alt={item.title} loading="lazy" />
								{:else}
									<div class="image-placeholder small">
										<svg viewBox="0 0 24 24" fill="currentColor" class="placeholder-icon">
											<path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z"/>
										</svg>
									</div>
								{/if}
								<div class="play-icon">
									<svg viewBox="0 0 24 24" fill="currentColor">
										<path d="M8 5v14l11-7z"/>
									</svg>
								</div>
								{#if item.duration_seconds}
									<span class="media-duration">{formatDuration(item.duration_seconds)}</span>
								{/if}
							</div>
							<div class="media-info">
								{#if media.length > 1}
									<span class="part-label">
										{#if item.part_number}
											Del {item.part_number}{#if item.total_parts}/{item.total_parts}{/if}
										{:else if item.media_type === 'intro'}
											Introduksjon
										{:else}
											{item.title}
										{/if}
									</span>
								{/if}
								<span class="watch-label">{performance?.medium === 'radio' ? 'Lytt på NRK Radio' : 'Se på NRK TV'}</span>
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Contributors section -->
		{#if Object.keys(contributorGroups).length > 0}
			<section class="contributors">
				<h2>Medvirkende</h2>

				<div class="contributor-groups">
					{#each Object.entries(contributorGroups) as [role, contribs]}
						<div class="contributor-group">
							<h3>{getRoleLabel(role)}</h3>
							<ul>
								{#each contribs as c}
									<li>
										<a href="/person/{c.person_id}">{c.person_name}</a>
										{#if c.character_name}
											<span class="character">som {c.character_name}</span>
										{/if}
									</li>
								{/each}
							</ul>
						</div>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Other performances of the same work -->
		{#if otherPerformances.length > 0}
			<section class="other-performances">
				<h2>Andre opptak av {work?.title || 'dette stykket'}</h2>
				<div class="other-performances-grid">
					{#each otherPerformances as other}
						<a href="/performance/{other.id}" class="other-performance-card">
							<div class="other-thumbnail">
								{#if hasImage(other.image_url)}
									<img src={other.image_url} alt={other.title || ''} loading="lazy" />
								{:else}
									<div class="image-placeholder small">
										<svg viewBox="0 0 24 24" fill="currentColor" class="placeholder-icon">
											<path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z"/>
										</svg>
									</div>
								{/if}
							</div>
							<div class="other-info">
								<span class="other-year">{other.year}</span>
								{#if other.director_name}
									<span class="other-director">Regi: {other.director_name}</span>
								{/if}
								{#if other.total_duration}
									<span class="other-duration">{formatDuration(other.total_duration)}</span>
								{/if}
							</div>
						</a>
					{/each}
				</div>
			</section>
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
		margin-bottom: 1.5rem;
		color: #666;
		text-decoration: none;
	}

	.back-link:hover {
		color: #e94560;
	}

	.performance-detail {
		background: white;
		border-radius: 8px;
		padding: 2rem;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.performance-header {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 2rem;
		margin-bottom: 2rem;
	}

	.performance-image {
		border-radius: 8px;
		overflow: hidden;
		background: #eee;
	}

	.performance-image img {
		width: 100%;
		height: auto;
		display: block;
	}

	.performance-image.playable {
		display: block;
		position: relative;
		text-decoration: none;
	}

	.performance-image.playable:hover .header-play-icon {
		opacity: 1;
		transform: translate(-50%, -50%) scale(1.1);
	}

	.header-play-icon {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		width: 80px;
		height: 80px;
		background: rgba(233, 69, 96, 0.9);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		color: white;
		opacity: 0.9;
		transition: opacity 0.2s, transform 0.2s;
	}

	.header-play-icon svg {
		width: 36px;
		height: 36px;
		margin-left: 4px;
	}

	.header-duration {
		position: absolute;
		bottom: 12px;
		right: 12px;
		background: rgba(0, 0, 0, 0.75);
		color: white;
		padding: 0.3rem 0.6rem;
		border-radius: 4px;
		font-size: 0.9rem;
	}

	.performance-info h1 {
		font-size: 2rem;
		margin-bottom: 0.75rem;
		line-height: 1.2;
	}

	.meta-line {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
		margin-bottom: 1.5rem;
		font-size: 0.95rem;
		color: #666;
	}

	.meta-line .year {
		background: #e94560;
		color: white;
		padding: 0.2rem 0.6rem;
		border-radius: 4px;
		font-weight: 500;
	}

	/* Work preview box */
	.work-preview {
		background: #f8f9fa;
		border-left: 4px solid #e94560;
		padding: 1rem 1.25rem;
		border-radius: 0 8px 8px 0;
		margin-bottom: 1.5rem;
	}

	.work-preview-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.work-preview-header .label {
		font-size: 0.8rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #888;
	}

	.work-link {
		font-size: 0.85rem;
		color: #e94560;
		text-decoration: none;
	}

	.work-link:hover {
		text-decoration: underline;
	}

	.work-preview h2 {
		font-size: 1.25rem;
		margin: 0;
	}

	.work-preview h2 a {
		color: inherit;
		text-decoration: none;
	}

	.work-preview h2 a:hover {
		color: #e94560;
	}

	.year-written {
		font-weight: normal;
		color: #666;
	}

	.playwright {
		margin: 0.25rem 0 0;
		font-size: 0.95rem;
		color: #555;
	}

	.playwright a {
		color: #e94560;
		text-decoration: none;
	}

	.playwright a:hover {
		text-decoration: underline;
	}

	.description {
		line-height: 1.7;
		color: #444;
	}

	/* Media section */
	.media-section {
		border-top: 1px solid #eee;
		padding-top: 2rem;
		margin-bottom: 2rem;
	}

	.media-section h2 {
		font-size: 1.3rem;
		margin-bottom: 1rem;
	}

	.media-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: 1rem;
	}

	.media-card {
		display: block;
		text-decoration: none;
		color: inherit;
		border-radius: 8px;
		overflow: hidden;
		background: #f9f9f9;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.media-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
	}

	.media-thumbnail {
		position: relative;
		aspect-ratio: 16/9;
		background: #eee;
	}

	.media-thumbnail img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.play-icon {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		width: 50px;
		height: 50px;
		background: rgba(233, 69, 96, 0.9);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		color: white;
		opacity: 0.9;
		transition: opacity 0.2s, transform 0.2s;
	}

	.media-card:hover .play-icon {
		opacity: 1;
		transform: translate(-50%, -50%) scale(1.1);
	}

	.play-icon svg {
		width: 24px;
		height: 24px;
		margin-left: 3px;
	}

	.media-duration {
		position: absolute;
		bottom: 8px;
		right: 8px;
		background: rgba(0, 0, 0, 0.75);
		color: white;
		padding: 0.2rem 0.5rem;
		border-radius: 4px;
		font-size: 0.8rem;
	}

	.media-info {
		padding: 0.75rem;
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.part-label {
		font-weight: 600;
		font-size: 0.95rem;
	}

	.watch-label {
		font-size: 0.85rem;
		color: #e94560;
	}

	/* Contributors */
	.contributors {
		border-top: 1px solid #eee;
		padding-top: 2rem;
		margin-bottom: 2rem;
	}

	.contributors h2 {
		font-size: 1.3rem;
		margin-bottom: 1.5rem;
	}

	.contributor-groups {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.contributor-group h3 {
		font-size: 0.9rem;
		font-weight: 600;
		margin-bottom: 0.75rem;
		color: #666;
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}

	.contributor-group ul {
		list-style: none;
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 2rem;
	}

	.contributor-group li {
		white-space: nowrap;
	}

	.contributor-group a {
		color: #333;
		text-decoration: none;
	}

	.contributor-group a:hover {
		color: #e94560;
	}

	.character {
		font-size: 0.85rem;
		color: #888;
	}

	/* Other performances */
	.other-performances {
		border-top: 1px solid #eee;
		padding-top: 2rem;
	}

	.other-performances h2 {
		font-size: 1.3rem;
		margin-bottom: 1rem;
	}

	.other-performances-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: 1rem;
	}

	.other-performance-card {
		display: block;
		text-decoration: none;
		color: inherit;
		border-radius: 8px;
		overflow: hidden;
		background: #f5f5f5;
		transition: transform 0.2s;
	}

	.other-performance-card:hover {
		transform: translateY(-2px);
	}

	.other-thumbnail {
		aspect-ratio: 16/9;
		background: #ddd;
	}

	.other-thumbnail img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.other-info {
		padding: 0.75rem;
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
	}

	.other-year {
		font-weight: 600;
		color: #e94560;
	}

	.other-director, .other-duration {
		font-size: 0.85rem;
		color: #666;
	}

	/* Medium badge in title */
	.medium-badge {
		display: inline-block;
		padding: 0.25rem 0.6rem;
		border-radius: 4px;
		font-size: 0.7rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.02em;
		vertical-align: middle;
		margin-left: 0.75rem;
	}

	.medium-badge.tv {
		background: #e94560;
		color: white;
	}

	.medium-badge.radio {
		background: #6b5ce7;
		color: white;
	}

	/* Image placeholder */
	.image-placeholder {
		width: 100%;
		aspect-ratio: 16/9;
		background: linear-gradient(135deg, #2a2a3e 0%, #1a1a2e 100%);
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 8px;
	}

	.image-placeholder.small {
		border-radius: 0;
	}

	.placeholder-icon {
		width: 64px;
		height: 64px;
		color: rgba(233, 69, 96, 0.6);
	}

	.image-placeholder.small .placeholder-icon {
		width: 40px;
		height: 40px;
	}

	@media (max-width: 768px) {
		.performance-header {
			grid-template-columns: 1fr;
		}

		.performance-info h1 {
			font-size: 1.5rem;
		}

		.media-grid {
			grid-template-columns: repeat(2, 1fr);
		}

		.placeholder-icon {
			width: 48px;
			height: 48px;
		}

		.image-placeholder.small .placeholder-icon {
			width: 32px;
			height: 32px;
		}
	}
</style>

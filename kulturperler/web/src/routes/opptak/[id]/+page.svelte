<script lang="ts">
	import { page } from '$app/stores';
	import { getPerformance, getPerformanceContributors, getPerformanceMedia, getOtherPerformances, getPlay, getWork } from '$lib/db';
	import type { PerformanceWithDetails, PerformancePerson, Episode, Play, Work } from '$lib/types';

	let performance: PerformanceWithDetails | null = null;
	let work: (Play & { playwright_name?: string; composer_name?: string }) | null = null;
	let workDetails: Work | null = null;
	let contributors: (PerformancePerson & { person_name: string })[] = [];
	let media: Episode[] = [];
	let otherPerformances: PerformanceWithDetails[] = [];
	let loading = true;
	let error: string | null = null;

	// Concert work types
	const CONCERT_TYPES = ['symphony', 'concerto', 'orchestral', 'opera', 'ballet', 'chamber', 'choral', 'konsert'];

	$: performanceId = parseInt($page.params.id || '0');

	$: if (performanceId) {
		loadPerformance();
	}

	// Check if this is a concert/classical music recording
	$: isConcert = workDetails?.work_type ? CONCERT_TYPES.includes(workDetails.work_type) : false;

	// Check if this is a kulturprogram (literature/book program)
	$: isKulturprogram = workDetails?.category === 'kulturprogram';

	// Get conductor for concerts, director for theater
	$: conductorName = getConductorName();
	$: directorName = getDirectorName();
	$: leaderName = isConcert ? conductorName : directorName;
	$: leaderLabel = isConcert ? 'Dirigent' : 'Regi';

	// Extract YouTube video ID if available
	$: youtubeId = extractYouTubeId(media[0]?.youtube_url);

	// Get best available image (performance image or first episode's image)
	$: headerImage = performance?.image_url || media[0]?.image_url || null;

	// Get author name (playwright for theater, composer for music)
	$: authorName = isConcert ? work?.composer_name : work?.playwright_name;

	function loadPerformance() {
		loading = true;
		error = null;
		work = null;
		workDetails = null;
		otherPerformances = [];

		try {
			performance = getPerformance(performanceId);
			if (performance) {
				contributors = getPerformanceContributors(performanceId);
				media = getPerformanceMedia(performanceId);

				if (performance.work_id) {
					work = getPlay(performance.work_id);
					workDetails = getWork(performance.work_id);
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

	function extractYouTubeId(url: string | null | undefined): string | null {
		if (!url) return null;
		const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\s]+)/);
		return match ? match[1] : null;
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
			conductor: 'Dirigent',
			actor: 'Skuespillere',
			soloist: 'Solist',
			playwright: 'Manus',
			composer: 'Komponist',
			set_designer: 'Scenografi',
			costume_designer: 'Kostymer',
			producer: 'Produsent',
			orchestra: 'Orkester',
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

	function getConductorName(): string | null {
		const conductor = contributors.find(c => c.role === 'conductor');
		return conductor?.person_name || null;
	}

	$: contributorGroups = groupContributors(contributors);
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

		<div class="performance-header" class:no-media={!youtubeId && !hasImage(headerImage)}>
			<!-- YouTube embed takes priority -->
			{#if youtubeId}
				<div class="youtube-embed">
					<iframe
						src="https://www.youtube.com/embed/{youtubeId}"
						title="{performance.title || 'Video'}"
						frameborder="0"
						allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
						allowfullscreen
					></iframe>
				</div>
			<!-- Show image only if we have one -->
			{:else if hasImage(headerImage)}
				{#if media.length === 1}
					<a
						href={media[0].nrk_url || `https://tv.nrk.no/se?v=${media[0].prf_id}`}
						target="_blank"
						rel="noopener"
						class="performance-image playable"
					>
						<img src={headerImage} alt={performance.title || ''} />
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
						<img src={headerImage} alt={performance.title || ''} />
					</div>
				{/if}
			{/if}
			<!-- No placeholder shown when no image - just show metadata -->

			<div class="performance-info">
				<h1>
					{performance.title || work?.title || 'Ukjent tittel'}
					{#if isConcert}
						<span class="medium-badge concert">Konsert</span>
					{:else if isKulturprogram}
						<span class="medium-badge kulturprogram">Kulturprogram</span>
					{:else if performance.medium === 'radio'}
						<span class="medium-badge radio">Radioteater</span>
					{:else}
						<span class="medium-badge tv">Fjernsynsteater</span>
					{/if}
					{#if performance.language && performance.language !== 'no'}
						<span class="medium-badge lang">{performance.language === 'sv' ? 'Svensk' : performance.language === 'da' ? 'Dansk' : performance.language === 'fi' ? 'Finsk' : performance.language}</span>
					{/if}
				</h1>

				<div class="meta-line">
					{#if performance.year}
						<span class="year">{performance.year}</span>
					{/if}
					{#if performance.total_duration}
						<span class="duration">{formatDurationLong(performance.total_duration)}</span>
					{/if}
					{#if leaderName}
						<span class="director">{leaderLabel}: {leaderName}</span>
					{/if}
					{#if performance.venue}
						<span class="venue">{performance.venue}</span>
					{/if}
				</div>

				<!-- Watch button prominently placed after title/meta when no header media -->
				{#if media.length === 1 && !youtubeId && !hasImage(headerImage)}
					<a
						href={media[0].nrk_url || `https://tv.nrk.no/se?v=${media[0].prf_id}`}
						target="_blank"
						rel="noopener"
						class="watch-button inline"
					>
						<svg viewBox="0 0 24 24" fill="currentColor" class="play-icon">
							<path d="M8 5v14l11-7z"/>
						</svg>
						{#if performance?.source === 'bergenphilive'}
							Se på BergenPhilLive
						{:else if performance?.source === 'sr'}
							Lytt på Sveriges Radio
						{:else if performance?.medium === 'radio'}
							Lytt på NRK Radio
						{:else}
							Se på NRK TV
						{/if}
					</a>
				{/if}

				{#if performance.description}
					<p class="description">{performance.description}</p>
				{:else if workDetails?.synopsis}
					<p class="synopsis">{workDetails.synopsis}</p>
				{/if}

				{#if work}
					<div class="work-link-row">
						<a href="/verk/{work.id}" class="work-context-link">
							<span class="work-context-label">Fra verket</span>
							<span class="work-context-title">{work.title}</span>
							{#if authorName}
								<span class="work-context-author">av {authorName}</span>
							{/if}
							{#if otherPerformances.length > 0}
								<span class="work-context-count">+{otherPerformances.length} andre opptak</span>
							{/if}
						</a>
					</div>
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
							href={item.youtube_url || item.nrk_url || `https://tv.nrk.no/se?v=${item.prf_id}`}
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
						<a href="/opptak/{other.id}" class="other-performance-card">
							<div class="other-thumbnail">
								{#if hasImage(other.image_url)}
									<img src={other.image_url} alt={other.title || ''} loading="lazy" />
								{:else}
									<div class="other-placeholder">
										{other.medium === 'radio' ? 'R' : 'TV'}
									</div>
								{/if}
							</div>
							<div class="other-info">
								<div class="other-meta">
									{#if other.year}
										<span class="other-year">{other.year}</span>
									{/if}
								</div>
								{#if other.orchestra_name}
									<span class="other-detail">{other.orchestra_name}</span>
								{/if}
								{#if other.conductor_name}
									<span class="other-detail">{other.conductor_name}</span>
								{:else if other.director_name && !isConcert}
									<span class="other-detail">{other.director_name}</span>
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

	.performance-header.no-media {
		grid-template-columns: 1fr;
	}

	/* YouTube embed */
	.youtube-embed {
		position: relative;
		width: 100%;
		padding-bottom: 56.25%; /* 16:9 aspect ratio */
		border-radius: 8px;
		overflow: hidden;
		background: #000;
	}

	.youtube-embed iframe {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
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

	/* Compact work context link */
	.work-link-row {
		margin-top: 1rem;
	}

	.work-context-link {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0.75rem;
		background: #f5f5f5;
		border-radius: 6px;
		text-decoration: none;
		color: inherit;
		font-size: 0.9rem;
		transition: background 0.15s;
	}

	.work-context-link:hover {
		background: #eee;
	}

	.work-context-label {
		color: #888;
		font-size: 0.8rem;
	}

	.work-context-title {
		font-weight: 600;
		color: #333;
	}

	.work-context-author {
		color: #666;
		font-size: 0.85rem;
	}

	.work-context-count {
		color: #e94560;
		font-size: 0.85rem;
	}

	.description {
		line-height: 1.7;
		color: #444;
	}

	.synopsis {
		line-height: 1.7;
		color: #555;
		font-style: italic;
		background: #f8f9fa;
		padding: 1rem;
		border-radius: 6px;
		border-left: 3px solid #e94560;
	}

	.venue {
		color: #666;
	}

	/* YouTube embed */
	.youtube-embed-container {
		margin: 1.5rem 0;
		max-width: 800px;
	}

	.youtube-embed {
		position: relative;
		padding-bottom: 56.25%;
		height: 0;
		overflow: hidden;
		border-radius: 12px;
		background: #000;
	}

	.youtube-embed iframe {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		border: none;
	}

	/* Watch button */
	.watch-button {
		display: inline-flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem 2rem;
		background: #e94560;
		color: white;
		text-decoration: none;
		border-radius: 8px;
		font-size: 1.1rem;
		font-weight: 600;
		margin: 1.5rem 0;
		transition: background 0.2s, transform 0.2s;
	}

	.watch-button.inline {
		margin: 1rem 0;
	}

	.watch-button:hover {
		background: #d63850;
		transform: translateY(-2px);
	}

	.watch-button .play-icon {
		width: 24px;
		height: 24px;
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

	/* Other performances - compact horizontal layout */
	.other-performances {
		border-top: 1px solid #eee;
		padding-top: 1.5rem;
	}

	.other-performances h2 {
		font-size: 1.1rem;
		margin-bottom: 1rem;
	}

	.other-performances-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: 1rem;
	}

	.other-performance-card {
		display: flex;
		flex-direction: column;
		text-decoration: none;
		color: inherit;
		border-radius: 8px;
		background: #f9f9f9;
		overflow: hidden;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.other-performance-card:hover {
		transform: translateY(-3px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
	}

	.other-thumbnail {
		aspect-ratio: 16/9;
		width: 100%;
		background: #ddd;
		overflow: hidden;
	}

	.other-thumbnail img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.other-placeholder {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		background: linear-gradient(135deg, #1a1a2e, #16213e);
		color: rgba(255, 255, 255, 0.5);
		font-size: 0.8rem;
	}

	.other-info {
		padding: 0.6rem;
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.other-title {
		font-size: 0.85rem;
		font-weight: 500;
		color: #333;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.other-meta {
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}

	.other-year {
		font-weight: 600;
		font-size: 0.9rem;
		color: #e94560;
	}

	.other-detail {
		font-size: 0.75rem;
		color: #555;
		line-height: 1.3;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.other-duration {
		font-size: 0.8rem;
		color: #666;
		display: none;
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

	.medium-badge.concert {
		background: #10b981;
		color: white;
	}

	.medium-badge.kulturprogram {
		background: #8b5cf6;
		color: white;
	}

	.medium-badge.lang {
		background: #0ea5e9;
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

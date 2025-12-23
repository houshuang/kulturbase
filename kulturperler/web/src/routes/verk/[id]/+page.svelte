<script lang="ts">
	import { page } from '$app/stores';
	import { getWork, getWorkPerformancesByMedium, getPerformanceMedia, getWorkExternalLinks, getPerson, getWorksByPlaywright, getSourceWork, getAdaptations, getPerformanceContributors, getWorkComposers, getComposerRoleLabel, type WorkWithDetails, type WorkWithCounts } from '$lib/db';
	import type { Work, WorkExternalLink, PerformanceWithDetails, Episode, Person, PerformancePerson, WorkComposer, ComposerRole } from '$lib/types';

	interface PerformanceWithMedia extends PerformanceWithDetails {
		media: Episode[];
	}

	let work: (Work & { playwright_name?: string; composer_name?: string }) | null = null;
	let playwright: Person | null = null;
	let composers: WorkComposer[] = [];
	let tvPerformances: PerformanceWithMedia[] = [];
	let radioPerformances: PerformanceWithMedia[] = [];
	let streamPerformances: PerformanceWithMedia[] = [];
	let externalLinks: WorkExternalLink[] = [];
	let moreByAuthor: WorkWithCounts[] = [];
	let sourceWork: WorkWithDetails | null = null;
	let adaptations: WorkWithDetails[] = [];
	let singlePerfContributors: (PerformancePerson & { person_name: string })[] = [];
	let loading = true;
	let error: string | null = null;

	// Concert work types
	const CONCERT_TYPES = ['symphony', 'concerto', 'orchestral', 'opera', 'ballet', 'chamber', 'choral', 'konsert'];

	$: workId = parseInt($page.params.id || '0');

	// Reload data when workId changes (handles client-side navigation)
	$: if (workId) loadWork();

	$: allPerformances = [...tvPerformances, ...radioPerformances, ...streamPerformances];
	$: totalPerformances = allPerformances.length;
	$: isSinglePerformance = totalPerformances === 1;
	$: singlePerf = isSinglePerformance ? allPerformances[0] : null;
	$: isSingleEpisode = singlePerf && singlePerf.media.length === 1;
	$: isConcert = work?.work_type ? CONCERT_TYPES.includes(work.work_type) : false;
	$: leaderLabel = isConcert ? 'Dirigent' : 'Regi';
	// Check if radio/stream section is the first content after header (no external links, no hero, no TV section)
	$: noContentBeforeRadio = externalLinks.length === 0 && !isSinglePerformance && tvPerformances.length === 0;
	$: noContentBeforeStream = noContentBeforeRadio && radioPerformances.length === 0;

	function loadWork() {
		// Reset state for new load
		loading = true;
		error = null;
		work = null;
		playwright = null;
		composers = [];
		tvPerformances = [];
		radioPerformances = [];
		streamPerformances = [];
		externalLinks = [];
		moreByAuthor = [];
		sourceWork = null;
		adaptations = [];
		singlePerfContributors = [];

		try {
			work = getWork(workId);
			if (work) {
				// Get playwright details
				if (work.playwright_id) {
					playwright = getPerson(work.playwright_id);
					// Get more works by this playwright (excluding current)
					moreByAuthor = getWorksByPlaywright(work.playwright_id, workId, 10);
				} else {
					playwright = null;
					moreByAuthor = [];
				}

				// Get composers (multiple)
				composers = getWorkComposers(workId);

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

				// Get Stream performances (YouTube, etc.)
				const streamPerfs = getWorkPerformancesByMedium(workId, 'stream');
				streamPerformances = streamPerfs.map(perf => ({
					...perf,
					media: getPerformanceMedia(perf.id).filter(m => !m.is_introduction)
				}));

				// Load external links
				externalLinks = getWorkExternalLinks(workId);

				// Load contributors if single performance
				const allPerfs = [...tvPerformances, ...radioPerformances, ...streamPerformances];
				if (allPerfs.length === 1) {
					singlePerfContributors = getPerformanceContributors(allPerfs[0].id);
				}

				// Load work relationships
				sourceWork = getSourceWork(workId);
				adaptations = getAdaptations(workId);
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
			konsert: 'Konsert',
			orchestral: 'Orkesterverk',
			symphony: 'Symfoni',
			concerto: 'Konsert',
			chamber: 'Kammermusikk',
			choral: 'Korverk',
			ballet: 'Ballett',
			operetta: 'Operette'
		};
		return labels[type || ''] || type || '';
	}

	function getMediumLabel(source: string | undefined, category: string | null, medium: string): string {
		if (source === 'bergenphilive') return 'Bergen Phil Live';
		if (source === 'youtube') return 'YouTube';
		if (medium === 'stream') return 'Videoopptak';
		if (category === 'dramaserie') return 'Dramaserie';
		if (category === 'teater') return medium === 'tv' ? 'Fjernsynsteater' : 'Radioteater';
		return medium === 'tv' ? 'TV-opptak' : 'Lydopptak';
	}

	function extractYouTubeId(url: string | null | undefined): string | null {
		if (!url) return null;
		const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\s]+)/);
		return match ? match[1] : null;
	}

	function getYouTubeIdFromPerformance(perf: PerformanceWithMedia): string | null {
		if (perf.media.length > 0) {
			const episode = perf.media[0];
			const id = extractYouTubeId(episode.youtube_url);
			if (id) return id;
		}
		return null;
	}

	function getAdaptationTypeLabel(type: string | null): string {
		const labels: Record<string, string> = {
			opera: 'Opera',
			ballet: 'Ballett',
			orchestral: 'Orkesterverk',
			symphony: 'Symfoni',
			concerto: 'Konsert'
		};
		return labels[type || ''] || 'Bearbeidelse';
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
		return labels[role || ''] || role || 'Ukjent';
	}

	function groupContributors(contribs: typeof singlePerfContributors) {
		const groups: Record<string, typeof singlePerfContributors> = {};
		for (const c of contribs) {
			const role = c.role || 'other';
			if (!groups[role]) groups[role] = [];
			groups[role].push(c);
		}
		return groups;
	}

	$: contributorGroups = groupContributors(singlePerfContributors);
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
					<div class="title-row">
						<h1>{work.title}</h1>
						{#if work.sceneweb_url || work.wikipedia_url}
							<div class="header-links">
								{#if work.sceneweb_url}
									<a href={work.sceneweb_url} target="_blank" rel="noopener" class="header-link">Sceneweb</a>
								{/if}
								{#if work.wikipedia_url}
									<a href={work.wikipedia_url} target="_blank" rel="noopener" class="header-link">Wikipedia</a>
								{/if}
							</div>
						{/if}
					</div>

					<p class="work-meta">
						{#if playwright}
							<a href="/person/{playwright.id}" class="author-link">{playwright.name}</a>
							{#if playwright.birth_year || playwright.death_year}
								<span class="author-dates">({playwright.birth_year || '?'}–{playwright.death_year || ''})</span>
							{/if}
						{:else if composers.length > 0}
							{#each composers as comp, i}
								<a href="/person/{comp.person_id}" class="author-link">{comp.person_name}</a>{#if comp.role !== 'composer'} <span class="role-label">({getComposerRoleLabel(comp.role)})</span>{/if}{#if comp.person_birth_year || comp.person_death_year} <span class="author-dates">({comp.person_birth_year || '?'}–{comp.person_death_year || ''})</span>{/if}{#if i < composers.length - 1}<span class="composer-separator">, </span>{/if}
							{/each}
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

		<!-- External links (prominent) -->
		{#if externalLinks.length > 0}
			<section class="external-sources prominent">
				<div class="sources-grid">
					{#each externalLinks.filter(l => l.type === 'bokselskap' || l.type === 'text') as link}
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
					{#each externalLinks.filter(l => l.type === 'archive.org') as link}
						<a href={link.url} target="_blank" rel="noopener" class="source-card archive">
							<span class="source-icon">🎬</span>
							<div class="source-info">
								<span class="source-title">{link.title}</span>
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

		<!-- Smart layout: Single performance with single episode = inline player -->
		{#if isSinglePerformance && singlePerf}
			{@const singleYoutubeId = getYouTubeIdFromPerformance(singlePerf)}
			<section class="single-performance-hero">
				<div class="hero-with-contributors">
					<div class="hero-media">
						{#if singleYoutubeId}
							<!-- YouTube embed for stream performances -->
							<div class="hero-youtube">
								<div class="youtube-embed hero-embed">
									<iframe
										src="https://www.youtube.com/embed/{singleYoutubeId}"
										title={singlePerf.title || work?.title || 'Video'}
										frameborder="0"
										allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
										allowfullscreen
									></iframe>
								</div>
							</div>
						{:else if isSingleEpisode}
							<!-- Direct play for single episode -->
							<a
								href={singlePerf.media[0].nrk_url || `https://tv.nrk.no/se?v=${singlePerf.media[0].prf_id}`}
								target="_blank"
								rel="noopener"
								class="hero-player"
							>
								<div class="hero-image">
									{#if singlePerf.image_url}
										<img src={getImageUrl(singlePerf.image_url, 800)} alt={work?.title || ''} />
									{:else}
										<div class="hero-placeholder">{singlePerf.medium === 'tv' ? 'TV' : singlePerf.medium === 'stream' ? 'Video' : 'Radio'}</div>
									{/if}
									<div class="play-overlay">
										<span class="play-button">▶</span>
									</div>
									{#if singlePerf.total_duration}
										<span class="duration-badge large">{formatDuration(singlePerf.total_duration)}</span>
									{/if}
								</div>
							</a>
						{:else}
							<!-- Single performance with multiple episodes - link list -->
							<div class="hero-multi-episode">
								{#if singlePerf.image_url}
									<img src={getImageUrl(singlePerf.image_url, 600)} alt={work?.title || ''} class="multi-ep-image" />
								{/if}
								<div class="episodes-list">
									{#each singlePerf.media as episode, i}
										<a
											href={episode.nrk_url || `https://tv.nrk.no/se?v=${episode.prf_id}`}
											target="_blank"
											rel="noopener"
											class="episode-link"
										>
											<span class="episode-number">Del {i + 1}</span>
											{#if episode.duration_seconds}
												<span class="episode-duration">{formatDuration(episode.duration_seconds)}</span>
											{/if}
											<span class="episode-play">▶ Spill</span>
										</a>
									{/each}
								</div>
							</div>
						{/if}
						<div class="hero-meta">
							<span class="medium-label {singleYoutubeId ? 'youtube' : ''}">{getMediumLabel(singlePerf.source, work?.category, singlePerf.medium)}</span>
							{#if singlePerf.year}
								<span class="year-badge">{singlePerf.year}</span>
							{/if}
							{#if singlePerf.description}
								<span class="perf-description">{singlePerf.description}</span>
							{/if}
						</div>
					</div>

					{#if singlePerfContributors.length > 0}
						<div class="hero-contributors">
							<h3>Medvirkende</h3>
							<div class="contributors-compact">
								{#each Object.entries(contributorGroups) as [role, contribs]}
									<div class="contrib-group">
										<span class="contrib-role">{getRoleLabel(role)}</span>
										<div class="contrib-names">
											{#each contribs as c, i}<span class="contrib-person"><a href="/person/{c.person_id}">{c.person_name}</a>{#if c.character_name}<span class="char-name"> ({c.character_name})</span>{/if}</span>{/each}
										</div>
									</div>
								{/each}
							</div>
							<a href="/opptak/{singlePerf.id}" class="more-details-link">Se alle detaljer →</a>
						</div>
					{/if}
				</div>
			</section>
		{:else if totalPerformances > 1}
			<!-- Multiple performances: Show cards by medium -->
			{#if tvPerformances.length > 0}
			<section class="performances tv-section">
				<h2>
					<span class="medium-icon tv">TV</span>
					{isConcert ? 'TV-opptak' : 'Fjernsynsteater'}
					{#if tvPerformances.length > 1}<span class="count">({tvPerformances.length})</span>{/if}
				</h2>

				<div class="performances-grid">
					{#each tvPerformances as perf}
						<a href="/opptak/{perf.id}" class="performance-card" class:no-image={!perf.image_url}>
							{#if perf.image_url}
								<div class="perf-image">
									<img src={getImageUrl(perf.image_url)} alt={perf.title || work?.title || ''} loading="lazy" />
									{#if perf.total_duration}
										<span class="duration-badge">{formatDuration(perf.total_duration)}</span>
									{/if}
									{#if perf.media.length > 1}
										<span class="parts-badge">{perf.media.length} deler</span>
									{/if}
								</div>
							{/if}
							<div class="perf-info">
								<div class="perf-meta-row">
									{#if perf.year}
										<span class="perf-year">{perf.year}</span>
									{/if}
									<span class="source-badge nrk">NRK TV</span>
									{#if perf.total_duration && !perf.image_url}
										<span class="perf-duration-inline">{formatDuration(perf.total_duration)}</span>
									{/if}
								</div>
								{#if perf.title && perf.title !== work?.title}
									<h3 class="perf-title">{perf.title}</h3>
								{/if}
								{#if isConcert && perf.conductor_name}
									<p class="perf-director">{leaderLabel}: {perf.conductor_name}</p>
								{:else if perf.director_name}
									<p class="perf-director">{leaderLabel}: {perf.director_name}</p>
								{:else if perf.description}
									<p class="perf-desc">{perf.description}</p>
								{/if}
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		{#if radioPerformances.length > 0}
			<section class="performances radio-section" class:first-section={noContentBeforeRadio}>
				<h2>
					<span class="medium-icon radio">R</span>
					{isConcert ? 'Lydopptak' : 'Radioteater'}
					{#if radioPerformances.length > 1}<span class="count">({radioPerformances.length})</span>{/if}
				</h2>

				<div class="performances-grid">
					{#each radioPerformances as perf}
						<a href="/opptak/{perf.id}" class="performance-card" class:no-image={!perf.image_url}>
							{#if perf.image_url}
								<div class="perf-image radio-image">
									<img src={getImageUrl(perf.image_url)} alt={perf.title || work?.title || ''} loading="lazy" />
									{#if perf.total_duration}
										<span class="duration-badge">{formatDuration(perf.total_duration)}</span>
									{/if}
									{#if perf.media.length > 1}
										<span class="parts-badge">{perf.media.length} deler</span>
									{/if}
								</div>
							{/if}
							<div class="perf-info">
								<div class="perf-meta-row">
									{#if perf.year}
										<span class="perf-year radio">{perf.year}</span>
									{/if}
									<span class="source-badge nrk">NRK Radio</span>
									{#if perf.total_duration && !perf.image_url}
										<span class="perf-duration-inline">{formatDuration(perf.total_duration)}</span>
									{/if}
								</div>
								{#if perf.title && perf.title !== work?.title}
									<h3 class="perf-title">{perf.title}</h3>
								{/if}
								{#if isConcert && perf.conductor_name}
									<p class="perf-director">{leaderLabel}: {perf.conductor_name}</p>
								{:else if perf.director_name}
									<p class="perf-director">{leaderLabel}: {perf.director_name}</p>
								{:else if perf.description}
									<p class="perf-desc">{perf.description}</p>
								{/if}
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		{#if streamPerformances.length > 0}
			<section class="performances stream-section" class:first-section={noContentBeforeStream}>
				<h2>
					<span class="medium-icon stream">▶</span>
					Videoopptak
					{#if streamPerformances.length > 1}<span class="count">({streamPerformances.length})</span>{/if}
				</h2>

				<div class="performances-grid stream-grid">
					{#each streamPerformances as perf}
						{@const youtubeId = getYouTubeIdFromPerformance(perf)}
						<a href="/opptak/{perf.id}" class="performance-card stream-card">
							{#if youtubeId}
								<div class="youtube-thumb">
									<img src="https://img.youtube.com/vi/{youtubeId}/mqdefault.jpg" alt={perf.title || work?.title || ''} loading="lazy" />
									<span class="play-icon">▶</span>
									{#if perf.total_duration}
										<span class="duration-badge">{formatDuration(perf.total_duration)}</span>
									{/if}
								</div>
							{:else if perf.image_url}
								<div class="perf-image">
									<img src={getImageUrl(perf.image_url)} alt={perf.title || work?.title || ''} loading="lazy" />
									{#if perf.total_duration}
										<span class="duration-badge">{formatDuration(perf.total_duration)}</span>
									{/if}
								</div>
							{/if}
							<div class="perf-info">
								<div class="perf-meta-row">
									{#if perf.year}<span class="perf-year stream">{perf.year}</span>{/if}
									<span class="source-badge {perf.source}">{perf.source === 'youtube' ? 'YouTube' : perf.source === 'bergenphilive' ? 'BergenPhilLive' : 'Video'}</span>
								</div>
								{#if perf.title}
									<h3 class="perf-title">{perf.title}</h3>
								{/if}
								{#if perf.orchestra_name || perf.conductor_name}
									<p class="perf-credits">
										{#if perf.orchestra_name}{perf.orchestra_name}{/if}
										{#if perf.orchestra_name && perf.conductor_name} · {/if}
										{#if perf.conductor_name}Dirigent: {perf.conductor_name}{/if}
									</p>
								{/if}
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}
		{/if}

		<!-- Source work (based on) -->
		{#if sourceWork}
			<section class="based-on-section">
				<h2>Basert pa</h2>
				<a href="/verk/{sourceWork.id}" class="source-work-card">
					{#if sourceWork.image_url}
						<img src={getImageUrl(sourceWork.image_url, 200)} alt={sourceWork.title} />
					{:else}
						<div class="source-work-placeholder">Verk</div>
					{/if}
					<div class="source-work-info">
						<h3>{sourceWork.title}</h3>
						{#if sourceWork.playwright_name}
							<p class="source-work-author">{sourceWork.playwright_name}</p>
						{:else if sourceWork.composer_name}
							<p class="source-work-author">{sourceWork.composer_name}</p>
						{/if}
						{#if sourceWork.year_written}
							<span class="source-work-year">{sourceWork.year_written}</span>
						{/if}
						{#if sourceWork.performance_count > 0}
							<span class="source-work-count">{sourceWork.performance_count} opptak</span>
						{/if}
					</div>
				</a>
			</section>
		{/if}

		<!-- Adaptations -->
		{#if adaptations.length > 0}
			<section class="adaptations-section">
				<h2>Bearbeidelser av dette verket</h2>
				<div class="adaptations-grid">
					{#each adaptations as adaptation}
						<a href="/verk/{adaptation.id}" class="adaptation-card">
							{#if adaptation.image_url}
								<img src={getImageUrl(adaptation.image_url, 200)} alt={adaptation.title} />
							{:else}
								<div class="adaptation-placeholder">{getAdaptationTypeLabel(adaptation.work_type)}</div>
							{/if}
							<div class="adaptation-info">
								<span class="adaptation-type">{getAdaptationTypeLabel(adaptation.work_type)}</span>
								<h3>{adaptation.title}</h3>
								{#if adaptation.composer_name}
									<p class="adaptation-creator">{adaptation.composer_name}</p>
								{/if}
								{#if adaptation.performance_count > 0}
									<span class="adaptation-count">{adaptation.performance_count} opptak</span>
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
					{#if moreByAuthor.length >= 10}
						<a href="/person/{playwright.id}" class="see-all">Se alle verk →</a>
					{/if}
				</div>
				<div class="author-works-grid">
					{#each moreByAuthor as authorWork}
						<a href="/verk/{authorWork.id}" class="author-work-card" data-sveltekit-preload-data>
							<div class="author-work-image">
								{#if authorWork.image_url}
									<img src={getImageUrl(authorWork.image_url, 240)} alt={authorWork.title || ''} loading="lazy" />
								{:else}
									<div class="author-work-placeholder">Verk</div>
								{/if}
							</div>
							<div class="author-work-info">
								<h3>{authorWork.title}</h3>
								<div class="author-work-meta">
									{#if authorWork.performance_count > 1}
										<span class="author-work-count">{authorWork.performance_count} opptak</span>
									{/if}
									{#if authorWork.year_written}
										<span class="author-work-year">{authorWork.year_written}</span>
									{/if}
								</div>
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

	.title-row {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 1rem;
	}

	.work-header h1 {
		font-size: 1.75rem;
		margin: 0 0 0.5rem 0;
		line-height: 1.2;
	}

	.header-links {
		display: flex;
		gap: 0.5rem;
		flex-shrink: 0;
	}

	.header-link {
		padding: 0.3rem 0.6rem;
		background: #f0f0f0;
		border-radius: 4px;
		text-decoration: none;
		color: #555;
		font-size: 0.8rem;
		transition: background-color 0.15s;
		white-space: nowrap;
	}

	.header-link:hover {
		background: #e0e0e0;
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
		margin-left: 0.25rem;
	}

	.role-label {
		color: #888;
		font-size: 0.85rem;
		margin-left: 0.2rem;
	}

	.composer-separator {
		color: #888;
		margin-right: 0.25rem;
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

	.source-card.archive {
		background: linear-gradient(135deg, #2d3748, #1a202c);
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

	.medium-icon.stream {
		background: #ff0000;
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

	.perf-duration {
		font-size: 0.85rem;
		color: #888;
		margin: 0;
	}

	.performance-card.no-image {
		background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
	}

	.performance-card.no-image .perf-info {
		padding: 1.25rem;
	}

	.tv-section {
		margin-bottom: 2rem;
	}

	.radio-section,
	.stream-section {
		border-top: 1px solid #eee;
		padding-top: 1.5rem;
	}

	/* Remove top border when it's the first performances section (no preceding content) */
	.stream-section.first-section,
	.radio-section.first-section {
		border-top: none;
		padding-top: 0;
	}

	.stream-grid {
		grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
	}

	.stream-card {
		background: #f9f9f9;
	}

	.youtube-embed {
		position: relative;
		width: 100%;
		padding-bottom: 56.25%;
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

	.hero-youtube {
		border-radius: 12px;
		overflow: hidden;
		background: #000;
	}

	.hero-embed {
		max-height: 500px;
	}

	.medium-label.youtube {
		background: #ff0000;
	}

	.perf-year.stream {
		background: #ff0000;
	}

	.details-link {
		display: inline-block;
		color: #e94560;
		text-decoration: none;
		font-size: 0.85rem;
		margin-top: 0.5rem;
	}

	.details-link:hover {
		text-decoration: underline;
	}

	.youtube-thumb {
		position: relative;
		aspect-ratio: 16/9;
		background: #000;
	}

	.youtube-thumb img {
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
		background: rgba(255, 0, 0, 0.9);
		border-radius: 8px;
		display: flex;
		align-items: center;
		justify-content: center;
		color: white;
		font-size: 1.25rem;
	}

	.perf-meta-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: nowrap;
		margin-bottom: 0.5rem;
	}

	.source-badge {
		padding: 0.15rem 0.5rem;
		border-radius: 4px;
		font-size: 0.75rem;
		font-weight: 500;
		background: #666;
		color: white;
	}

	.source-badge.youtube {
		background: #ff0000;
	}

	.source-badge.bergenphilive {
		background: #1a1a2e;
	}

	.source-badge.nrk {
		background: #26292a;
	}

	.perf-duration-inline {
		font-size: 0.85rem;
		color: #666;
	}

	.perf-title {
		font-size: 0.95rem;
		font-weight: 600;
		margin: 0 0 0.25rem 0;
		line-height: 1.3;
	}

	.perf-desc {
		font-size: 0.85rem;
		color: #666;
		margin: 0;
		line-height: 1.4;
	}

	.perf-credits {
		font-size: 0.85rem;
		color: #555;
		margin: 0.25rem 0 0 0;
		line-height: 1.4;
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

	.author-works-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: 1rem;
	}

	.author-work-card {
		display: flex;
		flex-direction: column;
		background: #f9f9f9;
		border-radius: 8px;
		overflow: hidden;
		text-decoration: none;
		color: inherit;
		cursor: pointer;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.author-work-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
	}

	.author-work-card:active {
		transform: translateY(-2px);
	}

	.author-work-image {
		aspect-ratio: 16/9;
		overflow: hidden;
		background: #ddd;
	}

	.author-work-image img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.author-work-placeholder {
		width: 100%;
		height: 100%;
		background: linear-gradient(135deg, #1a1a2e, #16213e);
		display: flex;
		align-items: center;
		justify-content: center;
		color: rgba(255, 255, 255, 0.5);
		font-size: 0.85rem;
	}

	.author-work-info {
		padding: 0.75rem;
		flex: 1;
	}

	.author-work-info h3 {
		font-size: 0.9rem;
		margin: 0 0 0.25rem 0;
		line-height: 1.3;
	}

	.author-work-meta {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		flex-wrap: wrap;
	}

	.author-work-count {
		font-size: 0.75rem;
		background: #e94560;
		color: white;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
	}

	.author-work-year {
		font-size: 0.8rem;
		color: #888;
	}

	/* External sources prominent */
	.external-sources.prominent {
		margin-bottom: 1.5rem;
	}

	.source-icon {
		font-size: 1.25rem;
	}

	/* Single performance hero */
	.single-performance-hero {
		margin-bottom: 2rem;
	}

	.hero-with-contributors {
		display: grid;
		grid-template-columns: 1fr 320px;
		gap: 1.5rem;
		background: #f9f9f9;
		border-radius: 12px;
		overflow: hidden;
	}

	.hero-media {
		display: flex;
		flex-direction: column;
	}

	.hero-media .hero-youtube {
		flex: 1;
	}

	.hero-media .hero-player {
		flex: 1;
		border-radius: 0;
	}

	.hero-contributors {
		padding: 1.25rem;
		display: flex;
		flex-direction: column;
		overflow-y: auto;
		max-height: 400px;
	}

	.hero-contributors h3 {
		font-size: 0.9rem;
		font-weight: 600;
		margin: 0 0 1rem 0;
		color: #333;
		text-transform: uppercase;
		letter-spacing: 0.02em;
	}

	.contributors-compact {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		flex: 1;
	}

	.contrib-group {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
	}

	.contrib-role {
		font-size: 0.75rem;
		font-weight: 600;
		color: #888;
		text-transform: uppercase;
	}

	.contrib-names {
		font-size: 0.9rem;
		line-height: 1.5;
	}

	.contrib-names a {
		color: #333;
		text-decoration: none;
	}

	.contrib-names a:hover {
		color: #e94560;
	}

	.contrib-person:not(:last-child)::after {
		content: ', ';
	}

	.char-name {
		color: #888;
		font-size: 0.85rem;
	}

	.more-details-link {
		margin-top: auto;
		padding-top: 1rem;
		color: #e94560;
		text-decoration: none;
		font-size: 0.85rem;
	}

	.more-details-link:hover {
		text-decoration: underline;
	}

	.perf-description {
		color: #555;
		font-size: 0.9rem;
	}

	.hero-multi-episode {
		padding: 1rem;
	}

	.multi-ep-image {
		width: 100%;
		max-width: 400px;
		border-radius: 8px;
		margin-bottom: 1rem;
	}

	.hero-player {
		display: block;
		text-decoration: none;
		color: inherit;
		border-radius: 12px;
		overflow: hidden;
		background: #f5f5f5;
	}

	.hero-image {
		position: relative;
		aspect-ratio: 16/9;
		max-height: 400px;
	}

	.hero-image img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.hero-placeholder {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		background: linear-gradient(135deg, #1a1a2e, #16213e);
		color: rgba(255, 255, 255, 0.5);
		font-size: 1.5rem;
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

	.hero-player:hover .play-overlay {
		opacity: 1;
	}

	.play-button {
		width: 80px;
		height: 80px;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.95);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 2rem;
		color: #e94560;
		padding-left: 6px;
	}

	.duration-badge.large {
		position: absolute;
		bottom: 1rem;
		right: 1rem;
		background: rgba(0, 0, 0, 0.85);
		color: white;
		padding: 0.4rem 0.8rem;
		border-radius: 6px;
		font-size: 1rem;
		font-weight: 500;
	}

	.hero-meta {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1rem 1.5rem;
		background: #f9f9f9;
	}

	.medium-label {
		background: #e94560;
		color: white;
		padding: 0.25rem 0.75rem;
		border-radius: 4px;
		font-size: 0.85rem;
		font-weight: 500;
	}

	.year-badge {
		background: #1a1a2e;
		color: white;
		padding: 0.25rem 0.6rem;
		border-radius: 4px;
		font-size: 0.9rem;
	}

	.hero-meta .director {
		color: #666;
		font-size: 0.95rem;
	}

	/* Multi-episode single performance */
	.hero-content {
		display: grid;
		grid-template-columns: 350px 1fr;
		gap: 1.5rem;
		background: #f9f9f9;
		border-radius: 12px;
		padding: 1.5rem;
	}

	.hero-image-container {
		border-radius: 8px;
		overflow: hidden;
	}

	.hero-image-container img {
		width: 100%;
		aspect-ratio: 16/9;
		object-fit: cover;
	}

	.hero-info {
		display: flex;
		flex-direction: column;
	}

	.hero-meta-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 0.75rem;
	}

	.hero-info .director {
		color: #666;
		margin: 0 0 0.5rem 0;
	}

	.episodes-label {
		font-weight: 600;
		color: #333;
		margin: 0.5rem 0;
	}

	.episodes-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.episode-link {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 0.75rem 1rem;
		background: white;
		border-radius: 6px;
		text-decoration: none;
		color: inherit;
		transition: background 0.15s, box-shadow 0.15s;
	}

	.episode-link:hover {
		background: #f0f0f0;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.episode-number {
		font-weight: 600;
		color: #333;
	}

	.episode-duration {
		color: #666;
		font-size: 0.9rem;
	}

	.episode-play {
		margin-left: auto;
		color: #e94560;
		font-weight: 500;
	}

	/* Comparison table */
	.performances-comparison {
		margin-bottom: 2rem;
	}

	.performances-comparison h2 {
		font-size: 1.25rem;
		margin-bottom: 1rem;
	}

	.comparison-table-wrapper {
		overflow-x: auto;
		border-radius: 8px;
		border: 1px solid #e0e0e0;
	}

	.comparison-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.95rem;
	}

	.comparison-table th {
		text-align: left;
		padding: 0.75rem 1rem;
		background: #f8f9fa;
		font-weight: 600;
		color: #555;
		border-bottom: 2px solid #e0e0e0;
	}

	.comparison-table td {
		padding: 0.75rem 1rem;
		border-bottom: 1px solid #eee;
	}

	.comparison-table tr:last-child td {
		border-bottom: none;
	}

	.comparison-table tr:hover {
		background: #fafafa;
	}

	.table-year {
		font-weight: 600;
		color: #333;
		font-size: 1.1rem;
	}

	.table-medium {
		display: inline-block;
		padding: 0.2rem 0.5rem;
		border-radius: 4px;
		font-size: 0.8rem;
		font-weight: 500;
	}

	.table-medium.tv {
		background: #e94560;
		color: white;
	}

	.table-medium.radio {
		background: #6b5ce7;
		color: white;
	}

	.table-medium.stream {
		background: #ff0000;
		color: white;
	}

	.director-cell {
		max-width: 200px;
	}

	.action-cell {
		text-align: right;
	}

	.table-link {
		color: #e94560;
		text-decoration: none;
		font-weight: 500;
	}

	.table-link:hover {
		text-decoration: underline;
	}

	/* Based on / Source work */
	.based-on-section {
		margin-bottom: 2rem;
		padding-top: 1.5rem;
		border-top: 1px solid #eee;
	}

	.based-on-section h2 {
		font-size: 1.1rem;
		margin-bottom: 1rem;
		color: #666;
	}

	.source-work-card {
		display: flex;
		gap: 1rem;
		padding: 1rem;
		background: #f9f9f9;
		border-radius: 8px;
		text-decoration: none;
		color: inherit;
		transition: background 0.15s;
		max-width: 400px;
	}

	.source-work-card:hover {
		background: #f0f0f0;
	}

	.source-work-card img {
		width: 100px;
		height: 60px;
		object-fit: cover;
		border-radius: 4px;
	}

	.source-work-placeholder {
		width: 100px;
		height: 60px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: linear-gradient(135deg, #1a1a2e, #16213e);
		color: rgba(255, 255, 255, 0.5);
		border-radius: 4px;
		font-size: 0.8rem;
	}

	.source-work-info {
		display: flex;
		flex-direction: column;
		justify-content: center;
	}

	.source-work-info h3 {
		font-size: 1rem;
		margin: 0 0 0.25rem 0;
	}

	.source-work-author {
		color: #e94560;
		font-size: 0.9rem;
		margin: 0;
	}

	.source-work-year, .source-work-count {
		font-size: 0.8rem;
		color: #888;
		margin-right: 0.5rem;
	}

	/* Adaptations */
	.adaptations-section {
		margin-bottom: 2rem;
		padding-top: 1.5rem;
		border-top: 1px solid #eee;
	}

	.adaptations-section h2 {
		font-size: 1.1rem;
		margin-bottom: 1rem;
		color: #666;
	}

	.adaptations-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: 1rem;
	}

	.adaptation-card {
		background: #f9f9f9;
		border-radius: 8px;
		overflow: hidden;
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.adaptation-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
	}

	.adaptation-card img {
		width: 100%;
		height: 100px;
		object-fit: cover;
	}

	.adaptation-placeholder {
		width: 100%;
		height: 100px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: linear-gradient(135deg, #667eea, #764ba2);
		color: white;
		font-size: 0.9rem;
	}

	.adaptation-info {
		padding: 0.75rem;
	}

	.adaptation-type {
		display: inline-block;
		background: #667eea;
		color: white;
		padding: 0.15rem 0.5rem;
		border-radius: 3px;
		font-size: 0.75rem;
		margin-bottom: 0.5rem;
	}

	.adaptation-info h3 {
		font-size: 0.9rem;
		margin: 0 0 0.25rem 0;
		line-height: 1.3;
	}

	.adaptation-creator {
		color: #666;
		font-size: 0.85rem;
		margin: 0;
	}

	.adaptation-count {
		font-size: 0.8rem;
		color: #888;
	}

	@media (max-width: 800px) {
		.hero-with-contributors {
			grid-template-columns: 1fr;
		}

		.hero-contributors {
			max-height: none;
			border-top: 1px solid #eee;
		}
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

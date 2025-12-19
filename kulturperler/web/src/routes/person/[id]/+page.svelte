<script lang="ts">
	import { page } from '$app/stores';
	import { getPerson, getDatabase, getNrkAboutPrograms } from '$lib/db';
	import type { Person, EpisodeWithDetails, NrkAboutProgram } from '$lib/types';
	import { onMount } from 'svelte';

	let person: Person | null = null;
	let playsByRole: { role: string; plays: { play_id: number; title: string; image_url: string | null; episode_count: number; year: number | null; playwright_name: string | null }[] }[] = [];
	let playsWritten: { id: number; title: string; year_written: number | null; performance_count: number; image_url: string | null }[] = [];
	let nrkAboutPrograms: NrkAboutProgram[] = [];
	let loading = true;
	let error: string | null = null;

	$: personId = parseInt($page.params.id || '0');

	onMount(() => {
		loadPerson();
	});

	function loadPerson() {
		try {
			person = getPerson(personId);
			if (person) {
				const db = getDatabase();

				// Get plays written by this person (with image from first performance's episode)
				const playsStmt = db.prepare(`
					SELECT p.id, p.title, p.year_written,
						(SELECT COUNT(*) FROM performances pf WHERE pf.work_id = p.id) as performance_count,
						(SELECT e.image_url FROM episodes e
						 JOIN performances pf ON e.performance_id = pf.id
						 WHERE pf.work_id = p.id LIMIT 1) as image_url
					FROM plays p
					WHERE p.playwright_id = ?
					ORDER BY p.year_written, p.title
				`);
				playsStmt.bind([personId]);
				playsWritten = [];
				while (playsStmt.step()) {
					playsWritten.push(playsStmt.getAsObject() as any);
				}
				playsStmt.free();

				// Get plays by role (excluding playwright since we show plays separately)
				const rolesStmt = db.prepare(`
					SELECT DISTINCT role FROM episode_persons
					WHERE person_id = ? AND role != 'playwright'
				`);
				rolesStmt.bind([personId]);
				const roles: string[] = [];
				while (rolesStmt.step()) {
					roles.push(rolesStmt.getAsObject().role as string);
				}
				rolesStmt.free();

				playsByRole = [];
				for (const role of roles) {
					const playsStmt = db.prepare(`
						SELECT
							p.id as play_id,
							p.title,
							MIN(e.image_url) as image_url,
							COUNT(*) as episode_count,
							MIN(e.year) as year,
							pw.name as playwright_name
						FROM episodes e
						JOIN episode_persons ep ON e.prf_id = ep.episode_id
						JOIN plays p ON e.play_id = p.id
						LEFT JOIN persons pw ON p.playwright_id = pw.id
						WHERE ep.person_id = ? AND ep.role = ?
						GROUP BY p.id
						ORDER BY year DESC
					`);
					playsStmt.bind([personId, role]);
					const plays: { play_id: number; title: string; image_url: string | null; episode_count: number; year: number | null; playwright_name: string | null }[] = [];
					while (playsStmt.step()) {
						plays.push(playsStmt.getAsObject() as any);
					}
					playsStmt.free();
					if (plays.length > 0) {
						playsByRole.push({ role, plays });
					}
				}

				// Get NRK programs about this person
				nrkAboutPrograms = getNrkAboutPrograms(personId);
			} else {
				error = 'Person ikke funnet';
			}
			loading = false;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Ukjent feil';
			loading = false;
		}
	}

	function getRoleLabel(role: string): string {
		const labels: Record<string, string> = {
			director: 'Regissert',
			actor: 'Spilt i',
			playwright: 'Manus',
			composer: 'Komponert',
			producer: 'Produsert',
			other: 'Annet'
		};
		return labels[role] || role;
	}

	function formatDuration(seconds: number | null): string {
		if (!seconds) return '';
		const h = Math.floor(seconds / 3600);
		const m = Math.floor((seconds % 3600) / 60);
		if (h > 0) return `${h}t ${m}m`;
		return `${m} min`;
	}

	function getImageUrl(url: string | null, width = 320): string {
		if (!url) return '/placeholder.jpg';
		if (url.includes('gfx.nrk.no')) {
			return url.replace(/\/\d+$/, `/${width}`);
		}
		return url;
	}
</script>

<svelte:head>
	{#if person}
		<title>{person.name} - Kulturperler</title>
	{/if}
</svelte:head>

{#if loading}
	<div class="loading">Laster...</div>
{:else if error}
	<div class="error">{error}</div>
{:else if person}
	<article class="person-detail">
		<a href="/" class="back-link">&larr; Tilbake til oversikt</a>

		<header class="person-header">
			<div class="header-content">
				<div class="header-text">
					<h1>{person.name}</h1>
					{#if person.birth_year || person.death_year}
						<p class="years">{person.birth_year || '?'}–{person.death_year || ''}</p>
					{/if}
					{#if person.bio}
						<p class="bio">{person.bio}</p>
					{/if}
					<div class="external-links">
						{#if person.sceneweb_url}
							<a href={person.sceneweb_url} target="_blank" rel="noopener" class="external-link">
								Sceneweb
							</a>
						{/if}
						{#if person.wikipedia_url}
							<a href={person.wikipedia_url} target="_blank" rel="noopener" class="external-link">
								Wikipedia
							</a>
						{/if}
					</div>
				</div>
			</div>
		</header>

		{#if playsWritten.length > 0}
			<section class="plays-written">
				<h2>Stykker tilgjengelig ({playsWritten.length})</h2>
				<div class="plays-grid">
					{#each playsWritten as play}
						<a href="/play/{play.id}" class="play-card">
							<div class="play-image">
								{#if play.image_url}
									<img src={getImageUrl(play.image_url)} alt={play.title} loading="lazy" />
								{:else}
									<div class="play-placeholder">
										<span>🎭</span>
									</div>
								{/if}
							</div>
							<div class="play-info">
								<h3>{play.title}</h3>
								{#if play.year_written}
									<span class="play-year">{play.year_written}</span>
								{/if}
								{#if play.performance_count > 0}
									<span class="play-count">{play.performance_count} opptak</span>
								{/if}
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		{#if nrkAboutPrograms.length > 0}
			<section class="nrk-about">
				<h2>I NRK-arkivet</h2>
				<div class="about-programs-grid">
					{#each nrkAboutPrograms as program}
						<a href={program.nrk_url} target="_blank" rel="noopener" class="about-card">
							<div class="about-image">
								{#if program.image_url}
									<img src={program.image_url} alt={program.title} loading="lazy" />
								{:else}
									<div class="about-placeholder">
										<span>📺</span>
									</div>
								{/if}
							</div>
							<div class="about-info">
								<h3>{program.title}</h3>
								<div class="about-meta">
									{#if program.program_type === 'serie'}
										<span class="about-type">Serie{#if program.episode_count} · {program.episode_count} ep{/if}</span>
									{/if}
									{#if program.duration_seconds}
										<span class="about-duration">{formatDuration(program.duration_seconds)}</span>
									{/if}
								</div>
							</div>
							<span class="external-arrow">↗</span>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		{#each playsByRole as group}
			<section class="role-section">
				<h2>{getRoleLabel(group.role)} ({group.plays.length})</h2>

				<div class="plays-grid">
					{#each group.plays as play}
						<a href="/play/{play.play_id}" class="play-card">
							<div class="play-image">
								{#if play.image_url}
									<img src={getImageUrl(play.image_url)} alt={play.title} loading="lazy" />
								{:else}
									<div class="play-placeholder">
										<span>🎭</span>
									</div>
								{/if}
							</div>
							<div class="play-info">
								<h3>{play.title}</h3>
								{#if play.year}
									<span class="play-year">{play.year}</span>
								{/if}
								{#if play.episode_count > 1}
									<span class="play-count">{play.episode_count} deler</span>
								{/if}
								{#if play.playwright_name}
									<span class="playwright">{play.playwright_name}</span>
								{/if}
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/each}
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

	.person-detail {
		background: white;
		border-radius: 8px;
		padding: 2rem;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.person-header {
		margin-bottom: 2rem;
		padding-bottom: 1.5rem;
		border-bottom: 1px solid #eee;
	}

	.header-content {
		display: flex;
		gap: 1.5rem;
		align-items: flex-start;
	}

	.person-portrait {
		width: 120px;
		height: 120px;
		border-radius: 50%;
		overflow: hidden;
		flex-shrink: 0;
		background: #f0f0f0;
	}

	.person-portrait img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.header-text {
		flex: 1;
	}

	.person-header h1 {
		font-size: 2rem;
		margin-bottom: 0.25rem;
	}

	.years {
		font-size: 1.1rem;
		color: #666;
		margin-bottom: 0.75rem;
	}

	.bio {
		font-size: 0.95rem;
		color: #444;
		line-height: 1.6;
		margin-bottom: 0.5rem;
	}

	.external-links {
		display: flex;
		gap: 1rem;
		margin-top: 1rem;
	}

	.external-link {
		padding: 0.5rem 1rem;
		background: #f5f5f5;
		border-radius: 4px;
		text-decoration: none;
		color: #333;
		font-size: 0.9rem;
	}

	.external-link:hover {
		background: #e94560;
		color: white;
	}

	.plays-written {
		margin-bottom: 2rem;
		padding-bottom: 1.5rem;
		border-bottom: 1px solid #eee;
	}

	.plays-written h2, .role-section h2, .nrk-about h2 {
		font-size: 1.3rem;
		margin-bottom: 1rem;
	}

	.plays-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: 1rem;
	}

	.play-card {
		background: #f9f9f9;
		border-radius: 8px;
		overflow: hidden;
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s;
	}

	.play-card:hover {
		transform: translateY(-2px);
	}

	.play-image {
		aspect-ratio: 16/9;
		background: #eee;
	}

	.play-image img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.play-placeholder {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		background: linear-gradient(135deg, #667 0%, #445 100%);
		font-size: 2rem;
	}

	.play-info {
		padding: 0.5rem 0.75rem;
	}

	.play-info h3 {
		font-size: 0.9rem;
		font-weight: 600;
		margin-bottom: 0.25rem;
		line-height: 1.3;
	}

	.play-year {
		display: inline-block;
		background: #e94560;
		color: white;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
		font-size: 0.75rem;
		margin-right: 0.5rem;
	}

	.play-count {
		font-size: 0.75rem;
		color: #666;
	}

	.nrk-about {
		margin-bottom: 2rem;
		padding-bottom: 1.5rem;
		border-bottom: 1px solid #eee;
	}

	.about-programs-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.75rem;
	}

	.about-card {
		display: flex;
		gap: 0.75rem;
		padding: 0.5rem;
		background: #f9f9f9;
		border-radius: 8px;
		text-decoration: none;
		color: inherit;
		transition: background 0.2s;
		align-items: flex-start;
	}

	.about-card:hover {
		background: #f0f0f0;
	}

	.about-image {
		width: 100px;
		height: 56px;
		border-radius: 4px;
		overflow: hidden;
		flex-shrink: 0;
		background: #ddd;
	}

	.about-image img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.about-placeholder {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		background: linear-gradient(135deg, #4a5568 0%, #2d3748 100%);
		font-size: 1.5rem;
	}

	.about-type {
		background: #e0e0e0;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
		font-size: 0.75rem;
	}

	.about-info {
		flex: 1;
		min-width: 0;
	}

	.about-info h3 {
		font-size: 0.95rem;
		font-weight: 600;
		margin-bottom: 0.25rem;
		line-height: 1.3;
	}

	.about-meta {
		display: flex;
		gap: 0.5rem;
		font-size: 0.8rem;
		color: #666;
		margin-bottom: 0.25rem;
	}


	.external-arrow {
		color: #999;
		font-size: 1.1rem;
		flex-shrink: 0;
	}

	.role-section {
		margin-bottom: 2rem;
	}

	.episodes-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: 1rem;
	}

	.episode-card {
		background: #f9f9f9;
		border-radius: 8px;
		overflow: hidden;
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s;
	}

	.episode-card:hover {
		transform: translateY(-2px);
	}

	.episode-image {
		aspect-ratio: 16/9;
		background: #eee;
	}

	.episode-image img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.episode-info {
		padding: 0.75rem;
	}

	.episode-info h3 {
		font-size: 0.95rem;
		font-weight: 600;
		margin-bottom: 0.25rem;
		line-height: 1.3;
	}

	.episode-info .year {
		display: inline-block;
		background: #e94560;
		color: white;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
		font-size: 0.75rem;
		margin-right: 0.5rem;
	}

	.episode-info .playwright,
	.play-info .playwright {
		display: block;
		font-size: 0.85rem;
		color: #666;
		margin-top: 0.25rem;
	}
</style>

<script lang="ts">
	import { page } from '$app/stores';
	import { getPerson, getDatabase, getNrkAboutPrograms } from '$lib/db';
	import type { Person, NrkAboutProgram } from '$lib/types';
	import { onMount } from 'svelte';

	interface WorkWritten {
		id: number;
		title: string;
		year_written: number | null;
		performance_count: number;
		image_url: string | null;
		work_type: string | null;
	}

	interface RoleGroup {
		role: string;
		performances: {
			id: number;
			work_id: number | null;
			work_title: string;
			image_url: string | null;
			year: number | null;
			playwright_name: string | null;
			character_name: string | null;
		}[];
	}

	let person: Person | null = null;
	let isCreator = false;
	let creatorRoles: string[] = [];

	// Creator stats
	let stats = {
		worksAsPlaywright: 0,
		worksAsComposer: 0,
		worksAsLibrettist: 0,
		performanceCount: 0
	};

	// Works written/composed by this person
	let worksWritten: WorkWritten[] = [];
	let worksComposed: WorkWritten[] = [];
	let librettos: WorkWritten[] = [];

	// Performances (for non-creators or additional roles)
	let performancesByRole: RoleGroup[] = [];

	// NRK programs about this person
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

				// Check if this person is a creator (playwright, composer, librettist)
				const creatorCheckStmt = db.prepare(`
					SELECT
						(SELECT COUNT(*) FROM works WHERE playwright_id = ?) as playwright_count,
						(SELECT COUNT(*) FROM works WHERE composer_id = ?) as composer_count,
						(SELECT COUNT(*) FROM works WHERE librettist_id = ?) as librettist_count
				`);
				creatorCheckStmt.bind([personId, personId, personId]);
				if (creatorCheckStmt.step()) {
					const counts = creatorCheckStmt.getAsObject() as {
						playwright_count: number;
						composer_count: number;
						librettist_count: number;
					};
					stats.worksAsPlaywright = counts.playwright_count;
					stats.worksAsComposer = counts.composer_count;
					stats.worksAsLibrettist = counts.librettist_count;

					if (counts.playwright_count > 0) creatorRoles.push('dramatiker');
					if (counts.composer_count > 0) creatorRoles.push('komponist');
					if (counts.librettist_count > 0) creatorRoles.push('librettist');

					isCreator = creatorRoles.length > 0;
				}
				creatorCheckStmt.free();

				// Get total performance count for works by this creator
				if (isCreator) {
					const perfCountStmt = db.prepare(`
						SELECT COUNT(DISTINCT p.id) as count
						FROM performances p
						JOIN works w ON p.work_id = w.id
						WHERE w.playwright_id = ? OR w.composer_id = ? OR w.librettist_id = ?
					`);
					perfCountStmt.bind([personId, personId, personId]);
					if (perfCountStmt.step()) {
						stats.performanceCount = (perfCountStmt.getAsObject() as { count: number }).count;
					}
					perfCountStmt.free();
				}

				// Get works where person is playwright
				if (stats.worksAsPlaywright > 0) {
					const playsStmt = db.prepare(`
						SELECT w.id, w.title, w.year_written, w.work_type,
							(SELECT COUNT(*) FROM performances pf WHERE pf.work_id = w.id) as performance_count,
							(SELECT e.image_url FROM episodes e
							 JOIN performances pf ON e.performance_id = pf.id
							 WHERE pf.work_id = w.id LIMIT 1) as image_url
						FROM works w
						WHERE w.playwright_id = ?
						ORDER BY w.year_written, w.title
					`);
					playsStmt.bind([personId]);
					worksWritten = [];
					while (playsStmt.step()) {
						worksWritten.push(playsStmt.getAsObject() as WorkWritten);
					}
					playsStmt.free();
				}

				// Get works where person is composer
				if (stats.worksAsComposer > 0) {
					const composerStmt = db.prepare(`
						SELECT w.id, w.title, w.year_written, w.work_type,
							(SELECT COUNT(*) FROM performances pf WHERE pf.work_id = w.id) as performance_count,
							(SELECT e.image_url FROM episodes e
							 JOIN performances pf ON e.performance_id = pf.id
							 WHERE pf.work_id = w.id LIMIT 1) as image_url
						FROM works w
						WHERE w.composer_id = ?
						ORDER BY w.year_written, w.title
					`);
					composerStmt.bind([personId]);
					worksComposed = [];
					while (composerStmt.step()) {
						worksComposed.push(composerStmt.getAsObject() as WorkWritten);
					}
					composerStmt.free();
				}

				// Get works where person is librettist
				if (stats.worksAsLibrettist > 0) {
					const librettoStmt = db.prepare(`
						SELECT w.id, w.title, w.year_written, w.work_type,
							(SELECT COUNT(*) FROM performances pf WHERE pf.work_id = w.id) as performance_count,
							(SELECT e.image_url FROM episodes e
							 JOIN performances pf ON e.performance_id = pf.id
							 WHERE pf.work_id = w.id LIMIT 1) as image_url
						FROM works w
						WHERE w.librettist_id = ?
						ORDER BY w.year_written, w.title
					`);
					librettoStmt.bind([personId]);
					librettos = [];
					while (librettoStmt.step()) {
						librettos.push(librettoStmt.getAsObject() as WorkWritten);
					}
					librettoStmt.free();
				}

				// Get performances by role (director, actor, etc.) - for both creators and non-creators
				const rolesStmt = db.prepare(`
					SELECT DISTINCT role FROM performance_persons
					WHERE person_id = ? AND role NOT IN ('playwright', 'composer', 'librettist')
				`);
				rolesStmt.bind([personId]);
				const roles: string[] = [];
				while (rolesStmt.step()) {
					roles.push(rolesStmt.getAsObject().role as string);
				}
				rolesStmt.free();

				performancesByRole = [];
				for (const role of roles) {
					const perfStmt = db.prepare(`
						SELECT DISTINCT
							p.id,
							p.work_id,
							COALESCE(w.title, p.title) as work_title,
							p.year,
							pw.name as playwright_name,
							pp.character_name,
							(SELECT e.image_url FROM episodes e WHERE e.performance_id = p.id LIMIT 1) as image_url
						FROM performances p
						JOIN performance_persons pp ON p.id = pp.performance_id
						LEFT JOIN works w ON p.work_id = w.id
						LEFT JOIN persons pw ON w.playwright_id = pw.id
						WHERE pp.person_id = ? AND pp.role = ?
						ORDER BY p.year DESC
					`);
					perfStmt.bind([personId, role]);
					const performances: RoleGroup['performances'] = [];
					while (perfStmt.step()) {
						performances.push(perfStmt.getAsObject() as RoleGroup['performances'][0]);
					}
					perfStmt.free();
					if (performances.length > 0) {
						performancesByRole.push({ role, performances });
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
			actor: 'Roller',
			playwright: 'Stykker',
			composer: 'Komponert',
			conductor: 'Dirigent',
			soloist: 'Solist',
			producer: 'Produsert',
			set_designer: 'Scenografi',
			costume_designer: 'Kostymer',
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
		if (!url) return '';
		if (url.includes('gfx.nrk.no')) {
			return url.replace(/\/\d+$/, `/${width}`);
		}
		return url;
	}
</script>

<svelte:head>
	{#if person}
		<title>{person.name} - Kulturbase.no</title>
	{/if}
</svelte:head>

{#if loading}
	<div class="loading">Laster...</div>
{:else if error}
	<div class="error">{error}</div>
{:else if person}
	<article class="person-detail">
		<a href="/" class="back-link">&larr; Tilbake</a>

		<header class="person-header">
			<div class="header-content">
				<div class="header-text">
					<h1>{person.name}</h1>
					{#if person.birth_year || person.death_year}
						<p class="years">{person.birth_year || '?'}–{person.death_year || ''}</p>
					{/if}

					{#if creatorRoles.length > 0}
						<div class="creator-roles">
							{#each creatorRoles as role}
								<span class="role-tag">{role}</span>
							{/each}
						</div>
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

		{#if isCreator}
			<!-- Creator stats -->
			<section class="creator-stats">
				<div class="stats-grid">
					{#if stats.worksAsPlaywright > 0}
						<div class="stat-item">
							<span class="stat-value">{stats.worksAsPlaywright}</span>
							<span class="stat-label">stykker</span>
						</div>
					{/if}
					{#if stats.worksAsComposer > 0}
						<div class="stat-item">
							<span class="stat-value">{stats.worksAsComposer}</span>
							<span class="stat-label">komposisjoner</span>
						</div>
					{/if}
					{#if stats.worksAsLibrettist > 0}
						<div class="stat-item">
							<span class="stat-value">{stats.worksAsLibrettist}</span>
							<span class="stat-label">librettoer</span>
						</div>
					{/if}
					<div class="stat-item">
						<span class="stat-value">{stats.performanceCount}</span>
						<span class="stat-label">opptak</span>
					</div>
				</div>
			</section>
		{/if}

		{#if worksWritten.length > 0}
			<section class="works-section">
				<h2>Stykker av {person.name} ({worksWritten.length})</h2>
				<div class="works-grid">
					{#each worksWritten as work}
						<a href="/work/{work.id}" class="work-card">
							<div class="work-image">
								{#if work.image_url}
									<img src={getImageUrl(work.image_url)} alt={work.title} loading="lazy" />
								{:else}
									<div class="work-placeholder">Teater</div>
								{/if}
							</div>
							<div class="work-info">
								<h3>{work.title}</h3>
								<div class="work-meta">
									{#if work.year_written}
										<span class="work-year">{work.year_written}</span>
									{/if}
									{#if work.performance_count > 0}
										<span class="work-count">{work.performance_count} opptak</span>
									{/if}
								</div>
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		{#if worksComposed.length > 0}
			<section class="works-section">
				<h2>Komponert ({worksComposed.length})</h2>
				<div class="works-grid">
					{#each worksComposed as work}
						<a href="/work/{work.id}" class="work-card">
							<div class="work-image">
								{#if work.image_url}
									<img src={getImageUrl(work.image_url)} alt={work.title} loading="lazy" />
								{:else}
									<div class="work-placeholder">Musikk</div>
								{/if}
							</div>
							<div class="work-info">
								<h3>{work.title}</h3>
								<div class="work-meta">
									{#if work.year_written}
										<span class="work-year">{work.year_written}</span>
									{/if}
									{#if work.performance_count > 0}
										<span class="work-count">{work.performance_count} opptak</span>
									{/if}
								</div>
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		{#if librettos.length > 0}
			<section class="works-section">
				<h2>Librettoer ({librettos.length})</h2>
				<div class="works-grid">
					{#each librettos as work}
						<a href="/work/{work.id}" class="work-card">
							<div class="work-image">
								{#if work.image_url}
									<img src={getImageUrl(work.image_url)} alt={work.title} loading="lazy" />
								{:else}
									<div class="work-placeholder">Opera</div>
								{/if}
							</div>
							<div class="work-info">
								<h3>{work.title}</h3>
								<div class="work-meta">
									{#if work.year_written}
										<span class="work-year">{work.year_written}</span>
									{/if}
									{#if work.performance_count > 0}
										<span class="work-count">{work.performance_count} opptak</span>
									{/if}
								</div>
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		{#if nrkAboutPrograms.length > 0}
			<section class="nrk-about">
				<h2>I NRK-arkivet (programmer om {person.name})</h2>
				<div class="about-programs-grid">
					{#each nrkAboutPrograms as program}
						<a href={program.nrk_url} target="_blank" rel="noopener" class="about-card">
							<div class="about-image">
								{#if program.image_url}
									<img src={program.image_url} alt={program.title} loading="lazy" />
								{:else}
									<div class="about-placeholder">NRK</div>
								{/if}
							</div>
							<div class="about-info">
								<h3>{program.title}</h3>
								<div class="about-meta">
									{#if program.program_type === 'serie'}
										<span class="about-type">Serie{#if program.episode_count} ({program.episode_count} ep){/if}</span>
									{/if}
									{#if program.duration_seconds}
										<span class="about-duration">{formatDuration(program.duration_seconds)}</span>
									{/if}
								</div>
							</div>
							<span class="external-arrow">NRK TV</span>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		{#each performancesByRole as group}
			<section class="role-section">
				<h2>{getRoleLabel(group.role)} ({group.performances.length})</h2>

				<div class="performances-grid">
					{#each group.performances as perf}
						<a href="/performance/{perf.id}" class="perf-card">
							<div class="perf-image">
								{#if perf.image_url}
									<img src={getImageUrl(perf.image_url)} alt={perf.work_title} loading="lazy" />
								{:else}
									<div class="perf-placeholder">Teater</div>
								{/if}
							</div>
							<div class="perf-info">
								<h3>{perf.work_title}</h3>
								{#if perf.character_name}
									<span class="character">som {perf.character_name}</span>
								{/if}
								<div class="perf-meta">
									{#if perf.year}
										<span class="perf-year">{perf.year}</span>
									{/if}
									{#if perf.playwright_name}
										<span class="playwright">{perf.playwright_name}</span>
									{/if}
								</div>
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/each}

		{#if !isCreator && performancesByRole.length === 0 && nrkAboutPrograms.length === 0}
			<div class="no-content">
				<p>Ingen opptak registrert for denne personen ennå.</p>
			</div>
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

	.creator-roles {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	.role-tag {
		background: #e94560;
		color: white;
		padding: 0.25rem 0.75rem;
		border-radius: 4px;
		font-size: 0.85rem;
		text-transform: capitalize;
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

	/* Creator stats */
	.creator-stats {
		background: #f8f9fa;
		border-radius: 8px;
		padding: 1.5rem;
		margin-bottom: 2rem;
	}

	.stats-grid {
		display: flex;
		justify-content: center;
		gap: 3rem;
	}

	.stat-item {
		display: flex;
		flex-direction: column;
		align-items: center;
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

	/* Works section */
	.works-section {
		margin-bottom: 2rem;
		padding-bottom: 1.5rem;
		border-bottom: 1px solid #eee;
	}

	.works-section h2, .role-section h2, .nrk-about h2 {
		font-size: 1.25rem;
		margin-bottom: 1rem;
	}

	.works-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 1rem;
	}

	.work-card {
		background: #f9f9f9;
		border-radius: 8px;
		overflow: hidden;
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.work-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
	}

	.work-image {
		aspect-ratio: 16/9;
		background: #eee;
	}

	.work-image img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.work-placeholder {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		background: linear-gradient(135deg, #1a1a2e, #16213e);
		color: rgba(255, 255, 255, 0.5);
		font-size: 0.9rem;
	}

	.work-info {
		padding: 0.75rem;
	}

	.work-info h3 {
		font-size: 0.95rem;
		font-weight: 600;
		margin-bottom: 0.5rem;
		line-height: 1.3;
	}

	.work-meta {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		flex-wrap: wrap;
	}

	.work-year {
		background: #e94560;
		color: white;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
		font-size: 0.75rem;
	}

	.work-count {
		font-size: 0.8rem;
		color: #666;
	}

	/* NRK About section */
	.nrk-about {
		margin-bottom: 2rem;
		padding-bottom: 1.5rem;
		border-bottom: 1px solid #eee;
	}

	.about-programs-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 0.75rem;
	}

	.about-card {
		display: flex;
		gap: 0.75rem;
		padding: 0.75rem;
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
		background: linear-gradient(135deg, #4a5568, #2d3748);
		color: rgba(255, 255, 255, 0.6);
		font-size: 0.8rem;
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
	}

	.about-type {
		background: #e0e0e0;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
		font-size: 0.75rem;
	}

	.external-arrow {
		color: #e94560;
		font-size: 0.8rem;
		flex-shrink: 0;
	}

	/* Role sections (performances) */
	.role-section {
		margin-bottom: 2rem;
	}

	.performances-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 1rem;
	}

	.perf-card {
		background: #f9f9f9;
		border-radius: 8px;
		overflow: hidden;
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.perf-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
	}

	.perf-image {
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

	.perf-info {
		padding: 0.75rem;
	}

	.perf-info h3 {
		font-size: 0.95rem;
		font-weight: 600;
		margin-bottom: 0.25rem;
		line-height: 1.3;
	}

	.character {
		display: block;
		font-size: 0.85rem;
		color: #e94560;
		font-style: italic;
		margin-bottom: 0.25rem;
	}

	.perf-meta {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		flex-wrap: wrap;
	}

	.perf-year {
		background: #1a1a2e;
		color: white;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
		font-size: 0.75rem;
	}

	.playwright {
		font-size: 0.8rem;
		color: #666;
	}

	.no-content {
		text-align: center;
		padding: 3rem;
		color: #666;
	}

	@media (max-width: 600px) {
		.stats-grid {
			flex-wrap: wrap;
			gap: 1.5rem;
		}

		.about-programs-grid {
			grid-template-columns: 1fr;
		}
	}
</style>

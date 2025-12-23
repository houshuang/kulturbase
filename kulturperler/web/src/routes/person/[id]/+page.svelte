<script lang="ts">
	import { page } from '$app/stores';
	import { getPerson, getDatabase, getNrkAboutPrograms, getWorksAsComposer, getComposerWorkCount, getComposerRoleLabel } from '$lib/db';
	import type { Person, NrkAboutProgram, ComposerRole } from '$lib/types';

	interface WorkWritten {
		id: number;
		title: string;
		year_written: number | null;
		performance_count: number;
		image_url: string | null;
		work_type: string | null;
		composer_role?: ComposerRole;
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

	interface RoleSummary {
		role: string;
		label: string;
		count: number;
	}

	let person: Person | null = null;
	let isCreator = false;
	let creatorRoles: string[] = [];
	let allRoles: RoleSummary[] = [];

	// Creator stats
	let stats = {
		worksAsPlaywright: 0,
		worksAsComposer: 0,
		worksAsLibrettist: 0,
		performanceCount: 0,
		directedCount: 0,
		actedCount: 0,
		conductedCount: 0
	};

	// Works written/composed by this person
	let worksWritten: WorkWritten[] = [];
	let worksComposed: WorkWritten[] = [];
	let librettos: WorkWritten[] = [];

	// Performances (for non-creators or additional roles)
	let performancesByRole: RoleGroup[] = [];

	// Track work IDs where this person is the creator (to avoid duplicates)
	let creatorWorkIds: Set<number> = new Set();

	// NRK programs about this person
	let nrkAboutPrograms: NrkAboutProgram[] = [];

	// Performances discussing this person (e.g., book programs about an author)
	interface PerformanceAbout {
		id: number;
		title: string;
		work_title: string;
		year: number | null;
		total_duration: number | null;
		image_url: string | null;
		medium: string | null;
		episode_count: number;
	}
	let performancesAbout: PerformanceAbout[] = [];

	// Individual episodes discussing this person
	interface EpisodeAbout {
		prf_id: string;
		title: string;
		perf_title: string;
		performance_id: number;
		year: number | null;
		duration_seconds: number | null;
		image_url: string | null;
		medium: string | null;
	}
	let episodesAbout: EpisodeAbout[] = [];

	let loading = true;
	let error: string | null = null;

	$: personId = parseInt($page.params.id || '0');
	$: if (personId) loadPerson();

	function loadPerson() {
		// Reset state for new person navigation
		loading = true;
		error = null;
		person = null;
		isCreator = false;
		creatorRoles = [];
		allRoles = [];
		stats = {
			worksAsPlaywright: 0,
			worksAsComposer: 0,
			worksAsLibrettist: 0,
			performanceCount: 0,
			directedCount: 0,
			actedCount: 0,
			conductedCount: 0
		};
		worksWritten = [];
		worksComposed = [];
		librettos = [];
		performancesByRole = [];
		creatorWorkIds = new Set();
		nrkAboutPrograms = [];
		performancesAbout = [];
		episodesAbout = [];

		try {
			person = getPerson(personId);
			if (person) {
				const db = getDatabase();

				// Check if this person is a creator (playwright, composer, librettist)
				const creatorCheckStmt = db.prepare(`
					SELECT
						(SELECT COUNT(*) FROM works WHERE playwright_id = ?) as playwright_count,
						(SELECT COUNT(DISTINCT work_id) FROM work_composers WHERE person_id = ?) as composer_count,
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
						LEFT JOIN work_composers wc ON w.id = wc.work_id
						WHERE w.playwright_id = ? OR wc.person_id = ? OR w.librettist_id = ?
					`);
					perfCountStmt.bind([personId, personId, personId]);
					if (perfCountStmt.step()) {
						stats.performanceCount = (perfCountStmt.getAsObject() as { count: number }).count;
					}
					perfCountStmt.free();
				}

				// Get works where person is playwright
				creatorWorkIds = new Set();
				if (stats.worksAsPlaywright > 0) {
					const playsStmt = db.prepare(`
						SELECT w.id, w.title, w.year_written, w.work_type,
							(SELECT COUNT(*) FROM performances pf WHERE pf.work_id = w.id) as performance_count,
							(SELECT e.image_url FROM episodes e
							 JOIN performances pf ON e.performance_id = pf.id
							 WHERE pf.work_id = w.id LIMIT 1) as image_url
						FROM works w
						WHERE w.playwright_id = ?
						ORDER BY performance_count DESC, w.title
					`);
					playsStmt.bind([personId]);
					worksWritten = [];
					while (playsStmt.step()) {
						const work = playsStmt.getAsObject() as WorkWritten;
						worksWritten.push(work);
						creatorWorkIds.add(work.id);
					}
					playsStmt.free();
				}

				// Get works where person is composer (using work_composers table)
				if (stats.worksAsComposer > 0) {
					const composerStmt = db.prepare(`
						SELECT w.id, w.title, w.year_written, w.work_type, wc.role as composer_role,
							(SELECT COUNT(*) FROM performances pf WHERE pf.work_id = w.id) as performance_count,
							(SELECT e.image_url FROM episodes e
							 JOIN performances pf ON e.performance_id = pf.id
							 WHERE pf.work_id = w.id LIMIT 1) as image_url
						FROM works w
						JOIN work_composers wc ON w.id = wc.work_id
						WHERE wc.person_id = ?
						ORDER BY performance_count DESC, w.title
					`);
					composerStmt.bind([personId]);
					worksComposed = [];
					while (composerStmt.step()) {
						const work = composerStmt.getAsObject() as WorkWritten;
						worksComposed.push(work);
						creatorWorkIds.add(work.id);
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
						ORDER BY performance_count DESC, w.title
					`);
					librettoStmt.bind([personId]);
					librettos = [];
					while (librettoStmt.step()) {
						const work = librettoStmt.getAsObject() as WorkWritten;
						librettos.push(work);
						creatorWorkIds.add(work.id);
					}
					librettoStmt.free();
				}

				// Get performances by role (director, actor, etc.) - for both creators and non-creators
				// Also exclude 'forfatter' (Norwegian for playwright) as it's redundant with the works section
				const rolesStmt = db.prepare(`
					SELECT DISTINCT role FROM performance_persons
					WHERE person_id = ? AND role NOT IN ('playwright', 'composer', 'librettist', 'forfatter')
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
						const perf = perfStmt.getAsObject() as RoleGroup['performances'][0];
						// Skip performances of works this person created (avoid duplicates)
						if (perf.work_id && creatorWorkIds.has(perf.work_id)) {
							continue;
						}
						performances.push(perf);
					}
					perfStmt.free();
					if (performances.length > 0) {
						performancesByRole.push({ role, performances });
					}
				}

				// Get NRK programs about this person
				nrkAboutPrograms = getNrkAboutPrograms(personId);

				// Get performances about this person (e.g., book programs discussing an author)
				const aboutStmt = db.prepare(`
					SELECT
						p.id,
						p.title,
						COALESCE(w.title, p.title) as work_title,
						p.year,
						p.total_duration,
						p.image_url,
						p.medium,
						(SELECT COUNT(*) FROM episodes e WHERE e.performance_id = p.id) as episode_count
					FROM performances p
					LEFT JOIN works w ON p.work_id = w.id
					WHERE p.about_person_id = ?
					ORDER BY p.year DESC
				`);
				aboutStmt.bind([personId]);
				performancesAbout = [];
				while (aboutStmt.step()) {
					performancesAbout.push(aboutStmt.getAsObject() as PerformanceAbout);
				}
				aboutStmt.free();

				// Get individual episodes about this person
				const episodesAboutStmt = db.prepare(`
					SELECT
						e.prf_id,
						e.title,
						p.title as perf_title,
						e.performance_id,
						e.year,
						e.duration_seconds,
						e.image_url,
						e.medium
					FROM episodes e
					LEFT JOIN performances p ON e.performance_id = p.id
					WHERE e.about_person_id = ?
					ORDER BY e.title
				`);
				episodesAboutStmt.bind([personId]);
				episodesAbout = [];
				while (episodesAboutStmt.step()) {
					episodesAbout.push(episodesAboutStmt.getAsObject() as EpisodeAbout);
				}
				episodesAboutStmt.free();

				// Build role summary for the header (use filtered counts)
				allRoles = [];
				if (stats.worksAsPlaywright > 0) {
					allRoles.push({ role: 'playwright', label: 'Dramatiker', count: stats.worksAsPlaywright });
				}
				if (stats.worksAsComposer > 0) {
					allRoles.push({ role: 'composer', label: 'Komponist', count: stats.worksAsComposer });
				}
				if (stats.worksAsLibrettist > 0) {
					allRoles.push({ role: 'librettist', label: 'Librettist', count: stats.worksAsLibrettist });
				}
				// Only add non-creator roles if they have performances not already shown
				for (const group of performancesByRole) {
					if (group.performances.length > 0) {
						allRoles.push({
							role: group.role,
							label: getRoleLabelNoun(group.role),
							count: group.performances.length
						});
					}
				}
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
			conductor: 'Dirigert',
			soloist: 'Solist',
			producer: 'Produsert',
			set_designer: 'Scenografi',
			costume_designer: 'Kostymer',
			other: 'Annet'
		};
		return labels[role] || role;
	}

	function getRoleLabelNoun(role: string): string {
		const labels: Record<string, string> = {
			director: 'Regissør',
			actor: 'Skuespiller',
			conductor: 'Dirigent',
			soloist: 'Solist',
			producer: 'Produsent',
			set_designer: 'Scenograf',
			costume_designer: 'Kostymedesigner',
			other: 'Medvirkende'
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
				{#if person.image_url}
					<div class="person-portrait">
						<img src={person.image_url} alt={person.name} />
					</div>
				{/if}
				<div class="header-text">
					<h1>{person.name}</h1>
					{#if person.birth_year || person.death_year}
						<p class="years">{person.birth_year || '?'}–{person.death_year || ''}</p>
					{/if}

					{#if allRoles.length > 0}
						<div class="all-roles">
							{#each allRoles as roleSummary}
								<span class="role-pill" class:creator={['playwright', 'composer', 'librettist'].includes(roleSummary.role)}>
									{roleSummary.label}
									<span class="role-count">{roleSummary.count}</span>
								</span>
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
						{#if person.bokselskap_url}
							<a href={person.bokselskap_url} target="_blank" rel="noopener" class="external-link">
								Bokselskap
							</a>
						{/if}
					</div>
				</div>
			</div>
		</header>

		{#if worksWritten.length > 0}
			<section class="works-section">
				<h2>Stykker av {person.name} ({worksWritten.length})</h2>
				<div class="works-grid">
					{#each worksWritten as work}
						<a href="/verk/{work.id}" class="work-card">
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
						<a href="/verk/{work.id}" class="work-card">
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
									{#if work.composer_role && work.composer_role !== 'composer'}
										<span class="composer-role">{getComposerRoleLabel(work.composer_role)}</span>
									{/if}
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
						<a href="/verk/{work.id}" class="work-card">
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

		{#if performancesAbout.length > 0 || episodesAbout.length > 0}
			<section class="nrk-about">
				<h2>Programmer om {person.name}</h2>
				<div class="about-grid">
					{#each performancesAbout as perf}
						<a href="/opptak/{perf.id}" class="about-card">
							<div class="about-image">
								{#if perf.image_url}
									<img src={getImageUrl(perf.image_url)} alt={perf.title} loading="lazy" />
								{:else}
									<div class="about-placeholder">{perf.medium === 'radio' ? 'Radio' : 'TV'}</div>
								{/if}
							</div>
							<div class="about-info">
								<h3>{perf.title}</h3>
								<div class="about-meta">
									{#if perf.episode_count > 1}
										<span class="about-badge">{perf.episode_count} episoder</span>
									{/if}
									{#if perf.total_duration}
										<span class="about-duration">{formatDuration(perf.total_duration)}</span>
									{/if}
									{#if perf.medium}
										<span class="medium-badge" class:radio={perf.medium === 'radio'}>
											{perf.medium === 'radio' ? 'Radio' : 'TV'}
										</span>
									{/if}
								</div>
							</div>
						</a>
					{/each}
					{#each episodesAbout as ep}
						<a href="/opptak/{ep.performance_id}" class="about-card">
							<div class="about-image">
								{#if ep.image_url}
									<img src={getImageUrl(ep.image_url)} alt={ep.title} loading="lazy" />
								{:else}
									<div class="about-placeholder">{ep.medium === 'radio' ? 'Radio' : 'TV'}</div>
								{/if}
							</div>
							<div class="about-info">
								<h3>{ep.title}</h3>
								<div class="about-meta">
									{#if ep.perf_title}
										<span class="about-badge">{ep.perf_title}</span>
									{/if}
									{#if ep.duration_seconds}
										<span class="about-duration">{formatDuration(ep.duration_seconds)}</span>
									{/if}
									{#if ep.medium}
										<span class="medium-badge" class:radio={ep.medium === 'radio'}>
											{ep.medium === 'radio' ? 'Radio' : 'TV'}
										</span>
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
				<h2>Om {person.name} i NRK-arkivet</h2>
				<div class="about-grid">
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
										<span class="about-badge">Serie ({program.episode_count} ep)</span>
									{/if}
									{#if program.duration_seconds}
										<span class="about-duration">{formatDuration(program.duration_seconds)}</span>
									{/if}
								</div>
							</div>
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
						<a href="/opptak/{perf.id}" class="perf-card">
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

		{#if allRoles.length === 0 && nrkAboutPrograms.length === 0}
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

	.person-portrait {
		width: 120px;
		height: 120px;
		border-radius: 50%;
		overflow: hidden;
		flex-shrink: 0;
		background: #eee;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
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

	.all-roles {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	.role-pill {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		background: #f0f0f0;
		color: #555;
		padding: 0.35rem 0.75rem;
		border-radius: 20px;
		font-size: 0.85rem;
	}

	.role-pill.creator {
		background: #e94560;
		color: white;
	}

	.role-count {
		background: rgba(0, 0, 0, 0.15);
		padding: 0.1rem 0.4rem;
		border-radius: 10px;
		font-size: 0.75rem;
		font-weight: 600;
	}

	.role-pill.creator .role-count {
		background: rgba(255, 255, 255, 0.25);
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

	.composer-role {
		background: #4a5568;
		color: white;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
		font-size: 0.75rem;
	}

	.work-count {
		font-size: 0.8rem;
		color: #666;
	}

	/* NRK About section - card grid */
	.nrk-about {
		margin-bottom: 2rem;
		padding-bottom: 1.5rem;
		border-bottom: 1px solid #eee;
	}

	.about-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: 1rem;
	}

	.about-card {
		display: flex;
		gap: 0.75rem;
		padding: 0.75rem;
		background: #f9f9f9;
		border-radius: 8px;
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.about-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
	}

	.about-image {
		width: 80px;
		height: 45px;
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
		font-size: 0.75rem;
	}

	.about-info {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		justify-content: center;
	}

	.about-info h3 {
		font-size: 0.9rem;
		font-weight: 600;
		margin-bottom: 0.25rem;
		line-height: 1.3;
	}

	.about-meta {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		font-size: 0.8rem;
		color: #666;
	}

	.about-badge {
		background: #e0e0e0;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
		font-size: 0.7rem;
	}

	.about-duration {
		font-size: 0.8rem;
	}

	.medium-badge {
		background: #e94560;
		color: white;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
		font-size: 0.7rem;
	}

	.medium-badge.radio {
		background: #6b5ce7;
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
		.about-programs-grid {
			grid-template-columns: 1fr;
		}
	}
</style>

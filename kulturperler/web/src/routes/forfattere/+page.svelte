<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getDb } from '$lib/db';
	import type { Person } from '$lib/types';

	interface CreatorWithStats extends Person {
		work_count: number;
		performance_count: number;
	}

	interface PersonWithPrograms extends Person {
		program_count: number;
	}

	type Tab = 'forfattere' | 'komponister' | 'personer';

	// Get tab from URL, default to 'forfattere'
	$: activeTab = ($page.url.searchParams.get('tab') as Tab) || 'forfattere';

	function setTab(tab: Tab) {
		goto(`?tab=${tab}`, { replaceState: false, keepFocus: true });
	}

	let playwrights: CreatorWithStats[] = [];
	let composers: CreatorWithStats[] = [];
	let personsWithPrograms: PersonWithPrograms[] = [];
	let loading = true;

	onMount(async () => {
		const db = getDb();
		if (!db) return;

		// Get playwrights (dramatikere)
		const playwrightResults = db.exec(`
			SELECT
				p.id,
				p.name,
				p.birth_year,
				p.death_year,
				p.nationality,
				p.bio,
				p.wikipedia_url,
				p.sceneweb_url,
				COUNT(DISTINCT w.id) as work_count,
				COUNT(DISTINCT perf.id) as performance_count
			FROM persons p
			JOIN works w ON w.playwright_id = p.id
			LEFT JOIN performances perf ON perf.work_id = w.id
			GROUP BY p.id
			ORDER BY work_count DESC, p.name
		`);

		if (playwrightResults.length > 0) {
			playwrights = playwrightResults[0].values.map((row: any[]) => ({
				id: row[0],
				name: row[1],
				normalized_name: null,
				birth_year: row[2],
				death_year: row[3],
				nationality: row[4],
				bio: row[5],
				wikipedia_url: row[6],
				sceneweb_url: row[7],
				wikidata_id: null,
				sceneweb_id: null,
				work_count: row[8] || 0,
				performance_count: row[9] || 0
			}));
		}

		// Get composers (komponister)
		const composerResults = db.exec(`
			SELECT
				p.id,
				p.name,
				p.birth_year,
				p.death_year,
				p.nationality,
				p.bio,
				p.wikipedia_url,
				p.sceneweb_url,
				COUNT(DISTINCT w.id) as work_count,
				COUNT(DISTINCT perf.id) as performance_count
			FROM persons p
			JOIN works w ON w.composer_id = p.id
			LEFT JOIN performances perf ON perf.work_id = w.id
			GROUP BY p.id
			ORDER BY work_count DESC, p.name
		`);

		if (composerResults.length > 0) {
			composers = composerResults[0].values.map((row: any[]) => ({
				id: row[0],
				name: row[1],
				normalized_name: null,
				birth_year: row[2],
				death_year: row[3],
				nationality: row[4],
				bio: row[5],
				wikipedia_url: row[6],
				sceneweb_url: row[7],
				wikidata_id: null,
				sceneweb_id: null,
				work_count: row[8] || 0,
				performance_count: row[9] || 0
			}));
		}

		// Get persons with programs about them (but no works)
		const programResults = db.exec(`
			SELECT
				p.id,
				p.name,
				p.birth_year,
				p.death_year,
				p.nationality,
				p.bio,
				p.wikipedia_url,
				p.sceneweb_url,
				COUNT(DISTINCT nap.id) as program_count
			FROM persons p
			JOIN nrk_about_programs nap ON nap.person_id = p.id
			WHERE p.id NOT IN (SELECT playwright_id FROM works WHERE playwright_id IS NOT NULL)
			  AND p.id NOT IN (SELECT composer_id FROM works WHERE composer_id IS NOT NULL)
			GROUP BY p.id
			ORDER BY program_count DESC, p.name
		`);

		if (programResults.length > 0) {
			personsWithPrograms = programResults[0].values.map((row: any[]) => ({
				id: row[0],
				name: row[1],
				normalized_name: null,
				birth_year: row[2],
				death_year: row[3],
				nationality: row[4],
				bio: row[5],
				wikipedia_url: row[6],
				sceneweb_url: row[7],
				wikidata_id: null,
				sceneweb_id: null,
				program_count: row[8] || 0
			}));
		}

		loading = false;
	});

	function formatLifespan(birth: number | null, death: number | null): string {
		if (!birth && !death) return '';
		if (birth && death) return `${birth}–${death}`;
		if (birth) return `f. ${birth}`;
		return `d. ${death}`;
	}
</script>

<svelte:head>
	<title>Personer | Kulturbase.no</title>
</svelte:head>

<div class="forfattere-page">
	<header class="page-header">
		<h1>Personer</h1>
		<p class="subtitle">Forfattere, komponister og kulturpersonligheter</p>
	</header>

	<div class="tabs">
		<button
			class="tab"
			class:active={activeTab === 'forfattere'}
			on:click={() => setTab('forfattere')}
		>
			Forfattere med teaterstykker ({playwrights.length})
		</button>
		<button
			class="tab"
			class:active={activeTab === 'komponister'}
			on:click={() => setTab('komponister')}
		>
			Komponister ({composers.length})
		</button>
		<button
			class="tab"
			class:active={activeTab === 'personer'}
			on:click={() => setTab('personer')}
		>
			Forfattere vi har program om ({personsWithPrograms.length})
		</button>
	</div>

	{#if loading}
		<div class="loading">Laster...</div>
	{:else}
		{#if activeTab === 'forfattere'}
			<p class="tab-description">Dramatikere og forfattere med teaterstykker i arkivet</p>
			<div class="creators-grid">
				{#each playwrights as creator}
					<a href="/person/{creator.id}" class="creator-card">
						<div class="creator-info">
							<h3>{creator.name}</h3>
							{#if creator.birth_year || creator.death_year}
								<p class="lifespan">{formatLifespan(creator.birth_year, creator.death_year)}</p>
							{/if}
						</div>
						<div class="creator-stats">
							<div class="stat-item">
								<span class="stat-value">{creator.work_count}</span>
								<span class="stat-label">verk</span>
							</div>
							<div class="stat-item">
								<span class="stat-value">{creator.performance_count}</span>
								<span class="stat-label">opptak</span>
							</div>
						</div>
					</a>
				{/each}
			</div>
		{:else if activeTab === 'komponister'}
			<p class="tab-description">Komponister med opera, ballett eller konserter i arkivet</p>
			<div class="creators-grid">
				{#each composers as creator}
					<a href="/person/{creator.id}" class="creator-card">
						<div class="creator-info">
							<h3>{creator.name}</h3>
							{#if creator.birth_year || creator.death_year}
								<p class="lifespan">{formatLifespan(creator.birth_year, creator.death_year)}</p>
							{/if}
						</div>
						<div class="creator-stats">
							<div class="stat-item">
								<span class="stat-value">{creator.work_count}</span>
								<span class="stat-label">verk</span>
							</div>
							<div class="stat-item">
								<span class="stat-value">{creator.performance_count}</span>
								<span class="stat-label">opptak</span>
							</div>
						</div>
					</a>
				{/each}
			</div>
		{:else}
			<p class="tab-description">Personer med dokumentarer eller programmer om dem i NRK</p>
			<div class="creators-grid">
				{#each personsWithPrograms as person}
					<a href="/person/{person.id}" class="creator-card">
						<div class="creator-info">
							<h3>{person.name}</h3>
							{#if person.birth_year || person.death_year}
								<p class="lifespan">{formatLifespan(person.birth_year, person.death_year)}</p>
							{/if}
						</div>
						<div class="creator-stats">
							<div class="stat-item">
								<span class="stat-value">{person.program_count}</span>
								<span class="stat-label">{person.program_count === 1 ? 'program' : 'programmer'}</span>
							</div>
						</div>
					</a>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<style>
	.forfattere-page {
		max-width: 1400px;
		margin: 0 auto;
	}

	.page-header {
		margin-bottom: 1.5rem;
	}

	.page-header h1 {
		font-size: 2rem;
		margin-bottom: 0.5rem;
	}

	.subtitle {
		color: #666;
		font-size: 1.1rem;
	}

	.tabs {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 1rem;
		border-bottom: 2px solid #eee;
		padding-bottom: 0;
	}

	.tab {
		padding: 0.75rem 1.5rem;
		border: none;
		background: none;
		cursor: pointer;
		font-size: 1rem;
		font-weight: 500;
		color: #666;
		border-bottom: 3px solid transparent;
		margin-bottom: -2px;
		transition: all 0.15s;
	}

	.tab:hover {
		color: #333;
	}

	.tab.active {
		color: #e94560;
		border-bottom-color: #e94560;
	}

	.tab-description {
		color: #666;
		margin-bottom: 1.5rem;
		font-size: 0.95rem;
	}

	.loading {
		text-align: center;
		padding: 4rem;
		color: #666;
	}

	.creators-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 1rem;
	}

	.creator-card {
		background: white;
		border-radius: 8px;
		padding: 1.25rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
	}

	.creator-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
	}

	.creator-info h3 {
		font-size: 1.1rem;
		margin-bottom: 0.25rem;
	}

	.lifespan {
		color: #666;
		font-size: 0.9rem;
		margin: 0;
	}

	.creator-stats {
		display: flex;
		gap: 1rem;
		text-align: center;
	}

	.stat-item {
		display: flex;
		flex-direction: column;
	}

	.stat-value {
		font-size: 1.25rem;
		font-weight: bold;
		color: #1a1a2e;
	}

	.stat-label {
		font-size: 0.7rem;
		color: #888;
		text-transform: uppercase;
	}

	@media (max-width: 600px) {
		.tabs {
			flex-wrap: wrap;
		}

		.tab {
			padding: 0.5rem 1rem;
			font-size: 0.9rem;
		}
	}
</style>

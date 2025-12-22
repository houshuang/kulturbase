<script lang="ts">
	import { onMount } from 'svelte';
	import { getDb } from '$lib/db';
	import type { Person } from '$lib/types';

	interface CreatorWithStats extends Person {
		work_count: number;
		performance_count: number;
		roles: string[];
	}

	let creators: CreatorWithStats[] = [];
	let loading = true;
	let roleFilter = '';

	// Count how many creators exist for each role (to show/hide filter buttons)
	let roleCounts = {
		dramatiker: 0,
		komponist: 0,
		librettist: 0
	};

	onMount(async () => {
		const db = getDb();
		if (!db) return;

		// Get creators (playwrights, composers, librettists) with their work counts
		const results = db.exec(`
			SELECT
				p.id,
				p.name,
				p.birth_year,
				p.death_year,
				p.nationality,
				p.bio,
				p.wikipedia_url,
				p.sceneweb_url,
				COUNT(DISTINCT w_playwright.id) as playwright_works,
				COUNT(DISTINCT w_composer.id) as composer_works,
				COUNT(DISTINCT w_librettist.id) as librettist_works,
				COUNT(DISTINCT perf.id) as performance_count
			FROM persons p
			LEFT JOIN works w_playwright ON w_playwright.playwright_id = p.id
			LEFT JOIN works w_composer ON w_composer.composer_id = p.id
			LEFT JOIN works w_librettist ON w_librettist.librettist_id = p.id
			LEFT JOIN performances perf ON perf.work_id IN (
				SELECT id FROM works WHERE playwright_id = p.id
				OR composer_id = p.id
				OR librettist_id = p.id
			)
			WHERE w_playwright.id IS NOT NULL
			   OR w_composer.id IS NOT NULL
			   OR w_librettist.id IS NOT NULL
			GROUP BY p.id
			ORDER BY (
				COUNT(DISTINCT w_playwright.id) +
				COUNT(DISTINCT w_composer.id) +
				COUNT(DISTINCT w_librettist.id)
			) DESC, p.name
		`);

		if (results.length > 0) {
			creators = results[0].values.map((row: any[]) => {
				const roles: string[] = [];
				if (row[8] > 0) {
					roles.push('dramatiker');
					roleCounts.dramatiker++;
				}
				if (row[9] > 0) {
					roles.push('komponist');
					roleCounts.komponist++;
				}
				if (row[10] > 0) {
					roles.push('librettist');
					roleCounts.librettist++;
				}

				return {
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
					work_count: (row[8] || 0) + (row[9] || 0) + (row[10] || 0),
					performance_count: row[11] || 0,
					roles
				};
			});
		}

		loading = false;
	});

	$: filteredCreators = roleFilter
		? creators.filter(c => c.roles.includes(roleFilter))
		: creators;

	$: hasMultipleRoles = (roleCounts.dramatiker > 0 ? 1 : 0) + (roleCounts.komponist > 0 ? 1 : 0) + (roleCounts.librettist > 0 ? 1 : 0) > 1;

	function formatLifespan(birth: number | null, death: number | null): string {
		if (!birth && !death) return '';
		if (birth && death) return `${birth}–${death}`;
		if (birth) return `f. ${birth}`;
		return `d. ${death}`;
	}
</script>

<svelte:head>
	<title>Skapere | Kulturbase.no</title>
</svelte:head>

<div class="skapere-page">
	<header class="page-header">
		<h1>Skapere</h1>
		<p class="subtitle">Dramatikere med verk i arkivet</p>
	</header>

	{#if loading}
		<div class="loading">Laster skapere...</div>
	{:else}
		{#if hasMultipleRoles}
			<div class="filters">
				<div class="filter-group">
					<span class="filter-label">Rolle</span>
					<div class="filter-buttons">
						<button
							class:active={roleFilter === ''}
							on:click={() => roleFilter = ''}
						>
							Alle ({creators.length})
						</button>
						{#if roleCounts.dramatiker > 0}
							<button
								class:active={roleFilter === 'dramatiker'}
								on:click={() => roleFilter = 'dramatiker'}
							>
								Dramatikere ({roleCounts.dramatiker})
							</button>
						{/if}
						{#if roleCounts.komponist > 0}
							<button
								class:active={roleFilter === 'komponist'}
								on:click={() => roleFilter = 'komponist'}
							>
								Komponister ({roleCounts.komponist})
							</button>
						{/if}
						{#if roleCounts.librettist > 0}
							<button
								class:active={roleFilter === 'librettist'}
								on:click={() => roleFilter = 'librettist'}
							>
								Librettister ({roleCounts.librettist})
							</button>
						{/if}
					</div>
				</div>
			</div>
		{/if}

		<div class="stats">
			<span class="stat">{filteredCreators.length} skapere</span>
		</div>

		<div class="creators-grid">
			{#each filteredCreators as creator}
				<a href="/person/{creator.id}" class="creator-card">
					<div class="creator-info">
						<h3>{creator.name}</h3>
						{#if creator.birth_year || creator.death_year}
							<p class="lifespan">{formatLifespan(creator.birth_year, creator.death_year)}</p>
						{/if}
						<div class="roles">
							{#each creator.roles as role}
								<span class="role-tag">{role}</span>
							{/each}
						</div>
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
	{/if}
</div>

<style>
	.skapere-page {
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

	.filters {
		background: white;
		padding: 1rem;
		border-radius: 8px;
		margin-bottom: 1.5rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.filter-group {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.filter-label {
		font-weight: 500;
		color: #333;
	}

	.filter-buttons {
		display: flex;
		gap: 0.5rem;
	}

	.filter-buttons button {
		padding: 0.5rem 1rem;
		border: 1px solid #ddd;
		background: white;
		border-radius: 6px;
		cursor: pointer;
		font-size: 0.9rem;
		transition: all 0.15s;
	}

	.filter-buttons button:hover {
		border-color: #e94560;
	}

	.filter-buttons button.active {
		background: #e94560;
		color: white;
		border-color: #e94560;
	}

	.stats {
		margin-bottom: 1.5rem;
		color: #666;
	}

	.stat {
		background: #e8e8e8;
		padding: 0.25rem 0.75rem;
		border-radius: 4px;
		font-size: 0.9rem;
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
		margin-bottom: 0.5rem;
	}

	.roles {
		display: flex;
		gap: 0.4rem;
		flex-wrap: wrap;
	}

	.role-tag {
		background: #f0f0f0;
		padding: 0.15rem 0.5rem;
		border-radius: 4px;
		font-size: 0.75rem;
		color: #666;
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
</style>

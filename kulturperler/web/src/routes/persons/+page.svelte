<script lang="ts">
	import { getAllPlaywrights, getNationalities, type PlaywrightWithDetails } from '$lib/db';
	import { onMount } from 'svelte';

	let allPlaywrights: PlaywrightWithDetails[] = [];
	let nationalities: string[] = [];
	let loading = true;

	// Filters
	let searchQuery = '';
	let selectedNationality = '';
	let sortBy: 'name' | 'plays' | 'birth' = 'plays';
	let sortDirection: 'asc' | 'desc' = 'desc';

	// Timeline
	let showTimeline = false;
	let timelineMin = 1800;
	let timelineMax = 2000;

	$: filteredPlaywrights = filterAndSort(allPlaywrights, searchQuery, selectedNationality, sortBy, sortDirection);

	$: {
		if (allPlaywrights.length > 0) {
			const birthYears = allPlaywrights.filter(p => p.birth_year).map(p => p.birth_year!);
			if (birthYears.length > 0) {
				timelineMin = Math.floor(Math.min(...birthYears) / 10) * 10;
				timelineMax = Math.ceil(Math.max(...birthYears) / 10) * 10;
			}
		}
	}

	onMount(() => {
		try {
			allPlaywrights = getAllPlaywrights();
			nationalities = getNationalities();
			loading = false;
		} catch (e) {
			console.error('Failed to load playwrights:', e);
			loading = false;
		}
	});

	function filterAndSort(
		playwrights: PlaywrightWithDetails[],
		query: string,
		nationality: string,
		sort: string,
		direction: string
	): PlaywrightWithDetails[] {
		let result = [...playwrights];

		// Filter by search query
		if (query) {
			const lowerQuery = query.toLowerCase();
			result = result.filter(p => p.name.toLowerCase().includes(lowerQuery));
		}

		// Filter by nationality
		if (nationality) {
			result = result.filter(p => p.nationality === nationality);
		}

		// Sort
		result.sort((a, b) => {
			let cmp = 0;
			if (sort === 'name') {
				cmp = a.name.localeCompare(b.name, 'no');
			} else if (sort === 'plays') {
				cmp = a.performance_count - b.performance_count;
			} else if (sort === 'birth') {
				const aYear = a.birth_year || 0;
				const bYear = b.birth_year || 0;
				cmp = aYear - bYear;
			}
			return direction === 'desc' ? -cmp : cmp;
		});

		return result;
	}

	function toggleSort(newSort: 'name' | 'plays' | 'birth') {
		if (sortBy === newSort) {
			sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
		} else {
			sortBy = newSort;
			sortDirection = newSort === 'name' ? 'asc' : 'desc';
		}
	}

	function getTimelinePosition(year: number | null): number {
		if (!year) return -1;
		return ((year - timelineMin) / (timelineMax - timelineMin)) * 100;
	}

	function getDecades(): number[] {
		const decades: number[] = [];
		for (let d = timelineMin; d <= timelineMax; d += 10) {
			decades.push(d);
		}
		return decades;
	}

	function getPlaywrightsInDecade(decade: number): PlaywrightWithDetails[] {
		return filteredPlaywrights.filter(p =>
			p.birth_year && p.birth_year >= decade && p.birth_year < decade + 10
		);
	}

	function getNationalityLabel(nationality: string | null): string {
		if (!nationality) return '';
		const labels: Record<string, string> = {
			'NO': 'Norge',
			'SE': 'Sverige',
			'DK': 'Danmark',
			'GB': 'Storbritannia',
			'US': 'USA',
			'DE': 'Tyskland',
			'FR': 'Frankrike',
			'RU': 'Russland',
			'IT': 'Italia',
			'ES': 'Spania',
			'IE': 'Irland',
			'AT': 'Østerrike',
			'CH': 'Sveits',
			'BE': 'Belgia',
			'NL': 'Nederland',
			'CZ': 'Tsjekkia',
			'PL': 'Polen',
			'GR': 'Hellas',
			'FI': 'Finland'
		};
		return labels[nationality] || nationality;
	}
</script>

<svelte:head>
	<title>Dramatikere - Kulturperler</title>
</svelte:head>

<div class="persons-page">
	<header class="page-header">
		<a href="/" class="back-link">&larr; Tilbake</a>
		<h1>Dramatikere</h1>
		<p class="subtitle">{filteredPlaywrights.length} av {allPlaywrights.length} dramatikere</p>
	</header>

	{#if loading}
		<div class="loading">Laster...</div>
	{:else}
		<div class="controls">
			<div class="filters">
				<div class="filter-group">
					<input
						type="search"
						bind:value={searchQuery}
						placeholder="Sok etter navn..."
						class="search-input"
					/>
				</div>

				<div class="filter-group">
					<select bind:value={selectedNationality} class="nationality-select">
						<option value="">Alle land</option>
						{#each nationalities as nat}
							<option value={nat}>{getNationalityLabel(nat)}</option>
						{/each}
					</select>
				</div>
			</div>

			<div class="view-controls">
				<div class="sort-buttons">
					<button
						class:active={sortBy === 'plays'}
						on:click={() => toggleSort('plays')}
					>
						Antall opptak {sortBy === 'plays' ? (sortDirection === 'desc' ? '↓' : '↑') : ''}
					</button>
					<button
						class:active={sortBy === 'name'}
						on:click={() => toggleSort('name')}
					>
						Navn {sortBy === 'name' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
					</button>
					<button
						class:active={sortBy === 'birth'}
						on:click={() => toggleSort('birth')}
					>
						Fodt {sortBy === 'birth' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
					</button>
				</div>

				<button
					class="timeline-toggle"
					class:active={showTimeline}
					on:click={() => showTimeline = !showTimeline}
				>
					Tidslinje
				</button>
			</div>
		</div>

		{#if showTimeline}
			<div class="timeline-view">
				<div class="timeline-decades">
					{#each getDecades() as decade}
						<div class="decade-column">
							<div class="decade-label">{decade}</div>
							<div class="decade-persons">
								{#each getPlaywrightsInDecade(decade) as person}
									<a href="/person/{person.id}" class="timeline-person" title="{person.name} ({person.birth_year})">
										<div class="person-placeholder">{person.name.charAt(0)}</div>
										<span class="person-name">{person.name}</span>
									</a>
								{/each}
							</div>
						</div>
					{/each}
				</div>
			</div>
		{:else}
			<div class="persons-grid">
				{#each filteredPlaywrights as person}
					<a href="/person/{person.id}" class="person-card">
						<div class="person-info">
							<h3>{person.name}</h3>
							<div class="person-meta">
								{#if person.birth_year || person.death_year}
									<span class="years">{person.birth_year || '?'}–{person.death_year || ''}</span>
								{/if}
								{#if person.nationality}
									<span class="nationality">{getNationalityLabel(person.nationality)}</span>
								{/if}
							</div>
							<div class="person-stats">
								<span class="stat">{person.play_count} stykker</span>
								<span class="stat">{person.performance_count} opptak</span>
							</div>
						</div>
					</a>
				{/each}
			</div>
		{/if}

		{#if filteredPlaywrights.length === 0 && !loading}
			<div class="no-results">
				<p>Ingen dramatikere funnet med disse filtrene.</p>
			</div>
		{/if}
	{/if}
</div>

<style>
	.persons-page {
		max-width: 1400px;
		margin: 0 auto;
	}

	.page-header {
		margin-bottom: 2rem;
	}

	.back-link {
		display: inline-block;
		margin-bottom: 1rem;
		color: #666;
		text-decoration: none;
	}

	.back-link:hover {
		color: #e94560;
	}

	h1 {
		font-size: 2rem;
		margin-bottom: 0.5rem;
	}

	.subtitle {
		color: #666;
		font-size: 1rem;
	}

	.loading {
		text-align: center;
		padding: 4rem;
		color: #666;
	}

	.controls {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 2rem;
		padding: 1rem;
		background: white;
		border-radius: 8px;
		box-shadow: 0 1px 3px rgba(0,0,0,0.1);
	}

	.filters {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
	}

	.filter-group {
		display: flex;
		gap: 0.5rem;
	}

	.search-input {
		padding: 0.5rem 1rem;
		border: 1px solid #ddd;
		border-radius: 4px;
		font-size: 0.95rem;
		min-width: 200px;
	}

	.nationality-select {
		padding: 0.5rem 1rem;
		border: 1px solid #ddd;
		border-radius: 4px;
		font-size: 0.95rem;
		background: white;
	}

	.view-controls {
		display: flex;
		gap: 1rem;
		align-items: center;
	}

	.sort-buttons {
		display: flex;
		gap: 0.25rem;
	}

	.sort-buttons button,
	.timeline-toggle {
		padding: 0.5rem 0.75rem;
		border: 1px solid #ddd;
		background: white;
		cursor: pointer;
		font-size: 0.85rem;
		transition: all 0.15s;
	}

	.sort-buttons button:first-child {
		border-radius: 4px 0 0 4px;
	}

	.sort-buttons button:last-child {
		border-radius: 0 4px 4px 0;
	}

	.sort-buttons button:not(:last-child) {
		border-right: none;
	}

	.sort-buttons button.active,
	.timeline-toggle.active {
		background: #e94560;
		color: white;
		border-color: #e94560;
	}

	.timeline-toggle {
		border-radius: 4px;
	}

	/* Grid view */
	.persons-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: 1.5rem;
	}

	.person-card {
		display: flex;
		gap: 1rem;
		padding: 1rem;
		background: white;
		border-radius: 8px;
		box-shadow: 0 1px 3px rgba(0,0,0,0.1);
		text-decoration: none;
		color: inherit;
		transition: transform 0.15s, box-shadow 0.15s;
	}

	.person-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0,0,0,0.15);
	}

	.person-image {
		width: 80px;
		height: 80px;
		border-radius: 50%;
		overflow: hidden;
		flex-shrink: 0;
		background: #f0f0f0;
	}

	.person-image img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.image-placeholder {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		background: linear-gradient(135deg, #667 0%, #445 100%);
		color: white;
		font-size: 2rem;
		font-weight: 600;
	}

	.person-info {
		flex: 1;
		min-width: 0;
	}

	.person-info h3 {
		font-size: 1rem;
		font-weight: 600;
		margin-bottom: 0.25rem;
		color: #e94560;
	}

	.person-meta {
		display: flex;
		gap: 0.75rem;
		font-size: 0.85rem;
		color: #666;
		margin-bottom: 0.5rem;
	}

	.years {
		white-space: nowrap;
	}

	.nationality {
		color: #888;
	}

	.person-stats {
		display: flex;
		gap: 1rem;
	}

	.stat {
		font-size: 0.8rem;
		color: #888;
		background: #f5f5f5;
		padding: 0.2rem 0.5rem;
		border-radius: 3px;
	}

	/* Timeline view */
	.timeline-view {
		background: white;
		border-radius: 8px;
		padding: 1.5rem;
		box-shadow: 0 1px 3px rgba(0,0,0,0.1);
		overflow-x: auto;
	}

	.timeline-decades {
		display: flex;
		gap: 0;
		min-width: max-content;
	}

	.decade-column {
		min-width: 120px;
		border-left: 1px solid #eee;
		padding: 0 0.5rem;
	}

	.decade-column:first-child {
		border-left: none;
	}

	.decade-label {
		font-weight: 600;
		font-size: 0.9rem;
		color: #666;
		padding-bottom: 0.75rem;
		border-bottom: 2px solid #e94560;
		margin-bottom: 0.75rem;
	}

	.decade-persons {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.timeline-person {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.25rem;
		border-radius: 4px;
		text-decoration: none;
		color: inherit;
		transition: background 0.15s;
	}

	.timeline-person:hover {
		background: #f5f5f5;
	}

	.timeline-person img {
		width: 32px;
		height: 32px;
		border-radius: 50%;
		object-fit: cover;
	}

	.person-placeholder {
		width: 32px;
		height: 32px;
		border-radius: 50%;
		background: linear-gradient(135deg, #667 0%, #445 100%);
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.85rem;
		font-weight: 600;
	}

	.timeline-person .person-name {
		font-size: 0.85rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 80px;
	}

	.no-results {
		text-align: center;
		padding: 4rem;
		color: #666;
	}

	@media (max-width: 768px) {
		.controls {
			flex-direction: column;
			align-items: stretch;
		}

		.filters {
			flex-direction: column;
		}

		.search-input {
			min-width: 100%;
		}

		.view-controls {
			flex-wrap: wrap;
		}

		.persons-grid {
			grid-template-columns: 1fr;
		}

		.person-card {
			flex-direction: column;
			align-items: center;
			text-align: center;
		}

		.person-meta {
			justify-content: center;
		}

		.person-stats {
			justify-content: center;
		}
	}
</style>

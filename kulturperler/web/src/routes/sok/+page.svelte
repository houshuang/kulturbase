<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { searchAll, type SearchAllResults } from '$lib/db';

	let results: SearchAllResults = { persons: [], works: [], performances: [] };
	let loading = true;
	let searchQuery = '';
	let inputValue = '';
	let inputElement: HTMLInputElement;
	let debounceTimer: ReturnType<typeof setTimeout>;

	$: query = $page.url.searchParams.get('q') || '';

	// Sync inputValue with URL query on initial load and URL changes
	$: if (query !== searchQuery) {
		searchQuery = query;
		inputValue = query;
		performSearch();
	}

	function handleInput() {
		clearTimeout(debounceTimer);
		const trimmed = inputValue.trim();

		if (trimmed.length < 2) {
			if (trimmed.length === 0 && searchQuery) {
				// Clear search
				goto('/sok', { replaceState: true, keepFocus: true });
			}
			return;
		}

		loading = true;

		debounceTimer = setTimeout(() => {
			goto(`/sok?q=${encodeURIComponent(trimmed)}`, { replaceState: true, keepFocus: true });
		}, 400);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && inputValue.trim()) {
			clearTimeout(debounceTimer);
			goto(`/sok?q=${encodeURIComponent(inputValue.trim())}`, { replaceState: true, keepFocus: true });
		} else if (e.key === 'Escape') {
			inputElement?.blur();
		}
	}

	function performSearch() {
		if (!searchQuery.trim()) {
			results = { persons: [], works: [], performances: [] };
			loading = false;
			return;
		}

		loading = true;
		try {
			results = searchAll(searchQuery.trim(), 20);
		} catch {
			results = { persons: [], works: [], performances: [] };
		}
		loading = false;
	}

	onMount(() => {
		if (query) {
			inputValue = query;
			performSearch();
		} else {
			loading = false;
		}
		// Auto-focus search input
		inputElement?.focus();
	});

	function formatDuration(seconds: number | null): string {
		if (!seconds) return '';
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		if (hours > 0) return `${hours}t ${minutes}m`;
		return `${minutes}m`;
	}

	function formatYears(birth: number | null, death: number | null): string {
		if (!birth) return '';
		return death ? `${birth}–${death}` : `f. ${birth}`;
	}

	function getTotalCount(): number {
		return results.persons.length + results.works.length + results.performances.length;
	}
</script>

<svelte:head>
	<title>{query ? `Søk: ${query}` : 'Søk'} | Kulturbase.no</title>
</svelte:head>

<div class="search-page">
	<header class="page-header">
		<div class="search-container">
			<input
				bind:this={inputElement}
				bind:value={inputValue}
				on:input={handleInput}
				on:keydown={handleKeydown}
				type="text"
				placeholder="Søk etter stykker, personer..."
				autocomplete="off"
				aria-label="Søk"
			/>
		</div>
	</header>

	{#if loading}
		<div class="loading">Søker...</div>
	{:else if !query}
		<div class="empty-state">
			<p>Søk etter stykker, personer og opptak i arkivet.</p>
		</div>
	{:else if getTotalCount() === 0}
		<div class="empty-state">
			<p>Ingen resultater funnet for «{query}».</p>
			<p class="hint">Prøv å søke etter et annet ord, eller sjekk stavemåten.</p>
		</div>
	{:else}
		<div class="results-summary">
			<span class="total">{getTotalCount()} resultater</span>
			{#if results.persons.length > 0}
				<span class="count">{results.persons.length} personer</span>
			{/if}
			{#if results.works.length > 0}
				<span class="count">{results.works.length} verk</span>
			{/if}
			{#if results.performances.length > 0}
				<span class="count">{results.performances.length} opptak</span>
			{/if}
		</div>

		<!-- Persons Section -->
		{#if results.persons.length > 0}
			<section class="results-section">
				<h2>Personer ({results.persons.length})</h2>
				<div class="persons-list">
					{#each results.persons as person}
						<a href="/person/{person.id}" class="person-card">
							<div class="person-avatar">
								{person.name.charAt(0)}
							</div>
							<div class="person-info">
								<h3>{person.name}</h3>
								<div class="person-meta">
									{#if person.birth_year}
										<span class="years">{formatYears(person.birth_year, person.death_year)}</span>
									{/if}
									{#if person.nationality}
										<span class="nationality">{person.nationality}</span>
									{/if}
								</div>
								<div class="person-stats">
									{#if person.work_count > 0}
										<span>{person.work_count} verk</span>
									{/if}
									{#if person.performance_count > 0}
										<span>{person.performance_count} opptak</span>
									{/if}
								</div>
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Works Section -->
		{#if results.works.length > 0}
			<section class="results-section">
				<h2>Verk ({results.works.length})</h2>
				<div class="works-grid">
					{#each results.works as work}
						<a href="/verk/{work.id}" class="work-card">
							<div class="card-image">
								{#if work.image_url}
									<img src={work.image_url} alt={work.title} />
								{:else}
									<div class="no-image">
										{work.category === 'konsert' ? 'Konsert' : 'Verk'}
									</div>
								{/if}
								{#if work.language && work.language !== 'no'}
									<span class="lang-badge">{work.language === 'sv' ? 'Svensk' : work.language === 'da' ? 'Dansk' : work.language}</span>
								{/if}
							</div>
							<div class="card-content">
								<h3>{work.title}</h3>
								{#if work.playwright_name}
									<p class="creator">{work.playwright_name}</p>
								{:else if work.composer_name}
									<p class="creator">{work.composer_name}</p>
								{/if}
								<div class="meta">
									{#if work.year_written}
										<span class="year">{work.year_written}</span>
									{/if}
									{#if work.performance_count > 0}
										<span class="badge">{work.performance_count} opptak</span>
									{/if}
								</div>
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Performances Section -->
		{#if results.performances.length > 0}
			<section class="results-section">
				<h2>Opptak ({results.performances.length})</h2>
				<div class="performances-grid">
					{#each results.performances as perf}
						<a href="/opptak/{perf.id}" class="performance-card">
							<div class="card-image">
								{#if perf.image_url}
									<img src={perf.image_url} alt={perf.work_title || perf.title || ''} />
								{:else}
									<div class="no-image">
										{perf.medium === 'tv' ? 'TV' : 'Radio'}
									</div>
								{/if}
								{#if perf.language && perf.language !== 'no'}
									<span class="lang-badge">{perf.language === 'sv' ? 'Svensk' : perf.language === 'da' ? 'Dansk' : perf.language}</span>
								{/if}
							</div>
							<div class="card-content">
								<h3>{perf.work_title || perf.title}</h3>
								{#if perf.playwright_name}
									<p class="creator">{perf.playwright_name}</p>
								{/if}
								<div class="meta">
									{#if perf.year}
										<span class="year">{perf.year}</span>
									{/if}
									<span class="medium">{perf.medium === 'tv' ? 'TV' : 'Radio'}</span>
									{#if perf.total_duration}
										<span class="duration">{formatDuration(perf.total_duration)}</span>
									{/if}
								</div>
								{#if perf.director_name}
									<p class="director">Regi: {perf.director_name}</p>
								{/if}
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}
	{/if}
</div>

<style>
	.search-page {
		max-width: 1400px;
		margin: 0 auto;
	}

	.page-header {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 1.5rem 0;
		margin-bottom: 1rem;
	}

	.search-container {
		position: relative;
		width: 100%;
		max-width: 480px;
	}

	.search-container input {
		width: 100%;
		padding: 0.875rem 1.25rem;
		font-size: 1rem;
		border: 2px solid #e0e0e0;
		border-radius: 8px;
		outline: none;
		transition: border-color 0.15s, box-shadow 0.15s;
	}

	.search-container input:focus {
		border-color: #e94560;
		box-shadow: 0 0 0 3px rgba(233, 69, 96, 0.1);
	}

	.search-container input::placeholder {
		color: #999;
	}

	.loading,
	.empty-state {
		text-align: center;
		padding: 4rem;
		color: #666;
	}

	.empty-state p {
		margin-bottom: 0.5rem;
	}

	.hint {
		font-size: 0.9rem;
		color: #888;
	}

	.results-summary {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
		margin-bottom: 2rem;
		padding-bottom: 1rem;
		border-bottom: 1px solid #e0e0e0;
	}

	.total {
		font-weight: 600;
	}

	.count {
		background: #e8e8e8;
		padding: 0.25rem 0.75rem;
		border-radius: 4px;
		font-size: 0.9rem;
	}

	.results-section {
		margin-bottom: 3rem;
	}

	.results-section h2 {
		font-size: 1.25rem;
		margin-bottom: 1rem;
		color: #333;
	}

	/* Persons */
	.persons-list {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 1rem;
	}

	.person-card {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1rem;
		background: white;
		border-radius: 8px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.person-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
	}

	.person-avatar {
		width: 50px;
		height: 50px;
		border-radius: 50%;
		background: linear-gradient(135deg, #e94560, #1a1a2e);
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.25rem;
		font-weight: bold;
		flex-shrink: 0;
	}

	.person-info {
		flex: 1;
		min-width: 0;
	}

	.person-info h3 {
		font-size: 1rem;
		margin-bottom: 0.25rem;
	}

	.person-meta {
		display: flex;
		gap: 0.5rem;
		font-size: 0.85rem;
		color: #666;
		margin-bottom: 0.25rem;
	}

	.person-stats {
		display: flex;
		gap: 0.75rem;
		font-size: 0.8rem;
		color: #888;
	}

	/* Works and Performances Grid */
	.works-grid,
	.performances-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: 1.5rem;
	}

	.work-card,
	.performance-card {
		background: white;
		border-radius: 8px;
		overflow: hidden;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		text-decoration: none;
		color: inherit;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.work-card:hover,
	.performance-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
	}

	.card-image {
		position: relative;
	}

	.work-card img,
	.performance-card img {
		width: 100%;
		height: 140px;
		object-fit: cover;
	}

	.lang-badge {
		position: absolute;
		top: 6px;
		right: 6px;
		background: rgba(0, 0, 0, 0.7);
		color: white;
		font-size: 0.65rem;
		font-weight: 500;
		padding: 2px 6px;
		border-radius: 3px;
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}

	.no-image {
		width: 100%;
		height: 140px;
		background: linear-gradient(135deg, #1a1a2e, #16213e);
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1rem;
	}

	.card-content {
		padding: 1rem;
	}

	.card-content h3 {
		font-size: 0.95rem;
		margin-bottom: 0.25rem;
		line-height: 1.3;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.creator {
		color: #666;
		font-size: 0.85rem;
		margin-bottom: 0.5rem;
	}

	.director {
		color: #888;
		font-size: 0.8rem;
		margin-top: 0.5rem;
	}

	.meta {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
		font-size: 0.8rem;
		color: #888;
	}

	.medium,
	.badge {
		background: #f0f0f0;
		padding: 0.1rem 0.4rem;
		border-radius: 3px;
	}

	@media (max-width: 600px) {
		.search-container input {
			padding: 0.75rem 1rem;
			font-size: 0.95rem;
		}

		.persons-list {
			grid-template-columns: 1fr;
		}

		.works-grid,
		.performances-grid {
			grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		}
	}
</style>

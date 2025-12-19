<script lang="ts">
	import { page } from '$app/stores';
	import { getEpisode, getEpisodeContributors } from '$lib/db';
	import type { EpisodeWithDetails, EpisodePerson } from '$lib/types';
	import { onMount } from 'svelte';

	let episode: EpisodeWithDetails | null = null;
	let contributors: (EpisodePerson & { person_name: string })[] = [];
	let loading = true;
	let error: string | null = null;

	$: episodeId = $page.params.id || '';

	onMount(() => {
		loadEpisode();
	});

	function loadEpisode() {
		try {
			episode = getEpisode(episodeId);
			if (episode) {
				contributors = getEpisodeContributors(episodeId);
			} else {
				error = 'Episode ikke funnet';
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
		if (h > 0) return `${h} time${h > 1 ? 'r' : ''} ${m} min`;
		return `${m} minutter`;
	}

	function getImageUrl(url: string | null, width = 960): string {
		if (!url) return '/placeholder.jpg';
		if (url.includes('gfx.nrk.no')) {
			return url.replace(/\/\d+$/, `/${width}`);
		}
		return url;
	}

	function getRoleLabel(role: string | null): string {
		const labels: Record<string, string> = {
			director: 'Regissor',
			actor: 'Skuespiller',
			playwright: 'Manusforfatter',
			composer: 'Komponist',
			set_designer: 'Scenograf',
			costume_designer: 'Kostymedesigner',
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

	$: contributorGroups = groupContributors(contributors);
</script>

<svelte:head>
	{#if episode}
		<title>{episode.title} - Kulturperler</title>
	{/if}
</svelte:head>

{#if loading}
	<div class="loading">Laster...</div>
{:else if error}
	<div class="error">{error}</div>
{:else if episode}
	<article class="episode-detail">
		<a href="/" class="back-link">&larr; Tilbake til oversikt</a>

		<div class="episode-header">
			<div class="episode-image">
				<img
					src={getImageUrl(episode.image_url)}
					alt={episode.title}
				/>
			</div>

			<div class="episode-meta">
				<h1>{episode.title}</h1>

				<div class="meta-badges">
					{#if episode.year}
						<span class="badge year">{episode.year}</span>
					{/if}
					{#if episode.duration_seconds}
						<span class="badge duration">{formatDuration(episode.duration_seconds)}</span>
					{/if}
				</div>

				{#if episode.playwright_name}
					<p class="playwright">
						Av <a href="/person/{episode.playwright_name}">{episode.playwright_name}</a>
					</p>
				{/if}

				{#if episode.play_title}
					<p class="play">Teaterstykke: {episode.play_title}</p>
				{/if}

				{#if episode.description}
					<p class="description">{episode.description}</p>
				{/if}

				<div class="actions">
					{#if episode.nrk_url}
						<a
							href={episode.nrk_url}
							target="_blank"
							rel="noopener"
							class="btn btn-primary"
						>
							Se på NRK TV
						</a>
					{:else}
						<a
							href="https://tv.nrk.no/se?v={episode.prf_id}"
							target="_blank"
							rel="noopener"
							class="btn btn-primary"
						>
							Se på NRK TV
						</a>
					{/if}
				</div>
			</div>
		</div>

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

	.episode-detail {
		background: white;
		border-radius: 8px;
		padding: 2rem;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.episode-header {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 2rem;
		margin-bottom: 2rem;
	}

	.episode-image {
		border-radius: 8px;
		overflow: hidden;
		background: #eee;
	}

	.episode-image img {
		width: 100%;
		height: auto;
		display: block;
	}

	.episode-meta h1 {
		font-size: 2rem;
		margin-bottom: 1rem;
		line-height: 1.2;
	}

	.meta-badges {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	.badge {
		padding: 0.25rem 0.75rem;
		border-radius: 4px;
		font-size: 0.9rem;
	}

	.badge.year {
		background: #e94560;
		color: white;
	}

	.badge.duration {
		background: #1a1a2e;
		color: white;
	}

	.playwright {
		font-size: 1.1rem;
		margin-bottom: 0.5rem;
	}

	.playwright a {
		color: #e94560;
	}

	.play {
		font-size: 0.95rem;
		color: #666;
		margin-bottom: 1rem;
	}

	.description {
		line-height: 1.7;
		color: #444;
		margin-bottom: 1.5rem;
	}

	.actions {
		display: flex;
		gap: 1rem;
	}

	.btn {
		padding: 0.75rem 1.5rem;
		border-radius: 6px;
		text-decoration: none;
		font-weight: 500;
		transition: background-color 0.2s;
	}

	.btn-primary {
		background: #e94560;
		color: white;
	}

	.btn-primary:hover {
		background: #d13350;
	}

	.contributors {
		border-top: 1px solid #eee;
		padding-top: 2rem;
	}

	.contributors h2 {
		font-size: 1.5rem;
		margin-bottom: 1.5rem;
	}

	.contributor-groups {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: 2rem;
	}

	.contributor-group h3 {
		font-size: 1rem;
		font-weight: 600;
		margin-bottom: 0.75rem;
		color: #666;
	}

	.contributor-group ul {
		list-style: none;
	}

	.contributor-group li {
		margin-bottom: 0.5rem;
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

	@media (max-width: 768px) {
		.episode-header {
			grid-template-columns: 1fr;
		}

		.episode-meta h1 {
			font-size: 1.5rem;
		}
	}
</style>

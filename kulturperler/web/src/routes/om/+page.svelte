<script lang="ts">
</script>

<svelte:head>
	<title>Om - Kulturbase.no</title>
</svelte:head>

<article class="about-page">
	<div class="page-layout">
		<div class="content-column">
			<h1>Om Kulturbase.no</h1>

			<section class="intro">
				<p>
					Dette er et forsøk på å organisere lenker til opptak av teater på norsk, opera, ballett
					og klassisk musikk spilt av norske orkestere på en måte som gjør det lett å finne,
					men også å utforske.
				</p>

				<p>
					Jeg har selv satt veldig pris på NRK Arkivet i min egen læringsreise rundt teater, opera,
					klassisk musikk og litteratur, men jeg syntes alltid det var vanskelig å navigere.
					Og når jeg først hadde begynt å fikse det problemet, kom jeg stadig på andre kilder
					det kunne være aktuelt å legge til.
				</p>
			</section>

			<section class="feedback">
				<h2>Tilbakemeldinger</h2>
				<p>
					Det er ofte rotete metadata og det har vært ganske mye automatisk arbeid med å prøve
					å strukturere alt, så det er garantert feil, misforståelser, døde lenker etc.
					Gi meg gjerne beskjed så fikser jeg!
				</p>
				<p>
					Det samme hvis du kjenner verker som er tilgjengelig for streaming og ikke forsvinner
					fra nettet med det første, jeg legger dem gjerne til. (Ideer etc tas også i mot!)
				</p>
			</section>

			<section class="contact">
				<p class="signature">
					<strong>Stian Håklev</strong><br>
					<a href="mailto:shaklev@gmail.com">shaklev@gmail.com</a>
				</p>
			</section>

		</div>

		<aside class="image-column">
			<figure class="featured-image">
				<img
					src="/images/peasant-dance.jpg"
					alt="Bondedansen - Pieter Bruegel den eldre, ca. 1567"
				/>
				<figcaption>
					<em>Bondedansen</em><br>
					Pieter Bruegel den eldre, ca. 1567
				</figcaption>
			</figure>

			<section class="other-projects">
				<h2>Andre prosjekter</h2>
				<ul>
					<li>
						<a href="https://1814dagfordag.substack.com/" target="_blank" rel="noopener">
							1814 dag for dag
						</a>
						<span class="project-desc">— leser avisene fra 1814 gjennom hele 2025</span>
					</li>
					<li>
						<a href="https://kaninhull.substack.com/" target="_blank" rel="noopener">
							Kaninhull og røde tråder
						</a>
						<span class="project-desc">— blogg der jeg gjør litt dypdykk i kulturhistorien</span>
					</li>
					<li>
						<a href="https://app.tana.inc/shared/ressurser-for-ambisiose-barn/WWhzM1FISkU2MS9OdkMwbDYxeGRBRnk=" target="_blank" rel="noopener">
							Ressurser for ambisiøse barn
						</a>
						<span class="project-desc">— eldre bøker, filmer, operaer og skuespill (inkludert en del fra NRK Arkivet) som er testet på en 10-11 åring</span>
					</li>
				</ul>
			</section>
		</aside>
	</div>
</article>

<style>
	.about-page {
		max-width: 1400px;
		margin: 0 auto;
		background: white;
		border-radius: 12px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
		padding: 3rem;
	}

	.page-layout {
		display: flex;
		gap: 4rem;
		align-items: flex-start;
	}

	.content-column {
		flex: 1;
		min-width: 0;
	}

	.image-column {
		flex-shrink: 0;
		width: 650px;
	}

	h1 {
		font-size: 2rem;
		margin-bottom: 2rem;
		color: #1a1a2e;
	}

	.featured-image {
		margin: 0;
	}

	.featured-image img {
		width: 100%;
		border-radius: 8px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
	}

	.featured-image figcaption {
		margin-top: 0.75rem;
		font-size: 0.85rem;
		color: #666;
		text-align: center;
		line-height: 1.5;
	}

	h2 {
		font-size: 1.25rem;
		margin-bottom: 1rem;
		color: #1a1a2e;
		padding-top: 1.5rem;
		border-top: 1px solid #eee;
	}

	section {
		margin-bottom: 1.5rem;
	}

	.intro {
		font-size: 1.1rem;
		line-height: 1.8;
	}

	p {
		margin-bottom: 1rem;
		color: #444;
	}

	.contact {
		margin-top: 2rem;
	}

	.signature {
		font-size: 1.05rem;
		line-height: 1.6;
	}

	.signature a {
		color: #e94560;
		text-decoration: none;
	}

	.signature a:hover {
		text-decoration: underline;
	}

	.other-projects ul {
		list-style: none;
		padding: 0;
	}

	.other-projects li {
		margin-bottom: 1rem;
		line-height: 1.6;
	}

	.other-projects a {
		color: #e94560;
		text-decoration: none;
		font-weight: 500;
	}

	.other-projects a:hover {
		text-decoration: underline;
	}

	.project-desc {
		color: #666;
	}

	@media (max-width: 900px) {
		.page-layout {
			flex-direction: column;
			gap: 2rem;
		}

		.image-column {
			width: 100%;
			max-width: 500px;
			margin: 0 auto;
		}
	}

	@media (max-width: 600px) {
		.about-page {
			padding: 1.5rem;
			border-radius: 0;
		}

		h1 {
			font-size: 1.5rem;
		}

		.intro {
			font-size: 1rem;
		}
	}
</style>

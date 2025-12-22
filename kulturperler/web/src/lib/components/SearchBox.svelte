<script lang="ts">
	import { goto } from '$app/navigation';
	import { getAutocompleteSuggestions, type AutocompleteSuggestion } from '$lib/db';

	export let placeholder = 'Søk etter stykker, personer...';
	export let expanded = false;

	let query = '';
	let suggestions: AutocompleteSuggestion[] = [];
	let showSuggestions = false;
	let selectedIndex = -1;
	let inputElement: HTMLInputElement;
	let debounceTimer: ReturnType<typeof setTimeout>;

	function handleInput() {
		clearTimeout(debounceTimer);
		selectedIndex = -1;

		if (query.trim().length < 2) {
			suggestions = [];
			showSuggestions = false;
			return;
		}

		debounceTimer = setTimeout(() => {
			try {
				suggestions = getAutocompleteSuggestions(query.trim());
				showSuggestions = suggestions.length > 0;
			} catch {
				suggestions = [];
				showSuggestions = false;
			}
		}, 150);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'ArrowDown') {
			event.preventDefault();
			selectedIndex = Math.min(selectedIndex + 1, suggestions.length);
		} else if (event.key === 'ArrowUp') {
			event.preventDefault();
			selectedIndex = Math.max(selectedIndex - 1, -1);
		} else if (event.key === 'Enter') {
			event.preventDefault();
			if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
				navigateToSuggestion(suggestions[selectedIndex]);
			} else if (query.trim()) {
				navigateToSearch();
			}
		} else if (event.key === 'Escape') {
			showSuggestions = false;
			inputElement?.blur();
		}
	}

	function navigateToSuggestion(suggestion: AutocompleteSuggestion) {
		query = '';
		showSuggestions = false;
		goto(suggestion.url);
	}

	function navigateToSearch() {
		const searchQuery = query.trim();
		query = '';
		showSuggestions = false;
		goto(`/sok?q=${encodeURIComponent(searchQuery)}`);
	}

	function handleFocus() {
		if (query.trim().length >= 2 && suggestions.length > 0) {
			showSuggestions = true;
		}
	}

	function handleBlur() {
		// Delay hiding to allow click events on suggestions
		setTimeout(() => {
			showSuggestions = false;
		}, 200);
	}

	function getTypeLabel(type: string): string {
		switch (type) {
			case 'person':
				return 'Person';
			case 'work':
				return 'Verk';
			case 'performance':
				return 'Opptak';
			default:
				return type;
		}
	}
</script>

<div class="search-box" class:expanded>
	<div class="search-input-wrapper">
		<svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
			<circle cx="11" cy="11" r="8" />
			<path d="M21 21l-4.35-4.35" />
		</svg>
		<input
			bind:this={inputElement}
			bind:value={query}
			on:input={handleInput}
			on:keydown={handleKeydown}
			on:focus={handleFocus}
			on:blur={handleBlur}
			type="search"
			{placeholder}
			autocomplete="off"
			aria-label="Søk"
			aria-expanded={showSuggestions}
			aria-controls="search-suggestions"
		/>
	</div>

	{#if showSuggestions}
		<ul id="search-suggestions" class="suggestions" role="listbox">
			{#each suggestions as suggestion, i}
				<li
					class="suggestion"
					class:selected={i === selectedIndex}
					role="option"
					aria-selected={i === selectedIndex}
				>
					<button
						type="button"
						on:click={() => navigateToSuggestion(suggestion)}
						on:mouseenter={() => (selectedIndex = i)}
					>
						{#if suggestion.image_url}
							<img src={suggestion.image_url} alt="" class="suggestion-image" />
						{:else}
							<div class="suggestion-image placeholder" data-type={suggestion.type}>
								{#if suggestion.type === 'person'}
									<svg viewBox="0 0 24 24" fill="currentColor">
										<path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
									</svg>
								{:else}
									<svg viewBox="0 0 24 24" fill="currentColor">
										<path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z" />
									</svg>
								{/if}
							</div>
						{/if}
						<div class="suggestion-content">
							<span class="suggestion-title">{suggestion.title}</span>
							{#if suggestion.subtitle}
								<span class="suggestion-subtitle">{suggestion.subtitle}</span>
							{/if}
						</div>
						<span class="suggestion-type">{getTypeLabel(suggestion.type)}</span>
					</button>
				</li>
			{/each}
			<li class="suggestion search-all" class:selected={selectedIndex === suggestions.length}>
				<button
					type="button"
					on:click={navigateToSearch}
					on:mouseenter={() => (selectedIndex = suggestions.length)}
				>
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<circle cx="11" cy="11" r="8" />
						<path d="M21 21l-4.35-4.35" />
					</svg>
					<span>Søk etter «{query}»</span>
				</button>
			</li>
		</ul>
	{/if}
</div>

<style>
	.search-box {
		position: relative;
		width: 200px;
		transition: width 0.2s ease;
	}

	.search-box.expanded {
		width: 100%;
		max-width: 400px;
	}

	.search-box:focus-within {
		width: 280px;
	}

	.search-box.expanded:focus-within {
		width: 100%;
		max-width: 500px;
	}

	.search-input-wrapper {
		position: relative;
		display: flex;
		align-items: center;
	}

	.search-icon {
		position: absolute;
		left: 10px;
		width: 18px;
		height: 18px;
		color: rgba(255, 255, 255, 0.5);
		pointer-events: none;
	}

	input {
		width: 100%;
		padding: 0.5rem 0.75rem 0.5rem 2.25rem;
		border: none;
		border-radius: 6px;
		background: rgba(255, 255, 255, 0.1);
		color: white;
		font-size: 0.9rem;
		transition: background 0.15s, box-shadow 0.15s;
	}

	input::placeholder {
		color: rgba(255, 255, 255, 0.5);
	}

	input:focus {
		outline: none;
		background: rgba(255, 255, 255, 0.15);
		box-shadow: 0 0 0 2px rgba(233, 69, 96, 0.5);
	}

	/* Hide native search cancel button */
	input[type='search']::-webkit-search-cancel-button {
		-webkit-appearance: none;
	}

	.suggestions {
		position: absolute;
		top: calc(100% + 4px);
		left: 0;
		right: 0;
		background: white;
		border-radius: 8px;
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
		list-style: none;
		overflow: hidden;
		z-index: 1000;
		max-height: 400px;
		overflow-y: auto;
	}

	.suggestion button {
		width: 100%;
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		border: none;
		background: none;
		text-align: left;
		cursor: pointer;
		color: #333;
		transition: background 0.1s;
	}

	.suggestion.selected button,
	.suggestion button:hover {
		background: #f5f5f5;
	}

	.suggestion-image {
		width: 40px;
		height: 40px;
		border-radius: 4px;
		object-fit: cover;
		flex-shrink: 0;
	}

	.suggestion-image.placeholder {
		display: flex;
		align-items: center;
		justify-content: center;
		background: #e8e8e8;
		color: #999;
	}

	.suggestion-image.placeholder[data-type='person'] {
		border-radius: 50%;
	}

	.suggestion-image.placeholder svg {
		width: 20px;
		height: 20px;
	}

	.suggestion-content {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
	}

	.suggestion-title {
		font-weight: 500;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.suggestion-subtitle {
		font-size: 0.8rem;
		color: #666;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.suggestion-type {
		font-size: 0.75rem;
		color: #999;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		flex-shrink: 0;
	}

	.search-all button {
		border-top: 1px solid #eee;
		color: #e94560;
		font-weight: 500;
	}

	.search-all svg {
		width: 18px;
		height: 18px;
		flex-shrink: 0;
	}

	@media (max-width: 900px) {
		.search-box {
			width: 100%;
		}

		.search-box:focus-within {
			width: 100%;
		}
	}
</style>

<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	$: workId = $page.params.id;

	onMount(() => {
		goto(`/verk/${workId}`, { replaceState: true });
	});
</script>

<div class="redirect">
	<p>Omdirigerer til /verk/{workId}...</p>
</div>

<style>
	.redirect {
		text-align: center;
		padding: 4rem;
		color: #666;
	}
</style>

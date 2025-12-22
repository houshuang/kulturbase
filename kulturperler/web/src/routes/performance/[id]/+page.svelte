<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	$: performanceId = $page.params.id;

	onMount(() => {
		goto(`/opptak/${performanceId}`, { replaceState: true });
	});
</script>

<div class="redirect">
	<p>Omdirigerer til /opptak/{performanceId}...</p>
</div>

<style>
	.redirect {
		text-align: center;
		padding: 4rem;
		color: #666;
	}
</style>

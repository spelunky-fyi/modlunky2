<script lang="ts">
  export let count: number = 0;
</script>

<div class="flex items-center gap-2 py-0.5 px-2 bg-zinc-100 dark:bg-zinc-800 text-sm">
  <slot />
  {#if count > 0}
    <span class="text-xs opacity-50">{count}</span>
  {/if}
</div>

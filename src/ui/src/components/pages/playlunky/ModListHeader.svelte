<script lang="ts">
  export let count: number = 0;
</script>

<div class="flex items-center gap-1.5 py-0.5 px-2 bg-gray-100">
  <slot />
  {#if count > 0}
    <span class="text-xs">({count})</span>
  {/if}
</div>

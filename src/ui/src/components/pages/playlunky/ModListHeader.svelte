<script lang="ts">
  export let count: number = 0;
</script>

<div class="flex items-center gap-2 py-1 px-2 elevation-1 text-xs uppercase font-bold tracking-widest">
  <slot />
  {#if count > 0}
    <span class="text-xs opacity-50">{count}</span>
  {/if}
</div>

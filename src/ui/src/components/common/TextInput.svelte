<script lang="ts">
  import Text from "./Text.svelte";

  export let label = "";
  export let value = "";

  const baseStyle =
    "w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-800 focus:bg-white dark:focus:bg-zinc-700 dark:focus:bg-opacity-90 focus:shadow-sm focus:outline-none transition";
</script>

{#if label}
  <label class="flex items-center gap-2 {$$restProps.class || ''}">
    <Text level="h5" class="shrink-0">{label}</Text>
    <input
      {...$$props}
      class="{baseStyle} focus:outline-none"
      type="text"
      bind:value
      on:change
      on:keydown
    />
  </label>
{:else}
  <input
    {...$$props}
    type="text"
    class="{baseStyle} {$$restProps.class || ''}"
    bind:value
    on:change
    on:keydown
  />
{/if}

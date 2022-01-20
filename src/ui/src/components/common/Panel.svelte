<script lang="ts">
  export let rounded: boolean = false;
  export let padding: PanelPadding = "default";

  const paddingSizes = {
    none: "p-0",
    small: "p-2",
    default: "p-4",
    large: "p-6",
    huge: "p-8",
  };
</script>

<div
  {...$$props}
  class="{paddingSizes[
    padding
  ]} bg-zinc-100 dark:bg-zinc-600 divide-y divide-zinc-200 dark:divide-zinc-500 border border-zinc-200 dark:border-zinc-500 {rounded
    ? 'rounded-md'
    : ''} {$$restProps.class || ''}"
>
  <slot />
</div>

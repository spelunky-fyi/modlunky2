<script lang="ts">
  export let direction: StackDirection = "horizontal";
  export let spacing: StackSpacing = "default";
  export let align: StackAlign = "stretch";
  export let justify: StackJustify = "stretch";

  const stackSpacing = {
    none: "0",
    small: "2",
    default: "4",
    large: "6",
  };

  const s = typeof spacing === "number" ? `[${spacing}px]` : stackSpacing[spacing];
</script>

<div
  {...$$props}
  on:click
  class="flex items-{align} justify-{justify} {spacing === 'none' ? '' : `gap-${s}`} {direction ===
  'horizontal'
    ? 'flex-row'
    : 'flex-col'} {$$restProps.class || ''}"
>
  <slot />
</div>

<script lang="ts">
  type TextLevel = "p" | "h1" | "h2" | "h3" | "h4" | "h5" | "h6" | "span";

  export let level: TextLevel = "p";

  const textStyles = {
    base: "whitespace-normal",
  };
</script>

{#if level === "p"}
  <p
    {...$$props}
    class="{textStyles.base} text-sm leading-relaxed {$$restProps.class || ''}"
  >
    <slot />
  </p>
{:else if level === "span"}
  <span {...$$props} class="{textStyles.base} {$$restProps.class || ''}">
    <slot />
  </span>
{:else if level === "h1"}
  <h1 {...$$props} class="{textStyles.base} text-xl {$$restProps.class || ''}">
    <slot />
  </h1>
{:else if level === "h2"}
  <h2 {...$$props} class="{textStyles.base} text-lg {$$restProps.class || ''}">
    <slot />
  </h2>
{:else if level === "h3"}
  <h3
    {...$$props}
    class="{textStyles.base} text-base {$$restProps.class || ''}"
  >
    <slot />
  </h3>
{:else if level === "h4"}
  <h4 {...$$props} class="{textStyles.base} text-sm {$$restProps.class || ''}">
    <slot />
  </h4>
{:else if level === "h5"}
  <h5 {...$$props} class="{textStyles.base} text-xs {$$restProps.class || ''}">
    <slot />
  </h5>
{:else if level === "h6"}
  <h6 {...$$props} class="{textStyles.base} text-2xs {$$restProps.class || ''}">
    <slot />
  </h6>
{/if}

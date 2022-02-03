<script lang="ts">
  import classes from "../../../util/classes";
  import Text from "../text/text.svelte";

  const id = Symbol().toString();

  export let size: InputTextSize = "md";
  export let label = "";
  export let value = "";
  export let placeholder = "";

  let _class = "";
  export { _class as class };
</script>

{#if label}
  <label for={id} class="shrink-0">
    <Text level="h5">{label}</Text>
  </label>
{/if}

<input
  {id}
  {placeholder}
  type="text"
  bind:value
  on:change
  on:keydown
  on:keyup
  on:keypress
  class:sm={size === "sm"}
  class:md={size === "md"}
  class:lg={size === "lg"}
  class={classes("input-text", _class)}
/>

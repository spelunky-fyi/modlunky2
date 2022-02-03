<script lang="ts">
  import classes from "../../../util/classes";

  export let size: ButtonSize | string = "md";
  export let primary = false;
  export let transparent = false;
  export let outline = false;
  export let disabled = false;
  export let rounded = true;

  let _class = "";
  export { _class as class };
</script>

<button
  on:click
  on:mousedown
  on:mouseup
  on:touchstart
  on:touchend
  {disabled}
  class:rounded
  class:btn-primary={primary}
  class:btn-transparent={transparent}
  class:btn-outline={outline}
  class:sm={size === "sm"}
  class:md={size === "md"}
  class:lg={size === "lg"}
  class={classes("btn", _class)}
>
  <slot />
</button>

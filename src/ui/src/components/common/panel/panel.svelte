<script lang="ts">
  import classes from "../../../util/classes";

  export let padding: PanelPadding = "md";
  export let rounded = true;

  let _class = "";
  export { _class as class };
</script>

<div
  class:rounded
  class:p-0={padding === "none"}
  class:p-2={padding === "sm"}
  class:p-4={padding === "md"}
  class:p-8={padding === "lg"}
  class={classes("panel", _class)}
>
  <slot />
</div>

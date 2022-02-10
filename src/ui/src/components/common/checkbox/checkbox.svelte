<script lang="ts">
  import classes from "@/util/classes";
  import Text from "../text/text.svelte";

  export let checked = false;
  export let size: CheckboxSize = "md";
  export let disabled = false;
  export let rounded = false;

  let _class = "";
  export { _class as class };
</script>

<label
  {disabled}
  class:sm={size === "sm"}
  class:md={size === "md"}
  class:lg={size === "lg"}
  class={classes("checkbox", _class)}
>
  <input type="checkbox" bind:checked class:rounded />
  <Text level="span">
    <slot>{size}</slot>
  </Text>
</label>

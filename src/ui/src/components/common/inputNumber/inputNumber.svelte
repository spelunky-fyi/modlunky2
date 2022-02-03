<script lang="ts">
  import classes from "../../../util/classes";
  import Text from "../text/text.svelte";

  export let size: InputNumberSize = "md";
  export let value: number;

  // class="w-14 px-2 py-1 rounded bg-theme-800 border border-theme-600 focus:bg-theme-700 focus:shadow-sm focus:outline-none focus:ring-2 focus:border-theme-primary/80 focus:ring-theme-primary/30 transition ease-in-out {$$restProps.class ||
  let _class = "";
  export { _class as class };
</script>

<label class="flex items-center gap-1.5">
  <input
    type="number"
    bind:value
    class:sm={size === "sm"}
    class:md={size === "md"}
    class:lg={size === "lg"}
    class={classes("input-number", _class)}
  />
  <Text level="span"><slot /></Text>
</label>

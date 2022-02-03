<script lang="ts">
  import classes from "../../../util/classes";

  export let spacing: StackSpacing = "md";
  export let align: StackAlign = "stretch";
  export let justify: StackJustify = "stretch";
  export let vertical = false;

  let _class = "";
  export { _class as class };
</script>

<div
  {...$$props}
  on:click
  class:gap-0={spacing === "none"}
  class:gap-1={spacing === "sm"}
  class:gap-2={spacing === "md"}
  class:gap-4={spacing === "lg"}
  class:items-stretch={align === "stretch"}
  class:items-center={align === "center"}
  class:items-start={align === "start"}
  class:items-end={align === "end"}
  class:justify-stretch={justify === "stretch"}
  class:justify-center={justify === "center"}
  class:justify-start={justify === "start"}
  class:justify-end={justify === "end"}
  class:justify-between={justify === "between"}
  class:flex-col={vertical}
  class={classes("stack", _class)}
>
  <slot />
</div>

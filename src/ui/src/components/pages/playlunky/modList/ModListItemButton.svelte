<script lang="ts">
  import classes from "@/util/classes";
  import { Button } from "@/components/common";

  let _class = "";
  export { _class as class };
</script>

<Button
  transparent
  size="sm"
  rounded={false}
  class={classes("w-11", _class)}
  on:click
  on:mousedown
  on:mouseup
  on:touchstart
  on:touchend
>
  <slot />
</Button>

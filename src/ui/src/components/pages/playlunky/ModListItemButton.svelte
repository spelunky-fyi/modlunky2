<script lang="ts">
  import { Button } from "../../common";
</script>

<Button
  color="transparent"
  class="text-zinc-500 {$$restProps.class || ''}"
  on:click
  on:mousedown
  on:mouseup
  on:touchstart
  on:touchend
>
  <slot />
</Button>

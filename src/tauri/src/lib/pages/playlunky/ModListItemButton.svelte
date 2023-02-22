<script lang="ts">
  import { Button } from "../../common";

  export let styleClass = "";
</script>

<Button
  color="transparent"
  class="text-zinc-500 {styleClass}"
  on:click
  on:mousedown
  on:mouseup
  on:touchstart
  on:touchend
>
  <slot />
</Button>

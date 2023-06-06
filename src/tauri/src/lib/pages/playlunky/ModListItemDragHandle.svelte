<script lang="ts">
  import { buttonStyles } from "../../common/Button.svelte"

  export let styleClass = "";
</script>

<div
  {...$$props}
  on:mousedown
  on:mouseup
  on:touchstart
  on:touchend
  class="{buttonStyles.base}
    {buttonStyles.size.default}
    {buttonStyles.colors.transparent}
    text-zinc-500 {styleClass}"
>
  <slot />
</div>

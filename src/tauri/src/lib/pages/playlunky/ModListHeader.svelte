<script lang="ts">
  import { Stack, Text } from "../../common";

  export let count = 0;
</script>

<Stack spacing="small" align="center" class="uppercase tracking-widest font-semibold">
  <Text level="h4">
    <slot />
  </Text>
  {#if count > 0}
    <Text level="h4" class="opacity-50">{count}</Text>
  {/if}
</Stack>

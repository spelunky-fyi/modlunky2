<script lang="ts">
  import { Stack, Text } from "@/components/common";

  export let count = 0;
</script>

<Stack
  spacing="sm"
  align="center"
  class="bg-theme-700/25 px-2 uppercase tracking-widest opacity-50"
>
  <Text level="h4">
    <slot />
  </Text>
  {#if count > 0}
    <Text level="h4" class="opacity-50">{count}</Text>
  {/if}
</Stack>

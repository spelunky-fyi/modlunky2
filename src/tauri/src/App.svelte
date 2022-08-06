<script lang="ts">
  import { activeTabIndex } from "./store";
  import { tabs } from "./tabs";
  import { Stack } from "./lib/common";
  import Console from "./lib/Console.svelte";
  import TabBar from "./lib/TabBar.svelte";

  $: padding = $activeTabIndex !== 4 && $activeTabIndex !== 7;
</script>

<main
  class="flex flex-col h-full elevation-0 select-none font-sans text-zinc-600 dark:text-zinc-400"
>
  <TabBar />
  <Stack class="{padding ? 'p-6' : ''} flex-1 overflow-hidden">
    <svelte:component this={tabs[$activeTabIndex].component} />
  </Stack>
  {#if padding}
    <Console />
  {/if}
</main>

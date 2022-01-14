<script lang="ts">
  import TabBar from "./components/TabBar.svelte";
  import Console from "./components/Console.svelte";
  import { tabs } from "./tabs";
  import { activeTabIndex } from "./store";
</script>

<main class="flex flex-col h-full select-none elevation-0 text-zinc-700 dark:text-zinc-300">
  <TabBar />
  <div class="flex-grow flex p-3 overflow-hidden">
    <svelte:component this={tabs[$activeTabIndex].component} />
  </div>
  <Console />
</main>

<script lang="ts">
  import { activeTabIndex } from "./store";
  import { tabs } from "./tabs";
  import Console from "./components/Console.svelte";
  import TabBar from "./components/tabBar/TabBar.svelte";
  import Titlebar from "./components/Titlebar.svelte";
</script>

<main
  class="flex h-full select-none flex-col overflow-hidden rounded border border-theme-700 bg-theme-800 font-sans text-theme-300 shadow-2xl"
>
  <Titlebar />
  <TabBar />
  <section class="flex-1 overflow-hidden">
    <svelte:component this={tabs[$activeTabIndex].component} />
  </section>
  {#if !tabs[$activeTabIndex].hideConsole}
    <Console />
  {/if}
</main>

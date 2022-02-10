<script lang="ts">
  import { activeTabIndex } from "@/store";
  import { tabs } from "@/tabs";

  function selectTab(index: number) {
    $activeTabIndex = index;
  }
</script>

<nav
  class="relative flex justify-center gap-1 border-b border-b-theme-800/50 bg-theme-800 px-3 pt-2 pb-1"
>
  {#each tabs as tab, index}
    <button
      on:click={() => selectTab(index)}
      disabled={tab.disabled}
      class="tabbar"
      class:opacity-50={tab.disabled}
      class:tabbar-selected={$activeTabIndex === index}>{tab.title}</button
    >
  {/each}
</nav>

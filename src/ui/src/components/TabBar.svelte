<script lang="ts">
  import { tabs } from "../tabs";
  import { activeTabIndex } from "../store";
  import ThemeToggle from "./ThemeToggle.svelte";

  function selectTab(index: number) {
    $activeTabIndex = index;
  }
</script>

<div class="relative flex px-3 pt-5 elevation-2">
  {#each tabs as tab, index}
    <button
      on:click={() => selectTab(index)}
      disabled={tab.disabled}
      class="tab text-sm"
      class:opacity-50={tab.disabled}
      class:tab-active={$activeTabIndex === index}>{tab.title}</button
    >
  {/each}
  <ThemeToggle class="absolute inset-y-2 right-2"/>
</div>

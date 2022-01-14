<script lang="ts">
  import { tabs } from "../tabs";
  import { activeTabIndex } from "../store";

  function selectTab(index) {
    $activeTabIndex = index;
  }
</script>

<div class="flex gap-1">
  {#each tabs as tab, index}
    <button
      on:click={() => (selectTab(index))}
      disabled={tab.disabled}
      class="tab text-xs"
      class:opacity-50={tab.disabled}
      class:tab-active={$activeTabIndex === index}>{tab.title}</button
    >
  {/each}
</div>

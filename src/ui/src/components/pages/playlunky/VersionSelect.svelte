<script lang="ts">
  import { fade } from "svelte/transition";
  import IconChevronDown from "~icons/fa-solid/chevron-down";
  import { version, versions } from "@/store";
  import { clickOutside } from "@/actions/clickOutside";
  import { Button } from "@/components/common";

  const menuVersions = versions.slice(2);
  let lastSelected = menuVersions[0];
  let versionMenuOpen = false;

  function handleVersionSelect(v: Version) {
    $version = v;
    lastSelected = v;
    versionMenuOpen = false;
  }
</script>

<svelte:window
  on:keydown={(e) => {
    if (versionMenuOpen && e.key === "Escape") {
      versionMenuOpen = false;
    }
  }}
/>

<div class="relative">
  <div class="m-1 flex">
    <Button
      size="sm"
      class="basis-16 rounded-r-none {$version === versions[0] &&
        'bg-theme-primary hover:bg-theme-primary/50 text-white'}"
      on:click={() => ($version = versions[0])}>stable</Button
    >
    <Button
      size="sm"
      class="basis-16 rounded-l-none rounded-r-none {$version === versions[1] &&
        'bg-theme-primary hover:bg-theme-primary/50 text-white'}"
      on:click={() => ($version = versions[1])}>nightly</Button
    >
    <div class="group relative contents">
      <Button
        size="sm"
        class="flex-1 rounded-l-none rounded-r-none {$version !== versions[0] &&
          $version !== versions[1] &&
          'bg-theme-primary hover:bg-theme-primary/50 text-white'}"
        on:click={() => ($version = lastSelected)}
      >
        {lastSelected.revision}
      </Button>
      <Button
        size="sm"
        class="w-8 rounded-l-none"
        on:click={() => (versionMenuOpen = !versionMenuOpen)}
      >
        <IconChevronDown />
      </Button>
    </div>
  </div>
  {#if versionMenuOpen}
    <div
      use:clickOutside
      on:clickoutside={() => (versionMenuOpen = false)}
      transition:fade={{ duration: 150 }}
      class="absolute right-0 z-10 mt-1 w-56 overflow-hidden rounded-sm bg-theme-50 shadow-lg ring-1 ring-theme-200/5 focus:outline-none"
    >
      {#each menuVersions as v}
        <button
          class="w-full px-4 py-2 text-left text-sm font-semibold text-theme-700 hover:bg-theme-100"
          on:click={() => handleVersionSelect(v)}>{v.revision}</button
        >
      {/each}
    </div>
  {/if}
</div>

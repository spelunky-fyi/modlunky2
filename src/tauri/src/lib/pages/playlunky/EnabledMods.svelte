<script lang="ts">
  import { enabledMods, filteredEnabledMods, mods, searchInput } from "../../../store";
  import { dndzone } from "svelte-dnd-action";
  import ModListItem from "./ModListItem.svelte";
  import ModListHeader from "./ModListHeader.svelte";

  const flipDurationMs = 120;
  let dragDisabled = true;

  function handleConsider(event: CustomEvent) {
    $mods = [...event.detail.items];
  }

  function handleFinalize(event: CustomEvent) {
    $mods = [...event.detail.items];
    dragDisabled = true;
  }

  function startDrag() {
    dragDisabled = false;
  }

  function stopDrag() {
    dragDisabled = true;
  }
</script>

<ModListHeader count={$enabledMods.length}>Enabled</ModListHeader>
<ul
  use:dndzone={{
    items: $mods,
    dragDisabled,
    flipDurationMs,
    dropTargetStyle: {},
  }}
  on:consider={handleConsider}
  on:finalize={handleFinalize}
  class="flex flex-col"
>
  {#each $filteredEnabledMods as mod (mod.id)}
    <ModListItem
      name={mod.name}
      id={mod.id}
      on:toggle
      on:opendirectory
      on:uninstall
      on:mousedown={startDrag}
      on:touchstart={startDrag}
      on:mouseup={stopDrag}
      on:touchend={stopDrag}
      bind:dragging={dragDisabled}
      draggable={$searchInput.length === 0}
    />
  {/each}
</ul>

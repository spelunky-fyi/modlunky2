<script lang="ts">
  import {
    enabledMods,
    filteredEnabledMods,
    mods,
    searchInput,
toggleMod,
  } from "../../../store";
  import { dndzone } from "svelte-dnd-action";
  import ModListItem from "./ModListItem.svelte";
  import ModListHeader from "./ModListHeader.svelte";
  import { flip } from "svelte/animate";

  const flipDurationMs = 200;
  let dragDisabled = true;

  function handleConsider(event) {
    $mods = [...event.detail.items];
  }

  function handleFinalize(event) {
    $mods = [...event.detail.items];
    dragDisabled = true;
  }

  function startDrag() {
    dragDisabled = false;
  }

  function stopDrag() {
    dragDisabled = true;
  }

  function transformDraggedElement(draggedEl: HTMLElement, data, index) {
    draggedEl.classList.add("animate-pulse");
  }
</script>

<ModListHeader count={$enabledMods.length}>Enabled</ModListHeader>

<section
  use:dndzone={{
    items: $mods,
    dragDisabled,
    flipDurationMs,
    transformDraggedElement,
    dropTargetStyle: {},
  }}
  on:consider={handleConsider}
  on:finalize={handleFinalize}
  class="flex flex-col"
>
  {#each $filteredEnabledMods as mod (mod.id)}
    <div animate:flip={{ duration: flipDurationMs }}>
      <ModListItem
        name={mod.name}
        on:click={() => toggleMod(mod.id)}
        on:mousedown={startDrag}
        on:touchstart={startDrag}
        on:mouseup={stopDrag}
        on:touchend={stopDrag}
        bind:dragging={dragDisabled}
        draggable={$searchInput.length === 0}
      />
    </div>
  {/each}
</section>

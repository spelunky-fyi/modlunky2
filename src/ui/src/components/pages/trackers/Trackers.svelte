<script lang="ts">
  import OptionBoolean from "../../common/OptionBoolean.svelte";
  import { colorKey } from "../../../store";
  import ColorPicker from "./ColorPicker.svelte";

  let showPicker = false;
</script>

<section class="flex-1 flex gap-4">
  <div class="flex-1 flex flex-col gap-2">
    <div class="flex gap-2">
      <button class="btn-lg rounded flex-1">Pacifist</button>
      <OptionBoolean>Show kill count</OptionBoolean>
    </div>
    <div class="flex gap-2">
      <button class="btn-lg rounded flex-1">🐈 Category</button>
      <OptionBoolean>Always show modifiers</OptionBoolean>
    </div>
  </div>
  <div class="flex flex-col w-72">
    <div class="flex flex-col gap-2">
      <div class="flex items-center gap-2">
        <h3 class="text-xs whitespace-nowrap">Color Key</h3>
        <input type="text" class="flex-1 input" bind:value={$colorKey} />
        <div
          class="w-8 h-8 shrink-0 rounded"
          style="background-color: {$colorKey}"
        />
      </div>
      <div class="w-full justify-items-stretch flex gap-2 text-xs">
        <button
          class="btn-md rounded flex-1"
          on:click={() => ($colorKey = "#ff00ff")}>Magenta</button
        >
        <button
          class="btn-md rounded flex-1"
          on:click={() => ($colorKey = "#00ff00")}>Green</button
        >
        <button
          class="btn-md rounded flex-1"
          on:click={() => ($colorKey = "#0000ff")}>Blue</button
        >
        {#if !showPicker}
          <button
            class="btn-md rounded flex-1"
            on:click={() => (showPicker = true)}>Custom</button
          >
        {:else}
          <button
            class="btn-md rounded flex-1"
            on:click={() => (showPicker = false)}>Close</button
          >
        {/if}
      </div>
      {#if showPicker}
        <ColorPicker bind:value={$colorKey} />
      {/if}
      <button class="btn-md rounded">Tracker Files</button>
    </div>
  </div>
</section>

<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import Icon from "svelte-awesome";
  import {
    faBars,
    faFolder,
    faTrashAlt,
  } from "@fortawesome/free-solid-svg-icons";

  export let name: string = "Mod Name";
  export let draggable: boolean = false;
  export let dragging: boolean = false;
  export let id: number;

  const dispatch = createEventDispatcher();
</script>

<li class="flex items-center justify-between group hover:bg-zinc-50 dark:hover:bg-zinc-700/50 transition">
  <div
    class="flex-1 flex items-center gap-2 p-2 cursor-pointer"
    on:click={() => dispatch("toggle", id)}
  >
    <div class="bg-zinc-200 dark:bg-zinc-600/50 border border-dashed border-zinc-100/50 dark:border-zinc-600/50 w-8 h-8" />
    <h3 class="font-semibold">{name}</h3>
  </div>
  <div class="flex p-2 gap-1 opacity-0 group-hover:opacity-80 transition">
    <button
      class="flex items-center justify-center w-8 h-8 hover:bg-zinc-300 dark:hover:bg-zinc-600/50 rounded transition"
      on:click={() => dispatch("opendirectory", id)}
      ><Icon data={faFolder} /></button
    >
    <button
      class="flex items-center justify-center w-8 h-8 hover:bg-zinc-300 transition dark:hover:bg-zinc-600/50 rounded transition"
      on:click={() => dispatch("uninstall", id)}
      ><Icon data={faTrashAlt} /></button
    >
    {#if draggable}
      <div
        class="flex items-center justify-center w-8 h-8 rounded transition hover:bg-zinc-300 dark:hover:bg-zinc-600/50"
        class:cursor-grab={dragging}
        class:cursor-grabbing={!dragging}
        on:mousedown
        on:mouseup
        on:touchstart
        on:touchend
      >
        <Icon data={faBars} />
      </div>
    {/if}
  </div>
</li>

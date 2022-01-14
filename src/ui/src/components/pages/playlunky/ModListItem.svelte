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

<li class="flex items-center justify-between group">
  <div
    class="flex-1 flex items-center gap-2 p-2 cursor-pointer"
    on:click={() => dispatch("toggle", id)}
  >
    <div
      class="w-8 h-8 elevation-2"
    />
    <h3 class="font-semibold">{name}</h3>
  </div>
  <div class="flex p-2 gap-1 opacity-0 group-hover:opacity-80 transition">
    <button
      class="btn-md border-0 bg-opacity-0 hover:bg-opacity-100 px-1.5"
      on:click={() => dispatch("opendirectory", id)}
      ><Icon data={faFolder} /></button
    >
    <button
      class="btn-md border-0 bg-opacity-0 hover:bg-opacity-100 px-1.5"
      on:click={() => dispatch("uninstall", id)}
      ><Icon data={faTrashAlt} /></button
    >
    {#if draggable}
      <div
        class="btn-md border-0 bg-opacity-0 hover:bg-opacity-100 px-1.5"
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

<script lang="ts">
  import Icon from "svelte-awesome";
  import {
    faBars,
    faFolder,
    faTrashAlt,
  } from "@fortawesome/free-solid-svg-icons";

  export let name: string = "Mod Name";
  export let draggable: boolean = false;
  export let dragging: boolean = false;
</script>

<section
  on:click
  class="flex items-center justify-between p-2 cursor-pointer hover:bg-zinc-50"
>
  <div class="flex items-center gap-2">
    <div class="bg-gray-200 w-8 h-8" />
    <h3>{name}</h3>
  </div>
  <div class="flex gap-1">
    <button
      class="flex items-center justify-center w-7 h-7 hover:bg-gray-300 rounded transition"
      ><Icon data={faFolder} /></button
    >
    <button
      class="flex items-center justify-center w-7 h-7 hover:bg-gray-300 rounded transition"
      ><Icon data={faTrashAlt} /></button
    >
    {#if draggable}
      <div
        class="flex items-center justify-center w-7 h-7 rounded transition hover:bg-gray-300"
        class:cursor-grab={dragging}
        class:cursor-move={!dragging}
        on:mousedown
        on:mouseup
        on:touchstart
        on:touchend
      ><Icon data={faBars} /></div>
    {/if}
  </div>
</section>

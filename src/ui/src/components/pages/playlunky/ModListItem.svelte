<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import Icon from "svelte-awesome";
  import {
    faBars,
    faFolder,
    faTrashAlt,
  } from "@fortawesome/free-solid-svg-icons";
  import { Stack, Text } from "../../common";
  import ModLogo from "./ModLogo.svelte";
  import ModListItemButton from "./ModListItemButton.svelte";

  export let name: string = "Mod Name";
  export let draggable: boolean = false;
  export let dragging: boolean = false;
  export let id: number;

  const dispatch = createEventDispatcher();
</script>

<Stack justify="between" class="group">
  <Stack
    align="center"
    spacing="small"
    class="flex-1 p-2 cursor-pointer"
    on:click={() => dispatch("toggle", id)}
  >
    <ModLogo />
    <Text level="h3" class="font-black font-roboto">{name}</Text>
  </Stack>

  <Stack
    spacing="small"
    class="p-2 opacity-0 group-hover:opacity-80 transition"
  >
    <ModListItemButton on:click={() => dispatch("opendirectory", id)}>
      <Icon data={faFolder} />
    </ModListItemButton>
    <ModListItemButton on:click={() => dispatch("uninstall", id)}>
      <Icon data={faTrashAlt} />
    </ModListItemButton>
    {#if draggable}
      <ModListItemButton
        class={dragging ? "cursor-grab" : "cursor-grabbing"}
        on:mousedown
        on:mouseup
        on:touchstart
        on:touchend
      >
        <Icon data={faBars} />
      </ModListItemButton>
    {/if}
  </Stack>
</Stack>

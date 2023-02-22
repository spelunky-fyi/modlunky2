<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import { Stack, Text } from "../../common";
  import ModLogo from "./ModLogo.svelte";
  import ModListItemButton from "./ModListItemButton.svelte";

  export let name = "Mod Name";
  export let draggable = false;
  export let dragging = false;
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
      <div class="i-fa-solid-folder" />
    </ModListItemButton>
    <ModListItemButton on:click={() => dispatch("uninstall", id)}>
      <div class="i-fa-solid-trash-alt" />
    </ModListItemButton>
    {#if draggable}
      <ModListItemButton
        styleClass={dragging ? "cursor-grab" : "cursor-grabbing"}
        on:mousedown
        on:mouseup
        on:touchstart
        on:touchend
      >
        <div class="i-fa-solid-bars" />
      </ModListItemButton>
    {/if}
  </Stack>
</Stack>

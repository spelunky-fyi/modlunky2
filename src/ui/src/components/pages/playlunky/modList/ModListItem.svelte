<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import IconFolder from "~icons/tabler/folder";
  import IconTrash from "~icons/tabler/trash";
  import IconGripHorizontal from "~icons/tabler/grip-horizontal";
  import { Stack, Text } from "@/components/common";
  import ModListItemButton from "./ModListItemButton.svelte";

  export let name = "Mod Name";
  export let draggable = false;
  export let dragging = false;
  export let id: number;

  const dispatch = createEventDispatcher();
</script>

<Stack
  justify="between"
  class="group rounded-md transition hover:bg-theme-900/50 hover:shadow-md active:bg-theme-700"
>
  <Stack
    align="center"
    spacing="sm"
    class="flex-1 cursor-pointer p-2"
    on:click={() => dispatch("toggle", id)}
  >
    <div class="aspect-square h-full bg-black/20" />
    <Text level="h3">{name}</Text>
  </Stack>

  <Stack spacing="sm" class="opacity-0 transition group-hover:opacity-80">
    <ModListItemButton on:click={() => dispatch("opendirectory", id)}>
      <IconFolder />
    </ModListItemButton>
    <ModListItemButton on:click={() => dispatch("uninstall", id)}>
      <IconTrash />
    </ModListItemButton>
    {#if draggable}
      <ModListItemButton
        class={dragging ? "cursor-grab" : "cursor-grabbing"}
        on:mousedown
        on:mouseup
        on:touchstart
        on:touchend
      >
        <IconGripHorizontal />
      </ModListItemButton>
    {/if}
  </Stack>
</Stack>

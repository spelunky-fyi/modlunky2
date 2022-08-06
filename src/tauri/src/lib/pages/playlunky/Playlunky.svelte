<script lang="ts">
  import { searchInput, toggleMod } from "../../../store";
  import EnabledMods from "./EnabledMods.svelte";
  import InstalledMods from "./InstalledMods.svelte";
  import PlaylunkyOptions from "./PlaylunkyOptions.svelte";
  import { Button, TextInput, Stack } from "../../common";

  function handleToggle(event: CustomEvent) {
    toggleMod(event.detail);
  }

  function handleOpenDirectory(event: CustomEvent) {
    // TODO
    console.log(event);
  }

  function handleUninstall(event: CustomEvent) {
    // TODO
    console.log(event);
  }

  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      $searchInput = "";
    }
  }
</script>

<Stack class="flex-1 gap-4">
  <Stack direction="vertical" spacing="none" class="flex-1 justify-between">
    <Stack direction="vertical" spacing="none">
      <Stack class="mb-2" spacing="small">
        <Button size="small">
          <div class="i-fa-solid-sync-alt" />
        </Button>
        <Button size="small">
          <div class="i-fa-solid-folder" />
        </Button>
        <TextInput
          placeholder="Search mods..."
          class="flex-1"
          bind:value={$searchInput}
          on:keydown={handleKeyDown}
        />
      </Stack>

      <EnabledMods
        on:toggle={handleToggle}
        on:opendirectory={handleOpenDirectory}
        on:uninstall={handleUninstall}
      />

      <InstalledMods
        on:toggle={handleToggle}
        on:opendirectory={handleOpenDirectory}
        on:uninstall={handleUninstall}
      />
    </Stack>

    <Button color="primary" size="huge">Play</Button>
  </Stack>

  <PlaylunkyOptions />
</Stack>

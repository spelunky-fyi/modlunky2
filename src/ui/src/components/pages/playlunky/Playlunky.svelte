<script lang="ts">
  import { searchInput, toggleMod } from "../../../store";
  import Icon from "svelte-awesome";
  import { faFolder, faSyncAlt } from "@fortawesome/free-solid-svg-icons";
  import EnabledMods from "./EnabledMods.svelte";
  import InstalledMods from "./InstalledMods.svelte";
  import PlaylunkyOptions from "./PlaylunkyOptions.svelte";
  import { Button, TextInput, Stack } from "../../common";

  function handleToggle(event) {
    toggleMod(event.detail);
  }

  function handleOpenDirectory(event) {
    // TODO
  }

  function handleUninstall(event) {
    // TODO
  }

  function handleKeyDown(event) {
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
          <Icon data={faSyncAlt} />
        </Button>
        <Button size="small">
          <Icon data={faFolder} />
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

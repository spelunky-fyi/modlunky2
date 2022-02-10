<script lang="ts">
  import { Stack } from "@/components/common";
  import { toggleMod } from "@/store";
  import ModListSearch from "./ModListSearch.svelte";
  import EnabledMods from "./EnabledMods.svelte";
  import InstalledMods from "./InstalledMods.svelte";

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
</script>

<Stack vertical spacing="sm">
  <ModListSearch />
  <div class="p-3">
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
  </div>
</Stack>

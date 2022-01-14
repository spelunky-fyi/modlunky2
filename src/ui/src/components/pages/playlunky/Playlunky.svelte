<script lang="ts">
  import { faFolder, faSyncAlt } from "@fortawesome/free-solid-svg-icons";
  import Icon from "svelte-awesome";
  import { searchInput, toggleMod } from "../../../store";
  import EnabledMods from "./EnabledMods.svelte";
  import InstalledMods from "./InstalledMods.svelte";
  import PlaylunkyOptions from "./PlaylunkyOptions.svelte";

  function handleToggle(event) {
    toggleMod(event.detail);
  }

  function handleOpenDirectory(event) {
    // TODO
  }

  function handleUninstall(event) {
    // TODO
  }
</script>

<section class="flex flex-1 gap-4">
  <div class="flex-1 flex flex-col justify-between">
    <div class="flex flex-col">
      <div class="flex text-sm gap-2 mb-2">
        <button class="btn-md w-9 rounded"><Icon data={faSyncAlt} /></button>
        <button class="btn-md w-9 rounded"><Icon data={faFolder} /></button>
        <input
          type="text"
          class="flex-1 input"
          placeholder="Search mods..."
          bind:value={$searchInput}
        />
      </div>
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
    <button class="btn-lg">Play</button>
  </div>
  <PlaylunkyOptions />
</section>

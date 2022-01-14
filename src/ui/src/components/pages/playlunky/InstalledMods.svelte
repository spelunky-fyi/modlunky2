<script lang="ts">
  import { filteredInstalledMods } from "../../../store";
  import ModListHeader from "./ModListHeader.svelte";
  import ModListItem from "./ModListItem.svelte";
</script>

<ModListHeader count={$filteredInstalledMods.length}>Installed</ModListHeader>
<ul>
  {#each $filteredInstalledMods as mod (mod.id)}
    <ModListItem
      name={mod.name}
      id={mod.id}
      on:toggle
      on:opendirectory
      on:uninstall
    />
  {/each}
</ul>

<script lang="ts">
  import { filteredInstalledMods, toggleMod } from "../../../store";
  import ModListHeader from "./ModListHeader.svelte";
  import ModListItem from "./ModListItem.svelte";
</script>

<ModListHeader count={$filteredInstalledMods.length}>Installed</ModListHeader>
<ul>
    {#each $filteredInstalledMods as mod (mod.id)}
      <ModListItem name={mod.name} 
        on:click={() => toggleMod(mod.id)}
       />
    {/each}
</ul>

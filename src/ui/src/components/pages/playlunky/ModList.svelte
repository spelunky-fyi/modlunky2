<script lang="ts">
  import ModListHeader from "./ModListHeader.svelte";
  import ModListItem from "./ModListItem.svelte";
  import { mods } from "../../../store";
  import InputText from "../../common/InputText.svelte";
  import { faFolder, faSyncAlt } from "@fortawesome/free-solid-svg-icons";
  import Icon from "svelte-awesome";

  let searchInput = "";

  $: filteredMods = $mods.filter((mod) =>
    mod.name.toLowerCase().includes(searchInput)
  );
  $: enabledMods = filteredMods.filter((mod) => mod.enabled);
  $: installedMods = filteredMods.filter((mod) => !mod.enabled);

  function toggleMod(id) {
    mods.update((arr) =>
      arr.map((mod) =>
        mod.id === id ? { ...mod, enabled: !mod.enabled } : mod
      )
    );
  }
</script>

<div class="flex flex-col gap-2 overflow-hidden">
  <div class="flex text-sm gap-2">
    <button class="btn-md w-9 rounded"><Icon data={faSyncAlt} /></button>
    <button class="btn-md w-9 rounded"><Icon data={faFolder} /></button>
    <InputText class="flex-1" placeholder="Search mods..." bind:value={searchInput} />
  </div>

  <div class="relative gap-2 overflow-auto">
    <ul class="overflow-y-auto">
      <ModListHeader count={enabledMods.length}>Enabled</ModListHeader>
      {#if enabledMods}
        {#each enabledMods as mod (mod.id)}
          <ModListItem name={mod.name} on:click={() => toggleMod(mod.id)} />
        {/each}
      {/if}
      <ModListHeader count={installedMods.length}>Installed</ModListHeader>
      {#if installedMods}
        {#each installedMods as mod (mod.id)}
          <ModListItem name={mod.name} on:click={() => toggleMod(mod.id)} />
        {/each}
      {/if}
    </ul>
  </div>
</div>

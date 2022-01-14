<script lang="ts">
  import FileSelect from "../../common/FileSelect.svelte";
  import OptionBoolean from "../../common/OptionBoolean.svelte";
  import OptionGroup from "../../common/OptionGroup.svelte";
</script>

<section class="flex-1 flex flex-col gap-4">
  <OptionGroup>
    <h2 slot="heading">Game Install Directory</h2>
    <input
      type="text"
      class="input"
      value="C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2"
    />
    <div class="flex gap-2">
      <button class="flex-1 btn-md rounded">Browse</button>
      <button class="flex-1 btn-md rounded">I'm Feeling Lucky</button>
      <button class="flex-1 btn-md rounded">Clear</button>
    </div>
  </OptionGroup>
  <OptionGroup>
    <h2 slot="heading">spelunky.fyi Settings</h2>
    <button class="btn-md rounded">Update API Token</button>
  </OptionGroup>
  <OptionGroup>
    <h2 slot="heading">User Directories</h2>
    <div class="flex gap-2">
      <button class="flex-1 btn-md rounded">Cache</button>
      <button class="flex-1 btn-md rounded">Data</button>
      <button class="flex-1 btn-md rounded">Config</button>
      <button class="flex-1 btn-md rounded">Game</button>
    </div>
  </OptionGroup>
</section>

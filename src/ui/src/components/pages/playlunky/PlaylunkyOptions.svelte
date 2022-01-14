<script lang="ts">
  import OptionBoolean from "../../common/OptionBoolean.svelte";
  import OptionNumber from "../../common/OptionNumber.svelte";
  import OptionGroup from "../../common/OptionGroup.svelte";
  import VersionSelect from "./VersionSelect.svelte";
</script>

<div class="flex flex-col justify-between w-72">
  <div class="flex flex-col gap-2">
    <VersionSelect />

    <OptionGroup>
      <h3 slot="heading">General</h3>
      <OptionBoolean>Enable loose file warning</OptionBoolean>
      <OptionBoolean>Disable asset caching</OptionBoolean>
      <OptionBoolean>Speedrun mode</OptionBoolean>
      <OptionBoolean>Block save game</OptionBoolean>
      <OptionBoolean>Allow save game mods</OptionBoolean>
      <OptionBoolean>Leave terminal running</OptionBoolean>
      <OptionBoolean>Desktop Shortcut</OptionBoolean>
    </OptionGroup>

    <OptionGroup>
      <h3 slot="heading">Scripts</h3>
      <OptionBoolean>Enable developer mode</OptionBoolean>
      <OptionBoolean>Enable developer console</OptionBoolean>
      <OptionNumber value={20}>Console history size</OptionNumber>
    </OptionGroup>

    <OptionGroup>
      <h3 slot="heading">Audio</h3>
      <OptionBoolean>Enable loose audio files</OptionBoolean>
      <OptionBoolean>Cache decoded audio files</OptionBoolean>
      <OptionBoolean>Synchronous Update</OptionBoolean>
    </OptionGroup>

    <OptionGroup>
      <h3 slot="heading">Sprites</h3>
      <OptionBoolean>Random character select</OptionBoolean>
      <OptionBoolean>Generate character journal stickers</OptionBoolean>
      <OptionBoolean>Generate character journal entries</OptionBoolean>
      <OptionBoolean>Generate sticker pixel art</OptionBoolean>
      <OptionBoolean>Enable sprite hot loading</OptionBoolean>
      <OptionNumber value={500}>Sprite hot load delay</OptionNumber>
    </OptionGroup>
  </div>

  <div class="flex flex-col gap-2 text-xs">
    <button class="btn-md rounded">Open packs directory</button>
    <button class="btn-md rounded">User guide</button>
    <button class="btn-md rounded">Check for mod updates</button>
    <button class="btn-md rounded">Clear cache</button>
  </div>
</div>

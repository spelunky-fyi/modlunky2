<script lang="ts">
  import {
    Button,
    Stack,
    Text,
    OptionBoolean,
    OptionGroup,
    OptionNumber,
  } from "../../common";
  import VersionSelect from "./VersionSelect.svelte";
</script>

<Stack direction="vertical" justify="between" spacing="small" class="w-72">
  <Stack direction="vertical" spacing="small" class="overflow-y-auto">
    <VersionSelect />

    <OptionGroup>
      <Text level="h3" slot="heading">General</Text>
      <OptionBoolean>Enable loose file warning</OptionBoolean>
      <OptionBoolean>Disable asset caching</OptionBoolean>
      <OptionBoolean>Speedrun mode</OptionBoolean>
      <OptionBoolean>Block save game</OptionBoolean>
      <OptionBoolean>Allow save game mods</OptionBoolean>
      <OptionBoolean>Leave terminal running</OptionBoolean>
      <OptionBoolean>Desktop Shortcut</OptionBoolean>
    </OptionGroup>

    <OptionGroup>
      <Text slot="heading">Scripts</Text>
      <OptionBoolean>Enable developer mode</OptionBoolean>
      <OptionBoolean>Enable developer console</OptionBoolean>
      <OptionNumber value={20}>Console history size</OptionNumber>
    </OptionGroup>

    <OptionGroup>
      <Text slot="heading">Audio</Text>
      <OptionBoolean>Enable loose audio files</OptionBoolean>
      <OptionBoolean>Cache decoded audio files</OptionBoolean>
      <OptionBoolean>Synchronous Update</OptionBoolean>
    </OptionGroup>

    <OptionGroup>
      <Text slot="heading">Sprites</Text>
      <OptionBoolean>Random character select</OptionBoolean>
      <OptionBoolean>Generate character journal stickers</OptionBoolean>
      <OptionBoolean>Generate character journal entries</OptionBoolean>
      <OptionBoolean>Generate sticker pixel art</OptionBoolean>
      <OptionBoolean>Enable sprite hot loading</OptionBoolean>
      <OptionNumber value={500}>Sprite hot load delay</OptionNumber>
    </OptionGroup>
  </Stack>

  <Stack direction="vertical" spacing="small">
    <Button>Open packs directory</Button>
    <Button>User guide</Button>
    <Button>Check for mod updates</Button>
    <Button>Clear cache</Button>
  </Stack>
</Stack>

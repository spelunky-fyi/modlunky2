<script lang="ts">
  import { Button, Checkbox, Stack, Text, Panel, InputNumber } from "../../common";
  import VersionSelect from "./VersionSelect.svelte";
</script>

<Stack vertical justify="between" spacing="sm" class="min-h-0 w-72">
  <div class="flex flex-1 overflow-auto pt-4 pr-2">
    <Stack vertical spacing="sm" class="scrollbar flex-1 overflow-y-auto text-xs">
      <VersionSelect />

      <Panel padding="sm">
        <Stack vertical spacing="sm">
          <Text level="h4" class="-mt-1 text-center leading-none opacity-50">General</Text>
          <Checkbox size="sm">Enable loose file warning</Checkbox>
          <Checkbox size="sm">Enable loose file warning</Checkbox>
          <Checkbox size="sm">Disable asset caching</Checkbox>
          <Checkbox size="sm">Speedrun mode</Checkbox>
          <Checkbox size="sm">Block save game</Checkbox>
          <Checkbox size="sm">Allow save game mods</Checkbox>
          <Checkbox size="sm">Leave terminal running</Checkbox>
          <Checkbox size="sm">Desktop Shortcut</Checkbox>
        </Stack>
      </Panel>

      <Panel padding="sm">
        <Stack vertical spacing="sm">
          <Text level="h4" class="-mt-1 text-center leading-none opacity-50">Scripts</Text>
          <Checkbox size="sm">Enable developer mode</Checkbox>
          <Checkbox size="sm">Enable developer console</Checkbox>
          <InputNumber size="sm" value={20}>Console history size</InputNumber>
        </Stack>
      </Panel>

      <Panel padding="sm">
        <Stack vertical spacing="sm">
          <Text level="h4" class="-mt-1 text-center leading-none opacity-50">Audio</Text>
          <Checkbox size="sm">Enable loose audio files</Checkbox>
          <Checkbox size="sm">Cache decoded audio files</Checkbox>
          <Checkbox size="sm">Synchronous Update</Checkbox>
        </Stack>
      </Panel>

      <Panel padding="sm">
        <Stack vertical spacing="sm">
          <Text level="h4" class="-mt-1 text-center leading-none opacity-50">Sprites</Text>
          <Checkbox size="sm">Random character select</Checkbox>
          <Checkbox size="sm">Generate character journal stickers</Checkbox>
          <Checkbox size="sm">Generate character journal entries</Checkbox>
          <Checkbox size="sm">Generate sticker pixel art</Checkbox>
          <Checkbox size="sm">Enable sprite hot loading</Checkbox>
          <InputNumber size="sm" value={500}>Sprite hot load delay</InputNumber>
        </Stack>
      </Panel>
    </Stack>
  </div>

  <Stack vertical spacing="sm" class="shrink-0 p-4">
    <Button size="sm">Open packs directory</Button>
    <Button size="sm">User guide</Button>
    <Button size="sm">Check for mod updates</Button>
    <Button size="sm">Clear cache</Button>
  </Stack>
</Stack>

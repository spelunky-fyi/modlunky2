<script lang="ts">
  import { colorKey } from "../../../store";
  import { Button, ColorInput, Stack, OptionBoolean, TextInput } from "../../common";
</script>

<section class="flex-1 flex gap-4">
  <Stack direction="vertical" spacing="small" class="flex-1">
    <Stack spacing="small">
      <Button size="huge" class="flex-1">Pacifist</Button>
      <OptionBoolean>Show kill count</OptionBoolean>
    </Stack>
    <Stack spacing="small">
      <Button size="huge" class="flex-1">🐈 Category</Button>
      <OptionBoolean>Always show modifiers</OptionBoolean>
    </Stack>
  </Stack>
  <Stack direction="vertical" class="w-72">
    <Stack direction="vertical" spacing="small">
      <Stack align="center" spacing="small" class="relative">
        <ColorInput
          bind:value={$colorKey}
          class="absolute inset-y-2 right-2 shrink-0 cursor-pointer"
        />
        <TextInput bind:value={$colorKey} label="Color Key" />
      </Stack>
      <Stack spacing="small">
        <Button size="tiny" class="flex-1" on:click={() => ($colorKey = "#ff00ff")}>Magenta</Button>
        <Button size="tiny" class="flex-1" on:click={() => ($colorKey = "#00ff00")}>Green</Button>
        <Button size="tiny" class="flex-1" on:click={() => ($colorKey = "#0000ff")}>Blue</Button>
      </Stack>
      <Button>Tracker Files</Button>
    </Stack>
  </Stack>
</section>

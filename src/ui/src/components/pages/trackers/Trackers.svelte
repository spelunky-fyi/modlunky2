<script lang="ts">
  import { colorKey } from "@/store";
  import { Button, Checkbox, InputColor, Stack, Panel, InputText } from "@/components/common";
</script>

<div class="center h-full">
  <Panel padding="lg">
    <Stack>
      <Stack vertical spacing="sm" class="flex-2">
        <Stack spacing="sm">
          <Button size="lg" class="flex-1">Pacifist</Button>
          <Checkbox>Show kill count</Checkbox>
        </Stack>
        <Stack spacing="sm">
          <Button size="lg" class="flex-1">🐈 Category</Button>
          <Checkbox>Always show modifiers</Checkbox>
        </Stack>
      </Stack>
      <Stack vertical class="w-72">
        <Stack vertical>
          <div class="relative flex items-center gap-1">
            <InputColor bind:value={$colorKey} class="absolute inset-y-1 right-1 h-6 w-6" />
            <InputText bind:value={$colorKey} label="Color Key" />
          </div>
          <Stack spacing="sm">
            <Button size="sm" class="flex-1" on:click={() => ($colorKey = "#ff00ff")}
              >Magenta</Button
            >
            <Button size="sm" class="flex-1" on:click={() => ($colorKey = "#00ff00")}>Green</Button>
            <Button size="sm" class="flex-1" on:click={() => ($colorKey = "#0000ff")}>Blue</Button>
          </Stack>
          <Button>Tracker Files</Button>
        </Stack>
      </Stack>
    </Stack>
  </Panel>
</div>

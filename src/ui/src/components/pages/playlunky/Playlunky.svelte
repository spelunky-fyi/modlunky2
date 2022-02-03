<script lang="ts">
  import PlaylunkyOptions from "./PlaylunkyOptions.svelte";
  import { Button, Panel, Stack } from "../../common";
  import Console from "../../Console.svelte";
  import ModList from "./modList/ModList.svelte";
</script>

<Stack class="h-full" spacing="none">
  <Stack vertical class="flex-1">
    <Stack vertical class="h-full p-4">
      <Panel padding="none">
        <ModList />
      </Panel>
      <Button primary size="lg" class="mt-auto">Play</Button>
    </Stack>
    <Console />
  </Stack>
  <PlaylunkyOptions />
</Stack>

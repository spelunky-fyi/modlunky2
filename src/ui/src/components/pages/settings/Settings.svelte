<script lang="ts">
  import { Button, Panel, Stack, Text, InputText } from "../../common";
</script>

<div class="center h-full">
  <Panel padding="lg" class="container">
    <Stack vertical spacing="lg">
      <Text level="h3">Game Install Directory</Text>
      <InputText value="C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2" class="text-xl" />
      <Stack spacing="sm">
        <Button class="flex-1">Browse</Button>
        <Button class="flex-1">I'm Feeling Lucky</Button>
        <Button class="flex-1">Clear</Button>
      </Stack>
      <Text level="h3">spelunky.fyi Settings</Text>
      <Button>Update API Token</Button>
      <Text level="h3">User Directories</Text>
      <Stack spacing="sm">
        <Button class="flex-1">Cache</Button>
        <Button class="flex-1">Data</Button>
        <Button class="flex-1">Config</Button>
        <Button class="flex-1">Game</Button>
      </Stack>
    </Stack>
  </Panel>
</div>

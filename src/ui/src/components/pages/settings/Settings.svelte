<script lang="ts">
  import {
    Button,
    Panel,
    Stack,
    Text,
    TextInput,
    OptionGroup,
  } from "../../common";
</script>

<Stack align="center" justify="center" class="p-16 flex-1">
  <Panel rounded padding="huge" class="min-w-180">
    <Stack direction="vertical" spacing="large">
      <OptionGroup>
        <Text level="h3" slot="heading">Game Install Directory</Text>
        <TextInput
          value="C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2"
          class="text-xl"
        />
        <Stack spacing="small">
          <Button class="flex-1">Browse</Button>
          <Button class="flex-1">I'm Feeling Lucky</Button>
          <Button class="flex-1">Clear</Button>
        </Stack>
      </OptionGroup>
      <OptionGroup>
        <Text level="h3" slot="heading">spelunky.fyi Settings</Text>
        <Button>Update API Token</Button>
      </OptionGroup>
      <OptionGroup>
        <Text level="h3" slot="heading">User Directories</Text>
        <Stack spacing="small">
          <Button class="flex-1">Cache</Button>
          <Button class="flex-1">Data</Button>
          <Button class="flex-1">Config</Button>
          <Button class="flex-1">Game</Button>
        </Stack>
      </OptionGroup>
    </Stack>
  </Panel>
</Stack>

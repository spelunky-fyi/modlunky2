<script lang="ts">
  import {
    Button,
    FileSelect,
    Panel,
    Stack,
    Text,
    TextInput,
  } from "../../common";
</script>

<Stack align="center" justify="center" class="flex-1">
  <Stack justify="center">
    <Panel rounded padding="large">
      <Stack
        direction="vertical"
        justify="between"
        spacing="small"
        class="h-full"
      >
        <Text level="h3">spelunky.fyi Installation</Text>
        <Text level="h2" class="mt-auto">Install Code</Text>
        <Text level="p"
          >Enter the 'Install Code' from a mod page on spelunky.fyi</Text
        >
        <Stack spacing="small">
          <TextInput class="flex-1" />
          <Button color="primary">Install</Button>
        </Stack>
      </Stack>
    </Panel>
    <Panel rounded padding="large">
      <Stack direction="vertical" spacing="large">
        <Text level="h3">Local Installation</Text>
        <Stack direction="vertical" spacing="small">
          <Text level="h2">Source</Text>
          <Text level="p">Choose the file you want to install</Text>
          <FileSelect />
        </Stack>
        <Stack direction="vertical" spacing="small">
          <Text level="h2">Destination</Text>
          <Text level="p">Choose or create a pack</Text>
          <FileSelect />
        </Stack>
      </Stack>
    </Panel>
  </Stack>
</Stack>

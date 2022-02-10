<script lang="ts">
  import { Button, InputFile, Panel, Stack, Text, InputText } from "@/components/common";
</script>

<div class="center h-full">
  <Stack justify="center">
    <Panel padding="lg">
      <Stack vertical justify="between" spacing="sm" class="h-full">
        <Text level="h3">spelunky.fyi Installation</Text>
        <Text level="h2" class="mt-auto">Install Code</Text>
        <Text level="p">Enter the 'Install Code' from a mod page on spelunky.fyi</Text>
        <Stack spacing="sm">
          <InputText class="flex-1" />
          <Button primary>Install</Button>
        </Stack>
      </Stack>
    </Panel>
    <Panel padding="lg">
      <Stack vertical spacing="lg">
        <Text level="h3">Local Installation</Text>
        <Stack vertical spacing="sm">
          <Text level="h2">Source</Text>
          <Text level="p">Choose the file you want to install</Text>
          <InputFile />
        </Stack>
        <Stack vertical spacing="sm">
          <Text level="h2">Destination</Text>
          <Text level="p">Choose or create a pack</Text>
          <InputFile />
        </Stack>
      </Stack>
    </Panel>
  </Stack>
</div>

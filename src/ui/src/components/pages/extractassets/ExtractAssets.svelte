<script>
  import { Button, Stack, Text, InputFile, Checkbox, Panel } from "@/components/common";
</script>

<div class="center h-full">
  <Panel>
    <Stack vertical class="w-96" spacing="lg">
      <InputFile />
      <Button size="lg" primary>Extract</Button>
      <Button>Open Extract Directory</Button>
      <Stack vertical spacing="sm">
        <Text level="h4">Options</Text>
        <Checkbox size="sm">Create entity sprites</Checkbox>
        <Checkbox size="sm">Generate string hashes</Checkbox>
        <Checkbox size="sm">Extract .wav files</Checkbox>
        <Checkbox size="sm">Extract .ogg files</Checkbox>
        <Checkbox size="sm">Reuse extracted assets</Checkbox>
      </Stack>
    </Stack>
  </Panel>
</div>

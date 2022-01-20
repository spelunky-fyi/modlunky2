<script>
  import {
    Button,
    Stack,
    Text,
    FileSelect,
    OptionBoolean,
    OptionGroup,
  } from "../../common";
</script>

<section class="flex-1 flex gap-4">
  <Stack direction="vertical" class="flex-1">
    <FileSelect />
    <Button size="large" color="primary">Extract</Button>
  </Stack>
  <Stack direction="vertical" spacing="small" class="w-72">
    <Button>Open Extract Directory</Button>
    <OptionGroup>
      <Text level="h3" slot="heading">Options</Text>
      <OptionBoolean>Create entity sprites</OptionBoolean>
      <OptionBoolean>Generate string hashes</OptionBoolean>
      <OptionBoolean>Extract .wav files</OptionBoolean>
      <OptionBoolean>Extract .ogg files</OptionBoolean>
      <OptionBoolean>Reuse extracted assets</OptionBoolean>
    </OptionGroup>
  </Stack>
</section>

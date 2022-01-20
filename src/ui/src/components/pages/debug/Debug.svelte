<script lang="ts">
  import { Button, Panel, Stack, Text } from "../../common";

  const buttonColors: ButtonColor[] = [
    "default",
    "primary",
    "transparent",
    "warning",
    "danger",
    "info",
  ];

  const buttonSizes: ButtonSize[] = ["tiny", "small", "default", "large", "huge"];
</script>

<Stack align="center" justify="center" class="flex-1">
  <Panel rounded>
    <Stack>
      <Stack direction="vertical" class="p-4" spacing="small">
        <Text level="h1">Heading 1</Text>
        <Text level="h2">Heading 2</Text>
        <Text level="h3">Heading 3</Text>
        <Text level="h4">Heading 4</Text>
        <Text level="h5">Heading 5</Text>
        <Text level="h6">Heading 6</Text>
        <Text level="p">Paragraph</Text>
        <Text level="span">Span</Text>
      </Stack>

      <Stack align="center" spacing="small">
        {#each buttonColors as color}
          <Stack direction="vertical" align="center" spacing="small">
            {#each buttonSizes.reverse() as size}
              <Button {size} {color}>{color}</Button>
            {/each}
          </Stack>
        {/each}
      </Stack>
    </Stack>
  </Panel>
</Stack>

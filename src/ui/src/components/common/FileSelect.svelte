<script lang="ts">
  import { Button, Stack, TextInput } from "../common";

  let files: FileList;
  let input: HTMLInputElement;
  let text: string;

  $: if (files && files.length > 0) {
    text = files.item(0).name;
  }
</script>

<Stack spacing="small">
  <input bind:files bind:this={input} type="file" class="hidden" />
  <TextInput bind:value={text} class="flex-1" />
  <Button size="small" on:click={() => input.click()}>Browse</Button>
</Stack>

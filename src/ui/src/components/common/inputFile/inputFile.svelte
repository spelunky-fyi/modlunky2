<script lang="ts">
  import Stack from "../stack/stack.svelte";
  import InputText from "../inputText/inputText.svelte";
  import Button from "../button/button.svelte";

  let files: FileList;
  let input: HTMLInputElement;
  let text: string;

  $: if (files && files.length > 0) {
    const file = files.item(0);
    if (file) text = file.name;
  }
</script>

<Stack spacing="sm">
  <input bind:files bind:this={input} type="file" class="hidden" />
  <InputText bind:value={text} size="sm" class="flex-1" />
  <Button size="sm" on:click={() => input.click()}>Browse</Button>
</Stack>

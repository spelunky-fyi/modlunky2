<script lang="ts">
  let files: FileList;
</script>

<div class="flex gap-2">
  <div class="flex-1 flex items-center bg-zinc-50">
    {#if files}
      {#each Array.from(files) as file}
        <span class="px-2">{file.name}</span>
      {/each}
    {/if}
  </div>
  <label class="btn-md cursor-pointer">
    Browse...
    <input type="file" bind:files hidden={true} />
  </label>
</div>

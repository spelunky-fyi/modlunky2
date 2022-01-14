<script lang="ts">
  let files: FileList;
</script>

<div class="flex gap-1.5">
  <div class="flex-1 flex items-center bg-zinc-50 dark:bg-zinc-800/50 rounded">
    {#if files}
      {#each Array.from(files) as file}
        <span class="px-2">{file.name}</span>
      {/each}
    {/if}
  </div>
  <label class="btn-md rounded cursor-pointer">
    Browse...
    <input type="file" bind:files hidden={true} class="bg-opacity-10" />
  </label>
</div>

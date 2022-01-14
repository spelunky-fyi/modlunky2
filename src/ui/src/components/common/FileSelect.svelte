<script lang="ts">
  let files: FileList;
</script>

<div class="flex gap-1.5">
  <div class="flex-1 input">
    {#if files}
      {#each Array.from(files) as file}
        <span class="px-2">{file.name}</span>
      {/each}
    {/if}
  </div>
  <label class="btn-md rounded cursor-pointer">
    Browse...
    <input type="file" bind:files hidden={true} />
  </label>
</div>

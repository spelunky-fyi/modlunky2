<script lang="ts">
  export let value: number = 0;
</script>

<label class="gap-2 text-xs">
  <input type="number" bind:value class="p-1 w-16 dark:bg-zinc-800 rounded dark:focus:bg-zinc-700 transition focus:outline-none" />
  <span><slot /></span>
</label>

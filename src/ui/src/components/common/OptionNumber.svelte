<script lang="ts">
  export let value: number = 0;
</script>

<label class="gap-2 text-xs">
  <input type="number" bind:value class="p-1 w-16" />
  <span><slot /></span>
</label>

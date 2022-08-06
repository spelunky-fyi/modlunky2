<script lang="ts">
  export let value = 0;
</script>

<label class="gap-2 text-xs">
  <input type="number" bind:value class="input p-1 w-16" />
  <span><slot /></span>
</label>

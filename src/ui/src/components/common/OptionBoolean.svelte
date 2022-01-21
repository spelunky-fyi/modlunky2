<script lang="ts">
  export let value = false;
</script>

<label class="flex items-center gap-1.5 text-xs">
  <input type="checkbox" bind:checked={value} class="w-4 h-4" />
  <span><slot /></span>
</label>

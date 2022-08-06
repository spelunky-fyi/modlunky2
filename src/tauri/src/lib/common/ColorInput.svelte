<script lang="ts">
  export let value: string;
</script>

<input
  type="color"
  bind:value
  class="w-8 h-5 rounded overflow-hidden transition {$$restProps.class || ''}"
/>

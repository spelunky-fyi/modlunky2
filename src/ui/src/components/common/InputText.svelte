<script lang="ts">
  export let value: string = "";
  export let placeholder: string = "";
  export let disabled: boolean = false;
</script>

<input
  type="text"
  bind:value
  {placeholder}
  {disabled}
  class="p-2 bg-zinc-50 dark:bg-zinc-800 dark:focus:bg-zinc-700 focus:outline-none rounded transition {$$restProps.class ||
    ''}"
/>

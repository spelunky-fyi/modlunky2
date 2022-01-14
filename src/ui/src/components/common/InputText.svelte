<script lang="ts">
  export let value: string = "";
  export let placeholder: string = "";
  export let disabled: boolean = false;
</script>

<input type="text" bind:value {placeholder} {disabled} class="p-2 bg-zinc-50 focus:outline-none rounded {$$restProps.class || ''}" />

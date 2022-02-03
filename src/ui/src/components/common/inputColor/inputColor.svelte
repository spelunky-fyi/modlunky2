<script lang="ts">
  import classes from "../../../util/classes";

  export let value: string;

  let _class = "";
  export { _class as class };
</script>

<input type="color" bind:value class={classes("input-color", _class)} />

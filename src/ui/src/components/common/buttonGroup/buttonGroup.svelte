<script lang="ts">
  import classes from "../../../util/classes";

  let _class = "";
  export { _class as class };
</script>

<div class={classes("btn-group", _class)}>
  <slot />
</div>

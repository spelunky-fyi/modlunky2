<script lang="ts">
  import classes from "@/util/classes";

  export let level: TextLevel = "p";

  let _class = "";
  export { _class as class };
</script>

{#if level === "span"}
  <span class={classes("text", _class)}><slot /></span>
{:else if level === "p"}
  <p class={classes("text", _class)}><slot /></p>
{:else if level === "h1"}
  <h1 class={classes("text", _class)}><slot /></h1>
{:else if level === "h2"}
  <h2 class={classes("text", _class)}><slot /></h2>
{:else if level === "h3"}
  <h3 class={classes("text", _class)}><slot /></h3>
{:else if level === "h4"}
  <h4 class={classes("text", _class)}><slot /></h4>
{:else if level === "h5"}
  <h5 class={classes("text", _class)}><slot /></h5>
{/if}

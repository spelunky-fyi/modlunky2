<script lang="ts">
  import { onMount } from "svelte";
  import IconLightMode from "~icons/ic/baseline-light-mode";
  import IconDarkMode from "~icons/ic/baseline-dark-mode";
  import { Button } from "./common";
  import classes from "../util/classes";

  const storageKey = "theme-preference";

  const theme = {
    value: getColorPreference(),
  };

  function getColorPreference(): string {
    const item = localStorage.getItem(storageKey);
    if (item) {
      return item;
    } else {
      return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
  }

  function setColorPreference(): void {
    localStorage.setItem(storageKey, theme.value);
    reflectColorPreference();
  }

  function reflectColorPreference() {
    if (theme.value === "dark") {
      document.body.classList.remove("theme-light");
      document.body.classList.add("theme-dark");
    } else {
      document.body.classList.remove("theme-dark");
      document.body.classList.add("theme-light");
    }
  }

  function handleClick() {
    theme.value = theme.value === "light" ? "dark" : "light";
    setColorPreference();
  }

  reflectColorPreference();

  onMount(() => {
    reflectColorPreference();
    window
      .matchMedia("(prefers-color-scheme: dark)")
      .addEventListener("change", ({ matches: isDark }) => {
        theme.value = isDark ? "dark" : "light";
        setColorPreference();
      });
  });

  let _class = "";
  export { _class as class };
</script>

<Button transparent rounded={false} on:click={handleClick} class={classes(_class)}>
  {#if theme.value === "light"}
    <IconDarkMode />
  {:else}
    <IconLightMode />
  {/if}
</Button>

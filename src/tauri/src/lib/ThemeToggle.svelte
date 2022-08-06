<script lang="ts">
  import { faMoon, faSun } from "@fortawesome/free-solid-svg-icons";
  import { onMount } from "svelte";
  import Icon from "svelte-awesome";
  import { Button } from "./common";

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
      document.body.classList.remove("light");
      document.body.classList.add("dark");
    } else {
      document.body.classList.remove("dark");
      document.body.classList.add("light");
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
</script>

<Button color="transparent" on:click={handleClick} class="w-9 h-9 {$$restProps.class || ''}">
  <Icon data={theme.value === "dark" ? faSun : faMoon} />
</Button>

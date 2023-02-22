<script lang="ts">
  import { onMount } from "svelte";
  import Button from "./Button.svelte";

  let open = false;
  let menu: HTMLElement;
  export let styleClass = "";

  onMount(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (open && !menu.contains(event.target as Node)) {
        open = false;
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (open && event.key === "Escape") {
        open = false;
      }
    };

    // add events when element is added to the DOM
    document.addEventListener("click", handleOutsideClick, false);
    document.addEventListener("keyup", handleEscape, false);

    // remove events when element is removed from the DOM
    return () => {
      document.removeEventListener("click", handleOutsideClick, false);
      document.removeEventListener("keyup", handleEscape, false);
    };
  });
</script>

<div class="relative " bind:this={menu}>
  <Button class={styleClass} on:click={() => (open = !open)}>
    <slot />
  </Button>
  {#if open}
    <div class="absolute origin-top-right right-0 w-48 elevation-2">
      <slot name="content" />
    </div>
  {/if}
</div>

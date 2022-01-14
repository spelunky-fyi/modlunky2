<script lang="ts">
  import { onMount } from "svelte";

  let open: boolean = false;
  let menu: HTMLElement = null;

  onMount(() => {
    const handleOutsideClick = (event) => {
      if (open && !menu.contains(event.target)) {
        open = false;
      }
    };

    const handleEscape = (event) => {
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

<div class="relative" bind:this={menu}>
  <button class="btn-md {$$restProps.class || ''}" on:click={() => (open = !open)}>
    <slot />
  </button>
  {#if open}
    <div class="absolute origin-top-right right-0 w-48 elevation-2">
      <slot name="content" />
    </div>
  {/if}
</div>

<script lang="ts">
  import { appWindow } from "@tauri-apps/api/window";
  import IconMinimize from "~icons/mdi/window-minimize";
  import IconMaximize from "~icons/mdi/window-maximize";
  import IconClose from "~icons/mdi/close";
  import { Button } from "./common";
  import ThemeToggle from "./ThemeToggle.svelte";
</script>

<div
  data-tauri-drag-region
  class="relative flex h-8 select-none items-center border-b border-b-theme-800/50 bg-theme-900 px-3 text-theme-200 shadow"
>
  <span class="pointer-events-none text-xs font-semibold">Modlunky 2</span>
  <div class="absolute top-0 right-0 flex h-[30px]">
    <ThemeToggle />
    <Button
      size="sm"
      transparent
      rounded={false}
      class="box-content w-[30px] px-0"
      on:click={() => appWindow.minimize()}
    >
      <IconMinimize /></Button
    >
    <Button
      size="sm"
      transparent
      rounded={false}
      class="box-content w-[30px] px-0"
      on:click={() => appWindow.toggleMaximize()}
    >
      <IconMaximize />
    </Button>
    <Button
      size="sm"
      transparent
      rounded={false}
      class="box-content w-[30px] px-0"
      on:click={() => appWindow.close()}><IconClose /></Button
    >
  </div>
</div>

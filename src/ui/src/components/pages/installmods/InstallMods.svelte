<script lang="ts">
import InputText from "../../common/InputText.svelte";

import FileSelect from "../../common/FileSelect.svelte";

  let installCode;
  let sourceFiles;
  let destinationFolder;
</script>

<section class="flex-1">
  <div class="flex">
    <h2 class="flex-1 flex items-center justify-center text-lg font-medium">spelunky.fyi Installation</h2>
    <h2 class="flex-1 flex items-center justify-center text-lg font-medium">Local Installation</h2>
  </div>
  <div class="h-full grid grid-rows-2 grid-cols-2 gap-4 text-sm place-content-center">
    <div class="row-span-2 flex flex-col gap-2">
      <h3 class="font-medium">Install Code</h3>
      <p class="text-xs">
        Enter the 'Install Code' from a mod page on <a
          class="underline"
          href="https://spelunky.fyi">spelunky.fyi</a
        >
      </p>
      <InputText bind:value={installCode} />
      <button class="btn-lg rounded">Install</button>
    </div>
    <div class="flex flex-col gap-2">
      <h3 class="font-medium">Source</h3>
      <p class="text-xs">Choose the file you want to install</p>
      <FileSelect />
    </div>
    <div class="flex flex-col gap-2">
      <h3 class="font-medium">Destination</h3>
      <p class="text-xs">Choose or create a pack</p>
      <FileSelect />
    </div>
  </div>
</section>

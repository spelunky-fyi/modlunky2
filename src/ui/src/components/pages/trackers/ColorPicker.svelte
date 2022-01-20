<script lang="ts">
  import { onMount } from "svelte";
  import iro from "@jaames/iro";

  let colorPicker;
  export let value: string = "#ffffff";

  onMount(() => {
    colorPicker = iro.ColorPicker(colorPicker, {});

    function handleColorChange(color) {
      value = color.hexString;
    }

    colorPicker.on("color:change", handleColorChange);

    return () => {
      colorPicker.off("color:change", handleColorChange);
    };
  });
</script>

<div bind:this={colorPicker} />

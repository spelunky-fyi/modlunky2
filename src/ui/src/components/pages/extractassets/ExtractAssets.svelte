<script>
import FileSelect from "../../common/FileSelect.svelte";
import OptionBoolean from "../../common/OptionBoolean.svelte";
import OptionGroup from "../../common/OptionGroup.svelte";

let selected;

const executables = [
  "Spel2.exe",
  "Overlunky.exe",
];
</script>

<section class="flex-1 flex gap-4">
  <div class="flex-1 flex flex-col gap-4">
    <FileSelect />
    <button class="btn-lg">Extract</button>
  </div>
  <div class="flex flex-col w-72 gap-2">
    <button class="btn-md">Open Extract Directory</button>
    <OptionGroup>
      <h3 slot="heading">Options</h3>
      <OptionBoolean>Create entity sprites</OptionBoolean>
      <OptionBoolean>Generate string hashes</OptionBoolean>
      <OptionBoolean>Extract .wav files</OptionBoolean>
      <OptionBoolean>Extract .ogg files</OptionBoolean>
      <OptionBoolean>Reuse extracted assets</OptionBoolean>
    </OptionGroup>
  </div>
</section>
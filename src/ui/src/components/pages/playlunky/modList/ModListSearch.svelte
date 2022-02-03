<script lang="ts">
  import { Button, Stack, InputText } from "../../../common";
  import { searchInput } from "../../../../store";
  import IconRefresh from "~icons/ic/baseline-refresh";
  import IconFolder from "~icons/ic/baseline-folder-open";

  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      $searchInput = "";
    }
  }
</script>

<Stack class="px-2 pt-2">
  <Button outline size="sm">
    <IconRefresh />
  </Button>
  <Button outline size="sm">
    <IconFolder />
  </Button>
  <InputText
    placeholder="Search mods..."
    class="flex-1"
    bind:value={$searchInput}
    on:keydown={handleKeyDown}
  />
</Stack>

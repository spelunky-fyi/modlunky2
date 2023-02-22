<script lang="ts">
  // import {
  //   faCheck,
  //   faChevronDown,
  //   faDownload,
  //   faSyncAlt,
  //   faTrashAlt,
  // } from "@fortawesome/free-solid-svg-icons";
  import { version, versions } from "../../../store";
  import { Button, Stack, Text, OptionGroup, Menu } from "../../common";

  function selectVersion(index: number) {
    $version = versions[index];
  }
</script>

<OptionGroup>
  <Text level="h3" slot="heading">Version Select</Text>
  <Stack spacing="none">
    <Button size="tiny" class="flex-1 rounded-l rounded-r-none border-r-0"
      >stable</Button
    >
    <Button size="tiny" class="flex-1 rounded-none border-x-0">nightly</Button>
    <Stack class="flex-1" spacing="none">
      <Button size="tiny" class="flex-1 rounded-none border-x-0"
        >{$version.revision}</Button
      >
      <Menu styleClass="rounded-l-none rounded-r">
        <div class="i-fa-solid-chevron-down" />
        <Stack direction="vertical" spacing="none" slot="content">
          {#each versions as v, index (v.id)}
            <div
              on:click={() => selectVersion(index)}
              class="px-2 py-1 text-sm flex items-center justify-between cursor-pointer gap-2"
            >
              <Stack justify="between">
                {#if v.installed}
                  <div class="i-fa-solid-check" />
                {/if}
                <Text level="span">{v.revision}</Text>
              </Stack>
              {#if v.installed}
                <Button color="danger" class="p-1">
                  <div class="i-fa-solid-trash-alt" />
                </Button>
              {:else}
                <Button color="info">
                  <div class="i-fa-solid-download" />
                </Button>
              {/if}
            </div>
          {/each}
        </Stack>
      </Menu>
    </Stack>
    <Button class="ml-2">
      <div class="i-fa-solid-sync-alt" />
    </Button>
  </Stack>
</OptionGroup>

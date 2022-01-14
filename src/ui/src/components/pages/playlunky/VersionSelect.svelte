<script lang="ts">
  import OptionGroup from "../../common/OptionGroup.svelte";
  import Menu from "../../common/Menu.svelte";
  import Icon from "svelte-awesome";
  import {
    faCheck,
    faChevronDown,
    faSyncAlt,
    faTrashAlt,
  } from "@fortawesome/free-solid-svg-icons";
  import { version, versions } from "../../../store";

  function selectVersion(index) {
    $version = versions[index];
  }
</script>

<OptionGroup>
  <h3 slot="heading">Version Select</h3>
  <div class="flex w-full">
    <button class="btn-md flex-1 rounded-l">stable</button>
    <button class="btn-md flex-1">nightly</button>
    <div class="flex w-32">
      <button class="btn-md flex-1">{$version.revision}</button>
      <Menu class="rounded-r">
        <Icon data={faChevronDown} />
        <div slot="content" class="flex flex-col">
          {#each versions as v, index (v.id)}
            <div
              on:click={() => selectVersion(index)}
              class="px-2 py-1 text-sm flex items-center cursor-pointer gap-2 justify-between"
              class:bg-gray-800={$version === v}
              class:text-white={$version === v}
            >
              <span
                class="flex items-center gap-2"
                class:font-semibold={v.installed}
                class:opacity-50={!v.installed}
                >{#if v.installed}
                  <Icon data={faCheck} scale={0.5} />
                {/if}
                {v.revision}</span
              >
              {#if v.installed}
                <button class="flex items-center justify-center"><Icon data={faTrashAlt} /></button>
              {/if}
            </div>
          {/each}
        </div>
      </Menu>
    </div>
    <button class="btn-md ml-1 rounded">
      <Icon data={faSyncAlt} />
    </button>
  </div>
</OptionGroup>

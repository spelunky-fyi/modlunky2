<script lang="ts">
  import ModList from "./ModList.svelte";
  import PlaylunkyOptions from "./PlaylunkyOptions.svelte";
</script>

<section class="flex flex-1 gap-4">
  <div class="flex-1 flex flex-col justify-between gap-4">
    <ModList />
    <button class="btn-lg rounded">Play</button>
  </div>

  <PlaylunkyOptions />
</section>

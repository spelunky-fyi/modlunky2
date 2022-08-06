<script lang="ts">
  let messages: string[] = [new Date().toString() + ": Test console output"];
</script>

<div class="overflow-y-scroll elevation-1 h-20 p-1.5 text-xs font-mono">
  <ul>
    {#each messages as message}
      <li>{message}</li>
    {/each}
  </ul>
</div>

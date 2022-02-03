<script lang="ts">
  type ConsoleMessage = {
    text: string;
    date: Date;
  };

  let messages: ConsoleMessage[] = [
    {
      date: new Date(),
      text: "another line! wow",
    },
    {
      date: new Date(),
      text: "console output",
    },
  ];
</script>

<div class="striped scrollbar h-28 shrink-0 overflow-y-scroll bg-theme-900/50 font-mono text-xs">
  {#each messages as { text, date }}
    <div class="flex gap-2 px-2 py-1">
      <span class="text-theme-300/50">{date.toLocaleTimeString()}:</span>
      <span class="text-theme-300">{text}</span>
    </div>
  {/each}
</div>

<script lang="ts">
  import { invoke } from "@tauri-apps/api/tauri";
  let count: number = 0;
  const increment = () => {
    invoke("my_custom_command", { number: 42 })
      .then((res) => console.log(res))
      .catch((err) => console.error(err));
    count += 1;
  };
</script>

<button on:click={increment}>
  count is {count}
</button>

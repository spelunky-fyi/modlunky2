<script lang="ts">
  export let size: ButtonSize = "default";
  export let color: ButtonColor = "default";
  export let disabled = false;

  const buttonStyles = {
    base: "flex items-center justify-center gap-2.5 border-none rounded transition font-medium font-roboto cursor-pointer focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed",

    size: {
      default: "px-2.5 py-1.5 text-base",
      tiny: "px-1.5 py-1 text-xs",
      small: "px-2 py-1.25 text-sm",
      large: "px-4 py-2 text-lg",
      huge: "px-6 py-3 text-xl",
    },

    colors: {
      default:
        "bg-zinc-500 active:bg-opacity-80 hover:bg-zinc-400 disabled:bg-zinc-500 text-zinc-100",
      primary:
        "bg-emerald-500 hover:bg-emerald-400 active:bg-opacity-60 disabled:bg-emerald-500 text-emerald-900",
      transparent:
        "bg-zinc-400 bg-opacity-0 active:bg-zinc-500 hover:bg-opacity-25 text-zinc-600 dark:text-zinc-100",
      danger:
        "bg-red-600 bg-opacity-75 active:bg-red-700 hover:bg-red-500 disabled:bg-red-600 text-red-100",
      warning:
        "bg-amber-600 hover:bg-amber-500 active:bg-opacity-75 disabled:bg-amber-600 text-amber-100",
      info: "bg-sky-600 hover:bg-sky-500 active:bg-opacity-75 disabled:bg-sky-600 text-sky-100",
    },
  };
</script>

<button
  {...$$props}
  on:click
  on:mousedown
  on:mouseup
  on:touchstart
  on:touchend
  class="{buttonStyles.base} {buttonStyles.size[size]} {buttonStyles.colors[
    color
  ]} {$$restProps.class || ''}"
  {disabled}
>
  <slot />
</button>

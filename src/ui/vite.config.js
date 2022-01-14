import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import Unocss from "unocss/vite";
import { extractorSvelte } from 'unocss';
import presetWind from "@unocss/preset-wind";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    Unocss({
      extractors: [extractorSvelte],
      shortcuts: {
        "btn": "flex items-center justify-center bg-zinc-200 dark:bg-zinc-800 font-semibold hover:bg-zinc-100 dark:hover:bg-zinc-700 transition",
        "btn-md": "btn px-2 py-1.5",
        "btn-lg": "btn p-4 text-xl",
        "tab": "px-3 py-1 flex items-center justify-center bg-zinc-300 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded-t transition",
        "tab-active": "bg-zinc-50 dark:bg-zinc-600",
      },
      presets: [presetWind({
        dark: "media"
      })],
    }),
    svelte(),
  ],
});

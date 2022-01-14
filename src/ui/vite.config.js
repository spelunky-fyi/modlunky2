import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import Unocss from "unocss/vite";
import { extractorSvelte } from "unocss";
import presetWind from "@unocss/preset-wind";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    Unocss({
      extractors: [extractorSvelte],
      shortcuts: [
        {
          btn: "flex items-center justify-center font-semibold elevation-1 bg-opacity-75 hover:bg-opacity-0 dark:bg-opacity-50 dark:hover:bg-opacity-100 rounded transition border border-zinc-300 dark:border-zinc-800",
          "btn-md": "btn px-2 py-1.5",
          "btn-lg": "btn p-4 text-xl",
          tab: "flex items-center justify-center px-2 py-1.5 font-semibold rounded-t hover:bg-zinc-100 dark:hover:bg-zinc-600 transition",
          "tab-active": "elevation-0",
          input:
            "p-2 elevation-1 bg-opacity-50 dark:bg-opacity-50 focus:outline-none focus:bg-opacity-100 rounded transition",
        },
        [
          /^elevation-(.*)$/,
          ([, c]) =>
            c == 0
              ? "bg-zinc-50 dark:bg-zinc-900"
              : `bg-zinc-${c}00 dark:bg-zinc-${9 - c}00`,
        ],
      ],
      presets: [
        presetWind({
          dark: "media",
        }),
      ],
    }),
    svelte(),
  ],
});

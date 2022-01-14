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
        "btn": "flex items-center justify-center bg-gray-200 font-semibold hover:bg-gray-100 transition",
        "btn-md": "btn px-2 py-1.5",
        "btn-lg": "btn p-4 text-xl",
        "tab": "px-3 py-1 flex items-center justify-center bg-gray-300 rounded-t-sm transition",
        "tab-active": "bg-gray-50",
      },
      presets: [presetWind()],
    }),
    svelte(),
  ],
});

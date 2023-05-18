import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import Unocss from "unocss/vite";
import { presetIcons, presetWebFonts } from "unocss";
import extractorSvelte from "@unocss/extractor-svelte";
import { presetWind } from "@unocss/preset-wind";

// https://vitejs.dev/config/
export default defineConfig({
  clearScreen: false,
  server: {
    strictPort: true,
  },
  envPrefix: ["VITE_", "TAURI_"],
  build: {
    target: ["es2021", "chrome100", "safari13"],
    minify: !process.env.TAURI_DEBUG ? "esbuild" : false,
    sourcemap: !!process.env.TAURI_DEBUG,
  },
  plugins: [
    Unocss({
      extractors: [extractorSvelte()],
      shortcuts: [
        {
          tab: "flex items-center justify-center px-2 py-1.5 font-semibold rounded-t hover:bg-zinc-100 dark:hover:bg-zinc-600 transition",
          "tab-active": "elevation-0",
        },
        [
          /^elevation-(.*)$/,
          ([, c]) =>
            c === "0"
              ? "bg-zinc-50 dark:bg-zinc-900"
              : `bg-zinc-${c}00 dark:bg-zinc-${9 - c}00`,
        ],
      ],
      presets: [
        presetWind({
          dark: "class",
        }),
        presetIcons(),
        presetWebFonts({
          provider: "google",
          fonts: {
            sans: "Inter",
            mono: "JetBrains Mono",
            roboto: {
              name: "Roboto",
              weights: [400, 500, 700],
            },
          },
        }),
      ],

      theme: {
        fontSize: {
          "2xs": "0.65rem",
        },
      },

      // Always generate these classes so they are available dynamically
      safelist: [
        // Stack
        "gap-0",
        "gap-2",
        "gap-4",
        "gap-6",
        "justify-start",
        "justify-end",
        "items-start",
        "items-end",

        // text input
        "bg-zinc-600",
        "bg-zinc-700",
        "bg-zinc-800",

        // default
        "text-zinc-100",
        "bg-zinc-300",
        "bg-zinc-400",
        "bg-zinc-500",

        // primary
        "text-emerald-900",
        "bg-emerald-400",
        "bg-emerald-500",
        "bg-emerald-600",

        // transparent
        "bg-transparent",

        // danger
        "text-red-100",
        "bg-red-600",
        "bg-red-700",

        // success
        "text-lime-900",
        "bg-lime-500",
        "bg-lime-600",
        "bg-lime-700",

        // warning
        "text-amber-100",
        "bg-amber-500",
        "bg-amber-600",
        "bg-amber-700",

        // info
        "text-sky-100",
        "bg-sky-500",
        "bg-sky-600",
        "bg-sky-700",
      ],
    }),
    svelte(),
  ],
});

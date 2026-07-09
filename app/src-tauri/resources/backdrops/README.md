# Backdrop images

Full-screen background art bundled with the app (not sourced from the user's
game extract). Compiled straight into the binary via `include_bytes!` and
exposed to the frontend as base64 data URLs.

## `cosmos.png`

Cosmic Ocean starfield backdrop, preserved from Python's
`src/modlunky2/static/images/cosmos.png`. Loaded by
`level_editor::get_cosmic_backdrop()` and consumed by `TileCanvas`'s
`cosmicBackdropUrl` prop. Wired in the Custom editor
(`EditorWindow.tsx`) to render when the current file's
`LevelConfiguration.theme` resolves to `COSMIC_OCEAN_THEME` (10). The tiling
math (per-row X shift, 4-room / 3-room step) matches the tkinter editor's
`level_canvas.py::draw_background` exactly.

Not yet wired in the Vanilla editor because Vanilla doesn't yet infer per-file
theme from filename; when that lands, feed the same `cosmicBackdropUrl` prop
through the same switch (CO subtheme fallback per Python's
`biome_for_theme`).

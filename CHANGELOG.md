# Changelog

All notable changes to Modlunky2 (the Tauri rewrite, 2.x) are documented in
this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.16] - 2026-07-11

### Added

- Update check: click the version number in the top bar to check for updates on
  demand. It shows "checking" then "up to date", or, if the check can't reach
  GitHub, an error with the reason.

### Fixed

- Vanilla level editor: saving a file no longer erases tiles it inherits from a
  parent file. Files like `blackmarket.lvl` build their rooms almost entirely
  from tilecodes defined in `generic.lvl` (and area parents); the save was only
  aware of the file's own palette, so it blanked every inherited tile (~96% of
  `blackmarket.lvl`'s cells). Saves now resolve tile names back through the same
  inheritance chain used to load them, so inherited tiles round-trip intact.
- Update check: failures are no longer silent. If the latest-version lookup
  fails (offline, GitHub API rate limit, or a blocked connection), the reason is
  logged and the version number turns amber with the reason on hover, instead of
  the update pill just never appearing.
- Trackers: the tracker icons are now crisp SVGs instead of small bitmaps that
  looked blurry when scaled up.
- Level editor: the door sprite (and its `eggplant_door` and `starting_exit`
  variants) now renders centered on its cell instead of shifted off to one side
  and stretched too wide. Its crop was misaligned by half a cell in every biome.
- Level editor: a newly added multi-cell tile (a door, statue, big trap, etc.)
  now draws at its full size and correct position the moment you add it, instead
  of being squished into a single cell until the next refresh.
- Level editor: switching level files no longer carries over a selected brush
  tile that the new file's palette doesn't define, which let you paint an
  undefined tilecode into that file. The brush now falls back to a valid tile
  when the previous one isn't in the new palette.
- Level editor: the `moai_statue` sprite is no longer cut in half; its crop was
  only half the width of the actual art.
- Level editor: the `empress_grave` sprite now renders. Its crop ran past the
  bottom edge of the sprite sheet, so the tile came up blank.
- Level editor: palette swatches for non-square tiles (such as `moai_statue` or
  `shopkeeper_vat`) no longer show a sliver of the neighbouring tile bleeding in
  from the packed sprite atlas.
- Level editor: biomes that have no background art of their own now fall back to
  the right one instead of keeping whichever background was on screen from the
  previously open file. Olmec-area files (e.g. `olmecarea.lvl`) use the stone
  background, and the Base Camp theme uses the cave background.

## [2.0.15] - 2026-07-11

### Added

- Toast notifications: a Settings option controls which severities pop on
  screen. Defaults to warnings and higher, so routine confirmations no longer
  cover the UI. Every toast is still recorded to the toast log regardless.
- Level editor: an option to skip the save confirmation dialog. Tick "Don't ask
  again" in the dialog, or toggle "Ask for confirmation before saving" in the
  editor settings.
- Level editor: the Add Tile dialog now shows the tile code it will assign and
  lets you change it. The picker groups codes as available, available but
  overriding an inherited file's binding (with a warning), and unavailable
  (already used in this file, shown so you can see what's using it).
- Level editor: the Add Tile name dropdown now previews each tile's sprite
  beside its name. Tiles already in the palette are shown
  greyed out and can't be picked.

### Changed

- Toast notifications now appear at the bottom center instead of a corner, so
  they no longer cover the Save or Play buttons. Success and info messages
  (e.g. "Copied") are log-only by default (see the new Settings option).

## [2.0.14] - 2026-07-11

### Added

- Light theme. A Sun/Moon button in the top bar toggles between the dark
  (default) and light themes

### Fixed

- Self-updater: an update now downloads the exact release the version check
  resolved (from that release's own asset URL) instead of GitHub's
  `latest/download` link, whose separate cache could briefly serve the previous
  version and leave the app "updating" to the same older build in a loop.

## [2.0.13] - 2026-07-10

### Fixed

- Level editor: Duat theme now use a solid black background instead of
  the tiled `bg_duat` texture, which didn't tile like the other biomes.
- Level editor: in the dual (foreground + background) view, a marquee selection
  is locked to the layer it starts in, so it no longer straddles the gap. It
  previously let you select across both halves but only acted on the
  foreground.

## [2.0.12] - 2026-07-10

### Added

- Vanilla level editor: keyboard navigation in the rooms list. Up/Down move
  between rooms (opening each as you go) and templates; Left/Right collapse and
  expand a template.
- Vanilla level editor: a button in the rooms list header expands or collapses
  every template at once.
- Vanilla level editor: delete rooms from the Rooms manager. Each room card has
  a delete button, and each template a "Delete all rooms" button; both ask for
  confirmation by needing a second click. Deleting a template's last room clears
  it to a blank room rather than removing it.
- Vanilla level editor: the template context menu has a "Delete all rooms"
  option that resets the template to a single blank room.
- Vanilla level editor: drag and drop rooms in the Rooms manager to reorder
  them within a template or move them to another. Templates whose rooms are a
  different size are dimmed and won't accept the drop; moving a template's last
  room out leaves it with one blank room.
- Level editor: a folder button in both editors' top bar opens the pack's
  folder.
- Level editor: right-clicking a level file (the file switcher in the Vanilla
  editor, a file in the Custom editor's list) offers "Open" and "Open with..."
  to open it in an external program, for anything the editor can't handle.
- Vanilla level editor: "Open preview" on a room's right-click menu opens a
  read-only window pinned to that room, useful for referencing other rooms (e.g.
  on a second monitor) while editing. Multiple previews can be open at once, and
  they reload to the latest saved state when you save.

### Changed

- Level editor: switching rooms no longer flashes a black canvas before the new
  room appears. The canvas keeps a single renderer for the whole session and
  swaps the room in place.

### Fixed

- Level editor: editing a room and then clicking a different room no longer
  marks that second room as edited when you haven't touched it.
- Level editor: a level whose palette reuses a tile code across two entries no
  longer triggers a React duplicate-key warning.

## [2.0.11] - 2026-07-09

### Added

- Level editor: a compact palette toggle in the palette header collapses it to
  icon-only swatches that wrap into a dense grid. It's a persistent setting
  shared by both editors; reorder mode ignores it and stays expanded so
  drag-and-drop and delete keep their full rows.

## [2.0.10] - 2026-07-09

### Added

- Trackers: the Window settings now include Text color, Outline, and Outline
  color, applied consistently to every tracker.
- Trackers: the font picker lists the fonts installed on your machine instead
  of a fixed list (which showed fonts like Helvetica that silently fall back to
  Arial on Windows).
- Trackers: each settings section's help now opens in a modal with a proper
  setup guide (adding OBS Browser and Text sources) and tips for customizing the
  look with CSS.

### Changed

- Trackers: the OBS pages wrap their text in a `.tracker-content` element and
  drive styling through CSS variables, so an OBS Browser Source's Custom CSS can
  override alignment (on `body`) and any text styling (on `.tracker-content`).

### Fixed

- Mods list: a mod whose logo file extension is uppercase (e.g. `icon.PNG`) now
  shows its logo.
- Character Chooser: scrolling inside a dropdown no longer closes it (only
  scrolling the page behind it does).
- Trackers were centered instead of left-aligned, a regression from the previous
  version.
- Trackers: the text outline appeared only on some trackers; it is now a single
  uniform Outline setting (off by default).
- Trackers: clicking the "Chroma key" label no longer snaps the color back to
  green.

## [2.0.9] - 2026-07-08

### Added

- Vanilla level editor: the level view now supports challenge and Palace
  of Pleasure files (their `challenge_{y}-{x}` / `palaceofpleasure_{y}-{x}`
  grids) in addition to setroom levels.
- Vanilla level editor: the room list badges for room flags now wrap so
  they never force a horizontal scrollbar. Each badge and the room name have
  hover text, with the flag descriptions shared from the settings panel.
- Vanilla level editor: copy and paste multiple rooms at once. Right-click a
  template for "Copy all rooms", and "Paste room" is now "Paste room(s)".
  Right-clicking a room offers "Add to clipboard" to gather rooms from
  different templates before a single paste.
- Vanilla level editor: a Rooms manager (Manage button in the Rooms panel)
  showing every template and room with a foreground preview, inline comment
  editing, jump-to-room, a per-room copy button (hold Shift to add to the
  clipboard instead of replacing it), and a bulk remove-comments action (room
  comments, template comments, or both).

### Changed

- Vanilla level editor: the Open .lvl file dialog lists files in a single
  scannable column as I found scanning names left to right broke my brain.

### Fixed

- Vanilla level editor: editing a room's flags updates the room-list badges
  immediately and the change persists after saving (previously the badges only
  refreshed after switching files).
- Vanilla level editor: removing a room's dual flag now drops its back layer on
  save instead of leaving a stray second layer that re-marked the room as dual.
- Vanilla level editor: right-clicking a different room or template while a
  context menu is open now moves the menu there instead of popping the browser's
  native menu and leaving the old one open.
- Vanilla level editor: room comments no longer show their raw `//` markers when
  edited.

## [2.0.8] - 2026-07-08

### Added

- Character Chooser: a new menu for assigning character mods to the
  20 game character slots. Reachable per-pack by right-clicking a mod in the
  mods list ("Set characters..."), or globally from the Active mods header to
  manage every active character.
- Vanilla level editor: the room list now badges every room setting (dual,
  flip, onlyflip, ignore, rare, hard, liquid, purge), each color-coded, not
  just dual.
- Vanilla level editor: in the dual (foreground + background) level view,
  rooms with no `!dual` layer are badged "No dual layer" so their empty
  background side reads as intentional.

### Fixed

- Vanilla level editor: rooms flagged `!onlyflip` are now shown mirrored in
  the level view, matching how the game plays them.
- Vanilla level editor: room variants flagged `!ignore` are skipped in the
  level view, falling through to the next variant.
- Vanilla level editor: tiles a level inherits from a parent file (for
  example a setroom using one of `generic.lvl`'s tiles) now render in the
  level view instead of appearing blank.
- Restored tile and entity sprites that were missing compared to the old
  editor: the drill and other biome decorations (Volcana, Jungle, Ice Caves,
  Sunken City, and base-camp furniture), Yama and the Empress grave, and the
  HUD art sheet.
- Playlunky could fail to launch with "no Playlunky version selected" even
  though a version was shown as selected, right after installing your first
  version. The shown version is now saved so launching works.

## [2.0.7] - 2026-07-07

### Fixed

- Level editor: switching from one file to another could leave part of the
  palette blank (some tiles never rendered).
- Creating a new Vanilla pack no longer scaffolds `main.lua` and
  `level_configuration.ls`, which are only relevant to Custom packs.

## [2.0.6] - 2026-07-07

### Added

- Editor settings: a Settings panel, reachable from the Level Editor tab and
  from both the Vanilla and Custom editor windows. Includes a default-zoom
  option (Fit, Fixed at a chosen percent, or Last used), a Clamp toggle, and
  default grid visibility. All preferences persist across sessions. Save
  format management moved into this panel and is clearly marked as Custom
  editor only.

### Changed

- Level editor: left click now defaults to the first paintable tile and right
  click to "empty", so you can erase without picking a tile first.

### Fixed

- Vanilla level editor: the Preview flip and Mirrored buttons now update the
  canvas immediately instead of doing nothing until you switched rooms.

## [2.0.5] - 2026-07-07

### Added

- Vanilla level editor: pack-only `.lvl` files that aren't base-game levels
  are now listed (with a distinct icon) so they can be viewed and edited.
- Vanilla level editor: per-file theme override, stored in the level file so
  it round-trips.
- Vanilla level editor: Cosmic Ocean theme support.

### Changed

- The inactive mods list is now sorted alphabetically by name.

### Fixed

- Opening a pack whose folder name contains spaces.
- Vanilla level editor: switching files could keep showing the previous file's
  rooms until you changed rooms.

## [2.0.0]

- Initial release of the Modlunky2 Tauri rewrite.

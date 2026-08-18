# modlunky2

[![Build](https://github.com/spelunky-fyi/modlunky2/actions/workflows/build.yml/badge.svg)](https://github.com/spelunky-fyi/modlunky2/actions/workflows/build.yml)
[![Rust Test](https://github.com/spelunky-fyi/modlunky2/actions/workflows/rust-test.yml/badge.svg)](https://github.com/spelunky-fyi/modlunky2/actions/workflows/rust-test.yml)
[![Latest Release](https://img.shields.io/github/release/spelunky-fyi/modlunky2.svg?style=flat)](https://github.com/spelunky-fyi/modlunky2/releases/latest)
![Downloads](https://img.shields.io/github/downloads/spelunky-fyi/modlunky2/total.svg?style=flat)

Modlunky 2 is a tool for creating and using mods related to Spelunky 2. It offers

- Mod management, including
  - Downloading and updating mods from spelunky.fyi
  - Launching Spelunky 2 with mods (via Playlunky)
- Creating and editing levels
- Extracting assets (e.g. images and audio)
- Updating and launching Overlunky
- Speedrun trackers

## Usage

### Windows

Download the latest `modlunky2.exe` from
[Releases](https://github.com/spelunky-fyi/modlunky2/releases/latest) and drop it
anywhere (desktop, Spelunky 2 install directory, wherever you keep tools).

### Linux

Download `modlunky2-x86_64.AppImage` from 
[Releases](https://github.com/spelunky-fyi/modlunky2/releases/latest), mark
it executable, and run it:

```console
chmod +x modlunky2-x86_64.AppImage
./modlunky2-x86_64.AppImage
```

Spelunky 2 has no native Linux build, so Modlunky runs it through the Proton
setup Steam already made for it. That's detected automatically, and "I'm feeling
lucky" in Settings finds your install directory. A few things to know:

- **Run Spelunky 2 from Steam once before using Modlunky.** Steam only creates
  the game's Proton prefix the first time you launch it, and Modlunky runs
  everything through that prefix.
- **Steam has to be running.** The game talks to it whether or not you launched
  through it.
- **Settings don't carry over** if you were previously running the Windows build
  under Proton. Modlunky now stores its config natively, at
  `~/.local/share/spelunky.fyi/modlunky2/`, so you'll set your profile up once.
- **If the level editor renders black**, your graphics driver is hitting a
  known WebKitGTK bug. Launch with `WEBKIT_DISABLE_DMABUF_RENDERER=1` set:

  ```console
  WEBKIT_DISABLE_DMABUF_RENDERER=1 ./modlunky2-x86_64.AppImage
  ```

  This costs GPU compositing, so only reach for it if you hit the problem. It
  is also worth trying in the rare case that no window appears at all. If
  you're launching from a Steam shortcut, set it in the launch options as
  `WEBKIT_DISABLE_DMABUF_RENDERER=1 %command%`.

On Steam Deck, see
[Modlunky 2 on Steam Deck](https://github.com/spelunky-fyi/modlunky2/wiki/Modlunky-2-on-Steam-Deck)
for a step by step walkthrough.

Requires glibc 2.35 or newer (Ubuntu 22.04, Debian 12, Fedora 36, or later).

Check out the docs at the [Modlunky 2 Wiki](https://github.com/spelunky-fyi/modlunky2/wiki).

> :warning: Spelunky 2 doesn't officially support modding. Do not report modding related bugs to Blitworks.

## Contributing

The [documentation for contributing](CONTRIBUTING.md) explains

- How to report bugs
- Where to discuss changes
- Setup for development

## Contributors

Special thanks to the following contributors for helping make modlunky possible:

`garebear`, `SciresM`, `Cloppershy`, `iojonmbnmb`, `Dregu`, `JackHasWifi`, `mriswithe`, `Malacath`, `MauveAlert`, `JayTheBusinessGoose`

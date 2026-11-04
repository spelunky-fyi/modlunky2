# Linux build environment for modlunky2, mirroring CI (.github/workflows/build.yml).
# Ubuntu 22.04 on purpose: the AppImage's glibc floor is whatever it's built on.
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential pkg-config curl ca-certificates git file xz-utils \
        libwebkit2gtk-4.1-dev libgtk-3-dev libsoup-3.0-dev \
        libayatana-appindicator3-dev librsvg2-dev libssl-dev \
        squashfs-tools patchelf desktop-file-utils \
    && rm -rf /var/lib/apt/lists/*

# Node 22
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Rust (stable, like CI). Toolchain lives in /opt so a mounted $HOME can't hide it.
ENV RUSTUP_HOME=/opt/rustup CARGO_HOME=/opt/cargo PATH=/opt/cargo/bin:$PATH
RUN curl -fsSL https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable \
    && rustup component add rustfmt clippy \
    && chmod -R a+rwX /opt/rustup /opt/cargo

# AppImage tooling is itself an AppImage and there's no FUSE in a container.
ENV APPIMAGE_EXTRACT_AND_RUN=1

WORKDIR /src

# Cache mount point, world-writable so a fresh named volume is usable by any --user.
RUN mkdir -p /cache/home /cache/cargo && chmod -R 777 /cache

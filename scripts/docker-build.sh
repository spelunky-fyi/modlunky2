#!/usr/bin/env bash
# Build the Linux AppImage inside a container so no toolchain touches the host.
#
#   scripts/docker-build.sh            # build release/modlunky2-x86_64.AppImage
#   scripts/docker-build.sh shell      # interactive shell in the build env
#   scripts/docker-build.sh <cmd...>   # run any command, e.g. cargo test
#
# Output lands in ./release, target/ and node_modules/ in the repo as usual.
# Cargo's registry and Tauri's downloaded tools are cached in named volumes.
# Set DOCKER=podman to use podman instead.
set -euo pipefail

cd "$(dirname "$0")/.."
DOCKER="${DOCKER:-docker}"
IMAGE=modlunky2-build

"$DOCKER" build -t "$IMAGE" docker

if [ $# -eq 0 ]; then
  set -- node scripts/build-release.mjs
elif [ "$1" = shell ]; then
  set -- bash
fi

tty=()
[ -t 0 ] && tty=(-it)

exec "$DOCKER" run --rm "${tty[@]}" \
  --user "$(id -u):$(id -g)" \
  -e HOME=/cache/home \
  -e CARGO_HOME=/cache/cargo \
  -v modlunky2-cache:/cache \
  -v "$PWD":/src \
  "$IMAGE" "$@"

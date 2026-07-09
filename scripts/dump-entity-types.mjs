#!/usr/bin/env node
// One-shot dump of `entities.json` into a generated Rust source file
// at `crates/ml2_trackers/src/entity_types.rs`.
//
// Output is a plain module of `pub const NAME: EntityType = ...`
// declarations, one per entity. Kept as .rs (not JSON) so it's grep-
// able, IDE-navigable, and type-checked at compile time. Rerun after
// any game update that changes the entity ID table.
//
// Usage (from the repo root):
//   node scripts/dump-entity-types.mjs

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(REPO_ROOT, "crates", "ml2_entity_data", "data", "entities.json");
const OUT = join(REPO_ROOT, "crates", "ml2_trackers", "src", "entity_types.rs");

const HEADER = `\
//! Auto-generated from \`crates/ml2_entity_data/data/entities.json\`.
//! Regenerate with \`node scripts/dump-entity-types.mjs\`; do not edit by
//! hand. Names match the game's \`ENT_TYPE_\` constants with the prefix
//! stripped; IDs are the exe's runtime type IDs.
//!
//! There are ~876 constants here. Trackers only pull the ones they
//! care about (mounts, backpacks, gems, powerups, etc); the rest are
//! kept so any future tracker or diagnostic can look up an entity by
//! its name without another round of codegen.

use crate::EntityType;

pub const DEFAULT_TYPE_ID: EntityType = EntityType(0);

`;

// `ENT_TYPE_MOUNT_TURKEY` -> `MOUNT_TURKEY`. Rejects anything with
// non-identifier characters so a bogus entities.json can't sneak
// garbage into the generated file.
const IDENT_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;
function rustifyName(name) {
  if (!name.startsWith("ENT_TYPE_")) {
    throw new Error(`unexpected key without ENT_TYPE_ prefix: ${JSON.stringify(name)}`);
  }
  const stripped = name.slice("ENT_TYPE_".length);
  if (!IDENT_RE.test(stripped)) {
    throw new Error(`invalid Rust identifier from ${JSON.stringify(name)}`);
  }
  return stripped;
}

const entities = JSON.parse(readFileSync(SRC, "utf8"));

const seenIds = new Map();
const lines = [];
for (const [name, obj] of Object.entries(entities)) {
  const rustName = rustifyName(name);
  const entityId = obj.id;
  if (!Number.isInteger(entityId)) {
    throw new Error(`${name}: id must be int, got ${JSON.stringify(entityId)}`);
  }
  if (seenIds.has(entityId)) {
    // ID collisions in entities.json would silently pick one variant
    // over the other; warn loudly so we notice.
    console.warn(
      `warning: id ${entityId} used by both ${seenIds.get(entityId)} and ${rustName}; keeping first`,
    );
    continue;
  }
  seenIds.set(entityId, rustName);
  lines.push(`pub const ${rustName}: EntityType = EntityType(${entityId});`);
}

writeFileSync(OUT, HEADER + lines.join("\n") + "\n", "utf8");
console.log(`wrote ${lines.length} constants to ${OUT}`);

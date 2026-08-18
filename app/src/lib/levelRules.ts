// Reconciling the Rules panel's in-memory state with what a save wrote.
//
// The editor shows `pendingEdit ?? loadedFromDisk` for each rules section. A
// save clears the pending edits, so unless the loaded copy is updated at the
// same time the panel drops straight back to the pre-edit values and the save
// looks like it silently reverted -- even though the file on disk is correct.

import type { EditedRules, RulesEntry } from "./commands";

/** The three rules sections a vanilla level file carries. */
export interface LevelRules {
  levelSettings: RulesEntry[];
  levelChances: RulesEntry[];
  monsterChances: RulesEntry[];
}

/**
 * Applies a just-saved rules payload on top of the level as loaded.
 *
 * Only the sections actually present in `saved` are replaced. The payload
 * omits sections the user didn't touch, and the backend leaves those alone on
 * disk (`Option<Vec<RulesEntry>>`, absent meaning "keep what's there"), so
 * overwriting them here would put the UI out of step with the file.
 *
 * Returns `prev` untouched when there was nothing to save.
 */
export function foldSavedRules<T extends LevelRules>(
  prev: T,
  saved: EditedRules | null,
): T {
  if (!saved) return prev;
  return {
    ...prev,
    levelSettings: saved.levelSettings ?? prev.levelSettings,
    levelChances: saved.levelChances ?? prev.levelChances,
    monsterChances: saved.monsterChances ?? prev.monsterChances,
  };
}

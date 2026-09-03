// The save editor.
//
// It holds two copies of the save: `original`, as it was read, and
// `draft`, as it is being edited. Everything else follows from comparing
// them - which sections are marked changed, whether the Save button does
// anything, and what a Revert puts back.
//
// The draft is one object rather than a field per section because that is
// what the backend takes and what the round-trip guarantee is written
// against: applying an untouched draft must not move a byte. Splitting it
// into a dozen pieces of state would mean reassembling it at save time and
// getting a chance to reassemble it wrong.
//
// Sections are memoized and each takes only its own slice, so typing in a
// journal field does not re-render the ninety-nine Cosmic Ocean levels
// next door.

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";

import {
  applySaveEdits,
  getEditableSave,
  type EditableSave,
  type SaveEdits,
  type SaveRef,
  type StoredSave,
} from "../../../lib/commands";
import { Modal } from "../../shared/Modal";
import { useToast } from "../../shared/Toast";
import { ConstellationEditor } from "./ConstellationEditor";
import {
  CharactersSection,
  DeathsSection,
  JournalSection,
  LastRunSection,
  ProfileSection,
  ProgressSection,
  SECTIONS,
  type SectionKey,
} from "./sections";
import "./editor.css";

interface Props {
  open: boolean;
  source: SaveRef;
  /** What to call this save in the header and in the backup's description. */
  title: string;
  onClose: () => void;
  /** Told when a write succeeded, so the page can refresh its lists. */
  onSaved?: (backup: StoredSave | null) => void;
}

export function SaveEditorModal({
  open,
  source,
  title,
  onClose,
  onSaved,
}: Props) {
  const toast = useToast();
  const [original, setOriginal] = useState<EditableSave | null>(null);
  const [draft, setDraft] = useState<EditableSave | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [section, setSection] = useState<SectionKey>("profile");
  const [busy, setBusy] = useState(false);
  const [confirmingClose, setConfirmingClose] = useState(false);

  const key = source.kind === "live" ? "live" : source.id;

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setOriginal(null);
    setDraft(null);
    setError(null);
    setSection("profile");
    getEditableSave(source).then(
      (save) => {
        if (cancelled) return;
        setOriginal(save);
        setDraft(save);
      },
      (err) => {
        if (!cancelled) setError(extractMessage(err));
      },
    );
    return () => {
      cancelled = true;
    };
    // `source` is rebuilt by the parent on every render, so the identity
    // that matters is which save it points at.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, key]);

  /** Which sections differ from what was read. */
  const changed = useMemo(
    () => changedSections(draft, original),
    [draft, original],
  );
  const dirty = changed.size > 0;

  const patch = useCallback(
    (next: Partial<EditableSave>) =>
      setDraft((current) => (current ? { ...current, ...next } : current)),
    [],
  );

  const close = useCallback(() => {
    if (dirty) {
      setConfirmingClose(true);
      return;
    }
    onClose();
  }, [dirty, onClose]);

  const save = useCallback(async () => {
    if (!draft) return;
    setBusy(true);
    try {
      const result = await applySaveEdits(
        source,
        toEdits(draft),
        true,
        `Before editing ${title}`,
      );
      // Rebase on what the backend read back, so the editor is showing the
      // file as it now is rather than as we hoped it would be.
      setOriginal(result.save);
      setDraft(result.save);
      if (result.changedBytes === 0) {
        toast.info("Nothing to save; the file already matched.");
      } else {
        toast.success(
          `Saved. ${result.changedBytes.toLocaleString()} ${
            result.changedBytes === 1 ? "byte" : "bytes"
          } changed${result.backup ? ", and the old save was archived" : ""}.`,
        );
      }
      onSaved?.(result.backup);
    } catch (err) {
      toast.error(extractMessage(err));
    } finally {
      setBusy(false);
    }
  }, [draft, onSaved, source, title, toast]);

  if (!open) return null;

  return (
    <>
      <Modal
        open
        onClose={close}
        title={`Edit ${title}`}
        size="xl"
        footer={
          <>
            <span className="ed-footer-note">
              {draft?.path}
              {draft && !draft.checksumValid && (
                <span className="ed-warn">
                  <AlertTriangle size={13} aria-hidden="true" /> This save's
                  checksum did not verify. Saving will write a correct one.
                </span>
              )}
            </span>
            <button
              type="button"
              className="saves-btn"
              disabled={!dirty || busy}
              onClick={() => setDraft(original)}
            >
              Revert
            </button>
            <button type="button" className="saves-btn" onClick={close}>
              Close
            </button>
            <button
              type="button"
              className="saves-btn saves-btn-primary"
              disabled={!dirty || busy}
              onClick={() => void save()}
            >
              {busy ? "Saving..." : dirty ? "Save changes" : "Saved"}
            </button>
          </>
        }
      >
        {error ? (
          <p className="ed-error">{error}</p>
        ) : !draft || !original ? (
          <p className="ed-loading">
            <Loader2 size={16} className="spin" aria-hidden="true" /> Reading
            the save...
          </p>
        ) : (
          <div className="ed-layout">
            <nav className="ed-rail" aria-label="Editor sections">
              {SECTIONS.map((entry) => (
                <button
                  key={entry.key}
                  type="button"
                  className={`ed-rail-item${
                    section === entry.key ? " on" : ""
                  }${changed.has(entry.key) ? " changed" : ""}`}
                  aria-current={section === entry.key}
                  onClick={() => setSection(entry.key)}
                >
                  {entry.label}
                  {changed.has(entry.key) && (
                    <span className="ed-dot" aria-label="changed" />
                  )}
                </button>
              ))}
            </nav>

            {/* The constellation section does its own scrolling: the
                canvas has to stay put while the inspector beside it
                scrolls, or changing a star's color scrolls the star out
                of view. Every other section is a plain scrolling column. */}
            <div
              className={`ed-panel${
                section === "constellation" ? " ed-panel-split" : ""
              }`}
            >
              {section === "profile" && (
                <ProfileSection
                  value={draft.profile}
                  original={original.profile}
                  camp={draft.camp}
                  originalCamp={original.camp}
                  onChange={(profile) => patch({ profile })}
                  onCampChange={(camp) => patch({ camp })}
                />
              )}
              {section === "progress" && (
                <ProgressSection
                  value={draft.unlocks}
                  original={original.unlocks}
                  shortcutStates={draft.shortcutStates}
                  onChange={(unlocks) => patch({ unlocks })}
                />
              )}
              {section === "journal" && (
                <JournalSection
                  sections={draft.journal}
                  original={original.journal}
                  onChange={(journal) => patch({ journal })}
                />
              )}
              {section === "characters" && (
                <CharactersSection
                  characters={draft.characters}
                  original={original.characters}
                  onCharactersChange={(characters) => patch({ characters })}
                />
              )}
              {section === "lastRun" && (
                <LastRunSection
                  value={draft.lastRun}
                  original={original.lastRun}
                  camp={draft.camp}
                  originalCamp={original.camp}
                  themeNames={draft.themes}
                  stickerNames={draft.stickerNames}
                  firstCharacterEntity={draft.firstCharacterEntity}
                  characters={draft.characters}
                  onChange={(lastRun) => patch({ lastRun })}
                  onCampChange={(camp) => patch({ camp })}
                />
              )}
              {section === "deaths" && (
                <DeathsSection
                  worlds={draft.deaths}
                  original={original.deaths}
                  onChange={(deaths) => patch({ deaths })}
                />
              )}
              {section === "constellation" && (
                <ConstellationEditor
                  value={draft.constellation}
                  original={original.constellation}
                  editable={draft.constellationEditable}
                  onChange={(constellation) => patch({ constellation })}
                />
              )}
            </div>
          </div>
        )}
      </Modal>

      <Modal
        open={confirmingClose}
        onClose={() => setConfirmingClose(false)}
        title="Discard changes?"
        footer={
          <>
            <button
              type="button"
              className="saves-btn"
              onClick={() => setConfirmingClose(false)}
            >
              Keep editing
            </button>
            <button
              type="button"
              className="saves-btn saves-btn-danger"
              onClick={() => {
                setConfirmingClose(false);
                onClose();
              }}
            >
              Discard
            </button>
          </>
        }
      >
        <p>
          Nothing has been written to the save yet. Closing now loses the
          changes in {describe(changed)}.
        </p>
      </Modal>
    </>
  );
}

/** The message out of a rejected command, which arrives as a string. */
function extractMessage(err: unknown): string {
  if (typeof err === "string") return err;
  if (err instanceof Error) return err.message;
  return String(err);
}

/** Turns the draft into the payload the backend applies. */
export function toEdits(save: EditableSave): SaveEdits {
  return {
    profile: save.profile,
    unlocks: save.unlocks,
    lastRun: save.lastRun,
    camp: save.camp,
    journal: save.journal.map((section) => ({
      key: section.key,
      discovered: section.entries.map((entry) => entry.discovered),
      // Categories that keep no kill counts send empty lists rather than
      // zeroes, which would otherwise be written over real data if a
      // category ever gained counters.
      killed: section.hasKills
        ? section.entries.map((entry) => entry.killed ?? 0)
        : [],
      killedBy: section.hasKills
        ? section.entries.map((entry) => entry.killedBy ?? 0)
        : [],
    })),
    characters: save.characters.map((character) => ({
      unlocked: character.unlocked,
      deaths: character.deaths,
    })),
    deaths: save.deaths.map((world) => ({
      world: world.world,
      firstLevel: world.firstLevel,
      levels: world.levels,
    })),
    themes: save.themes.map((theme) => theme.completed),
    constellation: save.constellation,
  };
}

/** Which sections of the draft differ from what was read. */
export function changedSections(
  draft: EditableSave | null,
  original: EditableSave | null,
): Set<SectionKey> {
  const changed = new Set<SectionKey>();
  if (!draft || !original) return changed;

  const differs = (a: unknown, b: unknown) =>
    JSON.stringify(a) !== JSON.stringify(b);

  if (differs(draft.profile, original.profile)) changed.add("profile");
  if (differs(draft.unlocks, original.unlocks)) changed.add("progress");
  if (differs(draft.journal, original.journal)) changed.add("journal");
  if (differs(draft.characters, original.characters)) changed.add("characters");
  if (differs(draft.lastRun, original.lastRun)) changed.add("lastRun");
  if (differs(draft.deaths, original.deaths)) changed.add("deaths");
  if (differs(draft.constellation, original.constellation)) {
    changed.add("constellation");
  }
  // The camp is edited from two places: the pet counts sit with the other
  // lifetime figures on the profile, and the daily date with the last run.
  // Marking both is honest about where the change might be.
  if (differs(draft.camp, original.camp)) {
    changed.add("profile");
    changed.add("lastRun");
  }
  return changed;
}

/** Names the changed sections for the discard prompt. */
function describe(changed: Set<SectionKey>): string {
  const labels = SECTIONS.filter((entry) => changed.has(entry.key)).map(
    (entry) => entry.label.toLowerCase(),
  );
  if (labels.length === 0) return "this save";
  if (labels.length === 1) return labels[0];
  return `${labels.slice(0, -1).join(", ")} and ${labels[labels.length - 1]}`;
}

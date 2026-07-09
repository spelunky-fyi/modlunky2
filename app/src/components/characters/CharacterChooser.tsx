// Managed character chooser (its own window). Read-only Phase 1: shows every
// character slot, who currently occupies it (resolved by load order), and
// "potential" character sheets shipped under non-standard names. Assign /
// disable / restore land on top of this in Phase 2.

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { createPortal } from "react-dom";
import { Check, ChevronDown, RefreshCw, TriangleAlert } from "lucide-react";
import {
  assignCharacter,
  disableCharacter,
  getCharacterPreview,
  getCharacters,
  getVanillaCharacterPreview,
  listMods,
  restoreCharacter,
  setCharacterConfirmed,
  setCharacterIgnored,
  unassignCharacter,
  type CharacterCandidate,
  type CharacterSlot,
  type CharactersResponse,
} from "../../lib/commands";
import "./CharacterChooser.css";

export function CharacterChooser({ pack }: { pack: string | null }) {
  const [data, setData] = useState<CharactersResponse | null>(null);
  const [modNames, setModNames] = useState<Map<string, string>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPossible, setShowPossible] = useState(false);
  const [showIgnored, setShowIgnored] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      // Global view is an active-mods manager; per-pack scopes to one pack.
      const [resp, mods] = await Promise.all([
        getCharacters(false, pack),
        listMods(),
      ]);
      setData(resp);
      setModNames(
        new Map(mods.map((m) => [m.id, m.manifest?.name ?? m.id])),
      );
      setError(null);
    } catch (err) {
      setError(extractMessage(err));
    } finally {
      setLoading(false);
    }
  }, [pack]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const nameForMod = useCallback(
    (packId: string) => modNames.get(packId) ?? packId,
    [modNames],
  );

  const runWrite = useCallback(
    async (fn: () => Promise<void>) => {
      try {
        await fn();
        await reload();
      } catch (err) {
        setError(extractMessage(err));
      }
    },
    [reload],
  );

  const handleSetIgnored = useCallback(
    (c: CharacterCandidate, ignored: boolean) =>
      runWrite(() => setCharacterIgnored(c.packId, c.relPath, ignored)),
    [runWrite],
  );
  const handleSetConfirmed = useCallback(
    (c: CharacterCandidate, confirmed: boolean) =>
      runWrite(() => setCharacterConfirmed(c.packId, c.relPath, confirmed)),
    [runWrite],
  );
  const handleAssign = useCallback(
    (c: CharacterCandidate, color: string) =>
      runWrite(() => assignCharacter(c.packId, c.relPath, color)),
    [runWrite],
  );
  const handleDisable = useCallback(
    (c: CharacterCandidate) =>
      runWrite(() => disableCharacter(c.packId, c.relPath)),
    [runWrite],
  );
  const handleUnassign = useCallback(
    (c: CharacterCandidate) =>
      runWrite(() => unassignCharacter(c.packId, c.relPath)),
    [runWrite],
  );
  const handleRestore = useCallback(
    (c: CharacterCandidate) =>
      runWrite(() => restoreCharacter(c.packId, c.relPath)),
    [runWrite],
  );

  // Global slot board: set a slot to `chosen` (or vanilla when null). The other
  // occupants are unassigned (kept available in the pool, not disabled) to
  // resolve the conflict, then, if the chosen character isn't already in this
  // slot, it's assigned here. Unassign runs before assign so the target
  // `char_<color>` path is free.
  const handleSetSlot = useCallback(
    (color: string, chosen: CharacterCandidate | null) =>
      runWrite(async () => {
        const occupants = (data?.candidates ?? []).filter(
          (c) => c.detectedColor === color && c.active,
        );
        for (const occ of occupants) {
          if (
            chosen &&
            occ.packId === chosen.packId &&
            occ.relPath === chosen.relPath
          ) {
            continue;
          }
          await unassignCharacter(occ.packId, occ.relPath);
        }
        if (chosen && chosen.detectedColor !== color) {
          await assignCharacter(chosen.packId, chosen.relPath, color);
        }
      }),
    [runWrite, data],
  );

  // Non-ignored candidates drive the slots + potentials; ignored ones are
  // tucked away behind the "show ignored" toggle.
  const visible = useMemo(
    () => (data?.candidates ?? []).filter((c) => !c.ignored),
    [data],
  );
  const ignored = useMemo(
    () => (data?.candidates ?? []).filter((c) => c.ignored),
    [data],
  );

  // Candidates that currently occupy a known slot, grouped by color and
  // ordered winner-first: active mods before inactive, then by load order.
  const bySlot = useMemo(() => {
    const map = new Map<string, CharacterCandidate[]>();
    for (const c of visible) {
      if (!c.detectedColor) continue;
      const arr = map.get(c.detectedColor) ?? [];
      arr.push(c);
      map.set(c.detectedColor, arr);
    }
    for (const arr of map.values()) arr.sort(compareOccupants);
    return map;
  }, [visible]);

  // The winning (loaded) character in each slot, for the "move here" picker.
  const slottedWinners = useMemo(() => {
    const out: CharacterCandidate[] = [];
    for (const s of data?.slots ?? []) {
      const w = (bySlot.get(s.color) ?? []).find((o) => o.active);
      if (w) out.push(w);
    }
    return out;
  }, [data, bySlot]);

  // The usable pool: sheets not in a slot that are real characters. Orphans
  // named `char_*` (likely), possibles the user confirmed, and parked sheets
  // (surfaced so they're recoverable). Unreviewed dimensions-only "possible"
  // matches are NOT here; they go to the review bucket first.
  const potentials = useMemo(
    () =>
      visible
        .filter(
          (c) =>
            !c.detectedColor &&
            (c.confidence !== "possible" || c.confirmed || c.userDisabled),
        )
        .sort((a, b) => a.fileName.localeCompare(b.fileName)),
    [visible],
  );

  // Dimensions-only matches awaiting a "is this a character?" decision.
  const reviewItems = useMemo(
    () =>
      visible
        .filter(
          (c) =>
            !c.detectedColor &&
            c.confidence === "possible" &&
            !c.confirmed &&
            !c.userDisabled,
        )
        .sort((a, b) => a.fileName.localeCompare(b.fileName)),
    [visible],
  );

  return (
    <div className="cc">
      <header className="cc-header">
        <div className="cc-title">
          {pack ? (
            <>
              Characters <span className="cc-title-scope">in {pack}</span>
            </>
          ) : (
            "Character Chooser"
          )}
        </div>
        <div className="cc-header-actions">
          {reviewItems.length > 0 && (
            <label className="cc-toggle">
              <input
                type="checkbox"
                checked={showPossible}
                onChange={(e) => setShowPossible(e.target.checked)}
              />
              <span>Review possible ({reviewItems.length})</span>
            </label>
          )}
          {ignored.length > 0 && (
            <label className="cc-toggle">
              <input
                type="checkbox"
                checked={showIgnored}
                onChange={(e) => setShowIgnored(e.target.checked)}
              />
              <span>Show ignored ({ignored.length})</span>
            </label>
          )}
          <button
            type="button"
            className="cc-btn"
            onClick={() => void reload()}
            disabled={loading}
          >
            <RefreshCw size={14} aria-hidden="true" />
            <span>Rescan</span>
          </button>
        </div>
      </header>

      {error && <div className="cc-error">{error}</div>}
      {loading && !data && (
        <div className="cc-status">Scanning packs for characters…</div>
      )}

      {data && pack && (
        <div className="cc-body">
          <PackAssignmentTable
            slots={data.slots}
            characters={visible}
            onAssign={handleAssign}
            onUnassign={handleUnassign}
            onDisable={handleDisable}
            onRestore={handleRestore}
            onIgnore={(c) => handleSetIgnored(c, true)}
          />
          {ignored.length > 0 && (
            <div className="cc-status cc-status-sm">
              {ignored.length} file(s) flagged not a character.{" "}
              <button
                type="button"
                className="cc-link-btn"
                onClick={() => setShowIgnored((v) => !v)}
              >
                {showIgnored ? "hide" : "review"}
              </button>
            </div>
          )}
          {showIgnored &&
            ignored.map((c) => (
              <div key={`${c.packId}:${c.relPath}`} className="cc-status-sm">
                <code>{c.relPath}</code>{" "}
                <button
                  type="button"
                  className="cc-link-btn"
                  onClick={() => void handleSetConfirmed(c, true)}
                >
                  it's a character
                </button>
              </div>
            ))}
        </div>
      )}

      {data && !pack && (
        <div className="cc-body">
          <section>
            <div className="cc-slotboard">
              {data.slots.map((slot) => (
                <SlotRow
                  key={slot.color}
                  slot={slot}
                  occupants={bySlot.get(slot.color) ?? []}
                  others={slottedWinners.filter(
                    (w) => w.detectedColor !== slot.color,
                  )}
                  unassigned={potentials}
                  nameForMod={nameForMod}
                  onSetSlot={handleSetSlot}
                />
              ))}
            </div>
          </section>

          {potentials.length > 0 && (
            <section>
              <h2 className="cc-section-title">
                Unassigned
                <span className="cc-section-sub">
                  {" "}
                  active-mod sheets not in a slot
                </span>
              </h2>
              <div className="cc-grid cc-grid-potential">
                {potentials.map((c) => (
                  <PotentialCard
                    key={`${c.packId}:${c.relPath}`}
                    candidate={c}
                    nameForMod={nameForMod}
                    onIgnore={() => void handleSetIgnored(c, true)}
                    onRestore={() => void handleRestore(c)}
                  />
                ))}
              </div>
            </section>
          )}

          {showPossible && reviewItems.length > 0 && (
            <section>
              <h2 className="cc-section-title">
                Possible characters
                <span className="cc-section-sub">
                  {" "}
                  char-sized files that might be characters
                </span>
              </h2>
              <div className="cc-grid cc-grid-potential">
                {reviewItems.map((c) => (
                  <PotentialCard
                    key={`${c.packId}:${c.relPath}`}
                    candidate={c}
                    nameForMod={nameForMod}
                    onConfirm={() => void handleSetConfirmed(c, true)}
                    onReject={() => void handleSetIgnored(c, true)}
                  />
                ))}
              </div>
            </section>
          )}

          {showIgnored && ignored.length > 0 && (
            <section>
              <h2 className="cc-section-title">
                Ignored
                <span className="cc-section-sub"> flagged not a character</span>
              </h2>
              <div className="cc-grid cc-grid-potential">
                {ignored.map((c) => (
                  <PotentialCard
                    key={`${c.packId}:${c.relPath}`}
                    candidate={c}
                    nameForMod={nameForMod}
                    onUnignore={() => void handleSetConfirmed(c, true)}
                  />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

/** Per-pack assignment table: one row per character sheet the pack ships, each
 *  with a slot dropdown and disable / restore / fix actions. */
function PackAssignmentTable({
  slots,
  characters,
  onAssign,
  onUnassign,
  onDisable,
  onRestore,
  onIgnore,
}: {
  slots: CharacterSlot[];
  characters: CharacterCandidate[];
  onAssign: (c: CharacterCandidate, color: string) => void;
  onUnassign: (c: CharacterCandidate) => void;
  onDisable: (c: CharacterCandidate) => void;
  onRestore: (c: CharacterCandidate) => void;
  onIgnore: (c: CharacterCandidate) => void;
}) {
  // Slotted first, then unassigned/pool, disabled last.
  const rows = [...characters].sort((a, b) => {
    const rank = (c: CharacterCandidate) =>
      c.userDisabled ? 2 : c.detectedColor ? 0 : 1;
    return rank(a) - rank(b) || a.fileName.localeCompare(b.fileName);
  });

  // Which slot each active sheet occupies, so the picker can grey out a slot
  // already used by another sheet in this pack.
  const usedByColor = new Map<string, string>();
  for (const c of characters) {
    if (c.detectedColor && !c.userDisabled) usedByColor.set(c.detectedColor, c.relPath);
  }

  if (rows.length === 0) {
    return (
      <div className="cc-status">No character sheets found in this pack.</div>
    );
  }

  return (
    <table className="cc-table">
      <thead>
        <tr>
          <th>Character</th>
          <th>Slot</th>
          <th className="cc-th-actions">Actions</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((c) => (
          <AssignRow
            key={`${c.packId}:${c.relPath}`}
            candidate={c}
            slots={slots}
            usedByColor={usedByColor}
            onAssign={onAssign}
            onUnassign={onUnassign}
            onDisable={onDisable}
            onRestore={onRestore}
            onIgnore={onIgnore}
          />
        ))}
      </tbody>
    </table>
  );
}

function AssignRow({
  candidate: c,
  slots,
  usedByColor,
  onAssign,
  onUnassign,
  onDisable,
  onRestore,
  onIgnore,
}: {
  candidate: CharacterCandidate;
  slots: CharacterSlot[];
  usedByColor: Map<string, string>;
  onAssign: (c: CharacterCandidate, color: string) => void;
  onUnassign: (c: CharacterCandidate) => void;
  onDisable: (c: CharacterCandidate) => void;
  onRestore: (c: CharacterCandidate) => void;
  onIgnore: (c: CharacterCandidate) => void;
}) {
  return (
    <tr className={c.userDisabled ? "cc-row-disabled" : ""}>
      <td className="cc-cell-char">
        <CandidatePreview candidate={c} />
        <div className="cc-occupant-meta">
          <div className="cc-occupant-name">
            {c.metadata?.fullName ?? c.fileName}
          </div>
          <div className="cc-files">
            <code className="cc-file">{c.relPath}</code>
            {c.metaRelPath && (
              <code className="cc-file cc-file-related">{c.metaRelPath}</code>
            )}
          </div>
          <CandidateBadges candidate={c} showConfidence />
        </div>
      </td>
      <td className="cc-cell-slot">
        {c.userDisabled ? (
          <span className="cc-disabled-label">Disabled</span>
        ) : (
          <SlotSelect
            slots={slots}
            value={c.detectedColor}
            selfRel={c.relPath}
            usedByColor={usedByColor}
            onChange={(color) => onAssign(c, color)}
          />
        )}
      </td>
      <td className="cc-cell-actions">
        <div className="cc-actions">
          {c.nameMismatch && c.detectedColor && (
            <button
              type="button"
              className="cc-action warn"
              onClick={() => onAssign(c, c.detectedColor!)}
              title="Rename to match its actual size"
            >
              Fix name
            </button>
          )}
          {c.originalRelPath && (
            <button
              type="button"
              className="cc-action"
              onClick={() => onRestore(c)}
              title="Restore the original file name"
            >
              Restore
            </button>
          )}
          {c.detectedColor && !c.userDisabled && (
            <>
              <button
                type="button"
                className="cc-action"
                onClick={() => onUnassign(c)}
                title="Remove from its slot, keep it available"
              >
                Unassign
              </button>
              <button
                type="button"
                className="cc-action ghost"
                onClick={() => onDisable(c)}
                title="Turn this character off entirely"
              >
                Disable
              </button>
            </>
          )}
          {!c.detectedColor &&
            !c.userDisabled &&
            !c.userUnassigned &&
            c.confidence === "possible" && (
              <button
                type="button"
                className="cc-action ghost"
                onClick={() => onIgnore(c)}
                title="Hide this file; it isn't a character"
              >
                Not a character
              </button>
            )}
        </div>
      </td>
    </tr>
  );
}

/** Popover menu anchored to a trigger button, rendered in a portal with
 *  `position: fixed` so it escapes the scroll container's clipping, and
 *  flipped above the trigger when there isn't room below. */
function useAnchoredMenu(width: number) {
  const [open, setOpen] = useState(false);
  const [style, setStyle] = useState<CSSProperties>({});
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const toggle = () => {
    if (open) {
      setOpen(false);
      return;
    }
    const btn = triggerRef.current;
    if (btn) {
      const r = btn.getBoundingClientRect();
      const margin = 8;
      const left = Math.max(
        margin,
        Math.min(r.right - width, window.innerWidth - width - margin),
      );
      const spaceBelow = window.innerHeight - r.bottom;
      const spaceAbove = r.top;
      const openUp = spaceBelow < 280 && spaceAbove > spaceBelow;
      const maxHeight = Math.max(
        160,
        (openUp ? spaceAbove : spaceBelow) - margin - 6,
      );
      setStyle({
        position: "fixed",
        left,
        width,
        maxHeight,
        overflowY: "auto",
        ...(openUp
          ? { bottom: window.innerHeight - r.top + 4, top: "auto" }
          : { top: r.bottom + 4, bottom: "auto" }),
      });
    }
    setOpen(true);
  };

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      const t = e.target as Node;
      if (triggerRef.current?.contains(t) || menuRef.current?.contains(t))
        return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    // A page/scroll-container scroll detaches the fixed-positioned menu from its
    // trigger, so close it. But scrolling *inside* the menu (it has its own
    // overflow) must not close it. The scroll listener is capture-phase, so it
    // sees menu-internal scrolls too; filter those out by target.
    const onScroll = (e: Event) => {
      if (e.target instanceof Node && menuRef.current?.contains(e.target)) {
        return;
      }
      setOpen(false);
    };
    const onResize = () => setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onResize);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onResize);
    };
  }, [open]);

  return { open, setOpen, style, triggerRef, menuRef, toggle };
}

/** Custom slot picker: shows every character with a portrait, and greys out
 *  slots already used by another sheet in the pack. Replaces a native select
 *  (whose option list renders unstyled/white-on-grey in the dark theme). */
function SlotSelect({
  slots,
  value,
  selfRel,
  usedByColor,
  onChange,
}: {
  slots: CharacterSlot[];
  value: string | null;
  selfRel: string;
  usedByColor: Map<string, string>;
  onChange: (color: string) => void;
}) {
  const { open, setOpen, style, triggerRef, menuRef, toggle } =
    useAnchoredMenu(280);
  const current = slots.find((s) => s.color === value) ?? null;

  return (
    <div className="cc-select">
      <button
        ref={triggerRef}
        type="button"
        className={`cc-select-btn${open ? " open" : ""}`}
        onClick={toggle}
      >
        {current ? (
          <>
            <VanillaPreview color={current.color} small />
            <span className="cc-select-current">{current.fullName}</span>
          </>
        ) : (
          <span className="cc-select-placeholder">Choose a slot…</span>
        )}
        <ChevronDown size={14} className="cc-select-caret" aria-hidden="true" />
      </button>
      {open &&
        createPortal(
          <div
            ref={menuRef}
            className="cc-floating-menu"
            style={style}
            role="listbox"
          >
            {slots.map((s) => {
              const owner = usedByColor.get(s.color);
              const taken = owner !== undefined && owner !== selfRel;
              const selected = s.color === value;
              return (
                <button
                  key={s.color}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  className={`cc-select-opt${selected ? " selected" : ""}${taken ? " taken" : ""}`}
                  disabled={taken}
                  onClick={() => {
                    onChange(s.color);
                    setOpen(false);
                  }}
                >
                  <VanillaPreview color={s.color} small />
                  <span className="cc-select-opt-name">{s.fullName}</span>
                  <span className="cc-select-opt-slug">char_{s.color}</span>
                  {taken ? (
                    <span className="cc-select-opt-flag">in use</span>
                  ) : selected ? (
                    <Check size={14} aria-hidden="true" />
                  ) : null}
                </button>
              );
            })}
          </div>,
          document.body,
        )}
    </div>
  );
}

/** One slot on the global board: who it replaces, who currently fills it (from
 *  active mods), and a picker to change/resolve it. */
function SlotRow({
  slot,
  occupants,
  others,
  unassigned,
  nameForMod,
  onSetSlot,
}: {
  slot: CharacterSlot;
  occupants: CharacterCandidate[];
  others: CharacterCandidate[];
  unassigned: CharacterCandidate[];
  nameForMod: (id: string) => string;
  onSetSlot: (color: string, chosen: CharacterCandidate | null) => void;
}) {
  const active = occupants.filter((o) => o.active);
  const winner = active[0] ?? null;
  const conflict = active.length > 1;

  return (
    <div className={`cc-slotrow${winner ? " filled" : ""}`}>
      <div className="cc-slotrow-slot">
        <VanillaPreview color={slot.color} />
        <div className="cc-slotrow-slotmeta">
          <div className="cc-slotrow-name">{slot.fullName}</div>
          <div className="cc-slotrow-slug">char_{slot.color}</div>
        </div>
      </div>

      <div className="cc-slotrow-fill">
        {winner ? (
          <>
            <CandidatePreview candidate={winner} />
            <div className="cc-occupant-meta">
              <div className="cc-occupant-name">
                {winner.metadata?.fullName ?? nameForMod(winner.packId)}
              </div>
              <div className="cc-occupant-sub">{nameForMod(winner.packId)}</div>
            </div>
            {conflict && (
              <span
                className="cc-conflict-badge"
                title={`${active.length} active mods target this slot`}
              >
                <TriangleAlert size={12} aria-hidden="true" />
                {active.length}
              </span>
            )}
          </>
        ) : (
          <span className="cc-vanilla-note">Vanilla</span>
        )}
      </div>

      <FillPicker
        color={slot.color}
        occupants={active}
        winner={winner}
        others={others}
        unassigned={unassigned}
        nameForMod={nameForMod}
        onSetSlot={onSetSlot}
      />
    </div>
  );
}

function sameCandidate(a: CharacterCandidate, b: CharacterCandidate): boolean {
  return a.packId === b.packId && a.relPath === b.relPath;
}

/** Dropdown to fill/resolve a slot: pick vanilla, one of the sheets already
 *  here, a character in another slot (moves it), or one from the pool. */
function FillPicker({
  color,
  occupants,
  winner,
  others,
  unassigned,
  nameForMod,
  onSetSlot,
}: {
  color: string;
  occupants: CharacterCandidate[];
  winner: CharacterCandidate | null;
  others: CharacterCandidate[];
  unassigned: CharacterCandidate[];
  nameForMod: (id: string) => string;
  onSetSlot: (color: string, chosen: CharacterCandidate | null) => void;
}) {
  const { open, setOpen, style, triggerRef, menuRef, toggle } =
    useAnchoredMenu(320);

  const pick = (chosen: CharacterCandidate | null) => {
    onSetSlot(color, chosen);
    setOpen(false);
  };

  return (
    <div className="cc-fillpicker">
      <button
        ref={triggerRef}
        type="button"
        className={`cc-action${open ? " open" : ""}`}
        onClick={toggle}
      >
        {winner ? "Change" : "Fill"}
        <ChevronDown size={12} aria-hidden="true" />
      </button>
      {open &&
        createPortal(
          <div
            ref={menuRef}
            className="cc-floating-menu"
            style={style}
            role="listbox"
          >
          {winner && (
            <button
              type="button"
              className="cc-select-opt"
              onClick={() => pick(null)}
            >
              <span className="cc-fillopt-name">Vanilla (remove)</span>
            </button>
          )}
          {occupants.length > 0 && (
            <div className="cc-menu-label">Here now</div>
          )}
          {occupants.map((o) => (
            <FillOption
              key={`${o.packId}:${o.relPath}`}
              candidate={o}
              modName={nameForMod(o.packId)}
              selected={winner ? sameCandidate(o, winner) : false}
              onClick={() => pick(o)}
            />
          ))}
          {others.length > 0 && (
            <div className="cc-menu-label">In other slots (move here)</div>
          )}
          {others.map((o) => (
            <FillOption
              key={`${o.packId}:${o.relPath}`}
              candidate={o}
              modName={nameForMod(o.packId)}
              selected={false}
              onClick={() => pick(o)}
            />
          ))}
          {unassigned.length > 0 && (
            <div className="cc-menu-label">Unassigned</div>
          )}
          {unassigned.map((o) => (
            <FillOption
              key={`${o.packId}:${o.relPath}`}
              candidate={o}
              modName={nameForMod(o.packId)}
              selected={false}
              onClick={() => pick(o)}
            />
          ))}
          </div>,
          document.body,
        )}
    </div>
  );
}

function FillOption({
  candidate,
  modName,
  selected,
  onClick,
}: {
  candidate: CharacterCandidate;
  modName: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="option"
      aria-selected={selected}
      className={`cc-select-opt cc-fillopt${selected ? " selected" : ""}`}
      onClick={onClick}
    >
      <CandidatePreview candidate={candidate} small />
      <span className="cc-fillopt-meta">
        <span className="cc-fillopt-name">
          {candidate.metadata?.fullName ?? candidate.fileName}
        </span>
        <span className="cc-fillopt-mod">{modName}</span>
      </span>
      {selected && <Check size={14} aria-hidden="true" />}
    </button>
  );
}

/** A character sheet not currently occupying a known slot (pool / review /
 *  ignored). When `onConfirm`/`onReject` are passed it renders an "Is this a
 *  character?" Yes/No triage instead of the plain actions. */
function PotentialCard({
  candidate,
  nameForMod,
  onIgnore,
  onUnignore,
  onRestore,
  onConfirm,
  onReject,
}: {
  candidate: CharacterCandidate;
  nameForMod: (id: string) => string;
  onIgnore?: () => void;
  onUnignore?: () => void;
  onRestore?: () => void;
  onConfirm?: () => void;
  onReject?: () => void;
}) {
  const triage = Boolean(onConfirm || onReject);
  return (
    <div className={`cc-potential${candidate.active ? "" : " inactive"}`}>
      <CandidatePreview candidate={candidate} />
      <div className="cc-occupant-meta">
        <div className="cc-occupant-name">
          {candidate.metadata?.fullName ?? candidate.fileName}
        </div>
        <div className="cc-occupant-sub" title={candidate.relPath}>
          {nameForMod(candidate.packId)}
        </div>
        <CandidateBadges candidate={candidate} showConfidence />
        {triage ? (
          <div className="cc-triage">
            <span className="cc-triage-q">Is this a character?</span>
            <div className="cc-triage-btns">
              <button type="button" className="cc-action" onClick={onConfirm}>
                Yes
              </button>
              <button type="button" className="cc-action ghost" onClick={onReject}>
                No
              </button>
            </div>
          </div>
        ) : (
          <div className="cc-card-actions">
            {onRestore && candidate.originalRelPath && (
              <button
                type="button"
                className="cc-link-btn"
                onClick={onRestore}
                title="Put it back where the mod shipped it"
              >
                Restore
              </button>
            )}
            {onIgnore && !candidate.userDisabled && (
              <button
                type="button"
                className="cc-link-btn"
                onClick={onIgnore}
                title="Hide this file; it isn't a character"
              >
                Not a character
              </button>
            )}
            {onUnignore && (
              <button type="button" className="cc-link-btn" onClick={onUnignore}>
                It's a character
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function CandidateBadges({
  candidate,
  showConfidence = false,
}: {
  candidate: CharacterCandidate;
  showConfidence?: boolean;
}) {
  return (
    <div className="cc-badges">
      {showConfidence && candidate.confidence !== "definite" && (
        <span className={`cc-badge conf-${candidate.confidence}`}>
          {candidate.confidence}
        </span>
      )}
      {candidate.isFull && <span className="cc-badge full">full</span>}
      {candidate.userUnassigned && (
        <span className="cc-badge muted" title="Removed from its slot, still available">
          unassigned
        </span>
      )}
      {candidate.userDisabled && (
        <span className="cc-badge muted" title="Turned off">
          disabled
        </span>
      )}
      {!candidate.active && <span className="cc-badge muted">inactive</span>}
      {candidate.nameMismatch && (
        <span className="cc-badge warn" title="Filename disagrees with size">
          misnamed
        </span>
      )}
      {!candidate.dimsOk && (
        <span
          className="cc-badge warn"
          title={`${candidate.width}x${candidate.height}, not a char sheet size`}
        >
          wrong size
        </span>
      )}
    </div>
  );
}

/** Lazily fetches and shows a candidate's standing-frame crop. */
function CandidatePreview({
  candidate,
  small = false,
}: {
  candidate: CharacterCandidate;
  small?: boolean;
}) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    getCharacterPreview(candidate.packId, candidate.relPath)
      .then((u) => {
        if (!cancelled) setUrl(u);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [candidate.packId, candidate.relPath]);
  return (
    <div className={`cc-preview${small ? " cc-preview-sm" : ""}`}>
      {url ? <img src={url} alt="" /> : <div className="cc-preview-ph" />}
    </div>
  );
}

/** Vanilla slot portrait; falls back to a color chip when assets are absent. */
function VanillaPreview({
  color,
  small = false,
}: {
  color: string;
  small?: boolean;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [tried, setTried] = useState(false);
  useEffect(() => {
    let cancelled = false;
    getVanillaCharacterPreview(color)
      .then((u) => {
        if (!cancelled) {
          setUrl(u);
          setTried(true);
        }
      })
      .catch(() => {
        if (!cancelled) setTried(true);
      });
    return () => {
      cancelled = true;
    };
  }, [color]);
  const cls = `cc-preview cc-preview-vanilla${small ? " cc-preview-sm" : ""}`;
  if (url) {
    return (
      <div className={cls}>
        <img src={url} alt="" />
      </div>
    );
  }
  return (
    <div
      className={`${cls} cc-chip`}
      title={tried ? "Extract assets to see vanilla art" : undefined}
    >
      {color}
    </div>
  );
}

/** Active mods before inactive; then by load order (lower rank first). */
function compareOccupants(a: CharacterCandidate, b: CharacterCandidate): number {
  if (a.active !== b.active) return a.active ? -1 : 1;
  const ra = a.loadRank ?? Number.POSITIVE_INFINITY;
  const rb = b.loadRank ?? Number.POSITIVE_INFINITY;
  return ra - rb;
}

function extractMessage(err: unknown): string {
  if (typeof err === "string") return err;
  if (err && typeof err === "object") {
    for (const v of Object.values(err)) {
      if (typeof v === "string") return v;
    }
    return JSON.stringify(err);
  }
  return String(err);
}

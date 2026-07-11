// Add-tile modal. Two side-by-side comboboxes for primary + alt (alt
// greyed out at 100% chance so its slot doesn't jump around when the
// slider moves), a chance slider, and a live preview swatch rendered
// from the backend so percent tiles show their diagonal composite.
//
// For vanilla files, the parent also passes `dependencyPalettes` (the
// palettes of the sister-location files that inherit into this one). A
// quick-pick strip at the top surfaces every tile the game will already
// know via inheritance, so a single click adopts it into this file
// instead of retyping the name.

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  getTileSprite,
  listShortCodes,
  listValidTileCodes,
  type CustomLevelPaletteEntry,
  type DependencyPalette,
  type EditorAtlas,
  type TileSprite,
} from "../../lib/commands";
import { Modal } from "../shared/Modal";
import "./AddTileModal.css";

// How a candidate tile code relates to what's already bound, given the tile
// being added:
//   free      - unused anywhere; safe.
//   match     - used by an inherited tile with the SAME name; reusing it keeps
//               the game's binding consistent, so it's the preferred pick.
//   inherited - used by a DIFFERENT inherited tile; picking it shadows that
//               binding in this file. Allowed, with a warning.
//   local     - already used by a tile in THIS file; a file can't bind one code
//               to two tiles, so this is blocked.
type CodeState = "free" | "match" | "inherited" | "local";

interface Props {
  existing: CustomLevelPaletteEntry[];
  /** Biome name used for tile-sprite lookup (defaults to cave). */
  biome?: string | null;
  /** Sister-location palettes for the current vanilla file. When passed,
   *  their tiles surface as a quick-pick section at the top of the
   *  modal so the user can adopt an inherited tile in one click. */
  dependencyPalettes?: DependencyPalette[];
  /** Shared atlas for swatch rendering. Falls back to a plain sprite
   *  request per tile if omitted. */
  atlas?: EditorAtlas | null;
  onClose: () => void;
  onSubmit: (name: string, preview: TileSprite, code: string) => void;
  /** Called when the user quick-picks an inherited tile. The parent
   *  handles collision-aware allocation and closes the modal on success. */
  onAdoptInherited?: (
    sourceFileName: string,
    entry: CustomLevelPaletteEntry,
  ) => void;
}

export function AddTileModal({
  existing,
  biome,
  dependencyPalettes,
  atlas,
  onClose,
  onSubmit,
  onAdoptInherited,
}: Props) {
  const [validNames, setValidNames] = useState<string[]>([]);
  const [primary, setPrimary] = useState("");
  const [percent, setPercent] = useState(100);
  const [alt, setAlt] = useState("empty");
  const [preview, setPreview] = useState<TileSprite | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<number | null>(null);
  // Advanced: the single-character tile code this tile binds to. Auto-picked
  // to a safe free code (or a matching inherited one) until the user overrides
  // it via the code combobox; `codeTouched` stops the auto-fill from stomping
  // their choice.
  const [codePool, setCodePool] = useState<string[]>([]);
  const [code, setCode] = useState("");
  const [codeTouched, setCodeTouched] = useState(false);
  const [codeOpen, setCodeOpen] = useState(false);
  const codeWrapRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    listValidTileCodes()
      .then((names) => {
        if (!cancelled) setValidNames(names);
      })
      .catch(() => {
        // Non-fatal; freeform input still works.
      });
    listShortCodes()
      .then((codes) => {
        if (!cancelled) setCodePool(codes);
      })
      .catch(() => {
        // Non-fatal; the code chip just won't offer picks.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const composedName = useMemo(() => {
    const name = primary.trim();
    if (!name) return "";
    if (percent >= 100) return name;
    const altName = alt.trim();
    if (!altName || altName === "empty") return `${name}%${percent}`;
    return `${name}%${percent}%${altName}`;
  }, [primary, percent, alt]);

  const existingNames = useMemo(
    () => new Set(existing.map((e) => e.name)),
    [existing],
  );

  // code -> the local tile using it (a file can't reuse a code).
  const localByCode = useMemo(() => {
    const m = new Map<string, string>();
    for (const e of existing) m.set(e.code, e.name);
    return m;
  }, [existing]);
  // code -> the first inherited tile using it (closest sister wins), skipping
  // codes already taken locally (those are a local conflict, not inherited).
  const inheritedByCode = useMemo(() => {
    const m = new Map<string, { file: string; tile: string }>();
    for (const dep of dependencyPalettes ?? []) {
      for (const e of dep.palette) {
        if (localByCode.has(e.code) || m.has(e.code)) continue;
        m.set(e.code, { file: dep.fileName, tile: e.name });
      }
    }
    return m;
  }, [dependencyPalettes, localByCode]);

  const classifyCode = useCallback(
    (c: string): { state: CodeState; context: string | null } => {
      const local = localByCode.get(c);
      if (local !== undefined) {
        return { state: "local", context: `this file: ${local}` };
      }
      const inh = inheritedByCode.get(c);
      if (inh) {
        const state = inh.tile === composedName ? "match" : "inherited";
        return { state, context: `${inh.file}: ${inh.tile}` };
      }
      return { state: "free", context: null };
    },
    [localByCode, inheritedByCode, composedName],
  );

  // Every valid code with its state, grouped available -> warning -> disabled
  // so the combobox reads as three tiers.
  const codeOptions = useMemo(() => {
    const rank: Record<CodeState, number> = {
      match: 0,
      free: 1,
      inherited: 2,
      local: 3,
    };
    return codePool
      .map((c) => ({ code: c, ...classifyCode(c) }))
      .sort((a, b) => rank[a.state] - rank[b.state]);
  }, [codePool, classifyCode]);

  // Preferred auto code: reuse a same-name inherited binding, else first free,
  // else first non-local (an inherited override) so there's always a pick when
  // free codes run out. Never a local code.
  const suggestedCode = useMemo(() => {
    for (const c of codePool) {
      const inh = inheritedByCode.get(c);
      if (inh && inh.tile === composedName && !localByCode.has(c)) return c;
    }
    for (const c of codePool) {
      if (!localByCode.has(c) && !inheritedByCode.has(c)) return c;
    }
    for (const c of codePool) {
      if (!localByCode.has(c)) return c;
    }
    return "";
  }, [codePool, inheritedByCode, localByCode, composedName]);

  // Follow the suggestion until the user picks a code themselves.
  useEffect(() => {
    if (!codeTouched) setCode(suggestedCode);
  }, [suggestedCode, codeTouched]);

  // Close the code combobox on an outside click.
  useEffect(() => {
    if (!codeOpen) return;
    const onDoc = (e: MouseEvent) => {
      if (!codeWrapRef.current?.contains(e.target as Node)) setCodeOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [codeOpen]);

  const codeState = useMemo(
    () => (code ? classifyCode(code).state : null),
    [code, classifyCode],
  );
  const codeInPool = codePool.length === 0 || codePool.includes(code);
  const codeError = useMemo(() => {
    // Pool unavailable (command failed): the chip is hidden and the parent
    // auto-allocates, so don't block on the empty code.
    if (codePool.length === 0) return null;
    if (!code) return "Pick a tile code.";
    if (!codeInPool) return `"${code}" isn't a valid tile code.`;
    if (codeState === "local") {
      return `Code "${code}" is already used by "${localByCode.get(code)}" in this file.`;
    }
    return null;
  }, [code, codeInPool, codeState, localByCode]);
  const codeWarning = useMemo(() => {
    if (codeState !== "inherited") return null;
    const inh = inheritedByCode.get(code);
    return `Overrides "${inh?.tile}" inherited from ${inh?.file}.`;
  }, [codeState, code, inheritedByCode]);

  const pickCode = useCallback((c: string) => {
    setCode(c);
    setCodeTouched(true);
    setCodeOpen(false);
  }, []);

  const validationError = useMemo(() => {
    if (!primary.trim()) return "Pick or type a primary tile.";
    if (existingNames.has(composedName)) {
      return `"${composedName}" is already in the palette.`;
    }
    return null;
  }, [primary, composedName, existingNames]);

  // Debounced preview fetch so typing doesn't hammer the backend.
  useEffect(() => {
    if (validationError) {
      setPreview(null);
      return;
    }
    if (debounceRef.current !== null) {
      window.clearTimeout(debounceRef.current);
    }
    setPreviewLoading(true);
    const handle = window.setTimeout(async () => {
      try {
        const p = await getTileSprite(composedName, biome ?? null);
        setPreview(p);
        setError(null);
      } catch (err) {
        setError(extractMessage(err));
        setPreview(null);
      } finally {
        setPreviewLoading(false);
      }
    }, 180);
    debounceRef.current = handle;
    return () => {
      window.clearTimeout(handle);
      setPreviewLoading(false);
    };
  }, [composedName, biome, validationError]);

  const canSubmit = !validationError && preview !== null && !codeError;
  const altDisabled = percent >= 100;

  return (
    <Modal
      open
      onClose={onClose}
      title="Add Tile"
      size="md"
      footer={
        <div className="add-tile-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            form="add-tile-form"
            className="btn btn-primary"
            disabled={!canSubmit}
          >
            Add tile
          </button>
        </div>
      }
    >
      <InheritedTilesStrip
        dependencyPalettes={dependencyPalettes}
        existing={existing}
        atlas={atlas}
        onAdopt={onAdoptInherited}
      />
      <form
        id="add-tile-form"
        className="add-tile-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (!canSubmit || !preview) return;
          onSubmit(composedName, preview, code);
        }}
      >
        <div className="add-tile-tile-row">
          <div className="add-tile-field">
            <span className="add-tile-label">Primary tile</span>
            <TileNameCombobox
              value={primary}
              onChange={setPrimary}
              names={validNames}
              placeholder="floor, spikes, treasure..."
              autoFocus
            />
          </div>
          <div className={`add-tile-field${altDisabled ? " disabled" : ""}`}>
            <span className="add-tile-label">Alt tile</span>
            <TileNameCombobox
              value={alt}
              onChange={setAlt}
              names={validNames}
              placeholder="empty"
              disabled={altDisabled}
            />
          </div>
        </div>

        <label className="add-tile-field">
          <span className="add-tile-label">Chance</span>
          <div className="add-tile-slider-row">
            <input
              type="range"
              min={1}
              max={100}
              step={1}
              value={percent}
              onChange={(e) => setPercent(Number(e.target.value))}
            />
            <input
              type="number"
              min={1}
              max={100}
              value={percent}
              onChange={(e) => setPercent(clamp(Number(e.target.value), 1, 100))}
              className="add-tile-percent"
            />
            <span>%</span>
          </div>
          <span className="add-tile-hint">
            {percent >= 100
              ? "Always the primary tile."
              : `${percent}% primary, ${100 - percent}% ${alt || "empty"}.`}
          </span>
        </label>

        <div className="add-tile-preview">
          <span className="add-tile-preview-label">Preview</span>
          <div className="add-tile-preview-swatch">
            {previewLoading && !preview && (
              <span className="add-tile-preview-status">Rendering...</span>
            )}
            {preview && (
              <img
                src={preview.pngDataUrl}
                alt="tile preview"
                width={96}
                height={96}
              />
            )}
          </div>
          <div className="add-tile-preview-name">
            {composedName || "(pick a primary tile)"}
          </div>
          {codePool.length > 0 && (
            <>
              <div className="add-tile-code" ref={codeWrapRef}>
                <span className="add-tile-code-label">code</span>
                <div className="add-tile-code-control">
                  <input
                    className={`add-tile-code-input${
                      codeError ? " invalid" : codeWarning ? " warn" : ""
                    }`}
                    value={code}
                    maxLength={1}
                    onChange={(e) => {
                      setCode(e.target.value);
                      setCodeTouched(true);
                    }}
                    onFocus={() => setCodeOpen(true)}
                    onClick={() => setCodeOpen(true)}
                    spellCheck={false}
                    aria-label="Tile code"
                    title="The single-character code this tile binds to"
                  />
                  {codeOpen && codeOptions.length > 0 && (
                    <ul className="add-tile-code-list" role="listbox">
                      {codeOptions.map((o) => (
                        <li
                          key={o.code}
                          role="option"
                          aria-selected={o.code === code}
                          aria-disabled={o.state === "local"}
                          className={`add-tile-code-opt ${o.state}${
                            o.code === code ? " current" : ""
                          }`}
                          onMouseDown={(e) => {
                            e.preventDefault();
                            if (o.state !== "local") pickCode(o.code);
                          }}
                        >
                          <span className="add-tile-code-opt-char">
                            {o.code}
                          </span>
                          {o.context && (
                            <span className="add-tile-code-opt-ctx">
                              {o.context}
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
              {(codeError || codeWarning) && (
                <div
                  className={`add-tile-code-msg${codeError ? " error" : " warn"}`}
                >
                  {codeError ?? codeWarning}
                </div>
              )}
            </>
          )}
        </div>

        {(error || validationError) && (
          <div className="add-tile-error">{error ?? validationError}</div>
        )}
      </form>
    </Modal>
  );
}

interface InheritedTilesStripProps {
  dependencyPalettes?: DependencyPalette[];
  existing: CustomLevelPaletteEntry[];
  atlas?: EditorAtlas | null;
  onAdopt?: (
    sourceFileName: string,
    entry: CustomLevelPaletteEntry,
  ) => void;
}

function InheritedTilesStrip({
  dependencyPalettes,
  existing,
  atlas,
  onAdopt,
}: InheritedTilesStripProps) {
  const existingNames = useMemo(
    () => new Set(existing.map((e) => e.name)),
    [existing],
  );
  const uvByName = useMemo(() => {
    const map = new Map<string, { x: number; y: number; w: number; h: number }>();
    if (atlas) {
      for (const t of atlas.tiles) {
        map.set(t.name, { x: t.x, y: t.y, w: t.w, h: t.h });
      }
    }
    return map;
  }, [atlas]);

  // Deduped list of adoptable inherited entries: first sister wins for
  // any given name so a tile that appears in generic AND junglearea only
  // shows up once. Order = the order dependencyPalettes came in, which
  // is closest-to-file first.
  const adoptable = useMemo(() => {
    const seen = new Set<string>();
    const out: { sourceFile: string; entry: CustomLevelPaletteEntry }[] = [];
    for (const dep of dependencyPalettes ?? []) {
      for (const entry of dep.palette) {
        if (existingNames.has(entry.name)) continue;
        if (seen.has(entry.name)) continue;
        seen.add(entry.name);
        out.push({ sourceFile: dep.fileName, entry });
      }
    }
    return out;
  }, [dependencyPalettes, existingNames]);

  if (!onAdopt || adoptable.length === 0) return null;

  const swatchSize = 36;
  const swatchStyleFor = (name: string): React.CSSProperties => {
    const uv = uvByName.get(name);
    if (uv && atlas) {
      const scale = Math.min(swatchSize / uv.w, swatchSize / uv.h);
      return {
        backgroundImage: `url(${atlas.pngDataUrl})`,
        backgroundPosition: `-${uv.x * scale}px -${uv.y * scale}px`,
        backgroundSize: `${atlas.width * scale}px ${atlas.height * scale}px`,
        backgroundRepeat: "no-repeat",
        width: swatchSize,
        height: swatchSize,
      };
    }
    return { width: swatchSize, height: swatchSize };
  };

  return (
    <section className="add-tile-inherited">
      <div className="add-tile-inherited-header">
        <span className="add-tile-inherited-title">
          Available from inherited files
        </span>
        <span className="add-tile-inherited-count">
          {adoptable.length}
        </span>
      </div>
      <p className="add-tile-inherited-hint">
        The game already knows these tiles through vanilla inheritance.
        Click one to adopt it into this file.
      </p>
      <ul className="add-tile-inherited-list">
        {adoptable.map(({ sourceFile, entry }) => (
          <li key={`${sourceFile}#${entry.name}`}>
            <button
              type="button"
              className="add-tile-inherited-item"
              onClick={() => onAdopt(sourceFile, entry)}
              title={`Adopt ${entry.name} from ${sourceFile}${entry.comment ? `\n${entry.comment}` : ""}`}
            >
              <span
                className="add-tile-inherited-swatch"
                style={swatchStyleFor(entry.name)}
              />
              <span className="add-tile-inherited-meta">
                <span className="add-tile-inherited-name">{entry.name}</span>
                <span className="add-tile-inherited-source">{sourceFile}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

interface ComboboxProps {
  value: string;
  onChange: (next: string) => void;
  names: string[];
  placeholder?: string;
  disabled?: boolean;
  autoFocus?: boolean;
}

// Filterable tile-name combobox. Free-form input still allowed so users
// can add custom Lua tiles that aren't in the built-in name list.
function TileNameCombobox({
  value,
  onChange,
  names,
  placeholder,
  disabled,
  autoFocus,
}: ComboboxProps) {
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const listRef = useRef<HTMLUListElement | null>(null);

  const filter = value.trim().toLowerCase();
  const filtered = useMemo(() => {
    if (!filter) return names.slice(0, 200);
    // Prefix matches first, then substring matches, capped so the DOM
    // doesn't get overwhelmed on empty filters.
    const prefix: string[] = [];
    const contains: string[] = [];
    for (const n of names) {
      const lower = n.toLowerCase();
      if (lower.startsWith(filter)) prefix.push(n);
      else if (lower.includes(filter)) contains.push(n);
    }
    return [...prefix, ...contains].slice(0, 200);
  }, [names, filter]);

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!wrapRef.current) return;
      if (!wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  // Reset active row when the filter changes.
  useEffect(() => {
    setActiveIdx(0);
  }, [filter]);

  // Keep the active row visible when arrow keys move it past the fold.
  useLayoutEffect(() => {
    if (!open) return;
    const el = listRef.current?.children[activeIdx] as HTMLElement | undefined;
    el?.scrollIntoView({ block: "nearest" });
  }, [open, activeIdx]);

  const commit = useCallback(
    (name: string) => {
      onChange(name);
      setOpen(false);
    },
    [onChange],
  );

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!open) setOpen(true);
      else setActiveIdx((i) => Math.min(filtered.length - 1, i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(0, i - 1));
    } else if (e.key === "Enter") {
      if (open && filtered[activeIdx]) {
        e.preventDefault();
        commit(filtered[activeIdx]);
      }
    } else if (e.key === "Escape") {
      if (open) {
        e.preventDefault();
        setOpen(false);
      }
    }
  };

  return (
    <div className="tile-combobox" ref={wrapRef}>
      <input
        type="text"
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          if (!open) setOpen(true);
        }}
        onClick={() => setOpen(true)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
        spellCheck={false}
      />
      {open && !disabled && filtered.length > 0 && (
        <ul className="tile-combobox-list" ref={listRef} role="listbox">
          {filtered.map((n, i) => (
            <li
              key={n}
              role="option"
              aria-selected={i === activeIdx}
              className={`tile-combobox-item${i === activeIdx ? " active" : ""}`}
              onMouseDown={(e) => {
                e.preventDefault();
                commit(n);
              }}
              onMouseMove={() => setActiveIdx(i)}
            >
              {n}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function clamp(v: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, v));
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

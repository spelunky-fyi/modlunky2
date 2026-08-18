import { useCallback, useEffect, useMemo, useState } from "react";
import { ask } from "@tauri-apps/plugin-dialog";
import { listen } from "@tauri-apps/api/event";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { restrictToVerticalAxis } from "@dnd-kit/modifiers";
import {
  checkFyiUpdates,
  checkMod,
  getConfig,
  getLoadOrder,
  listMods,
  openCharacterChooserWindow,
  openModFolder,
  refreshMods,
  removeMod,
  setConfig,
  setLoadOrder,
  setModFavorite,
  updateMod,
} from "../../lib/commands";
import {
  ArrowDownWideNarrow,
  ArrowUpNarrowWide,
  CircleFadingArrowUp,
  Plus,
  RotateCcw,
  Search,
  Star,
  Users,
} from "lucide-react";
import type { Mod, ModDensity, ModSort } from "../../types/mods";
import { describeProblem } from "../../types/mods";
import { relativeTime, sortMods } from "../../lib/modSort";
import {
  DEFAULT_MOD_DENSITY,
  MOD_DENSITIES,
  MOD_DENSITY_LABELS,
  MOD_SORTS,
  MOD_SORT_LABELS,
  defaultDescending,
  isModDensity,
  isModSort,
} from "../../types/mods";
import { useToast } from "../shared/Toast";
import { useSetup } from "../shared/SetupContext";
import { ModColumn } from "./ModColumn";
import { InstallModal } from "./InstallModal";
import "./ModsPage.css";

// Module-scope cache so remounting the tab (e.g. after switching away)
// can render the last-known list immediately instead of a full-page
// spinner. Important because Rust's mods handle serializes `list_mods`
// calls against in-flight updates: without a cache, remounting mid-update
// hangs on "Loading…" until the update finishes.
let cachedMods: Mod[] = [];
let cachedActiveIds: string[] = [];
let cachedUpdatingIds: Set<string> = new Set();
let hasCache = false;

// Any mounted ModsPage subscribes here. When the cache mutates from an
// async handler that closed over an unmounted instance (e.g. an in-flight
// updateMod that resolved after the user switched tabs), we still notify
// the fresh mount so it can re-read cache and drop the "Updating…" state.
type CacheListener = () => void;
const cacheListeners = new Set<CacheListener>();
function notifyCacheChanged() {
  for (const fn of cacheListeners) fn();
}

export function ModsPage() {
  const toast = useToast();
  const [mods, setMods] = useState<Mod[]>(cachedMods);
  const [activeIds, setActiveIds] = useState<string[]>(cachedActiveIds);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    hasCache ? "ready" : "loading",
  );
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [installOpen, setInstallOpen] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [checkingUpdates, setCheckingUpdates] = useState(false);
  const [search, setSearch] = useState("");
  // Ordering + favorites filtering apply to the Inactive column only. Active
  // is Playlunky's load_order.txt: its order is data the game reads, not a
  // view, and it's drag-reorderable. Reordering it here would either lie
  // about the load order or silently change what the game loads.
  const [sort, setSort] = useState<ModSort>("name");
  const [descending, setDescending] = useState(false);
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  // Density is page-wide rather than per-column: it answers "how much of my
  // list can I see", which isn't a question about one column.
  const [density, setDensity] = useState<ModDensity>(DEFAULT_MOD_DENSITY);
  // Guards the persist effect below so restoring the saved values doesn't
  // immediately write them straight back out.
  const [prefsLoaded, setPrefsLoaded] = useState(false);
  // Mods with an in-flight file check, so the badge can show progress and a
  // double-click can't queue a second scan of the same pack.
  const [checkingIds, setCheckingIds] = useState<Set<string>>(new Set());
  const setup = useSetup();
  // Ids of mods with an in-flight `updateMod` call. Used to disable the
  // row's Update button and swap its label to "Updating…" so the click
  // gives immediate feedback instead of appearing to do nothing.
  const [updatingIds, setUpdatingIds] = useState<Set<string>>(
    () => new Set(cachedUpdatingIds),
  );

  // `showLoading` flips the whole page into a spinner state; only the very
  // first mount (or an explicit hard reload) should do that. Post-action
  // refreshes and background `mods-changed` events must keep the current
  // list visible so clicking Update on a single row doesn't blank the page.
  // `force` sidesteps Rust's mod cache and hits disk directly, used by the
  // Refresh button and by post-action refreshes after a pack was created or
  // deleted outside the cache-managed flow.
  const reload = useCallback(
    async ({
      showLoading = false,
      force = false,
    }: { showLoading?: boolean; force?: boolean } = {}): Promise<void> => {
      if (showLoading && !hasCache) setStatus("loading");
      try {
        const [loadedMods, order] = await Promise.all([
          force ? refreshMods() : listMods(),
          getLoadOrder(),
        ]);
        const known = new Set(loadedMods.map((m) => m.id));
        const nextActive = order.filter((id) => known.has(id));
        cachedMods = loadedMods;
        cachedActiveIds = nextActive;
        hasCache = true;
        notifyCacheChanged();
        setMods(loadedMods);
        setActiveIds(nextActive);
        setStatus("ready");
      } catch (err) {
        setErrorMessage(extractMessage(err));
        // Only surface the error page when we don't already have a mod
        // list rendered. Silent refreshes during an in-flight update
        // occasionally race the FS; blanking the page for a transient
        // error looks like a regression to the user.
        setStatus((prev) => (prev === "ready" ? "ready" : "error"));
      }
    },
    [],
  );

  useEffect(() => {
    void reload({ showLoading: true });
  }, [reload]);

  // Restore the saved view preferences. These live in the shared config
  // rather than beside the mods, because unlike favorites they name no
  // particular mod and so mean the same thing whichever install is open.
  useEffect(() => {
    let cancelled = false;
    void getConfig()
      .then((cfg) => {
        if (cancelled) return;
        const saved = isModSort(cfg.modSort) ? cfg.modSort : "name";
        setSort(saved);
        // Null means never set, which is why the config keeps it nullable:
        // each field has a different natural direction.
        setDescending(cfg.modSortDesc ?? defaultDescending(saved));
        setFavoritesOnly(cfg.modFavoritesOnly);
        setDensity(
          isModDensity(cfg.modDensity) ? cfg.modDensity : DEFAULT_MOD_DENSITY,
        );
      })
      .catch(() => {
        // Falls back to the defaults already in state.
      })
      .finally(() => {
        if (!cancelled) setPrefsLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!prefsLoaded) return;
    void setConfig({
      modSort: sort,
      modSortDesc: descending,
      modFavoritesOnly: favoritesOnly,
      modDensity: density,
    }).catch(() => {});
  }, [prefsLoaded, sort, descending, favoritesOnly, density]);

  // Picking a different field resets the direction to that field's natural
  // one: nobody wants Z-to-A or oldest-first as the opening move, and the
  // arrow is right there when they do.
  const changeSort = (next: ModSort) => {
    setSort(next);
    setDescending(defaultDescending(next));
  };

  // Sync from cache when a handler on a prior instance mutates it (e.g.
  // handleUpdate's `finally` running after we've remounted).
  useEffect(() => {
    const sync = () => {
      setMods([...cachedMods]);
      setActiveIds([...cachedActiveIds]);
      setUpdatingIds(new Set(cachedUpdatingIds));
    };
    cacheListeners.add(sync);
    return () => {
      cacheListeners.delete(sync);
    };
  }, []);

  // Refetch reactively when the Rust side detects a Change (new version
  // available, update finished, mod removed, etc). Silent refresh so the UI
  // stays put.
  useEffect(() => {
    const unlistenPromise = listen("mods-changed", () => {
      void reload();
    });
    return () => {
      unlistenPromise.then((unlisten) => unlisten());
    };
  }, [reload]);

  // Persist load order on every change. Fire and forget with a toast on
  // failure; the UI state stays authoritative so the user's action isn't
  // rolled back on a transient write error.
  const persistOrder = (next: string[]) => {
    setLoadOrder(next).catch((err) => {
      toast.error(`Couldn't save load order: ${extractMessage(err)}`);
    });
  };

  const activeSet = useMemo(() => new Set(activeIds), [activeIds]);
  const searchQuery = search.trim().toLowerCase();
  const isFiltering = searchQuery.length > 0;
  const modMatches = useCallback(
    (mod: Mod) => {
      if (!isFiltering) return true;
      const idHit = mod.id.toLowerCase().includes(searchQuery);
      const name = mod.manifest?.name?.toLowerCase() ?? "";
      const slug = mod.manifest?.slug?.toLowerCase() ?? "";
      return idHit || name.includes(searchQuery) || slug.includes(searchQuery);
    },
    [isFiltering, searchQuery],
  );
  const activeMods = useMemo(
    () =>
      activeIds
        .map((id) => mods.find((m) => m.id === id))
        .filter((m): m is Mod => m !== undefined)
        .filter(modMatches),
    [activeIds, mods, modMatches],
  );
  // Inactive mods have no user-defined order (unlike active, which is the
  // drag-sortable load order), so they're ordered by whichever field the
  // user picked. Search and the favorites toggle both narrow the set; sort
  // owns the order. Keeping those jobs separate is why favorites is a filter
  // and not a pin -- a pin would silently overrule the sort control.
  const inactiveMods = useMemo(() => {
    const rows = mods
      .filter((m) => !activeSet.has(m.id))
      .filter(modMatches)
      .filter((m) => !favoritesOnly || m.favorite);
    return sortMods(rows, sort, descending);
  }, [mods, activeSet, modMatches, favoritesOnly, sort, descending]);

  // Sorting by a value the row doesn't display leaves the order looking
  // arbitrary, and "never played" is indistinguishable from "played months
  // ago" when both just sink to the bottom. That bites hardest on day one,
  // when nothing has been played yet and the sort appears to do nothing at
  // all. Only shown for the usage sort: the others order by something already
  // on screen (the name) or by a value with no empty case (the install time).
  const rowDetail = useMemo(() => {
    if (sort !== "used") return undefined;
    return (mod: Mod) =>
      mod.lastUsedAt
        ? `played ${relativeTime(mod.lastUsedAt)}`
        : "never played";
  }, [sort]);

  const favoriteCount = useMemo(
    () => mods.filter((m) => m.favorite && !activeSet.has(m.id)).length,
    [mods, activeSet],
  );

  const handleToggleFavorite = async (mod: Mod) => {
    const next = !mod.favorite;
    // Optimistic: the star should respond to the click immediately, and a
    // failed write is reported rather than silently reverted mid-list.
    const apply = (list: Mod[]) =>
      list.map((m) => (m.id === mod.id ? { ...m, favorite: next } : m));
    cachedMods = apply(cachedMods);
    notifyCacheChanged();
    setMods(apply);
    try {
      await setModFavorite(mod.id, next);
    } catch (err) {
      toast.error(`Couldn't save favorite: ${extractMessage(err)}`);
      await reload();
    }
  };

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  // Every load-order change goes through here. The module cache is part of
  // that write, not just the state: `sync` restores activeIds from
  // `cachedActiveIds`, so a commit that only touched state would be undone
  // by the next notifyCacheChanged() (a favorite toggle, a file check, an
  // update starting) and the reverted order would then be persisted by the
  // following commit. The cache is also the base every commit reads from,
  // because callers reach here after awaits where the closed-over state may
  // be a render behind.
  const commitActiveIds = (next: string[]) => {
    cachedActiveIds = next;
    notifyCacheChanged();
    setActiveIds(next);
    persistOrder(next);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const from = cachedActiveIds.indexOf(String(active.id));
    const to = cachedActiveIds.indexOf(String(over.id));
    if (from < 0 || to < 0) return;
    commitActiveIds(arrayMove(cachedActiveIds, from, to));
  };

  const commitActivate = (id: string) => {
    if (cachedActiveIds.includes(id)) return;
    commitActiveIds([...cachedActiveIds, id]);
  };

  /**
   * Enabling runs the file check first, against the files as they are right
   * now rather than whatever the badge cached, because this is the moment it
   * actually matters.
   *
   * It warns rather than refuses. We only detect files that are definitely
   * broken, but Playlunky is the authority on what it will accept, and being
   * wrong in the blocking direction would mean locking someone out of a mod
   * that works.
   */
  const activate = async (id: string) => {
    const mod = mods.find((m) => m.id === id);
    const name = mod?.manifest?.name ?? id;
    let problems: Awaited<ReturnType<typeof checkMod>> = [];
    try {
      problems = await checkMod(id);
    } catch {
      // A failed check is not a reason to block the user from their mod.
      commitActivate(id);
      return;
    }
    // Fold the fresh result back into the list so the badge agrees with what
    // we just found, whichever way the user answers.
    applyProblems(id, problems);
    if (problems.length > 0) {
      const detail = problems.map(describeProblem).join("\n");
      const ok = await ask(
        `${name} has a problem that can crash the game:

${detail}

Enable anyway?`,
        { title: "Problem found", kind: "warning" },
      );
      if (!ok) return;
    }
    commitActivate(id);
  };

  /** Writes a check result into both the render state and the module cache. */
  const applyProblems = (id: string, problems: Mod["problems"]) => {
    const apply = (list: Mod[]) =>
      list.map((m) => (m.id === id ? { ...m, problems } : m));
    cachedMods = apply(cachedMods);
    notifyCacheChanged();
    setMods(apply);
  };

  /** Re-runs the check on demand, for someone who has just fixed the file. */
  const handleRecheck = async (mod: Mod) => {
    if (checkingIds.has(mod.id)) return;
    setCheckingIds((prev) => new Set(prev).add(mod.id));
    try {
      const problems = await checkMod(mod.id);
      applyProblems(mod.id, problems);
      const name = mod.manifest?.name ?? mod.id;
      if (problems.length === 0) {
        toast.success(`${name} looks fine now.`);
      } else {
        toast.warning(
          `${name} still has a problem: ${describeProblem(problems[0])}`,
        );
      }
    } catch (err) {
      toast.error(`Couldn't check ${mod.id}: ${extractMessage(err)}`);
    } finally {
      setCheckingIds((prev) => {
        const next = new Set(prev);
        next.delete(mod.id);
        return next;
      });
    }
  };
  const deactivate = (id: string) => {
    if (!cachedActiveIds.includes(id)) return;
    commitActiveIds(cachedActiveIds.filter((x) => x !== id));
  };

  const handleDelete = async (mod: Mod) => {
    const name = mod.manifest?.name ?? mod.id;
    const confirmed = await ask(
      `Delete "${name}"? This removes the mod folder permanently.`,
      { title: "Delete mod", kind: "warning" },
    );
    if (!confirmed) return;
    try {
      await removeMod(mod.id);
      toast.success(`Deleted ${name}.`);
      // Force a disk-backed refresh so the deleted row disappears without
      // waiting for the cache's periodic scan.
      await reload({ force: true });
    } catch (err) {
      toast.error(`Delete failed: ${extractMessage(err)}`);
    }
  };

  const handleOpenFolder = async (id: string) => {
    try {
      await openModFolder(id);
    } catch (err) {
      toast.error(extractMessage(err));
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await reload({ force: true });
    } finally {
      setRefreshing(false);
    }
  };

  const handleCheckUpdates = async () => {
    setCheckingUpdates(true);
    try {
      const found = await checkFyiUpdates();
      if (found === 0) {
        toast.info("All mods are up to date.");
      } else if (found === 1) {
        toast.success("Found 1 mod with a new version.");
      } else {
        toast.success(`Found ${found} mods with new versions.`);
      }
    } catch (err) {
      toast.error(extractMessage(err));
    } finally {
      setCheckingUpdates(false);
    }
  };

  const handleUpdate = async (mod: Mod) => {
    const name = mod.manifest?.name ?? mod.id;
    if (updatingIds.has(mod.id) || cachedUpdatingIds.has(mod.id)) return;
    cachedUpdatingIds.add(mod.id);
    notifyCacheChanged();
    setUpdatingIds((prev) => {
      const next = new Set(prev);
      next.add(mod.id);
      return next;
    });
    try {
      await updateMod(mod.id);
      toast.success(`Updated ${name}.`);
      await reload();
    } catch (err) {
      toast.error(`Update failed: ${extractMessage(err)}`);
    } finally {
      cachedUpdatingIds.delete(mod.id);
      notifyCacheChanged();
      setUpdatingIds((prev) => {
        const next = new Set(prev);
        next.delete(mod.id);
        return next;
      });
    }
  };

  return (
    <div className="mods-page" data-density={density}>
      <header className="mods-header">
        <span className="mods-summary">
          {mods.length} installed, {activeIds.length} active
        </span>
        <div className="mods-search">
          <Search size={14} aria-hidden="true" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search…"
            aria-label="Filter mods by name"
            spellCheck={false}
          />
        </div>
        <div className="mods-actions">
          {/* Page-level rather than in a column header: it changes both
              columns, and it's the answer to "I have hundreds of mods and
              can only see nine", so it needs to be findable. */}
          <select
            className="mods-density-select"
            value={density}
            onChange={(e) => setDensity(e.target.value as ModDensity)}
            title="How tightly to pack the mod rows"
            aria-label="Row density"
          >
            {MOD_DENSITIES.map((option) => (
              <option key={option} value={option}>
                {MOD_DENSITY_LABELS[option]}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="icon-button mods-action-icon"
            title="Refresh"
            aria-label="Refresh"
            onClick={() => void handleRefresh()}
            disabled={refreshing || status === "loading"}
          >
            <RotateCcw size={16} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="icon-button mods-action-icon"
            title="Check spelunky.fyi for mod updates"
            aria-label="Check for mod updates"
            onClick={() => void handleCheckUpdates()}
            disabled={checkingUpdates}
          >
            <CircleFadingArrowUp size={16} aria-hidden="true" />
          </button>
          <button
            className="btn btn-primary"
            type="button"
            onClick={() => setInstallOpen(true)}
          >
            <Plus size={14} aria-hidden="true" /> Install
          </button>
        </div>
      </header>

      {status === "loading" && <div className="mods-empty">Loading…</div>}
      {status === "error" && (
        <div className="mods-empty mods-error">
          <p>Couldn’t read your mods:</p>
          <pre>{errorMessage}</pre>
          <div className="mods-error-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => void reload({ showLoading: true, force: true })}
            >
              Try again
            </button>
            {setup.status && setup.status.installDir !== "ok" && (
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setup.openSettings("installDir")}
              >
                Open Settings
              </button>
            )}
          </div>
        </div>
      )}

      {status === "ready" && (
        <>
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            modifiers={[restrictToVerticalAxis]}
            onDragEnd={handleDragEnd}
          >
            <div className="mods-columns">
              <ModColumn
                title="Inactive"
                mods={inactiveMods}
                toggleLabel="Enable"
                onToggle={(id) => void activate(id)}
                onDelete={handleDelete}
                onOpenFolder={handleOpenFolder}
                onUpdate={handleUpdate}
                onToggleFavorite={(mod) => void handleToggleFavorite(mod)}
                onRecheck={(mod) => void handleRecheck(mod)}
                checkingIds={checkingIds}
                updatingIds={updatingIds}
                detail={rowDetail}
                headerAction={
                  <div className="mods-sort">
                    <button
                      type="button"
                      className={`mod-column-action mods-fav-filter${favoritesOnly ? " is-on" : ""}`}
                      aria-pressed={favoritesOnly}
                      title={
                        favoritesOnly
                          ? "Showing favorites only"
                          : "Show favorites only"
                      }
                      onClick={() => setFavoritesOnly((v) => !v)}
                    >
                      <Star
                        size={13}
                        aria-hidden="true"
                        fill={favoritesOnly ? "currentColor" : "none"}
                      />
                      {favoriteCount > 0 && favoriteCount}
                    </button>
                    <label className="mods-sort-label" htmlFor="mods-sort-by">
                      Sort
                    </label>
                    <select
                      id="mods-sort-by"
                      className="mods-sort-select"
                      value={sort}
                      onChange={(e) => changeSort(e.target.value as ModSort)}
                    >
                      {MOD_SORTS.map((option) => (
                        <option key={option} value={option}>
                          {MOD_SORT_LABELS[option]}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      className="mod-column-action mods-sort-dir"
                      onClick={() => setDescending((v) => !v)}
                      title={
                        descending
                          ? `${MOD_SORT_LABELS[sort]}, descending`
                          : `${MOD_SORT_LABELS[sort]}, ascending`
                      }
                      aria-label={
                        descending
                          ? "Sorting descending, switch to ascending"
                          : "Sorting ascending, switch to descending"
                      }
                    >
                      {descending ? (
                        <ArrowDownWideNarrow size={14} aria-hidden="true" />
                      ) : (
                        <ArrowUpNarrowWide size={14} aria-hidden="true" />
                      )}
                    </button>
                  </div>
                }
                emptyMessage={
                  favoritesOnly && favoriteCount === 0
                    ? "No favorites yet. Star a mod to keep it here."
                    : isFiltering || favoritesOnly
                      ? "No matches."
                      : "No inactive mods."
                }
              />
              <SortableContext
                items={activeIds}
                strategy={verticalListSortingStrategy}
              >
                <ModColumn
                  title="Active (load order)"
                  mods={activeMods}
                  toggleLabel="Disable"
                  onToggle={deactivate}
                  // No onDelete: an active mod is one the game is set to
                  // load, so deleting it here is a click away from breaking
                  // the next launch. Disable it first, then delete it from
                  // the inactive column.
                  onOpenFolder={handleOpenFolder}
                  onUpdate={handleUpdate}
                  onToggleFavorite={(mod) => void handleToggleFavorite(mod)}
                  onRecheck={(mod) => void handleRecheck(mod)}
                  checkingIds={checkingIds}
                  updatingIds={updatingIds}
                  headerAction={
                    <button
                      type="button"
                      className="mod-column-action"
                      onClick={() => void openCharacterChooserWindow()}
                      title="Manage which active-mod character fills each slot"
                    >
                      <Users size={14} aria-hidden="true" /> Characters
                    </button>
                  }
                  // Skip drag handles while filtering: reordering a filtered
                  // subset would reorder against the visible-order and not
                  // the load-order, which is confusing.
                  sortable={!isFiltering}
                  emptyMessage={
                    isFiltering
                      ? "No matches."
                      : "No active mods. Enable one from the left."
                  }
                />
              </SortableContext>
            </div>
          </DndContext>
        </>
      )}

      <InstallModal open={installOpen} onClose={() => setInstallOpen(false)} />
    </div>
  );
}

function extractMessage(err: unknown): string {
  if (typeof err === "string") return err;
  if (err && typeof err === "object") {
    for (const value of Object.values(err)) {
      if (typeof value === "string") return value;
    }
    return JSON.stringify(err);
  }
  return String(err);
}

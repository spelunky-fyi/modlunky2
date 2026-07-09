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
  getLoadOrder,
  listMods,
  openCharacterChooserWindow,
  openModFolder,
  refreshMods,
  removeMod,
  setLoadOrder,
  updateMod,
} from "../../lib/commands";
import {
  CircleFadingArrowUp,
  Plus,
  RotateCcw,
  Search,
  Users,
} from "lucide-react";
import type { Mod } from "../../types/mods";
import { useToast } from "../shared/Toast";
import { ModColumn } from "./ModColumn";
import { InstallModal } from "./InstallModal";
import { PlaylunkyPane } from "./PlaylunkyPane";
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
  // drag-sortable load order), so sort them alphabetically by display name
  // -- the same `manifest.name ?? id` shown in the row -- for a scannable
  // list. Case-insensitive, numeric-aware so "Mod 2" precedes "Mod 10".
  const inactiveMods = useMemo(
    () =>
      mods
        .filter((m) => !activeSet.has(m.id))
        .filter(modMatches)
        .sort((a, b) =>
          (a.manifest?.name ?? a.id).localeCompare(
            b.manifest?.name ?? b.id,
            undefined,
            { sensitivity: "base", numeric: true },
          ),
        ),
    [mods, activeSet, modMatches],
  );

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    setActiveIds((current) => {
      const from = current.indexOf(String(active.id));
      const to = current.indexOf(String(over.id));
      if (from < 0 || to < 0) return current;
      const next = arrayMove(current, from, to);
      persistOrder(next);
      return next;
    });
  };

  const activate = (id: string) =>
    setActiveIds((c) => {
      const next = [...c, id];
      persistOrder(next);
      return next;
    });
  const deactivate = (id: string) =>
    setActiveIds((c) => {
      const next = c.filter((x) => x !== id);
      persistOrder(next);
      return next;
    });

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
    <div className="mods-page">
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
                onToggle={activate}
                onDelete={handleDelete}
                onOpenFolder={handleOpenFolder}
                onUpdate={handleUpdate}
                updatingIds={updatingIds}
                emptyMessage={isFiltering ? "No matches." : "No inactive mods."}
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
                  onDelete={handleDelete}
                  onOpenFolder={handleOpenFolder}
                  onUpdate={handleUpdate}
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

          <PlaylunkyPane activeCount={activeIds.length} />
        </>
      )}

      <InstallModal
        open={installOpen}
        onClose={() => setInstallOpen(false)}
      />
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

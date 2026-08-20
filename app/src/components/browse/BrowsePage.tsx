import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ask } from "@tauri-apps/plugin-dialog";
import { Search } from "lucide-react";
import { useSetup } from "../shared/SetupContext";
import { useToast } from "../shared/Toast";
import { ConnectAccount } from "./ConnectAccount";
import { ModCard, ModCardSkeleton } from "./ModCard";
import { ModDetailPane } from "./ModDetailPane";
import { ReconnectPrompt } from "./ReconnectPrompt";
import {
  asBrowseError,
  browseMods,
  browseModOptions,
  installedFyiMods,
  installFromFyi,
  isAuthFailure,
  type BrowseError,
  type BrowseOptions,
  type InstalledFyiMod,
  type ModListing,
} from "../../lib/commands";
import "./BrowsePage.css";

/** How many cards a page request asks for. The API caps at 100. */
const PAGE_SIZE = 30;

/** Long enough that typing a mod name is one request, short enough that it
 *  still feels like search rather than a form submit. */
const SEARCH_DEBOUNCE_MS = 300;

/** Placeholders shown before the first page arrives. A full page's worth, so a
 *  maximised window is covered rather than showing two rows and a void. */
const SKELETON_COUNT = PAGE_SIZE;

export function BrowsePage() {
  const { status } = useSetup();
  // Render nothing until setup state is known, so a connected user never sees
  // a flash of the connect wall.
  if (!status) return null;
  if (!status.hasApiToken) return <ConnectAccount />;
  return <BrowseGrid />;
}

interface Filters {
  q: string;
  modType: number | null;
  orderBy: string;
  favorite: boolean;
}

function BrowseGrid() {
  const toast = useToast();
  const [options, setOptions] = useState<BrowseOptions | null>(null);
  const [filters, setFilters] = useState<Filters>({
    q: "",
    modType: null,
    orderBy: "",
    favorite: false,
  });
  const [debouncedQ, setDebouncedQ] = useState("");

  const [results, setResults] = useState<ModListing[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<BrowseError | null>(null);
  const [selected, setSelected] = useState<ModListing | null>(null);
  const [installed, setInstalled] = useState<Map<string, InstalledFyiMod>>(
    new Map(),
  );
  const [installing, setInstalling] = useState<string | null>(null);

  // Guards against an older, slower request overwriting a newer one's results
  // when the user types quickly.
  const requestSeq = useRef(0);

  useEffect(() => {
    const timer = setTimeout(
      () => setDebouncedQ(filters.q.trim()),
      SEARCH_DEBOUNCE_MS,
    );
    return () => clearTimeout(timer);
  }, [filters.q]);

  useEffect(() => {
    let cancelled = false;
    void browseModOptions()
      .then((opts) => {
        if (cancelled) return;
        setOptions(opts);
        setFilters((prev) =>
          prev.orderBy ? prev : { ...prev, orderBy: opts.default_order_by },
        );
      })
      .catch(() => {
        // A missing filter bar shouldn't stop someone browsing; the list
        // endpoint has its own defaults.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const refreshInstalled = useCallback(() => {
    void installedFyiMods()
      .then((mods) => setInstalled(new Map(mods.map((m) => [m.slug, m]))))
      .catch(() => {
        // Badges are decoration. Losing them shouldn't break browsing.
      });
  }, []);

  useEffect(refreshInstalled, [refreshInstalled]);

  const load = useCallback(
    async (offset: number) => {
      const seq = ++requestSeq.current;
      if (offset === 0) setLoading(true);
      else setLoadingMore(true);
      try {
        const page = await browseMods({
          q: debouncedQ || undefined,
          modType: filters.modType ?? undefined,
          orderBy: filters.orderBy || undefined,
          favorite: filters.favorite || undefined,
          limit: PAGE_SIZE,
          offset,
        });
        if (seq !== requestSeq.current) return;
        setTotal(page.count);
        setResults((prev) =>
          offset === 0 ? page.results : [...prev, ...page.results],
        );
        setError(null);
      } catch (err) {
        if (seq !== requestSeq.current) return;
        setError(asBrowseError(err));
      } finally {
        if (seq === requestSeq.current) {
          setLoading(false);
          setLoadingMore(false);
        }
      }
    },
    [debouncedQ, filters.modType, filters.orderBy, filters.favorite],
  );

  useEffect(() => {
    void load(0);
  }, [load]);

  const install = async (mod: ModListing) => {
    const existing = installed.get(mod.slug);
    if (existing && !existing.hasUpdate) {
      const yes = await ask(
        `${mod.name} is already installed. Reinstall it at the latest version?`,
        { title: "Already installed", kind: "warning" },
      );
      if (!yes) return;
    }
    setInstalling(mod.slug);
    try {
      await installFromFyi(mod.slug, existing !== undefined);
      toast.success(
        existing ? `Updated ${mod.name}.` : `Installed ${mod.name}.`,
      );
      refreshInstalled();
    } catch (err) {
      if (isAuthFailure(err)) {
        // Promote it out of a toast: this one has a fix, and a toast takes the
        // fix away with it after a few seconds.
        setError({ kind: "unauthorized", message: extractMessage(err) });
      } else {
        toast.error(`Install failed: ${extractMessage(err)}`);
      }
    } finally {
      setInstalling(null);
    }
  };

  const hasMore = results.length < total;
  const summary = useMemo(() => {
    if (loading) return "Searching…";
    if (total === 0) return "No mods match";
    return `${results.length} of ${total} mods`;
  }, [loading, results.length, total]);

  return (
    <div className="browse-page">
      <header className="browse-header">
        <label className="browse-search">
          <Search size={14} aria-hidden="true" />
          <input
            type="search"
            value={filters.q}
            placeholder="Search mods"
            spellCheck={false}
            onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))}
          />
        </label>

        {options && (
          <>
            <select
              className="browse-select"
              aria-label="Mod type"
              value={filters.modType ?? ""}
              onChange={(e) =>
                setFilters((f) => ({
                  ...f,
                  modType: e.target.value ? Number(e.target.value) : null,
                }))
              }
            >
              <option value="">All types</option>
              {options.mod_types.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>

            <select
              className="browse-select"
              aria-label="Sort by"
              value={filters.orderBy}
              onChange={(e) =>
                setFilters((f) => ({ ...f, orderBy: e.target.value }))
              }
            >
              {options.order_by.map((choice) => (
                <option key={choice.value} value={choice.value}>
                  {choice.label}
                </option>
              ))}
            </select>

            <label className="browse-toggle">
              <input
                type="checkbox"
                checked={filters.favorite}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, favorite: e.target.checked }))
                }
              />
              Favorites
            </label>
          </>
        )}

        <span className="browse-summary">{summary}</span>
      </header>

      {error &&
        (error.kind === "unauthorized" || error.kind === "needsAccount" ? (
          <ReconnectPrompt
            message={error.message}
            onRetry={() => void load(0)}
          />
        ) : (
          <div className="browse-empty browse-error">
            <p>Couldn&rsquo;t load mods:</p>
            <pre>{error.message}</pre>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => void load(0)}
            >
              Try again
            </button>
          </div>
        ))}

      {!error && (
        <div className="browse-body">
          <div className="browse-results">
            {!loading && results.length === 0 && (
              <div className="browse-empty">
                <p>Nothing matched that.</p>
                <p className="browse-empty-note">Try a shorter search.</p>
              </div>
            )}

            {/* Only when there is nothing to show. A filter change keeps the
                previous results on screen while the next page loads, and
                replacing them with placeholders would throw away something
                readable in favour of something that is not. */}
            {loading && results.length === 0 ? (
              <div className="browse-grid">
                {Array.from({ length: SKELETON_COUNT }, (_, i) => (
                  <ModCardSkeleton key={i} />
                ))}
              </div>
            ) : (
              <div
                className={`browse-grid${loading ? " is-refreshing" : ""}`}
                aria-busy={loading || undefined}
              >
                {results.map((mod) => (
                  <ModCard
                    key={mod.id}
                    mod={mod}
                    installed={installed.get(mod.slug)}
                    selected={selected?.id === mod.id}
                    installing={installing === mod.slug}
                    onSelect={() => setSelected(mod)}
                    onInstall={() => void install(mod)}
                  />
                ))}
              </div>
            )}

            {hasMore && (
              <div className="browse-more">
                <button
                  type="button"
                  className="btn btn-ghost"
                  disabled={loadingMore}
                  onClick={() => void load(results.length)}
                >
                  {loadingMore ? "Loading…" : "Load more"}
                </button>
              </div>
            )}
          </div>

          {selected && (
            <ModDetailPane
              key={selected.slug}
              listing={selected}
              installed={installed.get(selected.slug)}
              installing={installing === selected.slug}
              hideRatings={options?.hide_ratings ?? false}
              onInstall={() => void install(selected)}
              onClose={() => setSelected(null)}
            />
          )}
        </div>
      )}
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

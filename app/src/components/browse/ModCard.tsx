import { useState } from "react";
import { ArrowUpCircle, Check, Download, Star } from "lucide-react";
import type { InstalledFyiMod, ModListing } from "../../lib/commands";
import "./ModCard.css";

interface Props {
  mod: ModListing;
  installed: InstalledFyiMod | undefined;
  selected: boolean;
  installing: boolean;
  onSelect: () => void;
  onInstall: () => void;
}

export function ModCard({
  mod,
  installed,
  selected,
  installing,
  onSelect,
  onInstall,
}: Props) {
  const hasUpdate = installed?.hasUpdate ?? false;
  const [broken, setBroken] = useState(false);
  const [loaded, setLoaded] = useState(false);

  return (
    /*
     * The card is a plain element, not a button, because it contains one.
     *
     * The name is the real control: it takes the tab stop and answers the
     * keyboard. The click handler out here is a mouse affordance layered on
     * top, so the whole card is a target without inventing a second focusable
     * thing that does the same job. Install stops propagation so pressing it
     * does not also swing the detail pane open.
     */
    <div
      className={`mod-card${selected ? " selected" : ""}`}
      onClick={onSelect}
      aria-current={selected || undefined}
    >
      <div className="mod-card-head">
        <span className="mod-card-logo">
          {broken ? (
            /* spelunkicons is a separate service behind its own nginx
               upstream, so it can be down while the API is fine. An initial
               beats a broken-image glyph in a grid of thirty. */
            <span className="mod-card-logo-fallback" aria-hidden="true">
              {mod.name.slice(0, 1).toUpperCase()}
            </span>
          ) : (
            <img
              /* A disk-cached image can finish decoding before React attaches
                 the load handler, in which case onLoad never fires at all.
                 `complete` is the only way to notice that, and without this
                 check a fade-in-on-load leaves those images invisible for
                 good -- which is most of them, on a second visit. */
              ref={(el) => {
                if (el?.complete) setLoaded(true);
              }}
              className={loaded ? "is-loaded" : undefined}
              src={mod.logo_url}
              alt=""
              loading="lazy"
              decoding="async"
              onLoad={() => setLoaded(true)}
              onError={() => setBroken(true)}
            />
          )}
        </span>

        <span className="mod-card-heading">
          <span className="mod-card-title">
            <button
              type="button"
              className="mod-card-name"
              onClick={onSelect}
              aria-pressed={selected}
            >
              {mod.name}
            </button>
            {installed && (
              <span
                className={`mod-card-badge${hasUpdate ? " update" : " installed"}`}
              >
                {hasUpdate ? (
                  <ArrowUpCircle size={11} aria-hidden="true" />
                ) : (
                  <Check size={11} aria-hidden="true" />
                )}
                {hasUpdate ? "Update" : "Installed"}
              </span>
            )}
          </span>
          <span className="mod-card-by">by {mod.submitter.username}</span>
        </span>
      </div>

      {/* Full width rather than in the logo's column: the logo is only as tall
          as the two lines beside it, and indenting everything below it left a
          dead strip down the side of every card. */}
      <p className="mod-card-desc">{mod.description}</p>

      <div className="mod-card-foot">
        <span className="mod-card-meta">
          {mod.mod_type_display && (
            <span className="mod-card-type">{mod.mod_type_display}</span>
          )}
          <span className="mod-card-stat">
            <Download size={11} aria-hidden="true" />
            {formatCount(mod.downloads)}
          </span>
          {mod.rating_count > 0 && (
            <span className="mod-card-stat">
              <Star size={11} aria-hidden="true" />
              {mod.rating_avg.toFixed(1)}
            </span>
          )}
        </span>

        <button
          type="button"
          className={`btn ${hasUpdate || !installed ? "btn-primary" : "btn-ghost"} mod-card-install`}
          disabled={installing}
          onClick={(event) => {
            event.stopPropagation();
            onInstall();
          }}
        >
          {installing
            ? "Installing…"
            : hasUpdate
              ? "Update"
              : installed
                ? "Reinstall"
                : "Install"}
        </button>
      </div>
    </div>
  );
}

/**
 * A card-shaped placeholder, in this file on purpose.
 *
 * Its whole job is to occupy the same space as the real thing, so it lives next
 * to the layout it mimics. Kept apart, the two drift and the grid jumps when
 * the results land, which is the problem a skeleton exists to avoid.
 */
export function ModCardSkeleton() {
  return (
    <div className="mod-card mod-card-skeleton" aria-hidden="true">
      <div className="mod-card-head">
        <span className="mod-card-logo skeleton-block" />
        <span className="mod-card-heading">
          <span className="skeleton-block skeleton-line name" />
          <span className="skeleton-block skeleton-line by" />
        </span>
      </div>
      <p className="mod-card-desc">
        <span className="skeleton-block skeleton-line" />
        <span className="skeleton-block skeleton-line short" />
      </p>
      <div className="mod-card-foot">
        <span className="skeleton-block skeleton-line meta" />
        <span className="skeleton-block skeleton-button" />
      </div>
    </div>
  );
}

/** 1200 -> "1.2k". Exact counts past a thousand are noise on a card. */
export function formatCount(value: number): string {
  if (value < 1000) return String(value);
  if (value < 1_000_000) return `${(value / 1000).toFixed(1)}k`;
  return `${(value / 1_000_000).toFixed(1)}M`;
}

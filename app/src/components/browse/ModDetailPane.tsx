import { useEffect, useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { ArrowUpRight, Download, Star, X } from "lucide-react";
import { formatCount } from "./ModCard";
import { ShotLightbox } from "./ShotLightbox";
import type { InstalledFyiMod, ModListing } from "../../lib/commands";
import "./ModDetailPane.css";

interface Props {
  listing: ModListing;
  installed: InstalledFyiMod | undefined;
  installing: boolean;
  hideRatings: boolean;
  onInstall: () => void;
  onClose: () => void;
}

/** Everything about a mod except the part written in markdown.
 *
 *  The write-up and the comment thread deliberately live on the website. What
 *  is shown here is plain text the site stores unformatted, numbers, dates, and
 *  screenshots hosted on our own media domain, so nothing a stranger authored
 *  is ever interpreted as markup inside the app.
 *
 *  Every field comes from the listing the grid already holds, screenshots
 *  included, which is why the browse command asks for
 *  `?include=preview_images`. Selecting a mod therefore costs no request, and
 *  the pane has no loading state to render.
 */
export function ModDetailPane({
  listing,
  installed,
  installing,
  hideRatings,
  onInstall,
  onClose,
}: Props) {
  const [shot, setShot] = useState(0);
  const [zoomed, setZoomed] = useState(false);

  // A different mod means a different gallery. Without this, selecting one
  // while zoomed into another's third screenshot carries the index across.
  useEffect(() => {
    setShot(0);
    setZoomed(false);
  }, [listing.slug]);

  const shots = listing.preview_images;
  const hasUpdate = installed?.hasUpdate ?? false;
  const current = Math.min(shot, Math.max(shots.length - 1, 0));

  return (
    <aside className="mod-detail">
      {/* Only this scrolls; the actions below are pinned. A mod with several
          screenshots is taller than the pane, and Install has to stay reachable
          at the point someone has finished deciding they want it. */}
      <div className="mod-detail-scroll">
        <div className="mod-detail-head">
          <h2 className="mod-detail-name">{listing.name}</h2>
          <button
            type="button"
            className="icon-button"
            aria-label="Close details"
            onClick={onClose}
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>

        <p className="mod-detail-by">
          by {listing.submitter.username}
          {listing.collaborators.length > 0 &&
            `, with ${listing.collaborators.map((c) => c.username).join(", ")}`}
        </p>

        {shots.length > 0 && (
          <div className="mod-detail-shots">
            {/* The pane is 22rem wide, so everything in it is a thumbnail
                whatever it was uploaded as. Clicking opens the real thing. */}
            <button
              type="button"
              className="mod-detail-shot-button"
              title="View screenshots full size"
              onClick={() => setZoomed(true)}
            >
              <Shot
                // Keyed by image, so switching thumbnails remounts and the new
                // one fades in from the reserved box rather than the previous
                // screenshot blanking out mid-swap.
                key={shots[current].id}
                url={shots[current].image_url}
                alt={`Screenshot ${current + 1} of ${listing.name}`}
              />
            </button>
            {shots.length > 1 && (
              <div className="mod-detail-thumbs">
                {shots.map((image, index) => (
                  <button
                    key={image.id}
                    type="button"
                    className={`mod-detail-thumb${index === current ? " active" : ""}`}
                    aria-label={`Screenshot ${index + 1}`}
                    onClick={() => setShot(index)}
                  >
                    <img src={image.image_url} alt="" loading="lazy" />
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <p className="mod-detail-desc">{listing.description}</p>

        <dl className="mod-detail-facts">
          {listing.mod_type_display && (
            <>
              <dt>Type</dt>
              <dd>{listing.mod_type_display}</dd>
            </>
          )}
          <dt>Downloads</dt>
          <dd>
            <Download size={12} aria-hidden="true" />{" "}
            {formatCount(listing.downloads)}
          </dd>
          {!hideRatings && listing.rating_count > 0 && (
            <>
              <dt>Rating</dt>
              <dd>
                <Star size={12} aria-hidden="true" />{" "}
                {listing.rating_avg.toFixed(1)} from {listing.rating_count}
              </dd>
            </>
          )}
          <dt>Updated</dt>
          <dd>{formatDate(listing.updated_at)}</dd>
          {listing.latest_file && (
            <>
              <dt>Latest file</dt>
              <dd className="mod-detail-file">
                {listing.latest_file.filename}
                <span>{formatDate(listing.latest_file.created_at)}</span>
              </dd>
            </>
          )}
        </dl>
      </div>

      {zoomed && shots.length > 0 && (
        <ShotLightbox
          shots={shots}
          index={current}
          title={listing.name}
          onIndex={setShot}
          onClose={() => setZoomed(false)}
        />
      )}

      <div className="mod-detail-actions">
        <button
          type="button"
          className={`btn ${hasUpdate || !installed ? "btn-primary" : "btn-ghost"}`}
          disabled={installing}
          onClick={onInstall}
        >
          {installing
            ? "Installing…"
            : hasUpdate
              ? "Update"
              : installed
                ? "Reinstall"
                : "Install"}
        </button>
        {/* Short label because the two buttons split the footer evenly. The
            arrow carries "this leaves the app"; the full wording is in the
            title for anyone who hovers. */}
        <button
          type="button"
          className="btn btn-ghost"
          title="Open this mod on spelunky.fyi"
          onClick={() => void openUrl(listing.web_url)}
        >
          Full page
          <ArrowUpRight size={14} aria-hidden="true" />
        </button>
      </div>
    </aside>
  );
}

/**
 * One screenshot in a box that exists before the image does.
 *
 * Without a reserved height the element is 0px tall until a half-megabyte JPEG
 * finishes decoding, at which point it springs to full size and shoves the
 * description, the facts and the footer down the pane. That shove is what reads
 * as the image popping into reality; the fade is only there to take the edge
 * off the last few milliseconds.
 *
 * 16:9 is an assumption, not a measurement. Preview uploads have no enforced
 * ratio, and reading the real one means either downloading the file server-side
 * or storing dimensions on the model, so anything else is letterboxed inside a
 * stable box instead of resizing it.
 */
function Shot({ url, alt }: { url: string; alt: string }) {
  const [loaded, setLoaded] = useState(false);

  return (
    <img
      // A cached image can be complete before React attaches onLoad, so the
      // event never fires and the fade would strand it at zero opacity.
      ref={(el) => {
        if (el?.complete) setLoaded(true);
      }}
      className={`mod-detail-shot${loaded ? " is-loaded" : ""}`}
      src={url}
      alt={alt}
      decoding="async"
      onLoad={() => setLoaded(true)}
    />
  );
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "unknown";
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

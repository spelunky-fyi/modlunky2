import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import type { PreviewImage } from "../../lib/commands";
import "./ShotLightbox.css";

interface Props {
  shots: PreviewImage[];
  index: number;
  /** Mod name, for the dialog label and the alt text. */
  title: string;
  onIndex: (index: number) => void;
  onClose: () => void;
}

/**
 * Screenshots at a size worth looking at.
 *
 * The detail pane is 22rem wide, so a preview in it is a thumbnail whatever it
 * was uploaded as. This is the escape hatch: the same images, filling whatever
 * the window has.
 *
 * Not built on `Modal` because that one is form-shaped, with a title bar and a
 * padded body sized to its content. Here the image is the content and should
 * meet the edges, so sharing the component would mean overriding most of it.
 */
export function ShotLightbox({ shots, index, title, onIndex, onClose }: Props) {
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const restoreRef = useRef<Element | null>(null);

  const count = shots.length;
  const current = shots[Math.min(index, count - 1)];

  useEffect(() => {
    // Remember where focus was so closing returns it, rather than dumping the
    // user back at the top of the document.
    restoreRef.current = document.activeElement;
    closeRef.current?.focus();
    return () => {
      const restore = restoreRef.current;
      if (restore instanceof HTMLElement) restore.focus();
    };
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      } else if (event.key === "ArrowLeft" && count > 1) {
        event.preventDefault();
        onIndex((index - 1 + count) % count);
      } else if (event.key === "ArrowRight" && count > 1) {
        event.preventDefault();
        onIndex((index + 1) % count);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [index, count, onIndex, onClose]);

  if (!current) return null;

  return createPortal(
    <div
      className="shot-lightbox"
      role="dialog"
      aria-modal="true"
      aria-label={`Screenshots of ${title}`}
      // mousedown rather than click, so a drag that starts on the image and
      // ends on the backdrop does not count as clicking away.
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <button
        ref={closeRef}
        type="button"
        className="shot-lightbox-close"
        aria-label="Close screenshots"
        onClick={onClose}
      >
        <X size={20} aria-hidden="true" />
      </button>

      {count > 1 && (
        <button
          type="button"
          className="shot-lightbox-nav prev"
          aria-label="Previous screenshot"
          onClick={() => onIndex((index - 1 + count) % count)}
        >
          <ChevronLeft size={26} aria-hidden="true" />
        </button>
      )}

      <LightboxImage
        key={current.id}
        url={current.image_url}
        alt={`Screenshot ${index + 1} of ${title}`}
      />

      {count > 1 && (
        <button
          type="button"
          className="shot-lightbox-nav next"
          aria-label="Next screenshot"
          onClick={() => onIndex((index + 1) % count)}
        >
          <ChevronRight size={26} aria-hidden="true" />
        </button>
      )}

      {count > 1 && (
        <p className="shot-lightbox-count" aria-live="polite">
          {index + 1} of {count}
        </p>
      )}
    </div>,
    document.body,
  );
}

/** Same fade-and-complete handling as the pane: a cached image can be done
 *  before React attaches onLoad, and fading in on that event alone would leave
 *  it invisible. */
function LightboxImage({ url, alt }: { url: string; alt: string }) {
  const [loaded, setLoaded] = useState(false);

  return (
    <img
      ref={(el) => {
        if (el?.complete) setLoaded(true);
      }}
      className={`shot-lightbox-img${loaded ? " is-loaded" : ""}`}
      src={url}
      alt={alt}
      decoding="async"
      onLoad={() => setLoaded(true)}
    />
  );
}

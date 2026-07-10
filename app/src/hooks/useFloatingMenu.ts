import { useEffect, useRef, useState, type RefObject } from "react";

interface FloatingMenu {
  /** Attach to the menu's root element. Used for viewport clamping and to tell
   *  clicks inside the menu from clicks outside it. */
  menuRef: RefObject<HTMLDivElement | null>;
  /** Clamped screen position. Spread into the menu's `style`. */
  pos: { left: number; top: number };
}

/**
 * Positions a floating context menu at `(x, y)`, clamped to stay within the
 * viewport, and dismisses it on outside click, right-click, Escape, or scroll.
 *
 * Dismissal uses capture-phase document listeners rather than a full-screen
 * backdrop. A backdrop swallows a second right-click (popping the browser's
 * native menu) and blocks the element underneath from reopening its own menu.
 * With no overlay, a right-click outside closes this menu and the element under
 * the cursor (e.g. another row) reopens its menu at the new spot -- the browser
 * menu never shows while ours is open.
 *
 * Pass the same `onClose` identity is not required; it's read through a ref so
 * the listeners subscribe once for the menu's lifetime.
 */
export function useFloatingMenu(
  x: number,
  y: number,
  onClose: () => void,
): FloatingMenu {
  const menuRef = useRef<HTMLDivElement | null>(null);
  const [pos, setPos] = useState({ left: x, top: y });

  // Clamp after mount (and on any move) since we need the menu's real size.
  useEffect(() => {
    const el = menuRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const pad = 4;
    setPos({
      left: Math.max(pad, Math.min(x, window.innerWidth - rect.width - pad)),
      top: Math.max(pad, Math.min(y, window.innerHeight - rect.height - pad)),
    });
  }, [x, y]);

  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useEffect(() => {
    const insideMenu = (target: EventTarget | null) =>
      target instanceof Node && !!menuRef.current?.contains(target);
    const onMouseDown = (e: MouseEvent) => {
      if (e.button === 2) return; // right-down handled by contextmenu below
      if (!insideMenu(e.target)) onCloseRef.current();
    };
    const onContext = (e: MouseEvent) => {
      // Never let the browser menu show while ours is open.
      e.preventDefault();
      if (!insideMenu(e.target)) onCloseRef.current();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCloseRef.current();
    };
    const onScroll = () => onCloseRef.current();
    document.addEventListener("mousedown", onMouseDown, true);
    document.addEventListener("contextmenu", onContext, true);
    document.addEventListener("keydown", onKey, true);
    window.addEventListener("scroll", onScroll, true);
    return () => {
      document.removeEventListener("mousedown", onMouseDown, true);
      document.removeEventListener("contextmenu", onContext, true);
      document.removeEventListener("keydown", onKey, true);
      window.removeEventListener("scroll", onScroll, true);
    };
  }, []);

  return { menuRef, pos };
}

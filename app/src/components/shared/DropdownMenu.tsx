import { cloneElement, useEffect, useRef, useState, type ReactElement } from "react";
import "./DropdownMenu.css";

export interface DropdownItem {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  icon?: ReactElement;
}

export interface DropdownSeparator {
  separator: true;
}

export type DropdownEntry = DropdownItem | DropdownSeparator;

interface DropdownMenuProps {
  trigger: ReactElement<{ onClick?: (e: React.MouseEvent) => void }>;
  items: DropdownEntry[];
  align?: "left" | "right";
  ariaLabel?: string;
}

export function DropdownMenu({
  trigger,
  items,
  align = "right",
  ariaLabel = "Menu",
}: DropdownMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (!rootRef.current) return;
      if (!rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    window.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      window.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  const wrappedTrigger = cloneElement(trigger, {
    onClick: (e: React.MouseEvent) => {
      trigger.props.onClick?.(e);
      setOpen((v) => !v);
    },
  });

  return (
    <div className="dropdown" ref={rootRef}>
      {wrappedTrigger}
      {open && (
        <div
          className={`dropdown-menu dropdown-align-${align}`}
          role="menu"
          aria-label={ariaLabel}
        >
          {items.map((entry, idx) => {
            if ("separator" in entry) {
              return <div key={`sep-${idx}`} className="dropdown-separator" />;
            }
            return (
              <button
                key={`${entry.label}-${idx}`}
                type="button"
                role="menuitem"
                className="dropdown-item"
                disabled={entry.disabled}
                onClick={() => {
                  setOpen(false);
                  entry.onClick();
                }}
              >
                {entry.icon && <span className="dropdown-item-icon">{entry.icon}</span>}
                <span className="dropdown-item-label">{entry.label}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

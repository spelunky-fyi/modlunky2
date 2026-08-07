// A labelled on/off switch.
//
// The app already had two ways to render a boolean: a bare accent-coloured
// checkbox (the options modals) and, briefly, pill-shaped chips invented for
// the launch dock. Neither works for a control that is the most important
// choice on the screen. A checkbox is too quiet to carry it, and the pills
// matched nothing else in the UI.
//
// This lives in shared/ rather than beside the dock so the next boolean that
// needs weight has something to reach for instead of inventing a third style.
// It wraps a real checkbox, so keyboard, focus and screen readers work without
// any aria-pressed juggling.

import "./Switch.css";

interface SwitchProps {
  label: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
  /** Tooltip, for when the label alone doesn't explain the consequence. */
  title?: string;
}

export function Switch({
  label,
  checked,
  onChange,
  disabled,
  title,
}: SwitchProps) {
  return (
    <label
      className={`switch${checked ? " on" : ""}${disabled ? " disabled" : ""}`}
      title={title}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="switch-track" aria-hidden="true">
        <span className="switch-knob" />
      </span>
      <span className="switch-label">{label}</span>
    </label>
  );
}

// A modal that asks for one line of text.
//
// It owns the draft rather than taking a value and an onChange, and that
// is the whole point of it existing. When the text lived in the page's
// state, every keystroke re-rendered the page - including both save lists
// and their date grouping. With a few hundred snapshots archived, typing
// a name visibly lagged behind the keyboard.
//
// Keeping the draft in here means a keystroke re-renders a text field and
// nothing else. The page only hears about it on submit.

import { useEffect, useRef, useState } from "react";
import { Modal } from "../shared/Modal";

interface TextPromptModalProps {
  open: boolean;
  title: string;
  label: string;
  /** What the field starts with each time the modal opens. */
  initialValue: string;
  placeholder?: string;
  /** Text under the field. */
  hint?: string;
  confirmLabel: string;
  busy?: boolean;
  onCancel: () => void;
  onConfirm: (value: string) => void;
}

export function TextPromptModal({
  open,
  title,
  label,
  initialValue,
  placeholder,
  hint,
  confirmLabel,
  busy,
  onCancel,
  onConfirm,
}: TextPromptModalProps) {
  const [value, setValue] = useState(initialValue);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Reset on open rather than on every render, so the field is not
  // fighting the user's typing.
  useEffect(() => {
    if (open) {
      setValue(initialValue);
      // Autofocus after the reset, or the caret lands before the text.
      requestAnimationFrame(() => inputRef.current?.select());
    }
  }, [open, initialValue]);

  if (!open) return null;

  const submit = () => {
    if (!busy) onConfirm(value);
  };

  return (
    <Modal
      open
      onClose={onCancel}
      title={title}
      footer={
        <>
          <button type="button" className="saves-btn" onClick={onCancel}>
            Cancel
          </button>
          <button
            type="button"
            className="saves-btn saves-btn-primary"
            onClick={submit}
            disabled={busy}
          >
            {confirmLabel}
          </button>
        </>
      }
    >
      <label className="saves-field">
        <span>{label}</span>
        <input
          ref={inputRef}
          type="text"
          value={value}
          autoFocus
          maxLength={200}
          placeholder={placeholder}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submit();
          }}
        />
      </label>
      {hint && <p className="saves-hint">{hint}</p>}
    </Modal>
  );
}

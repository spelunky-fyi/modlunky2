// Dialog for defining a new user-authored save format. Validation:
// exactly one {y} + one {x}, no stray braces, no collision with a
// built-in name or pattern.

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type SyntheticEvent,
} from "react";
import type { CustomLevelSaveFormat } from "../../lib/commands";
import { Modal } from "../shared/Modal";
import "./NewSaveFormatModal.css";

interface Props {
  /** Prefilled template pattern for the recovery flow, derived from an
   *  actual template name in the file. Null for the plain "add format"
   *  flow. */
  suggestedFormat?: string | null;
  /** Names already taken by built-ins + existing user formats, so the
   *  Name field can flag collisions inline. Compared case-insensitively. */
  existingNames: string[];
  onClose: () => void;
  onSubmit: (format: CustomLevelSaveFormat) => void | Promise<void>;
}

const RESERVED_NAMES = ["LevelSequence", "Vanilla setroom [warning]"];
const RESERVED_PATTERNS = ["setroom{y}_{x}", "setroom{y}-{x}"];
// Invert the standard y-then-x order in ways that other tools mishandle,
// so they're rejected even though they'd validate on placeholder count.
const BLOCKED_PATTERNS = ["setroom{x}-{y}"];

const DEFAULT_TEMPLATE = "setroom{y}_{x}";

export function NewSaveFormatModal({
  suggestedFormat,
  existingNames,
  onClose,
  onSubmit,
}: Props) {
  const [name, setName] = useState("");
  const [template, setTemplate] = useState(
    suggestedFormat && suggestedFormat.length > 0
      ? suggestedFormat
      : DEFAULT_TEMPLATE,
  );
  const [includeVanilla, setIncludeVanilla] = useState(true);
  const nameRef = useRef<HTMLInputElement | null>(null);
  useEffect(() => {
    nameRef.current?.focus();
  }, []);

  const takenNames = useMemo(
    () => new Set(existingNames.map((n) => n.toLowerCase())),
    [existingNames],
  );

  const trimmedName = name.trim();
  const trimmedTemplate = template.trim();

  const validationError = useMemo<string | null>(() => {
    if (!name) return null;
    if (!trimmedName) return "Enter a name for this format.";
    if (
      RESERVED_NAMES.some(
        (r) => r.toLowerCase() === trimmedName.toLowerCase(),
      )
    ) {
      return "Name collides with a built-in format.";
    }
    if (takenNames.has(trimmedName.toLowerCase())) {
      return "A format with this name already exists.";
    }
    if (!trimmedTemplate) return "Enter a template pattern.";
    const yCount = (trimmedTemplate.match(/\{y\}/g) ?? []).length;
    const xCount = (trimmedTemplate.match(/\{x\}/g) ?? []).length;
    if (yCount !== 1 || xCount !== 1) {
      return "Template must contain exactly one {y} and one {x}.";
    }
    const withoutPlaceholders = trimmedTemplate
      .replace("{y}", "")
      .replace("{x}", "");
    if (withoutPlaceholders.includes("{") || withoutPlaceholders.includes("}")) {
      return "Template has stray {} braces.";
    }
    if (RESERVED_PATTERNS.includes(trimmedTemplate)) {
      return "Pattern matches a built-in format; use the built-in instead.";
    }
    if (BLOCKED_PATTERNS.includes(trimmedTemplate)) {
      return "This pattern isn't supported.";
    }
    return null;
  }, [name, trimmedName, trimmedTemplate, takenNames]);

  const invalid = !trimmedName || !trimmedTemplate || validationError !== null;

  const handleSubmit = (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (invalid) return;
    void onSubmit({
      name: trimmedName,
      room_template_format: trimmedTemplate,
      include_vanilla_setrooms: includeVanilla,
    });
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="New save format"
      size="sm"
      footer={
        <div className="save-format-form-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            form="save-format-form"
            className="btn btn-primary"
            disabled={invalid}
          >
            Create
          </button>
        </div>
      }
    >
      <form
        id="save-format-form"
        className="save-format-form"
        onSubmit={handleSubmit}
      >
        <p className="save-format-form-hint">
          Editor-wide, adds to this and every pack.
        </p>
        <label className="save-format-form-label" htmlFor="save-format-name">
          Name
        </label>
        <input
          id="save-format-name"
          ref={nameRef}
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. My challenge rooms"
          spellCheck={false}
        />
        <label
          className="save-format-form-label"
          htmlFor="save-format-template"
        >
          Room template pattern
        </label>
        <input
          id="save-format-template"
          type="text"
          value={template}
          onChange={(e) => setTemplate(e.target.value)}
          spellCheck={false}
        />
        <p className="save-format-form-hint">
          Use <code>{"{y}"}</code> and <code>{"{x}"}</code> as placeholders
          for the room coordinates.
        </p>
        <label className="save-format-form-checkbox">
          <input
            type="checkbox"
            checked={includeVanilla}
            onChange={(e) => setIncludeVanilla(e.target.checked)}
          />
          <span>
            Include vanilla setrooms
            <span className="save-format-form-hint-inline">
              Also emit templates for boss themes (Ice Caves, Olmec, Tiamat,
              Duat, Eggplant, Hundun, Abzu) so those themes render your rooms
              instead of defaults. Recommended.
            </span>
          </span>
        </label>
        {validationError && (
          <div className="save-format-form-error">{validationError}</div>
        )}
      </form>
    </Modal>
  );
}

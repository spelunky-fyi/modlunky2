import { useState, type SyntheticEvent } from "react";
import { Modal } from "../shared/Modal";
import type { EditorMode } from "../../lib/commands";
import "./CreatePackModal.css";

interface Props {
  onSubmit: (name: string, mode: EditorMode) => void;
  onClose: () => void;
}

export function CreatePackModal({ onSubmit, onClose }: Props) {
  const [name, setName] = useState("");
  const [mode, setMode] = useState<EditorMode>("custom");

  const trimmed = name.trim();
  const canSubmit = trimmed.length > 0;

  const handleSubmit = (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!canSubmit) return;
    onSubmit(trimmed, mode);
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Create New Pack"
      size="md"
      footer={
        <div className="create-pack-footer">
          <button
            type="button"
            className="btn btn-ghost"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="submit"
            form="create-pack-form"
            className="btn btn-primary"
            disabled={!canSubmit}
          >
            Create and open
          </button>
        </div>
      }
    >
      <form
        id="create-pack-form"
        className="create-pack-form"
        onSubmit={handleSubmit}
      >
        <label className="create-pack-field">
          <span>Pack name</span>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="MyNewPack"
            autoFocus
          />
          <span className="create-pack-hint">
            Spaces become underscores. Lands under Mods/Packs/&lt;name&gt;/.
          </span>
        </label>
        <fieldset className="create-pack-mode">
          <legend>Open in</legend>
          <label>
            <input
              type="radio"
              name="mode"
              value="custom"
              checked={mode === "custom"}
              onChange={() => setMode("custom")}
            />
            <span>Custom Editor</span>
            <span className="create-pack-hint">
              For hand-authored levels backed by the LevelSequence Lua library.
            </span>
          </label>
          <label>
            <input
              type="radio"
              name="mode"
              value="vanilla"
              checked={mode === "vanilla"}
              onChange={() => setMode("vanilla")}
            />
            <span>Vanilla Editor</span>
            <span className="create-pack-hint">
              For overriding Spelunky's built-in .lvl files.
            </span>
          </label>
        </fieldset>
      </form>
    </Modal>
  );
}

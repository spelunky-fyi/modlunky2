// Explains every affordance in the palette panel: primary / secondary
// pick, reorder, delete, add, and the conflicts entry point.

import { Modal } from "../shared/Modal";
import "./PaletteHelpModal.css";

interface Props {
  onClose: () => void;
  /** "vanilla" surfaces the sister-file inheritance sections (adopt-tile
   *  hint + conflicts warning). "custom" hides them because custom
   *  levels don't inherit tilecodes from other files. */
  mode: "vanilla" | "custom";
}

export function PaletteHelpModal({ onClose, mode }: Props) {
  const isVanilla = mode === "vanilla";
  return (
    <Modal
      open
      onClose={onClose}
      title="Using the palette"
      size="sm"
      footer={
        <div className="palette-help-footer">
          <button type="button" className="btn btn-primary" onClick={onClose}>
            Got it
          </button>
        </div>
      }
    >
      <dl className="palette-help-list">
        <div className="palette-help-item">
          <dt>Left-click a tile</dt>
          <dd>
            Sets it as the <strong>primary</strong> tile. Left-click on
            the canvas paints with this one.
          </dd>
        </div>
        <div className="palette-help-item">
          <dt>Right-click a tile</dt>
          <dd>
            Sets it as the <strong>secondary</strong> tile. Right-click
            on the canvas paints with this one, so you can swap between
            two active tiles without leaving the mouse.
          </dd>
        </div>
        <div className="palette-help-item">
          <dt>Reorder / delete</dt>
          <dd>
            The lock icon at the top of the palette toggles reorder
            mode. When on, the whole row becomes a drag handle so you
            can pull tiles into a new order, and a trash icon appears
            for deleting entries. Deletion rewrites every cell that
            used the removed tile to <code>empty</code>.
          </dd>
        </div>
        <div className="palette-help-item">
          <dt>Add a new tile</dt>
          <dd>
            Use <em>+ Add tile</em> below the palette. The modal lets
            you type a tile name (freeform, custom Lua tiles work)
            {isVanilla
              ? " or adopt a tile from a sibling / parent file with one click"
              : ""}
            .
          </dd>
        </div>
        {isVanilla && (
          <div className="palette-help-item">
            <dt>Conflicts warning</dt>
            <dd>
              If a triangle icon appears in the top-right of the palette
              header, this file uses one or more tilecode characters that
              a sister-location file uses for a different tile. Click
              the icon to open the conflicts modal and reassign codes.
            </dd>
          </div>
        )}
      </dl>
    </Modal>
  );
}

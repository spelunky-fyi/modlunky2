// Lists every tilecode conflict between the current file and its sister
// locations. Per-row Resolve reassigns just that entry; Resolve all at
// the bottom rewrites every conflict in one pass.

import { Modal } from "../shared/Modal";
import "./ConflictsModal.css";

export interface TilecodeConflict {
  /** Tile name in the current file. */
  name: string;
  /** The shared code character. */
  code: string;
  /** Sister-location file name. */
  otherFile: string;
  /** Tile name in the sister file that also maps to `code`. */
  otherName: string;
}

interface Props {
  conflicts: TilecodeConflict[];
  onClose: () => void;
  /** Reassign the current file's code for just this entry. */
  onResolveOne: (conflict: TilecodeConflict) => void;
  /** Reassign codes for every conflicting entry in the current file. */
  onResolveAll: () => void;
}

export function ConflictsModal({
  conflicts,
  onClose,
  onResolveOne,
  onResolveAll,
}: Props) {
  return (
    <Modal
      open
      onClose={onClose}
      title="Tilecode conflicts"
      size="md"
      footer={
        <div className="conflicts-modal-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Close
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={onResolveAll}
            disabled={conflicts.length === 0}
          >
            Resolve all
          </button>
        </div>
      }
    >
      {conflicts.length === 0 ? (
        <p className="conflicts-modal-empty">
          No conflicts with sister files.
        </p>
      ) : (
        <>
          <p className="conflicts-modal-intro">
            Each row shows a tilecode used in this file that a sister file
            also uses for a different tile. Resolving reassigns the code
            in <em>this</em> file to something the sister does not use.
          </p>
          <ul className="conflicts-modal-list">
            {conflicts.map((c, i) => (
              <li
                key={`${c.name}-${c.otherFile}-${c.otherName}-${i}`}
                className="conflicts-modal-item"
              >
                <div className="conflicts-modal-row">
                  <div className="conflicts-modal-side">
                    <div className="conflicts-modal-side-label">
                      This file
                    </div>
                    <div className="conflicts-modal-side-body">
                      <code className="conflicts-modal-code">{c.code}</code>
                      <span className="conflicts-modal-arrow">→</span>
                      <span className="conflicts-modal-name">{c.name}</span>
                    </div>
                  </div>
                  <div className="conflicts-modal-vs">vs</div>
                  <div className="conflicts-modal-side">
                    <div className="conflicts-modal-side-label">
                      {c.otherFile}
                    </div>
                    <div className="conflicts-modal-side-body">
                      <code className="conflicts-modal-code">{c.code}</code>
                      <span className="conflicts-modal-arrow">→</span>
                      <span className="conflicts-modal-name">
                        {c.otherName}
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-ghost conflicts-modal-resolve"
                  onClick={() => onResolveOne(c)}
                >
                  Resolve
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </Modal>
  );
}

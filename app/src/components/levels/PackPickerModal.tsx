import { useEffect, useState } from "react";
import { Modal } from "../shared/Modal";
import { listLevelPacks, type EditorMode } from "../../lib/commands";
import "./PackPickerModal.css";

interface Props {
  mode: EditorMode;
  onPick: (pack: string) => void;
  onClose: () => void;
}

export function PackPickerModal({ mode, onPick, onClose }: Props) {
  const [packs, setPacks] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    let cancelled = false;
    listLevelPacks(mode)
      .then((p) => {
        if (!cancelled) setPacks(p);
      })
      .catch((err) => {
        if (!cancelled) setError(extractMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [mode]);

  const filtered = (packs ?? []).filter((p) =>
    p.toLowerCase().includes(filter.toLowerCase()),
  );

  return (
    <Modal
      open
      onClose={onClose}
      title={`Open ${mode} Editor`}
      size="md"
    >
      <div className="pack-picker">
        <input
          type="text"
          className="pack-picker-search"
          placeholder="Filter packs..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          autoFocus
        />
        {error && <div className="pack-picker-error">{error}</div>}
        {!error && packs === null && (
          <div className="pack-picker-status">Loading packs...</div>
        )}
        {!error && packs !== null && packs.length === 0 && (
          <div className="pack-picker-status">
            No packs found under Mods/Packs. Try "Create New Pack" from the
            splash.
          </div>
        )}
        {!error && filtered.length === 0 && (packs?.length ?? 0) > 0 && (
          <div className="pack-picker-status">
            No packs match "{filter}".
          </div>
        )}
        {filtered.length > 0 && (
          <ul className="pack-picker-list">
            {filtered.map((pack) => (
              <li key={pack}>
                <button
                  type="button"
                  className="pack-picker-item"
                  onClick={() => onPick(pack)}
                >
                  {pack}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Modal>
  );
}

function extractMessage(err: unknown): string {
  if (typeof err === "string") return err;
  if (err && typeof err === "object") {
    for (const v of Object.values(err)) {
      if (typeof v === "string") return v;
    }
    return JSON.stringify(err);
  }
  return String(err);
}

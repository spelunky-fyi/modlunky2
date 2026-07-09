// Keyboard shortcut cheatsheet. Both editors open this from the help
// button in the top bar. Groups shortcuts by task so users can scan for
// what they need instead of hunting through a wall of key combos.

import { Modal } from "../shared/Modal";
import "./KeyboardShortcutsModal.css";

interface Props {
  onClose: () => void;
  /** When true, includes editor-mode specifics that only apply to the
   *  Vanilla editor (e.g. the room/level view Tab shortcut). Custom
   *  passes false. */
  showVanillaOnly?: boolean;
}

interface Shortcut {
  keys: string[];
  desc: string;
}

interface Group {
  title: string;
  items: Shortcut[];
}

/** `+` between keys binds a chord, `/` between two options means "either." */
const GROUPS: Group[] = [
  {
    title: "Paint tools",
    items: [
      { keys: ["B"], desc: "Brush" },
      { keys: ["G"], desc: "Bucket fill" },
      { keys: ["U"], desc: "Rectangle" },
      { keys: ["E"], desc: "Eraser" },
      { keys: ["I"], desc: "Eyedropper" },
      { keys: ["M"], desc: "Marquee select" },
      { keys: ["Left click"], desc: "Paint with primary tile" },
      { keys: ["Right click"], desc: "Paint with secondary tile" },
    ],
  },
  {
    title: "View",
    items: [
      { keys: ["Ctrl", "Wheel"], desc: "Zoom at cursor" },
      { keys: ["Wheel"], desc: "Scroll vertically" },
      { keys: ["Shift", "Wheel"], desc: "Scroll horizontally" },
      { keys: ["Space", "Drag"], desc: "Free pan (both axes)" },
      { keys: ["Middle mouse", "Drag"], desc: "Free pan" },
    ],
  },
  {
    title: "History",
    items: [
      { keys: ["Ctrl", "Z"], desc: "Undo" },
      { keys: ["Ctrl", "Shift", "Z"], desc: "Redo" },
      { keys: ["Ctrl", "Y"], desc: "Redo (alternate)" },
    ],
  },
  {
    title: "Marquee selection",
    items: [
      { keys: ["Ctrl", "C"], desc: "Copy selection" },
      { keys: ["Ctrl", "X"], desc: "Cut selection" },
      { keys: ["Ctrl", "V"], desc: "Paste at hover cell" },
      { keys: ["Delete"], desc: "Erase selection contents" },
      { keys: ["Escape"], desc: "Clear selection" },
      { keys: ["Drag inside"], desc: "Move selection contents" },
    ],
  },
  {
    title: "File",
    items: [
      { keys: ["Ctrl", "S"], desc: "Save the current file" },
    ],
  },
];

const VANILLA_GROUP: Group = {
  title: "Vanilla view",
  items: [
    { keys: ["Tab"], desc: "Toggle Room / Level view" },
  ],
};

export function KeyboardShortcutsModal({
  onClose,
  showVanillaOnly = false,
}: Props) {
  const groups = showVanillaOnly ? [...GROUPS, VANILLA_GROUP] : GROUPS;
  return (
    <Modal open onClose={onClose} title="Keyboard shortcuts" size="md">
      <div className="kbd-modal">
        <p className="kbd-modal-hint">
          Shortcuts are disabled while a text field is focused, so typing
          letters still works.
        </p>
        <div className="kbd-modal-grid">
          {groups.map((g) => (
            <section key={g.title} className="kbd-modal-group">
              <h3 className="kbd-modal-group-title">{g.title}</h3>
              <ul className="kbd-modal-list">
                {g.items.map((s) => (
                  <li key={s.desc} className="kbd-modal-row">
                    <span className="kbd-modal-keys">
                      {s.keys.map((k, i) => (
                        <span key={i} className="kbd-modal-key-frag">
                          {i > 0 && (
                            <span className="kbd-modal-plus">+</span>
                          )}
                          <kbd className="kbd-modal-key">{k}</kbd>
                        </span>
                      ))}
                    </span>
                    <span className="kbd-modal-desc">{s.desc}</span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </div>
    </Modal>
  );
}

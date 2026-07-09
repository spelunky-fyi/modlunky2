import { useEffect, useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import {
  listValidLevelChances,
  listValidLevelSettings,
  listValidMonsterChances,
  type RulesEntry,
} from "../../lib/commands";
import "./RulesPanel.css";

type SectionKind = "levelSettings" | "levelChances" | "monsterChances";

const SECTION_TABS: {
  kind: SectionKind;
  label: string;
  hint: string;
  datalistId: string;
  namePlaceholder: string;
  valuePlaceholder: string;
}[] = [
  {
    kind: "levelSettings",
    label: "Level settings",
    hint: "One-off tunables for the whole level (chances, thresholds, size).",
    datalistId: "rules-valid-level-settings",
    namePlaceholder: "e.g. back_room_chance",
    valuePlaceholder: "e.g. 0",
  },
  {
    kind: "levelChances",
    label: "Level chances",
    hint: "Per-difficulty odds of traps, hazards, and world hooks spawning.",
    datalistId: "rules-valid-level-chances",
    namePlaceholder: "e.g. arrowtrap_chance",
    valuePlaceholder: "35 or 20, 25, 30, 40",
  },
  {
    kind: "monsterChances",
    label: "Monster chances",
    hint: "Spawn rates for individual enemies inside the level.",
    datalistId: "rules-valid-monster-chances",
    namePlaceholder: "e.g. frog",
    valuePlaceholder: "30 or 10, 20, 30, 40",
  },
];

interface Props {
  levelSettings: RulesEntry[];
  levelChances: RulesEntry[];
  monsterChances: RulesEntry[];
  onChange: (kind: SectionKind, next: RulesEntry[]) => void;
}

export function RulesPanel({
  levelSettings,
  levelChances,
  monsterChances,
  onChange,
}: Props) {
  const [active, setActive] = useState<SectionKind>("levelSettings");
  const [validSettings, setValidSettings] = useState<string[]>([]);
  const [validLevelChances, setValidLevelChances] = useState<string[]>([]);
  const [validMonsterChances, setValidMonsterChances] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      listValidLevelSettings(),
      listValidLevelChances(),
      listValidMonsterChances(),
    ])
      .then(([s, l, m]) => {
        if (cancelled) return;
        setValidSettings(s);
        setValidLevelChances(l);
        setValidMonsterChances(m);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const counts: Record<SectionKind, number> = {
    levelSettings: levelSettings.length,
    levelChances: levelChances.length,
    monsterChances: monsterChances.length,
  };

  const entries = {
    levelSettings,
    levelChances,
    monsterChances,
  }[active];

  const activeTab = SECTION_TABS.find((t) => t.kind === active)!;

  return (
    <div className="rules-panel">
      <datalist id="rules-valid-level-settings">
        {validSettings.map((n) => (
          <option key={n} value={n} />
        ))}
      </datalist>
      <datalist id="rules-valid-level-chances">
        {validLevelChances.map((n) => (
          <option key={n} value={n} />
        ))}
      </datalist>
      <datalist id="rules-valid-monster-chances">
        {validMonsterChances.map((n) => (
          <option key={n} value={n} />
        ))}
      </datalist>

      <nav className="rules-tabs" role="tablist">
        {SECTION_TABS.map((tab) => {
          const isActive = tab.kind === active;
          return (
            <button
              key={tab.kind}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={`rules-tab${isActive ? " active" : ""}`}
              onClick={() => setActive(tab.kind)}
            >
              <span className="rules-tab-label">{tab.label}</span>
              <span className="rules-tab-count">{counts[tab.kind]}</span>
            </button>
          );
        })}
      </nav>

      <p className="rules-hint">{activeTab.hint}</p>

      <RulesSection
        key={active}
        entries={entries}
        datalistId={activeTab.datalistId}
        namePlaceholder={activeTab.namePlaceholder}
        valuePlaceholder={activeTab.valuePlaceholder}
        onChange={(next) => onChange(active, next)}
      />
    </div>
  );
}

interface RulesSectionProps {
  entries: RulesEntry[];
  datalistId: string;
  namePlaceholder: string;
  valuePlaceholder: string;
  onChange: (next: RulesEntry[]) => void;
}

function RulesSection({
  entries,
  datalistId,
  namePlaceholder,
  valuePlaceholder,
  onChange,
}: RulesSectionProps) {
  const [addName, setAddName] = useState("");
  const [addValue, setAddValue] = useState("");

  const existingNames = useMemo(
    () => new Set(entries.map((e) => e.name)),
    [entries],
  );

  const trimmedName = addName.trim();
  const trimmedValue = addValue.trim();
  const canAdd =
    trimmedName.length > 0 &&
    trimmedValue.length > 0 &&
    !existingNames.has(trimmedName);

  const submitAdd = () => {
    if (!canAdd) return;
    onChange([
      ...entries,
      { name: trimmedName, value: trimmedValue, comment: null },
    ]);
    setAddName("");
    setAddValue("");
  };

  return (
    <div className="rules-section">
      {entries.length === 0 ? (
        <div className="rules-empty">
          No entries yet. Add one below.
        </div>
      ) : (
        <ul className="rules-list">
          {entries.map((entry, idx) => (
            <RulesRow
              key={`${entry.name}-${idx}`}
              entry={entry}
              onUpdate={(next) => {
                const copy = entries.slice();
                copy[idx] = next;
                onChange(copy);
              }}
              onDelete={() => {
                const copy = entries.slice();
                copy.splice(idx, 1);
                onChange(copy);
              }}
            />
          ))}
        </ul>
      )}

      <form
        className="rules-add-form"
        onSubmit={(e) => {
          e.preventDefault();
          submitAdd();
        }}
      >
        <input
          list={datalistId}
          type="text"
          className="rules-add-name"
          placeholder={namePlaceholder}
          value={addName}
          onChange={(e) => setAddName(e.target.value)}
        />
        <input
          type="text"
          className="rules-add-value"
          placeholder={valuePlaceholder}
          value={addValue}
          onChange={(e) => setAddValue(e.target.value)}
        />
        <button
          type="submit"
          className="rules-add-button"
          disabled={!canAdd}
          aria-label="Add row"
          title="Add row"
        >
          <Plus size={14} strokeWidth={2.4} aria-hidden="true" />
        </button>
      </form>
    </div>
  );
}

interface RulesRowProps {
  entry: RulesEntry;
  onUpdate: (next: RulesEntry) => void;
  onDelete: () => void;
}

function RulesRow({ entry, onUpdate, onDelete }: RulesRowProps) {
  return (
    <li className="rules-row">
      <span className="rules-row-name" title={entry.name}>
        {entry.name}
      </span>
      <input
        type="text"
        className="rules-row-value"
        value={entry.value}
        onChange={(e) => onUpdate({ ...entry, value: e.target.value })}
      />
      {/* Delete button must come BEFORE the full-width comment so grid
          auto-flow keeps it in row 1 col 3 instead of pushing it below. */}
      <button
        type="button"
        className="rules-row-delete"
        onClick={onDelete}
        aria-label={`Delete ${entry.name}`}
        title="Delete row"
      >
        <Trash2 size={14} aria-hidden="true" />
      </button>
      <input
        type="text"
        className="rules-row-comment"
        placeholder="Comment (optional)"
        value={entry.comment ?? ""}
        onChange={(e) =>
          onUpdate({
            ...entry,
            comment: e.target.value === "" ? null : e.target.value,
          })
        }
      />
    </li>
  );
}

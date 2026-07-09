import {
  TEMPLATE_SETTING_HINTS,
  TEMPLATE_SETTING_LABELS,
  TEMPLATE_SETTING_NAMES,
  type TemplateSettingName,
} from "../../lib/commands";
import "./RoomSettingsPanel.css";

interface Props {
  settings: string[];
  edited: boolean;
  onToggle: (setting: TemplateSettingName, next: boolean) => void;
}

export function RoomSettingsPanel({ settings, edited, onToggle }: Props) {
  const active = new Set(settings);
  return (
    <div className="room-settings-panel">
      <div className="room-settings-header">
        <span>Room settings</span>
        {edited && <span className="room-settings-dirty">•</span>}
      </div>
      <ul className="room-settings-list">
        {TEMPLATE_SETTING_NAMES.map((name) => {
          const checked = active.has(name);
          return (
            <li key={name}>
              <label
                className={`room-settings-item${checked ? " on" : ""}`}
                title={TEMPLATE_SETTING_HINTS[name]}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => onToggle(name, e.target.checked)}
                />
                <span className="room-settings-label">
                  {TEMPLATE_SETTING_LABELS[name]}
                </span>
              </label>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function coerceSettings(settings: string[]): TemplateSettingName[] {
  const known = new Set<TemplateSettingName>(TEMPLATE_SETTING_NAMES);
  return settings.filter((s): s is TemplateSettingName =>
    known.has(s as TemplateSettingName),
  );
}

import { Folder } from "lucide-react";
import { DropdownMenu, type DropdownEntry } from "./DropdownMenu";
import { openDirectory } from "../../lib/commands";
import { useToast } from "./Toast";
import type { DirectoryKind } from "../../types/paths";

export function FolderMenu() {
  const toast = useToast();

  const open = async (kind: DirectoryKind) => {
    try {
      await openDirectory(kind);
    } catch (err) {
      toast.error(extractMessage(err));
    }
  };

  const items: DropdownEntry[] = [
    { label: "Install Directory", onClick: () => open("install") },
    { label: "Packs", onClick: () => open("packs") },
    { label: "Extracted Assets", onClick: () => open("extracted") },
    { separator: true },
    { label: "Modlunky Data", onClick: () => open("appData") },
    { label: "Modlunky Cache", onClick: () => open("appCache") },
    { label: "Tracker Files", onClick: () => open("trackers") },
  ];

  return (
    <DropdownMenu
      ariaLabel="Open folder"
      trigger={
        <button
          className="icon-button"
          type="button"
          aria-label="Open folder"
          title="Open folder"
        >
          <Folder size={18} aria-hidden="true" />
        </button>
      }
      items={items}
    />
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

declare type DndEvent = import("svelte-dnd-action").DndEvent;
declare namespace svelte.JSX {
  interface HTMLAttributes<T> {
    onconsider?: (
      event: CustomEvent<DndEvent> & { target: EventTarget & T }
    ) => void;
    onfinalize?: (
      event: CustomEvent<DndEvent> & { target: EventTarget & T }
    ) => void;
  }
}

type ButtonSize = "tiny" | "small" | "default" | "large" | "huge";
type ButtonColor =
  | "default"
  | "primary"
  | "transparent"
  | "danger"
  | "warning"
  | "info";

type StackDirection = "horizontal" | "vertical";
type StackSpacing = "none" | "small" | "default" | "large" | number;
type StackAlign = "stretch" | "center" | "start" | "end";
type StackJustify = "stretch" | "center" | "start" | "end" | "between";

type PanelPadding = "none" | "small" | "default" | "large" | "huge";

type Mod = {
  id: number;
  name: string;
  enabled: boolean;
};

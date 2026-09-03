// Terra's quest, unpacked from the single number the save stores.
//
// The file keeps one value, 0 to 10, which is really two things at once:
// whether you have met Terra, and how many of nine deliveries you have
// made. The nine come in three groups of three, and each completed group
// opens one shortcut. Rendering the raw number, or the one-line
// description of the current step, throws that shape away.
//
//   0      never met Terra
//   1      met Terra, no deliveries yet
//   2..4   the three deliveries that open the 1-4 shortcut
//   5..7   the three that open 3-1
//   8..10  the three that open 5-1

/** One of the nine things Terra asks for. */
export interface Delivery {
  /** What she wants, e.g. "1 bomb". */
  label: string;
  done: boolean;
}

/** Three deliveries, and the shortcut they open between them. */
export interface ShortcutStage {
  /** The level the shortcut leads to, e.g. "1-4". */
  opens: string;
  deliveries: Delivery[];
  /** Whether all three are done, so the shortcut is open. */
  complete: boolean;
}

export interface ShortcutProgress {
  metTerra: boolean;
  /** How many of the nine deliveries are done. */
  delivered: number;
  total: number;
  stages: ShortcutStage[];
}

/** What Terra asks for, in the order the save numbers them. */
const REQUESTS: { opens: string; items: [string, string, string] }[] = [
  { opens: "1-4", items: ["$2,000", "1 bomb", "$10,000"] },
  { opens: "3-1", items: ["1 rope", "a weapon", "a mount"] },
  { opens: "5-1", items: ["$50,000", "a hired hand", "the golden key"] },
];

export const TOTAL_DELIVERIES = 9;

/**
 * Unpacks the stored value into the nine deliveries it stands for.
 *
 * Values outside 0..10 are clamped rather than rejected: a save editor
 * can write anything, and a progress bar is not the place to raise it.
 */
export function shortcutProgress(value: number): ShortcutProgress {
  const clamped = Number.isFinite(value)
    ? Math.min(10, Math.max(0, Math.floor(value)))
    : 0;
  // Value 1 is "met Terra" and is not itself a delivery, so the count of
  // deliveries is one behind the stored number.
  const delivered = Math.max(0, clamped - 1);

  const stages = REQUESTS.map((request, stageIndex) => {
    const deliveries = request.items.map((label, itemIndex) => ({
      label,
      done: delivered > stageIndex * 3 + itemIndex,
    }));
    return {
      opens: request.opens,
      deliveries,
      complete: deliveries.every((delivery) => delivery.done),
    };
  });

  return {
    metTerra: clamped >= 1,
    delivered,
    total: TOTAL_DELIVERIES,
    stages,
  };
}

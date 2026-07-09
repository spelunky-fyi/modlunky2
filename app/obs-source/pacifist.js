// Pacifist tracker's per-page glue. Reuses `final-death` styling for
// the "broken" (killed something) state so both trackers share the
// same red tint on their negative state.
"use strict";

startTracker({
  slug: "pacifist",
  onPayload: (data, el) => {
    el.textContent = data.text || "";
    if (data.broken) {
      el.classList.add("final-death");
    } else {
      el.classList.remove("final-death");
    }
  },
});

// Category tracker's per-page glue. Runtime handles connection +
// window config; this just decides how a CategoryPayload renders.
"use strict";

startTracker({
  slug: "category",
  onPayload: (data, el) => {
    el.textContent = data.text || "";
    if (data.final_death) {
      el.classList.add("final-death");
    } else {
      el.classList.remove("final-death");
    }
  },
});

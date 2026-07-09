"use strict";

startTracker({
  slug: "gem",
  onPayload: (data, el) => {
    el.textContent = data.text || "";
  },
});

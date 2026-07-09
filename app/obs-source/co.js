"use strict";

startTracker({
  slug: "co",
  onPayload: (data, el) => {
    el.textContent = data.text || "";
  },
});

"use strict";

startTracker({
  slug: "pacino-golf",
  onPayload: (data, el) => {
    el.textContent = data.text || "";
  },
});

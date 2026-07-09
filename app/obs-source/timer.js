// Timer tracker OBS page. Text is a multi-line label; CSS handles
// \n rendering via `white-space: pre-line` on .tracker-text-multiline.
"use strict";

startTracker({
  slug: "timer",
  onPayload: (data, el) => {
    el.textContent = data.text || "";
  },
});

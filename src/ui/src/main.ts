import "@unocss/reset/tailwind.css";
import "uno.css";
import "./index.css";
import App from "./App.svelte";

const app = new App({
  target: document.getElementById("app") as Element,
});

export default app;

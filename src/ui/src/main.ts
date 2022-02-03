import App from "./App.svelte";
import "./styles/index.css";

const app = new App({
  target: document.getElementById("app") as Element,
});

export default app;

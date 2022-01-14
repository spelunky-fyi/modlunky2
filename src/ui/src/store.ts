import { writable } from "svelte/store";

export const activeTabIndex = writable(0);

let id_counter = 0;
export const mods = writable([
  {
    name: "Backpack",
    enabled: true,
    id: id_counter++,
  },
  {
    name: "Tele-trainer",
    enabled: false,
    id: id_counter++,
  },
  {
    name: "Randomizer",
    enabled: true,
    id: id_counter++,
  },
]);

id_counter = 0;
export const versions = [
  {
    revision: "v0.12.0",
    installed: true,
    id: id_counter++,
  },
  {
    revision: "v0.11.1",
    installed: true,
    id: id_counter++,
  },
  {
    revision: "v0.11.0",
    installed: true,
    id: id_counter++,
  },
  {
    revision: "v0.10.1",
    installed: false,
    id: id_counter++,
  },
  {
    revision: "v0.10.0",
    installed: false,
    id: id_counter++,
  },
];
export const version = writable(versions[0]);

export const colorKey = writable("#ff00ff");

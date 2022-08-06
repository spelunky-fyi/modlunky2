import Playlunky from "./lib/pages/playlunky";
import InstallMods from "./lib/pages/installmods";
import Overlunky from "./lib/pages/overlunky";
import ExtractAssets from "./lib/pages/extractassets";
import Trackers from "./lib/pages/trackers";
import Settings from "./lib/pages/settings";

export const tabs = [
  {
    title: "Playlunky",
    component: Playlunky,
  },
  {
    title: "Install Mods",
    component: InstallMods,
  },
  {
    title: "Overlunky",
    component: Overlunky,
  },
  {
    title: "Extract Assets",
    component: ExtractAssets,
  },
  {
    title: "Level Editor",
    component: null,
    disabled: true,
  },
  {
    title: "Trackers",
    component: Trackers,
  },
  {
    title: "Settings",
    component: Settings,
  },
];

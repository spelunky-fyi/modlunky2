import Playlunky from "@/components/pages/playlunky";
import InstallMods from "@/components/pages/installmods";
import Overlunky from "@/components/pages/overlunky";
import ExtractAssets from "@/components/pages/extractassets";
import Trackers from "@/components/pages/trackers";
import Settings from "@/components/pages/settings";

export const tabs = [
  {
    title: "Playlunky",
    component: Playlunky,
    hideConsole: true,
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

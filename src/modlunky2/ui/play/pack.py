import json
import logging
import shutil
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from modlunky2.utils import open_directory


logger = logging.getLogger("modlunky2")


class Pack:
    def __init__(self, play_tab, parent, modlunky_config, folder):
        self.play_tab = play_tab
        self.modlunky_config = modlunky_config
        self.folder = folder
        self.needs_update = False

        self.pack_metadata_path = (
            modlunky_config.install_dir / "Mods/.ml/pack-metadata" / folder
        )
        self.manifest_path = self.pack_metadata_path / "manifest.json"

        self.manifest = {}
        self.logo_img = None
        self.name = folder

        self.logo = ttk.Label(parent)
        self.var = tk.BooleanVar()
        self.checkbutton = ttk.Checkbutton(
            parent,
            text=self.name,
            style="ModList.TCheckbutton",
            variable=self.var,
            onvalue=True,
            offvalue=False,
            compound="left",
            command=self.on_check,
        )

        button_padding = 1
        self.buttons = ttk.Frame(parent)
        self.buttons.rowconfigure(0, weight=1)

        self.buttons.update_button = ttk.Button(
            self.buttons,
            padding=button_padding,
            image=self.play_tab.packs_frame.update_icon,
            command=self.update_pack,
        )

        self.buttons.options_button = ttk.Button(
            self.buttons,
            padding=button_padding,
            image=self.play_tab.packs_frame.options_icon,
            command=self.open_pack_dir,
        )
        # self.buttons.options_button.grid(row=0, column=1, padx=(1, 0), sticky="e")

        self.buttons.folder_button = ttk.Button(
            self.buttons,
            padding=button_padding,
            image=self.play_tab.packs_frame.folder_icon,
            command=self.open_pack_dir,
        )
        self.buttons.folder_button.grid(row=0, column=2, padx=(1, 0), sticky="e")

        self.buttons.trash_button = ttk.Button(
            self.buttons,
            padding=button_padding,
            image=self.play_tab.packs_frame.trash_icon,
            command=self.remove_pack,
        )
        self.buttons.trash_button.grid(row=0, column=3, padx=(1, 0), sticky="e")
        self.on_load()

    @property
    def slug(self):
        return self.manifest.get("slug")

    def update_pack(self):
        answer = tk.messagebox.askokcancel(
            title="Update Pack?",
            message=(f"Are you sure you want to update {self.slug}?\n"),
            icon=tk.messagebox.INFO,
        )

        if not answer:
            return

        spelunky_fyi_root = self.modlunky_config.config_file.spelunky_fyi_root
        api_token = self.modlunky_config.config_file.spelunky_fyi_api_token

        self.play_tab.task_manager.call(
            "install:install_fyi_mod",
            install_dir=self.modlunky_config.install_dir,
            spelunky_fyi_root=spelunky_fyi_root,
            api_token=api_token,
            install_code=self.slug,
            overwrite=True,
        )
        logger.info("Coming soon...")

    def is_fyi_pack(self):
        if "slug" not in self.manifest:
            return False

        if "mod_file" not in self.manifest:
            return False

        if "id" not in self.manifest["mod_file"]:
            return False

        return True

    def get_latest_id(self):
        latest_path = self.pack_metadata_path / "latest.json"
        if not latest_path.exists():
            return None

        with latest_path.open("r", encoding="utf-8") as handle:
            try:
                return json.load(handle).get("id")
            except json.JSONDecodeError:
                return None

    def check_needs_update(self):
        if not self.is_fyi_pack():
            self.needs_update = False
            return

        latest_id = self.get_latest_id()
        if not latest_id:
            self.needs_update = False
            return

        if latest_id == self.manifest["mod_file"]["id"]:
            self.needs_update = False
        else:
            self.needs_update = True

    def on_load(self):
        if self.manifest_path.exists():
            with self.manifest_path.open("r", encoding="utf-8") as manifest_file:
                self.manifest = json.load(manifest_file)
        else:
            self.manifest = {}

        self.name = self.manifest.get("name", self.folder)
        self.checkbutton.configure(text=self.name)
        if (
            self.manifest.get("logo")
            and (self.pack_metadata_path / self.manifest["logo"]).exists()
        ):
            self.logo_img = ImageTk.PhotoImage(
                Image.open(self.pack_metadata_path / self.manifest["logo"]).resize(
                    (40, 40), Image.ANTIALIAS
                )
            )
            self.logo.configure(image=self.logo_img)
        else:
            self.logo_img = None
            self.logo.configure(image=None)

        self.check_needs_update()
        self.render_buttons()

    def forget(self):
        self.logo.grid_forget()
        self.checkbutton.grid_forget()
        self.buttons.grid_forget()

    def grid(self, row):
        self.logo.grid(row=row, column=0, sticky="ew")
        self.checkbutton.grid(row=row, column=1, pady=0, padx=5, sticky="nsw")
        self.buttons.grid(row=row, column=2, pady=0, padx=(5, 25), sticky="e")

    def render_buttons(self):
        if not (self.modlunky_config.install_dir / "Mods/Packs" / self.folder).exists():
            self.buttons.folder_button["state"] = tk.DISABLED
        else:
            self.buttons.folder_button["state"] = tk.NORMAL

        if self.needs_update:
            api_token = self.modlunky_config.config_file.spelunky_fyi_api_token
            self.buttons.update_button.grid(row=0, column=0, padx=(1, 0), sticky="e")
            if api_token:
                self.buttons.update_button["state"] = tk.NORMAL
            else:
                self.buttons.update_button["state"] = tk.DISABLED
        else:
            self.buttons.update_button.grid_forget()

    def selected(self):
        return self.var.get()

    def enable(self):
        self.var.set(True)

    def disable(self):
        self.var.set(False)

    def set(self, val: bool):
        if val:
            self.enable()
        else:
            self.disable()
        self.on_check()

    def destroy(self):
        self.checkbutton.destroy()
        self.buttons.destroy()
        self.logo.destroy()
        self.play_tab.load_order.delete(self.folder)

    def on_check(self):
        if self.var.get():
            self.play_tab.load_order.insert(self.folder)
        else:
            self.play_tab.load_order.delete(self.folder)
        self.play_tab.packs_frame.render_packs()

    def open_pack_dir(self):
        if self.folder.startswith("/"):
            logger.warning("Got dangerous pack name, aborting...")
            return

        pack_dir = self.modlunky_config.install_dir / "Mods/Packs" / self.folder
        if not pack_dir.exists():
            logger.info("No pack directory found to remove. Looked in %s", pack_dir)
            return

        open_directory(pack_dir)

    def remove_pack(self):
        if self.folder.startswith("/"):
            logger.warning("Got dangerous pack name, aborting...")
            return

        to_remove = []
        pack_dir = self.modlunky_config.install_dir / "Mods/Packs" / self.folder
        if pack_dir.exists():
            to_remove.append(pack_dir)

        if not to_remove:
            logger.info("No pack directory found to remove. Looked in %s", pack_dir)

        removing = "\n".join(map(str, to_remove))
        answer = tk.messagebox.askokcancel(
            title="Confirmation",
            message=(
                "Are you sure you want to remove this pack?\n"
                "\n"
                "This will remove the following:\n"
                f"{removing}"
            ),
            icon=tk.messagebox.WARNING,
        )

        if not answer:
            return

        for path in to_remove:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        self.play_tab.on_load()

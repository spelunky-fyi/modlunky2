import json
import logging
import shutil
import tkinter as tk
import zipfile
from io import BytesIO
from shutil import copyfile
from tkinter import ttk

import requests

from modlunky2.api import SpelunkyFYIClient
from modlunky2.config import Config
from modlunky2.constants import BASE_DIR
from modlunky2.utils import tb_info

logger = logging.getLogger(__name__)


class SequencePanel(ttk.Frame):
    def __init__(
        self, parent, modlunky_config: Config, on_update_sequence, *args, **kwargs
    ):
        super().__init__(parent, *args, **kwargs)
        self.config = modlunky_config

        self.pack_path = None
        self.level_order = None
        self.all_levels = None
        self.install_error = False

        self.on_update_sequence = on_update_sequence

        self.rowconfigure(0, minsize=200, weight=1)
        self.rowconfigure(1, minsize=200, weight=1)
        self.columnconfigure(0, weight=1)

        self.sequence_frame = SequenceFrame(
            self, self.remove_level, self.move_up, self.move_down
        )
        self.sequence_frame.grid(row=0, column=0, pady=5, padx=5, sticky="news")

        self.ignored_frame = IgnoredFrame(self, self.add_level)
        self.ignored_frame.grid(row=1, column=0, pady=5, padx=5, sticky="news")

        self.library_frame = tk.Frame(self)
        self.library_frame.grid(row=2, column=0, sticky="news")

        self.library_label = tk.Label(
            self.library_frame,
            text="Level Sequence Library",
            font=("TkDefaultFont", 12),
        )
        self.library_label.grid(row=0, column=0, sticky="nsw")

        self.library_status_label = tk.Label(
            self.library_frame, text="", wraplength=400, justify="left"
        )
        self.library_status_label.grid(row=1, column=0, sticky="nsw")

        self.library_install_button = tk.Button(
            self.library_frame,
            text="Install",
            command=self.install_level_sequence_with_confirmation,
        )
        self.library_install_button["state"] = tk.DISABLED
        self.library_install_button.grid(row=2, column=0, sticky="nsw")

        self.main_frame = tk.Frame(self)
        self.main_frame.grid(row=3, column=0, sticky="news")

        self.main_label = tk.Label(self.main_frame, text="main.lua file", font=("TkDefaultFont", 12))
        self.main_label.grid(row=0, column=0, sticky="nsw")

        self.main_status_label = tk.Label(
            self.main_frame, text="", wraplength=400, justify="left"
        )
        self.main_status_label.grid(row=1, column=0, sticky="nsw")

        self.main_install_button = tk.Button(
            self.main_frame,
            text="Generate",
            command=self.generate_main_file_with_confirmation,
        )
        self.main_install_button["state"] = tk.DISABLED
        self.main_install_button.grid(row=2, column=0, sticky="nsw")
        self.main_created = False


    def update_pack(self, pack_path, level_order, all_levels):
        self.pack_path = pack_path
        self.level_order = level_order
        self.all_levels = all_levels
        self.main_created = False

        self.refresh_lists()
        self.check_for_updates()
        self.update_main_file_views()

    # Handle the insall button. Ask a user about installing a new version if one exists, or install if none does. Check for updates instead
    # if already on the latest.
    def install_level_sequence_with_confirmation(self):
        latest_id = self.get_latest_id()
        current_id = self.get_current_id()
        if not self.level_sequence_path.exists():
            self.install_level_sequence()
        elif current_id is None:
            answer = tk.messagebox.askokcancel(
                title="Overwrite LevelSequence library?",
                message=(
                    f"Are you sure you want to install the latest version of LevelSequence from spelunky.fyi and overwrite the currently installed version?\n"
                ),
                icon=tk.messagebox.INFO,
            )

            if not answer:
                return

            self.install_level_sequence()
        elif latest_id is not None and latest_id != current_id:
            answer = tk.messagebox.askokcancel(
                title="Update LevelSequence library?",
                message=(
                    f"Are you sure you want to update to the latest version of LevelSequence?\n"
                ),
                icon=tk.messagebox.INFO,
            )

            if not answer:
                return

            self.install_level_sequence()
        else:
            self.check_for_updates()

    # Install the latest version of LevelSequence library, replacing any existing version.
    def install_level_sequence(self):
        self.install_error = False
        spelunky_fyi_root = self.config.spelunky_fyi_root
        api_token = self.config.spelunky_fyi_api_token
        api_client = SpelunkyFYIClient(spelunky_fyi_root, api_token)

        mod_details, code = api_client.get_mod("level-sequence")

        def error():
            self.install_error = True
            self.update_level_sequence_views()

        if mod_details is None:
            error()
            return

        mod_file = api_client.get_mod_file_from_details(mod_details)
        if mod_file is None:
            error()
            return

        url = mod_file["download_url"]

        if self.level_sequence_path.exists():
            shutil.rmtree(self.level_sequence_path)
        self.level_sequence_path.mkdir(parents=True, exist_ok=True)

        contents = BytesIO()
        try:
            response = requests.get(url, stream=True, allow_redirects=True, timeout=5)
            response.raise_for_status()
            amount_downloaded = 0
            block_size = 102400

            for data in response.iter_content(block_size):
                amount_downloaded += len(data)
                logger.info("Downloaded %s bytes", amount_downloaded)
                contents.write(data)

        except Exception:  # pylint: disable=broad-except
            logger.critical("Failed to download %s: %s", url, tb_info())
            error()
            return

        contents.seek(0)

        if contents is None:
            logger.warning("Failed to download file from %s", url)
            error()
            return

        modzip = zipfile.ZipFile(contents)
        modzip.extractall(self.level_sequence_path, modzip.infolist())

        current_details = {
            "id": mod_file["id"],
        }

        # Write id of the latest version to file.
        with self.latest_path.open("w", encoding="utf-8") as handle:
            json.dump(current_details, handle)

        # Write id of the current version to file.
        with self.current_path.open("w", encoding="utf-8") as handle:
            json.dump(current_details, handle)

        self.update_level_sequence_views()

    # Update level sequence views with current state based on installed version and latest version.
    def update_level_sequence_views(self):
        latest_id = self.get_latest_id()
        current_id = self.get_current_id()
        if not self.level_sequence_path.exists():
            self.library_status_label.grid_remove()
            self.library_install_button["state"] = tk.NORMAL
            self.library_install_button["text"] = "Install"
        elif current_id is None:
            self.library_status_label.grid()
            self.library_status_label[
                "text"
            ] = "Level Sequence library appears to be installed, but the current version is not detected. It may be managed remotely (eg, via git). To manage the library via Modlunky, you may overwrite the current version you have installed. Ensure you are okay with this before overwriting."
            self.library_install_button["state"] = tk.NORMAL
            self.library_install_button["text"] = "Overwrite"
        elif latest_id is not None and latest_id != current_id:
            self.library_status_label.grid()
            self.library_status_label["text"] = "New version found"
            self.library_install_button["state"] = tk.NORMAL
            self.library_install_button["text"] = "Update"
        else:
            self.library_status_label.grid()
            self.library_status_label["text"] = "Up to date!"
            self.library_install_button["state"] = tk.NORMAL
            self.library_install_button["text"] = "Check for Updates"

        if self.install_error:
            self.library_status_label.grid()
            self.library_status_label["text"] = "Failed to install LevelSequence."

    # Pulls mod info from spelunky.fyi to check what the latest version is, then updates views with this information.
    def check_for_updates(self):
        self.install_error = False
        # Download latest version from server and save it to latest.json file.
        self.download_updates()
        # Update the UI after fetching the latest version.
        self.update_level_sequence_views()

    # Pulls mod info from spelunky.fyi to check what the latest version is.
    def download_updates(self):
        # This modpack does not have the level sequence, do not attempt to check for updates.
        if not self.level_sequence_path.exists() or not self.current_path.exists():
            return

        spelunky_fyi_root = self.config.spelunky_fyi_root
        api_token = self.config.spelunky_fyi_api_token
        api_client = SpelunkyFYIClient(spelunky_fyi_root, api_token)

        # Download metadata for the level sequence to check the id of the latest version.
        details, code = api_client.get_mod("level-sequence")

        if code == 401 or code == 404:
            return

        if details is None:
            return

        mod_file = api_client.get_mod_file_from_details(details)

        if mod_file is None:
            return

        latest_details = {
            "id": mod_file["id"],
        }

        if self.latest_path.exists():
            with self.latest_path.open("r", encoding="utf-8") as handle:
                if latest_details == json.load(handle):
                    # There hasn't been a new version since we last checked.
                    return

        # Write id of the latest version to file.
        with self.latest_path.open("w", encoding="utf-8") as handle:
            json.dump(latest_details, handle)

    # Path to LevelSequence library.
    @property
    def level_sequence_path(self):
        return self.pack_path / "LevelSequence"

    # Path to file that contains the latest version id of LevelSequence library.
    @property
    def latest_path(self):
        return self.level_sequence_path / "latest.json"

    # Path to file that contains the currently installed version id of LevelSequence library.
    @property
    def current_path(self):
        return self.level_sequence_path / "current.json"

    # Returns the latest version id of LevelSequence library.
    def get_latest_id(self):
        if not self.latest_path.exists():
            return None

        with self.latest_path.open("r", encoding="utf-8") as handle:
            try:
                return json.load(handle).get("id")
            except json.JSONDecodeError:
                return None

    # Returns the currently installed version id of LevelSequence library.
    def get_current_id(self):
        if not self.current_path.exists():
            return None

        with self.current_path.open("r", encoding="utf-8") as handle:
            try:
                return json.load(handle).get("id")
            except json.JSONDecodeError:
                return None

    def generate_main_file_with_confirmation(self):
        if self.main_path.exists():
            answer = tk.messagebox.askokcancel(
                title="Overwrite main.lua?",
                message=(
                    f"Are you sure you want to overwrite your main.lua file?\n"
                ),
                icon=tk.messagebox.INFO,
            )

            if not answer:
                return

            answer = tk.messagebox.askokcancel(
                title="Overwrite main.lua?",
                message=(
                    f"Confirm once more: Are you sure you want to overwrite your main.lua file?\n\nIf you have custom logic you rely on, please abort this operation and commit your files into source control before continuing."
                ),
                icon=tk.messagebox.INFO,
            )

            if not answer:
                return
        self.generate_main_file()

    def generate_main_file(self):
        with self.main_template_path.open("r", encoding="utf-8") as template:
            with self.main_path.open("w", encoding="utf-8") as main:
                for line in template:
                    main.write(line.replace("<ModName>", self.pack_path.stem))

        self.main_created = True
        self.update_main_file_views()

    # Update level sequence views with current state based on installed version and latest version.
    def update_main_file_views(self):
        if not self.main_path.exists():
            self.main_status_label["text"] = "Generate main.lua file with the code required to play levels."
            self.main_status_label.grid()
            self.main_install_button["text"] = "Generate"
            self.main_install_button["state"] = tk.NORMAL
        elif self.main_created:
            self.main_status_label["text"] = "File generated!"
            self.main_status_label.grid()
            self.main_install_button["text"] = "Generate"
            self.main_install_button["state"] = tk.DISABLED
        else:
            self.main_status_label["text"] = "You already have a main.lua file. Clicking this button will overwrite it with the code required to play levels. This will delete the current contents of main.lua. Only do this if this is what you want."
            self.main_status_label.grid()
            self.main_install_button["text"] = "Overwrite"
            self.main_install_button["state"] = tk.NORMAL

    # Path to mod's main.lua file.
    @property
    def main_path(self):
        return self.pack_path / "main.lua"

    # Path to main.lua template file.
    @property
    def main_template_path(self):
        return BASE_DIR / "static/templates/main.lua.template"

    @property
    def unused_levels(self):
        unused_levels = []
        for level in self.all_levels:
            if level not in self.level_order:
                unused_levels.append(level)
        return unused_levels

    def update_sequence(self):
        self.on_update_sequence(self.level_order)
        self.refresh_lists()

    def refresh_lists(self):
        self.sequence_frame.update_level_order(self.level_order)
        self.ignored_frame.update_level_order(self.unused_levels)

    def remove_level(self, index):
        selection = index

        if selection is None:
            return

        self.level_order.pop(selection)
        self.update_sequence()

    def move_up(self, selection):
        if selection is None:
            return

        if selection == 0:
            return

        new = [self.level_order[selection], self.level_order[selection - 1]]
        self.level_order[selection - 1 : selection + 1] = [
            self.level_order[selection],
            self.level_order[selection - 1],
        ]
        self.update_sequence()

    def move_down(self, selection):
        size = len(self.level_order)

        if selection is None:
            return

        if selection == size - 1:
            return

        self.level_order[selection : selection + 2] = [
            self.level_order[selection + 1],
            self.level_order[selection],
        ]
        self.update_sequence()

    def add_level(self, index):
        self.level_order.append(self.unused_levels[index])
        self.update_sequence()


class SequenceFrame(ttk.LabelFrame):
    def __init__(self, parent, on_remove, on_move_up, on_move_down, *args, **kwargs):
        super().__init__(parent, text="Levels", *args, **kwargs)

        self.level_order = None

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(self, selectmode=tk.SINGLE)
        self.listbox.grid(
            row=0, column=0, columnspan=3, pady=5, padx=(5, 0), sticky="news"
        )

        self.scrollbar = ttk.Scrollbar(self)
        self.scrollbar.grid(row=0, column=1, columnspan=3, pady=5, sticky="nes")

        self.listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self.render_buttons)

        self.up_button = ttk.Button(
            self,
            text="Up",
            state=tk.DISABLED,
            command=lambda: on_move_up(self.current_selection()),
        )
        self.up_button.grid(row=1, column=0, pady=5, padx=2, sticky="news")

        self.down_button = ttk.Button(
            self,
            text="Down",
            state=tk.DISABLED,
            command=lambda: on_move_down(self.current_selection()),
        )
        self.down_button.grid(row=1, column=1, pady=5, padx=2, sticky="news")

        self.remove_button = ttk.Button(
            self,
            text="Remove",
            state=tk.DISABLED,
            command=lambda: on_remove(self.current_selection()),
        )
        self.remove_button.grid(row=1, column=2, pady=5, padx=2, sticky="news")

    def update_level_order(self, level_order):
        self.level_order = level_order
        self.refresh_list()

    def current_selection(self):
        selection = self.listbox.curselection()
        if not selection:
            return None
        return selection[0]

    def render_buttons(self, _event=None):
        size = self.listbox.size()
        selection = self.current_selection()
        if selection is None:
            self.remove_button["state"] = tk.DISABLED
        else:
            self.remove_button["state"] = tk.NORMAL

        # Too few items or none selected
        if size < 2 or selection is None:
            up_state = tk.DISABLED
            down_state = tk.DISABLED
        # First item selected
        elif selection == 0:
            up_state = tk.DISABLED
            down_state = tk.NORMAL
        # Last item selected
        elif selection == size - 1:
            up_state = tk.NORMAL
            down_state = tk.DISABLED
        else:
            up_state = tk.NORMAL
            down_state = tk.NORMAL

        self.up_button["state"] = up_state
        self.down_button["state"] = down_state

    def refresh_list(self):
        selection = self.current_selection()
        label = None
        if selection is not None:
            label = self.listbox.get(selection)

        self.listbox.delete(0, self.listbox.size())
        for level in self.level_order:
            self.listbox.insert(tk.END, level)
            if level == label:
                self.listbox.selection_set(self.listbox.size() - 1)

        new_selection = self.current_selection()
        if new_selection is not None:
            self.listbox.see(new_selection)
        self.render_buttons()


class IgnoredFrame(ttk.LabelFrame):
    def __init__(self, parent, on_add, *args, **kwargs):
        super().__init__(parent, text="Ignored Levels", *args, **kwargs)

        self.level_order = None

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(self, selectmode=tk.SINGLE)
        self.listbox.grid(
            row=0, column=0, columnspan=3, pady=5, padx=(5, 0), sticky="news"
        )

        self.scrollbar = ttk.Scrollbar(self)
        self.scrollbar.grid(row=0, column=1, columnspan=3, pady=5, sticky="nes")

        self.listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self.render_buttons)

        self.add_button = ttk.Button(
            self,
            text="Add",
            state=tk.DISABLED,
            command=lambda: on_add(self.current_selection()),
        )
        self.add_button.grid(row=1, column=2, pady=5, padx=2, sticky="news")

    def update_level_order(self, level_order):
        self.level_order = level_order
        self.refresh_list()

    def current_selection(self):
        selection = self.listbox.curselection()
        if not selection:
            return None
        return selection[0]

    def render_buttons(self, _event=None):
        size = self.listbox.size()
        selection = self.current_selection()
        if selection is None:
            self.add_button["state"] = tk.DISABLED
        else:
            self.add_button["state"] = tk.NORMAL

    def refresh_list(self):
        selection = self.current_selection()
        label = None
        if selection is not None:
            label = self.listbox.get(selection)

        self.listbox.delete(0, self.listbox.size())
        for level in self.level_order:
            self.listbox.insert(tk.END, level)
            if level == label:
                self.listbox.selection_set(self.listbox.size() - 1)

        new_selection = self.current_selection()
        if new_selection is not None:
            self.listbox.see(new_selection)
        self.render_buttons()

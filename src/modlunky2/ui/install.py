import logging
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from modlunky2.ui.widgets import Tab

logger = logging.getLogger("modlunky2")


class SourceChooser(ttk.Frame):
    def __init__(self, parent, modlunky_config):
        super().__init__(parent)
        self.modlunky_config = modlunky_config

        file_chooser_label = ttk.Label(self, text="Choose the file you want to install")
        file_chooser_label.grid(
            row=0, column=0, padx=5, pady=(2, 0), columnspan=3, sticky="w"
        )

        self.file_chooser_var = tk.StringVar()

        file_chooser_entry = ttk.Entry(
            self,
            textvariable=self.file_chooser_var,
            state=tk.DISABLED,
            width=80,
        )
        file_chooser_entry.columnconfigure(0, weight=1)
        file_chooser_entry.columnconfigure(1, weight=1)
        file_chooser_entry.columnconfigure(2, weight=1)
        file_chooser_entry.grid(
            row=1, column=0, padx=10, pady=10, columnspan=3, sticky="n"
        )

        file_chooser_browse = ttk.Button(self, text="Browse", command=self.browse)
        file_chooser_browse.grid(row=2, column=0, pady=5, padx=5, sticky="nsew")

    def browse(self):
        initial_dir = Path(self.modlunky_config.config_file.last_install_browse)
        if not initial_dir.exists():
            initial_dir = Path("/")

        filename = tk.filedialog.askopenfilename(parent=self, initialdir=initial_dir)
        if not filename:
            self.file_chooser_var.set("")
            self.master.master.render()
            return

        self.file_chooser_var.set(filename)
        parent = Path(filename).parent

        self.modlunky_config.config_file.last_install_browse = str(parent.as_posix())
        self.modlunky_config.config_file.save()
        self.master.master.render()


class DestinationChooser(ttk.Frame):
    def __init__(self, parent, modlunky_config):
        super().__init__(parent)
        self.modlunky_config = modlunky_config

        file_chooser_label = ttk.Label(self, text="Choose or Create a Pack")
        file_chooser_label.grid(
            row=0, column=0, padx=5, pady=(2, 0), columnspan=3, sticky="w"
        )

        self.file_chooser_var = tk.StringVar()

        file_chooser_entry = ttk.Entry(
            self,
            textvariable=self.file_chooser_var,
            state=tk.DISABLED,
            width=80,
        )
        file_chooser_entry.columnconfigure(0, weight=1)
        file_chooser_entry.columnconfigure(1, weight=1)
        file_chooser_entry.columnconfigure(2, weight=1)
        file_chooser_entry.grid(
            row=1, column=0, padx=10, pady=10, columnspan=3, sticky="n"
        )

        file_chooser_browse = ttk.Button(self, text="Browse", command=self.browse)
        file_chooser_browse.grid(row=2, column=0, pady=5, padx=5, sticky="nsew")

    def browse(self):
        initial_dir = self.modlunky_config.install_dir / "Mods/Packs"
        if not initial_dir.exists():
            logger.critical("Expected Packs dir not found.")
            return

        directory = tk.filedialog.askdirectory(parent=self, initialdir=initial_dir)
        if not directory:
            self.file_chooser_var.set("")
            self.master.master.render()
            return

        initial_dir = initial_dir.resolve()
        directory = Path(directory).resolve()

        if initial_dir == directory:
            logger.critical(
                "You must create a directory inside of Packs to install your mod into."
            )
            self.file_chooser_var.set("")
            self.master.master.render()
            return

        # Directory chosen Packs or above
        if initial_dir not in directory.parents:
            logger.critical("You chose a directory outside of Packs which is invalid.")
            self.file_chooser_var.set("")
            self.master.master.render()
            return

        # Directory chosen inside of a pack directory
        relative_pack_dir = directory.relative_to(initial_dir)
        if len(relative_pack_dir.parts) != 1:
            logger.critical(
                "You must choose a directory only one level deep inside of Packs."
            )
            self.file_chooser_var.set("")
            self.master.master.render()
            return

        self.file_chooser_var.set(relative_pack_dir)
        self.master.master.render()


def install_mod(call, install_dir: Path, source: Path, pack: str):
    packs_dir = install_dir / "Mods/Packs"
    dest_dir = packs_dir / pack

    if not dest_dir.exists():
        dest_dir.mkdir(parents=True, exist_ok=True)

    if source.suffix == ".zip":
        logger.info("Extracting %s to %s", source.name, dest_dir)
        shutil.unpack_archive(source, dest_dir)
    else:
        logger.info("Copying file %s to %s", source.name, dest_dir)
        shutil.copy(source.resolve(), dest_dir.resolve())

    logger.info("Finished installing %s to %s", source.name, dest_dir)
    call("play:reload")


class InstallTab(Tab):
    def __init__(self, tab_control, modlunky_config, task_manager, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.modlunky_config = modlunky_config
        self.task_manager = task_manager

        self.task_manager.register_task(
            "install:install_mod",
            install_mod,
            True,
        )

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, minsize=60)

        source_frame = ttk.LabelFrame(self, text="Source")
        source_frame.rowconfigure(0, weight=1)
        source_frame.columnconfigure(0, weight=1)
        source_frame.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

        self.file_chooser_frame = SourceChooser(source_frame, modlunky_config)
        self.file_chooser_frame.grid(row=0, column=0, pady=5, padx=5, sticky="new")

        dest_frame = ttk.LabelFrame(self, text="Destination")
        dest_frame.rowconfigure(0, weight=1)
        dest_frame.columnconfigure(0, weight=1)
        dest_frame.grid(row=1, column=0, pady=5, padx=5, sticky="nswe")

        self.file_chooser_frame2 = DestinationChooser(dest_frame, modlunky_config)
        self.file_chooser_frame2.grid(row=0, column=0, pady=5, padx=5, sticky="new")

        self.button_install = ttk.Button(self, text="Install", command=self.install)
        self.button_install.grid(row=2, column=0, pady=5, padx=5, sticky="nswe")

    def on_load(self):
        self.render()

    def install(self):
        source = Path(self.file_chooser_frame.file_chooser_var.get())
        pack = self.file_chooser_frame2.file_chooser_var.get()

        if not all([source, pack]):
            logger.critical("Attempted to install mod with missing source and pack")
            return

        self.file_chooser_frame.file_chooser_var.set("")
        self.file_chooser_frame2.file_chooser_var.set("")
        self.render()

        self.task_manager.call(
            "install:install_mod",
            install_dir=self.modlunky_config.install_dir,
            source=source,
            pack=pack,
        )

    def render(self):
        source = self.file_chooser_frame.file_chooser_var.get()
        dest = self.file_chooser_frame2.file_chooser_var.get()
        if source and dest:
            self.button_install["state"] = tk.NORMAL
        else:
            self.button_install["state"] = tk.DISABLED

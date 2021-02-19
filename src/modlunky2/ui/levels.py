import logging
import os
import os.path
import random
import tkinter as tk
import tkinter.font as font
import tkinter.messagebox as tkMessageBox
from tkinter import filedialog, ttk
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageTk

from modlunky2.constants import BASE_DIR
from modlunky2.ui.widgets import LevelsTree, RulesTree, ScrollableFrame, Tab
from modlunky2.sprites import SpelunkySpriteFetcher

from modlunky2.levels import LevelFile
from modlunky2.levels.tile_codes import VALID_TILE_CODES

logger = logging.getLogger("modlunky2")


class LevelsTab(Tab):
    def __init__(self, tab_control, install_dir, *args, **kwargs): # Loads editor start screen ##############################################################################################
        super().__init__(tab_control, *args, **kwargs)
        self.last_selected_room = None
        # TODO: Get actual resolution
        self.screen_width = 1290
        self.screen_height = 720
        self.extracts_mode = True
        self.dual_mode = False
        self.tab_control = tab_control
        self.install_dir = install_dir
        self.textures_dir = install_dir / "Mods/Extracted/Data/Textures"
        self._sprite_fetcher = SpelunkySpriteFetcher(self.install_dir / "Mods/Extracted")


        self.lvl_editor_start_canvas = tk.Canvas(self)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.lvl_editor_start_canvas.grid(row=0, column=0, columnspan=2, sticky="nswe")
        self.lvl_editor_start_canvas.columnconfigure(0, weight=1)
        self.lvl_editor_start_canvas.rowconfigure(0, weight=1)

        self.extracts_path = self.install_dir / "Mods" / "Extracted" / "Data" / "Levels"
        self.overrides_path = self.install_dir / "Mods" / "Overrides"

        self.welcome_label = tk.Label(
            self.lvl_editor_start_canvas,
            text=(
                "Welcome to the Spelunky 2 Level Editor! "
                "Created by JackHasWifi with lots of help from "
                "Garebear, Fingerspit, Wolfo, and the community\n\n "
                "NOTICE: Saving when viewing extracts will save the "
                "changes to a new file in overrides.\n"
                "When loading from extracts, if a file exists in overrides,\nit will be loaded from there instead.\n\n"
                "BIGGER NOTICE: Please make backups of your files. This is still in beta stages.."
            ),
            anchor="center",
            bg="black",
            fg="white",
        )
        self.welcome_label.grid(row=0, column=0, sticky="nswe", ipady=30, padx=(10, 10))

        def select_lvl_folder():
            dirname = filedialog.askdirectory(
                parent=self, initialdir="/", title="Please select a directory"
            )
            if not dirname:
                return
            else:
                self.extracts_mode = False
                self.lvls_path = dirname
                self.load_editor()

        def load_extracts_lvls():
            if os.path.isdir(self.extracts_path):
                self.extracts_mode = True
                self.lvls_path = self.extracts_path
                self.load_editor()

        self.btn_lvl_extracts = ttk.Button(
            self.lvl_editor_start_canvas,
            text="Load From Extracts",
            command=load_extracts_lvls,
        )
        self.btn_lvl_extracts.grid(
            row=1, column=0, sticky="nswe", ipady=30, padx=(20, 20), pady=(10, 1)
        )

        self.btn_lvl_folder = ttk.Button(
            self.lvl_editor_start_canvas,
            text="Load Levels Folder",
            command=select_lvl_folder,
        )
        self.btn_lvl_folder.grid(
            row=2, column=0, sticky="nswe", ipady=30, padx=(20, 20), pady=(10, 10)
        )

    def load_editor(self): # Run when start screen option is selected ############################################### Loads Editor UI ###############################################
        self.save_needed = False
        self.last_selected_file = None
        self.tiles = None
        self.tiles_meta = None
        self.lvl_editor_start_canvas.grid_remove()
        self.columnconfigure(0, minsize=200)  # Column 0 = Level List
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)  # Column 1 = Everything Else
        self.rowconfigure(0, weight=1)  # Row 0 = List box / Label

        # Loads lvl Files
        self.tree_files = ttk.Treeview(
            self, selectmode="browse"
        )  # This tree shows all the lvl files loaded from the chosen dir
        self.tree_files.place(x=30, y=95)
        self.vsb_tree_files = ttk.Scrollbar(
            self, orient="vertical", command=self.tree_files.yview
        )
        self.vsb_tree_files.place(x=30 + 200 + 2, y=95, height=200 + 20)
        self.tree_files.configure(yscrollcommand=self.vsb_tree_files.set)
        self.tree_files["columns"] = ("1",)
        self.tree_files["show"] = "headings"
        self.tree_files.column("1", width=100, anchor="w")
        self.tree_files.heading("1", text="Level Files")
        self.my_list = os.listdir(self.lvls_path)
        self.tree_files.grid(row=0, column=0, rowspan=1, sticky="nswe")
        self.vsb_tree_files.grid(row=0, column=0, sticky="nse")

        for (
            file
        ) in (
            self.my_list
        ):  # Loads list of all the lvl files in the left farthest treeview
            if str(file).endswith(".lvl"):
                self.tree_files.insert("", "end", values=str(file), text=str(file))

        # Seperates Level Rules and Level Editor into two tabs
        self.tab_control = ttk.Notebook(self)
        self.tab_control.grid(row=0, column=1, rowspan=3, sticky="nwse")

        self.tab1 = ttk.Frame(self.tab_control)  # Tab 1 shows a lvl files rules
        self.tab2 = ttk.Frame(self.tab_control)  # Tab 2 is the actual level editor

        self.button_back = tk.Button(
            self, text="Go Back", bg="black", fg="white", command=self.go_back
        )
        self.button_back.grid(row=1, column=0, sticky="nswe")

        self.button_save = tk.Button(
            self,
            text="Save",
            bg="purple",
            fg="white",
            command=self.save_changes,
        )
        self.button_save.grid(row=2, column=0, sticky="nswe")

        self.tab_control.add(  # Rules Tab ######################################################################################################
            self.tab1, text="Rules"
        )

        self.tab1.columnconfigure(0, weight=1)  # Column 1 = Everything Else
        self.tab1.rowconfigure(0, weight=1)  # Row 0 = List box / Label

        self.tree = RulesTree(
            self.tab1, selectmode="browse"
        )  # This tree shows rules parses from the lvl file
        self.tree.bind("<Double-1>", lambda e: self.on_double_click(self.tree))
        self.tree.place(x=30, y=95)
        # style = ttk.Style(self)
        self.vsb = ttk.Scrollbar(self.tab1, orient="vertical", command=self.tree.yview)
        self.vsb.place(x=30 + 200 + 2, y=95, height=200 + 20)
        self.tree.configure(yscrollcommand=self.vsb.set)
        self.tree["columns"] = ("1", "2", "3")
        self.tree["show"] = "headings"
        self.tree.column("1", width=100, anchor="w")
        self.tree.column("2", width=10, anchor="w")
        self.tree.column("3", width=100, anchor="w")
        self.tree.heading("1", text="Entry")
        self.tree.heading("2", text="Value")
        self.tree.heading("3", text="Notes")
        self.tree.grid(row=0, column=0, sticky="nwse")
        self.vsb.grid(row=0, column=1, sticky="nse")

        self.tab_control.add(  # Level Editor Tab ###############################################################################################
            self.tab2, text="Level Editor"
        )
        self.tab2.columnconfigure(0, minsize=200)  # Column 0 = Level List
        self.tab2.columnconfigure(1, weight=1)  # Column 1 = Everything Else
        self.tab2.rowconfigure(2, weight=1)  # Row 0 = List box / Label

        self.tree_levels = ttk.Treeview(
            self.tab2, selectmode="browse"
        )  # This tree shows the rooms in the level editor
        self.tree_levels.place(x=30, y=95)
        self.vsb_tree_levels = ttk.Scrollbar(
            self.tab2, orient="vertical", command=self.tree_levels.yview
        )
        self.vsb_tree_levels.place(x=30 + 200 + 2, y=95, height=200 + 20)
        self.tree_levels.configure(yscrollcommand=self.vsb_tree_levels.set)
        self.my_list = os.listdir(
            self.install_dir / "Mods" / "Extracted" / "Data" / "Levels"
        )
        self.tree_levels.grid(row=0, column=0, rowspan=5, sticky="nswe")
        self.vsb_tree_levels.grid(row=0, column=0, rowspan=5, sticky="nse")

        self.mag = 50  # the size of each tiles in the grid; 50 is optimal
        self.rows = (
            15  # default values, could be set to none and still work I think lol
        )
        self.cols = (
            15  # default values, could be set to none and still work I think lol
        )

        self.canvas_grids = tk.Canvas(  # this is the main level editor grid
            self.tab2,
            bg="#292929",
        )
        self.canvas_grids.grid(row=0, column=1, rowspan=4, columnspan=7, sticky="nwse")

        self.canvas_grids.columnconfigure(0, weight=1)
        self.canvas_grids.rowconfigure(0, weight=1)

        self.scrollable_canvas_frame = tk.Frame(self.canvas_grids, bg="#343434")

        # offsets the screen so user can freely scroll around work area
        self.scrollable_canvas_frame.columnconfigure(
            0, minsize=int(int(self.screen_width) / 2)
        )
        self.scrollable_canvas_frame.columnconfigure(1, weight=1)
        self.scrollable_canvas_frame.columnconfigure(2, minsize=50)
        self.scrollable_canvas_frame.columnconfigure(
            4, minsize=int(int(self.screen_width) / 2)
        )
        self.scrollable_canvas_frame.rowconfigure(
            0, minsize=int(int(self.screen_height) / 2)
        )
        self.scrollable_canvas_frame.rowconfigure(1, weight=1)
        self.scrollable_canvas_frame.rowconfigure(2, minsize=100)
        self.scrollable_canvas_frame.rowconfigure(2, minsize=100)
        self.scrollable_canvas_frame.rowconfigure(
            4, minsize=int(int(self.screen_height) / 2)
        )

        self.scrollable_canvas_frame.grid(row=0, column=0, sticky="nwes")

        self.foreground_label = tk.Label(
            self.scrollable_canvas_frame,
            text="Foreground Area",
            fg="white",
            bg="#343434",
        )
        self.foreground_label.grid(row=2, column=1, sticky="nwse")
        self.foreground_label.grid_remove()

        self.background_label = tk.Label(
            self.scrollable_canvas_frame,
            text="Background Area",
            fg="white",
            bg="#343434",
        )
        self.background_label.grid(row=2, column=3, sticky="nwse")
        self.background_label.grid_remove()

        self.vbar = ttk.Scrollbar(
            self.tab2, orient="vertical", command=self.canvas_grids.yview
        )
        self.vbar.grid(row=0, column=2, rowspan=4, columnspan=6, sticky="nse")
        self.hbar = ttk.Scrollbar(
            self.tab2, orient="horizontal", command=self.canvas_grids.xview
        )
        self.hbar.grid(row=0, column=1, rowspan=4, columnspan=7, sticky="wes")

        self.canvas_grids.config(
            xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set
        )
        x0 = self.canvas_grids.winfo_screenwidth() / 2
        y0 = self.canvas_grids.winfo_screenheight() / 2
        self.canvas_grids.create_window(
            (x0, y0), window=self.scrollable_canvas_frame, anchor="center"
        )
        self.scrollable_canvas_frame.bind(
            "<Configure>",
            lambda e: self.canvas_grids.configure(
                scrollregion=self.canvas_grids.bbox("all")
            ),
        )

        self.canvas = tk.Canvas(  # this is the main level editor grid
            self.scrollable_canvas_frame,
            bg="#343434",
        )
        self.canvas.grid(row=1, column=1)
        self.canvas.grid_remove()
        self.canvas_dual = tk.Canvas(  # this is for dual level, it shows the back area
            self.scrollable_canvas_frame,
            width=0,
            bg="yellow",
        )
        self.canvas_dual.grid(row=1, column=3, padx=(0, 50))
        self.canvas_dual.grid_remove()  # hides it for now
        self.dual_mode = False

        self.tile_pallete = ScrollableFrame(  # the tile palletes are loaded into here as buttons with their image as a tile and txt as their value to grab when needed
            self.tab2, text="Tile Pallete", width=50
        )
        self.tile_pallete.grid(row=2, column=8, columnspan=4, rowspan=3, sticky="swne")
        self.tile_pallete.scrollable_frame["width"] = 50

        self.tile_label = tk.Label(
            self.tab2,
            text="Primary Tile:",
        )  # shows selected tile. Important because this is used for more than just user convenience; we can grab the currently used tile here
        self.tile_label.grid(row=0, column=9, columnspan=1, sticky="we")
        self.tile_label_secondary = tk.Label(
            self.tab2,
            text="Secondary Tile:",
        )  # shows selected tile. Important because this is used for more than just user convenience; we can grab the currently used tile here
        self.tile_label_secondary.grid(row=1, column=9, columnspan=1, sticky="we")

        self.button_tilecode_del = tk.Button(
            self.tab2,
            text="Del",
            bg="red",
            fg="white",
            width=10,
            command=self.del_tilecode,
        )
        self.button_tilecode_del.grid(row=0, column=8, sticky="e")
        self.button_tilecode_del["state"] = tk.DISABLED

        self.button_tilecode_del_secondary = tk.Button(
            self.tab2,
            text="Del",
            bg="red",
            fg="white",
            width=10,
            command=self.del_tilecode_secondary,
        )
        self.button_tilecode_del_secondary.grid(row=1, column=8, sticky="e")
        self.button_tilecode_del_secondary["state"] = tk.DISABLED

        self.img_sel = ImageTk.PhotoImage(
            Image.open(BASE_DIR / "static/images/tilecodetextures.png") ########################################### set selected img
        )
        self.panel_sel = tk.Label(
            self.tab2, image=self.img_sel, width=50
        )  # shows selected tile image
        self.panel_sel.grid(row=0, column=10)
        self.panel_sel_secondary = tk.Label(
            self.tab2, image=self.img_sel, width=50
        )  # shows selected tile image
        self.panel_sel_secondary.grid(row=1, column=10)

        self.combobox = ttk.Combobox(self.tab2, height=20)
        self.combobox.grid(row=4, column=8, columnspan=1, sticky="nswe")
        self.combobox["state"] = tk.DISABLED
        self.combobox_alt = ttk.Combobox(self.tab2, height=40)
        self.combobox_alt.grid(row=4, column=9, columnspan=1, sticky="nswe")
        self.combobox_alt.grid_remove()
        self.combobox_alt["state"] = tk.DISABLED

        self.scale = tk.Scale(
            self.tab2, from_=0, to=100, orient=tk.HORIZONTAL, command=self.update_value
        )  # scale for the percent of a selected tile
        self.scale.grid(row=3, column=8, columnspan=2, sticky="we")
        self.scale.set(100)
        self.scale["state"] = tk.DISABLED

        self.button_tilecode_add = tk.Button(
            self.tab2,
            text="Add TileCode",
            bg="yellow",
            command=lambda: self.add_tilecode(
                str(self.combobox.get()), str(self.scale.get()), self.combobox_alt.get()
            ),
        )
        self.button_tilecode_add.grid(
            row=3, column=10, rowspan=2, columnspan=2, sticky="nswe"
        )

        self.var_ignore = tk.IntVar()
        self.var_flip = tk.IntVar()
        self.var_only_flip = tk.IntVar()
        self.var_dual = tk.IntVar()
        self.var_rare = tk.IntVar()
        self.var_hard = tk.IntVar()
        self.var_liquid = tk.IntVar()
        self.checkbox_ignore = ttk.Checkbutton(self.tab2, text='Ignore',var=self.var_ignore, onvalue=1, offvalue=0)
        self.checkbox_ignore.grid(row=4, column=1, sticky="w")
        self.checkbox_flip = ttk.Checkbutton(self.tab2, text='Flip',var=self.var_flip, onvalue=1, offvalue=0)
        self.checkbox_flip.grid(row=4, column=2, sticky="w")
        self.checkbox_only_flip = ttk.Checkbutton(self.tab2, text='Only Flip',var=self.var_only_flip, onvalue=1, offvalue=0)
        self.checkbox_only_flip.grid(row=4, column=3, sticky="w")
        self.checkbox_rare = ttk.Checkbutton(self.tab2, text='Rare',var=self.var_rare, onvalue=1, offvalue=0)
        self.checkbox_rare.grid(row=4, column=5, sticky="w")
        self.checkbox_hard = ttk.Checkbutton(self.tab2, text='Hard',var=self.var_hard, onvalue=1, offvalue=0)
        self.checkbox_hard.grid(row=4, column=6, sticky="w")
        self.checkbox_liquid = ttk.Checkbutton(self.tab2, text='Optimize Liquids',var=self.var_liquid, onvalue=1, offvalue=0)
        self.checkbox_liquid.grid(row=4, column=4, sticky="w")
        self.checkbox_dual = ttk.Checkbutton(self.tab2, text='Dual',var=self.var_dual, onvalue=1, offvalue=0) #, command=print_selection
        self.checkbox_dual.grid(row=4, column=7, sticky="w")

        # the tilecodes are in the same order as the tiles in the image(50x50, left to right)
        self.texture_images = []
        file_tile_codes = BASE_DIR / "tilecodes.txt"
        tile_lines = file_tile_codes.read_text(encoding="utf8").splitlines()
        count = 0
        count_total = 0
        x = 99
        y = 0
        # color_base = int(random.random())
        self.uni_tile_code_list = []
        self.tile_pallete_ref = []
        #self.panel_sel["image"] = self.texture_images[0]
        #self.tile_label["text"] = "Primary Tile: " + r"\?empty a"
        #self.panel_sel_secondary["image"] = self.texture_images[0]
        #self.tile_label_secondary["text"] = "Secondary Tile: " + r"\?empty a"

        self.draw_mode = [] # slight adjustments of textures for tile preview # 1 = resize by half # 2 = lower down half tile # 3 draw from bottom get_codes_left
        self.draw_mode.append(["anubis", 2])
        self.draw_mode.append(["crushtraplarge", 2])
        self.draw_mode.append(["mummy", 2])
        self.draw_mode.append(["lamassu", 2])
        self.draw_mode.append(["madametusk", 2])
        self.draw_mode.append(["cookfire", 1])
        self.draw_mode.append(["giant_frog", 3])

        def canvas_click(event, canvas):  # when the level editor grid is clicked
            # Get rectangle diameters
            col_width = self.mag
            row_height = self.mag
            col = 0
            row = 0
            if canvas == self.canvas_dual:
                col = ((event.x + int(self.canvas["width"])) + col_width) // col_width
                row = event.y // row_height
            else:
                # Calculate column and row number
                col = event.x // col_width
                row = event.y // row_height
            # If the tile is not filled, create a rectangle
            if self.dual_mode:
                if int(col) == int((len(self.tiles[0]) - 1) / 2):
                    print("Middle of dual detected; not tile placed")
                    return

            canvas.delete(self.tiles[int(row)][int(col)])
            self.tiles[row][col] = canvas.create_image(
                int(col) * self.mag,
                int(row) * self.mag,
                image=self.panel_sel["image"],
                anchor="nw",
            )
            self.tiles_meta[row][col] = self.tile_label["text"].split(" ", 4)[3]
            print(
                str(self.tiles_meta[row][col])
                + " replaced with "
                + self.tile_label["text"].split(" ", 4)[3]
            )
            self.remember_changes()  # remember changes made

        def canvas_click_secondary(
            event, canvas
        ):  # when the level editor grid is clicked
            # Get rectangle diameters
            col_width = self.mag
            row_height = self.mag
            col = 0
            row = 0
            if canvas == self.canvas_dual:
                col = ((event.x + int(self.canvas["width"])) + col_width) // col_width
                row = event.y // row_height
            else:
                # Calculate column and row number
                col = event.x // col_width
                row = event.y // row_height
            # If the tile is not filled, create a rectangle
            if self.dual_mode:
                if int(col) == int((len(self.tiles[0]) - 1) / 2):
                    print("Middle of dual detected; not tile placed")
                    return

            canvas.delete(self.tiles[int(row)][int(col)])
            self.tiles[row][col] = canvas.create_image(
                int(col) * self.mag,
                int(row) * self.mag,
                image=self.panel_sel_secondary["image"],
                anchor="nw",
            )
            self.tiles_meta[row][col] = self.tile_label_secondary["text"].split(" ", 4)[
                3
            ]
            print(
                str(self.tiles_meta[row][col])
                + " replaced with "
                + self.tile_label["text"].split(" ", 4)[3]
            )
            self.remember_changes()  # remember changes made

        self.canvas.bind("<Button-1>", lambda event: canvas_click(event, self.canvas))
        self.canvas.bind(
            "<B1-Motion>", lambda event: canvas_click(event, self.canvas)
        )  # These second binds are so the user can hold down their mouse button when painting tiles
        self.canvas.bind(
            "<Button-3>", lambda event: canvas_click_secondary(event, self.canvas)
        )
        self.canvas.bind(
            "<B3-Motion>", lambda event: canvas_click_secondary(event, self.canvas)
        )  # These second binds are so the user can hold down their mouse button when painting tiles
        self.canvas_dual.bind(
            "<Button-1>", lambda event: canvas_click(event, self.canvas_dual)
        )
        self.canvas_dual.bind(
            "<B1-Motion>", lambda event: canvas_click(event, self.canvas_dual)
        )
        self.canvas_dual.bind(
            "<Button-3>", lambda event: canvas_click_secondary(event, self.canvas_dual)
        )
        self.canvas_dual.bind(
            "<B3-Motion>", lambda event: canvas_click_secondary(event, self.canvas_dual)
        )

        def tree_filesitemclick(_event):
            if self.save_needed and self.last_selected_file is not None:
                msg_box = tk.messagebox.askquestion(
                    "Continue?",
                    "You have unsaved changes to "
                    + str(self.tree_files.item(self.last_selected_file, option="text"))
                    + "\nContinue without saving?",
                    icon="warning",
                )
                if msg_box == "yes":
                    self.save_needed = False
                    print("Entered new files witout saving")
                else:
                    self.tree_files.selection_set(self.last_selected_file)
                    return
            item_text = ""
            self.canvas.delete("all")
            self.canvas_dual.delete("all")
            self.canvas.grid_remove()
            self.canvas_dual.grid_remove()
            self.foreground_label.grid_remove()
            self.background_label.grid_remove()
            for item in self.tree_files.selection():
                self.last_selected_file = item
                item_text = self.tree_files.item(item, "text")
                self.read_lvl_file(item_text)

        self.tree_files.bind("<ButtonRelease-1>", tree_filesitemclick)

    def tile_pick(
        self, event, button_row, button_col
    ):  # When a tile is selected from the tile pallete
        selected_tile = self.tile_pallete.scrollable_frame.grid_slaves(
            button_row, button_col
        )[0]
        self.panel_sel["image"] = selected_tile["image"]
        self.tile_label["text"] = "Primary Tile: " + selected_tile["text"]

    def tile_pick_secondary(
        self, event, button_row, button_col
    ):  # When a tile is selected from the tile pallete
        selected_tile = self.tile_pallete.scrollable_frame.grid_slaves(
            button_row, button_col
        )[0]
        self.panel_sel_secondary["image"] = selected_tile["image"]
        self.tile_label_secondary["text"] = "Secondary Tile: " + selected_tile["text"]

    def get_codes_left(self):
        codes = ""
        for code in self.usable_codes:
            codes += str(code)
        print(str(len(self.usable_codes)) + " codes left (" + codes + ")")

    def save_changes(self):
        if self.save_needed:
            file_content = ""
            skip_line = False
            for entry in self.tree.get_children():
                values = self.tree.item(entry)["values"]
                if str(values[0]) == "COMMENT":
                    if not skip_line:
                        file_content += str(values[2])
                    else:
                        skip_line = False
                    if (
                        str(values[0]) == "//"
                        or str(values[0]).startswith("// !")
                        or str(values[0]).startswith("// S")
                    ):
                        file_content += "\n"
                    if str(values[2]).startswith("//  TILE CODES"):
                        file_content += "// ------------------------------"
                        for tilecode in self.tile_pallete_ref_in_use:
                            file_content += "\n" + str(tilecode[0])
                        skip_line = True
                        file_content += "\n"
                else:
                    file_content += (
                        str(values[0])
                        + " "
                        + str(values[1])
                        + " "
                        + str(values[2])
                        + "\n"
                    )

            file_content += "\n"
            for room_parent in self.tree_levels.get_children():
                file_content += "\n////////////////////////////////////////////////////////////////////////////////\n"
                file_content += str(self.tree_levels.item(room_parent)["text"])
                file_content += "\n////////////////////////////////////////////////////////////////////////////////\n"
                for room in self.tree_levels.get_children(room_parent):
                    room_check = self.tree_levels.item(room)["text"]
                    if room_check == "room" or room_check == "room (edited)":
                        room_data = self.tree_levels.item(room, option="values")

                        list_to_str = "\n".join(
                            [str(save_row) for save_row in room_data]
                        )
                        file_content += "\n" + list_to_str + "\n"
            path = None
            if not self.extracts_mode:
                path = (
                    self.lvls_path
                    + "/"
                    + str(self.tree_files.item(self.last_selected_file, option="text"))
                )
            else:
                print("adding to overrides")
                path = (
                    self.install_dir
                    / "Mods"
                    / "Overrides"
                    / str(self.tree_files.item(self.last_selected_file, option="text"))
                )
            f = open(path, "w", encoding= 'cp1252')
            f.write(file_content)
            f.close()
            self.save_needed = False

            print("Saved")
        else:
            print("No changes to save")

    def remember_changes(self):  # remembers changes made to rooms
        try:
            item_iid = self.tree_levels.selection()[0]
            parent_iid = self.tree_levels.parent(item_iid)  # gets selected room
            if parent_iid:
                self.canvas.delete("all")
                self.canvas_dual.delete("all")
                new_room_data = ""
                if self.var_dual.Get():
                    new_room_data += "\n" + "\!dual"
                if self.var_flip.Get():
                    new_room_data += "\n" + "\!flip"
                if self.var_only_flip.Get():
                    new_room_data += "\n" + "\!onlyflip"
                if self.var_rare.Get():
                    new_room_data += "\n" + "\!rare"
                if self.var_hard.Get():
                    new_room_data += "\n" + "\!hard"
                if self.var_liquid.Get():
                    new_room_data += "\n" + "\!liquid"
                if self.var_ignore.Get():
                    new_room_data += "\n" + "\!ignore"

                for row in self.tiles_meta:
                    if new_room_data != "":
                        new_room_data += "\n"
                    for block in row:
                        if str(block) == "None":
                            new_room_data += str(" ")
                        else:
                            new_room_data += str(block)
                room_save = []
                for line in new_room_data.split("\n", 100):
                    room_save.append(line)
                # Put it back in with the upated values
                edited = self.tree_levels.insert(
                    parent_iid,
                    self.tree_levels.index(item_iid),
                    text="room (edited)",
                    values=room_save,
                )
                # Remove it from the tree
                self.tree_levels.delete(item_iid)
                self.tree_levels.selection_set(edited)
                self.room_select(None)
                print("temp saved: \n" + new_room_data)
                print("Changes remembered!")
                self.save_needed = True
        except Exception as err:  # pylint: disable=broad-except
            print("No room to temp save " + str(err))

    def del_tilecode(self):
        msg_box = tk.messagebox.askquestion(
            "Delete Tilecode?",
            "Are you sure you want to delete this Tilecode?\nAll of its placements will be replaced with air",
            icon="warning",
        )
        if msg_box == "yes":
            tile_id = self.tile_label["text"].split(" ", 3)[2]
            tile_code = self.tile_label["text"].split(" ", 3)[3]
            if tile_id == r"\?empty":
                tkMessageBox.showinfo("Uh Oh!", "Can't delete empty!")
                return

            for room_parent in self.tree_levels.get_children():
                for room in self.tree_levels.get_children(room_parent):
                    room_data = []
                    room_name = self.tree_levels.item(room, option="text")
                    room_rows = self.tree_levels.item(room, option="values")
                    for row in room_rows:
                        new_row = ""
                        if not str(row).startswith(r"\!"):
                            for replace_code in row:
                                if replace_code == tile_code:
                                    replace_code = "0"
                                    new_row += "0"
                                else:
                                    new_row += str(replace_code)
                        else:
                            new_row = str(row)
                        room_data.append(new_row)
                    # Put it back in with the upated values
                    edited = self.tree_levels.insert(
                        room_parent,
                        self.tree_levels.index(room),
                        text=str(room_name),
                        values=room_data,
                    )
                    # Remove it from the tree
                    self.tree_levels.delete(room)
                    if room == self.last_selected_room:
                        self.tree_levels.selection_set(edited)
                        self.last_selected_room = edited
                        self.room_select(None)
            print("Replaced " + tile_id + " in all rooms with air/empty")

            self.usable_codes.append(str(tile_code))
            print(
                str(tile_code) + " is now available for use"
            )  # adds tilecode back to list to be reused
            ii = 0
            for id_ in self.tile_pallete_ref_in_use:
                if str(tile_id) == str(
                    id_[0].split(" ", 2)[0]
                ):  # removes tilecode from list in use
                    # self.usable_codes.pop(ii)
                    self.tile_pallete_ref_in_use.remove(id_)
                    print("Deleted " + str(tile_id))
                ii = ii + 1
            self.populate_tilecode_pallete()
            new_selection = self.tile_pallete_ref_in_use[0]
            if str(self.tile_label["text"]).split(" ", 3)[2] == tile_id:
                self.tile_label["text"] = (
                    "Primary Tile: "
                    + str(new_selection[0]).split(" ", 2)[0]
                    + " "
                    + str(new_selection[0]).split(" ", 2)[1]
                )
                self.panel_sel["image"] = new_selection[1]
            if str(self.tile_label_secondary["text"]).split(" ", 3)[2] == tile_id:
                self.tile_label_secondary["text"] = (
                    "Secondary Tile: "
                    + str(new_selection[0]).split(" ", 2)[0]
                    + " "
                    + str(new_selection[0]).split(" ", 2)[1]
                )
                self.panel_sel_secondary["image"] = new_selection[1]

            self.get_codes_left()
            self.save_needed = True
        else:
            return

    def del_tilecode_secondary(self):
        msg_box = tk.messagebox.askquestion(
            "Delete Tilecode?",
            "Are you sure you want to delete this Tilecode?\nAll of its placements will be replaced with air",
            icon="warning",
        )
        if msg_box == "yes":
            tile_id = self.tile_label_secondary["text"].split(" ", 3)[2]
            tile_code = self.tile_label_secondary["text"].split(" ", 3)[3]
            if tile_id == r"\?empty":
                tkMessageBox.showinfo("Uh Oh!", "Can't delete empty!")
                return

            for room_parent in self.tree_levels.get_children():
                for room in self.tree_levels.get_children(room_parent):
                    room_data = []
                    room_name = self.tree_levels.item(room, option="text")
                    room_rows = self.tree_levels.item(room, option="values")
                    for row in room_rows:
                        new_row = ""
                        if not str(row).startswith(r"\!"):
                            for replace_code in row:
                                if replace_code == tile_code:
                                    replace_code = "0"
                                    new_row += "0"
                                else:
                                    new_row += str(replace_code)
                        else:
                            new_row = str(row)
                        room_data.append(new_row)
                    # Put it back in with the upated values
                    edited = self.tree_levels.insert(
                        room_parent,
                        self.tree_levels.index(room),
                        text=str(room_name),
                        values=room_data,
                    )
                    # Remove it from the tree
                    self.tree_levels.delete(room)
                    if room == self.last_selected_room:
                        self.tree_levels.selection_set(edited)
                        self.last_selected_room = edited
                        self.room_select(None)
            print("Replaced " + tile_id + " in all rooms with air/empty")

            self.usable_codes.append(str(tile_code))
            print(
                str(tile_code) + " is now available for use"
            )  # adds tilecode back to list to be reused
            ii = 0
            for id_ in self.tile_pallete_ref_in_use:
                if str(tile_id) == str(
                    id_[0].split(" ", 2)[0]
                ):  # removes tilecode from list in use
                    # self.usable_codes.pop(ii)
                    self.tile_pallete_ref_in_use.remove(id_)
                    print("Deleted " + str(tile_id))
                ii = ii + 1
            self.populate_tilecode_pallete()
            new_selection = self.tile_pallete_ref_in_use[0]
            if str(self.tile_label["text"]).split(" ", 3)[2] == tile_id:
                self.tile_label["text"] = (
                    "Primary Tile: "
                    + str(new_selection[0]).split(" ", 2)[0]
                    + " "
                    + str(new_selection[0]).split(" ", 2)[1]
                )
                self.panel_sel["image"] = new_selection[1]
            if str(self.tile_label_secondary["text"]).split(" ", 3)[2] == tile_id:
                self.tile_label_secondary["text"] = (
                    "Secondary Tile: "
                    + str(new_selection[0]).split(" ", 2)[0]
                    + " "
                    + str(new_selection[0]).split(" ", 2)[1]
                )
                self.panel_sel_secondary["image"] = new_selection[1]

            self.get_codes_left()
            self.save_needed = True
        else:
            return

    def add_tilecode(self, tile, percent, alt_tile):
        usable_code = None

        tile = str(tile.split(" ", 3)[0])
        alt_tile = str(alt_tile.split(" ", 3)[0])  # isolates the id
        new_tile_code = r"\?" + tile

        tile_image = None
        tile_image_alt = None
        if any(
            tile + " " in self.e[0] for self.e in self.tile_pallete_ref
        ):  # compares tile id to tile ids in universal pallete list
            tile_image = self.e[1]

        if int(percent) < 100:
            new_tile_code += "%" + percent
            # Have to use a temporary directory due to TCL/Tkinter is trying to write
            # to a file name, not a file handle, and windows doesn't support sharing the
            # file between processes
            with tempfile.TemporaryDirectory() as tempdir:
                tempdir_path = Path(tempdir)
                temp1 = tempdir_path / "temp1"
                temp2 = tempdir_path / "temp2"
                tile_image._PhotoImage__photo.write(temp1, format="png")

                image1 = Image.open(
                    temp1,
                ).convert("RGBA")
                tile_text = percent + "%"
                if alt_tile != "empty":
                    if any(
                        alt_tile + " " in self.g[0] for self.g in self.tile_pallete_ref
                    ):  # compares tile id to tile ids in pallete list
                        tile_image_alt = self.g[1]
                    new_tile_code += "%" + alt_tile
                    tile_text += "/" + str(100 - int(percent)) + "%"

                    tile_image_alt._PhotoImage__photo.write(temp2)

                    image2 = Image.open(temp2).convert("RGBA")
                    image2.crop([25, 0, 50, 50]).save("temp2.png")
                    image2 = Image.open(temp2).convert("RGBA")

                    offset = (25, 0)
                    image1.paste(image2, offset)
                # make a blank image for the text, initialized to transparent text color
                txt = Image.new("RGBA", (50, 50), (255, 255, 255, 0))

                # get a drawing context
                d = ImageDraw.Draw(txt)

                # draw text, half opacity
                d.text((6, 34), tile_text, fill=(0, 0, 0, 255))
                d.text((4, 34), tile_text, fill=(0, 0, 0, 255))
                d.text((6, 36), tile_text, fill=(0, 0, 0, 255))
                d.text((4, 36), tile_text, fill=(0, 0, 0, 255))
                d.text((5, 35), tile_text, fill=(255, 255, 255, 255))

                out = Image.alpha_composite(image1, txt)
            tile_image = ImageTk.PhotoImage(out)

        if any(
            str(new_tile_code + " ") in str(self.g[0].split(" ", 3)[0]) + " "
            for self.g in self.tile_pallete_ref_in_use
        ):  # compares tile id to tile ids in pallete list
            tkMessageBox.showinfo("Uh Oh!", "You already have that!")
            return

        if len(self.usable_codes) > 0:
            usable_code = self.usable_codes[0]
            i = 0
            for ii in self.usable_codes:
                if ii == usable_code:
                    self.usable_codes.remove(ii)
                i = i + 1
        else:
            tkMessageBox.showinfo(
                "Uh Oh!", "You've reached the tilecode limit; delete some to add more"
            )
            return

        count_row = 0
        count_col = 0
        for i in self.tile_pallete_ref_in_use:
            if count_col == 7:
                count_col = -1
                count_row = count_row + 1
            count_col = count_col + 1

        ref_tile = []
        ref_tile.append(new_tile_code + " " + str(usable_code))
        ref_tile.append(tile_image)
        self.tile_pallete_ref_in_use.append(ref_tile)
        new_tile = tk.Button(
            self.tile_pallete.scrollable_frame,
            text=str(
                new_tile_code + " " + str(usable_code)
            ),  # keep seperate by space cause I use that for splitting
            width=40,
            height=40,
            image=tile_image,
        )
        new_tile.grid(row=count_row, column=count_col)
        new_tile.bind(
            "<Button-1>",
            lambda event, r=count_row, c=count_col: self.tile_pick(event, r, c),
        )
        new_tile.bind(
            "<Button-3>",
            lambda event, r=count_row, c=count_col: self.tile_pick_secondary(
                event, r, c
            ),
        )
        self.get_codes_left()
        self.save_needed = True

    def populate_tilecode_pallete(self):
        for (
            widget
        ) in (
            self.tile_pallete.scrollable_frame.winfo_children()
        ):  # resets tile pallete to add them all back without the deleted one
            widget.destroy()
        count_row = 0
        count_col = -1
        for tile_keep in self.tile_pallete_ref_in_use:
            if count_col == 7:
                count_col = -1
                count_row = count_row + 1
            count_col = count_col + 1

            new_tile = tk.Button(
                self.tile_pallete.scrollable_frame,
                text=str(tile_keep[0].split(" ", 2)[0])
                + " "
                + str(
                    tile_keep[0].split(" ", 2)[1]
                ),  # keep seperate by space cause I use that for splitting
                width=40,
                height=40,
                image=tile_keep[1],
            )
            new_tile.grid(row=count_row, column=count_col)
            new_tile.bind(
                "<Button-1>",
                lambda event, r=count_row, c=count_col: self.tile_pick(event, r, c),
            )
            new_tile.bind(
                "<Button-3>",
                lambda event, r=count_row, c=count_col: self.tile_pick_secondary(
                    event, r, c
                ),
            )

    def go_back(self):
        self.lvl_editor_start_canvas.grid()
        self.tab_control.grid_remove()
        self.tree_files.grid_remove()
        # Resets widgets
        self.scale["state"] = tk.DISABLED
        self.combobox["state"] = tk.DISABLED
        self.combobox_alt["state"] = tk.DISABLED
        self.button_tilecode_del["state"] = tk.DISABLED
        self.button_tilecode_del_secondary["state"] = tk.DISABLED
        self.canvas.delete("all")
        self.canvas_dual.delete("all")
        self.canvas.grid_remove()
        self.canvas_dual.grid_remove()
        self.foreground_label.grid_remove()
        self.background_label.grid_remove()
        self.button_back.grid_remove()
        self.button_save.grid_remove()
        self.vsb_tree_files.grid_remove()
        for (
            widget
        ) in (
            self.tile_pallete.scrollable_frame.winfo_children()
        ):  # removes any old tiles that might be there from the last file
            widget.destroy()

    def update_value(self, _event):
        if int(self.scale.get()) == 100:
            self.combobox_alt.grid_remove()
            self.combobox.grid(columnspan=2)
        else:
            self.combobox.grid(columnspan=1)
            self.combobox_alt.grid()

    def _draw_grid(self, cols, rows, canvas, dual):
        # resizes canvas for grids
        canvas["width"] = (self.mag * cols) - 3
        canvas["height"] = (self.mag * rows) - 3

        if not dual:  # applies normal bg image settings to main grid
            self.cur_lvl_bg_path = (
                self.lvl_bg_path
            )  # store as a temp dif variable so it can switch back to the normal bg when needed

            file_id = self.tree_files.selection()[0]
            room_item = self.tree_levels.selection()[0]
            room_id = self.tree_levels.parent(
                room_item
            )  # checks which room is being opened to see if a special bg is needed
            factor = 1.0  # keeps image the same
            if self.lvl_bg_path == self.textures_dir / "bg_ice.png" and str(
                self.tree_levels.item(room_id, option="text")
            ).startswith(
                r"\.setroom1"
            ):  # mothership rooms are setroom10-1 to setroom13-2
                self.cur_lvl_bg_path = self.textures_dir / "bg_mothership.png"
            elif str(self.tree_files.item(file_id, option="text")).startswith(
                "blackmark"
            ):
                factor = 2.5  # brightens the image for black market
            elif (
                str(self.tree_files.item(file_id, option="text")).startswith("generic")
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "cosmic"
                )
                or str(self.tree_files.item(file_id, option="text")).startswith("duat")
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "palace"
                )
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "ending_hard"
                )
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "challenge_m"
                )
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "challenge_st"
                )
            ):
                factor = 0  # darkens the image for cosmic ocean and duat and others

            image = Image.open(self.cur_lvl_bg_path)
            image = image.resize(
                (int(canvas["width"]), int(canvas["height"])), Image.BILINEAR
            )  ## The (250, 250) is (height, width)
            enhancer = ImageEnhance.Brightness(image)

            self.im_output = enhancer.enhance(factor)

            self.lvl_bg = ImageTk.PhotoImage(self.im_output)
            canvas.create_image(0, 0, image=self.lvl_bg, anchor="nw")
        else:  # applies special image settings if working with dual grid
            self.lvl_bgbg_path = (
                self.lvl_bg_path
            )  # Creates seperate image path variable for bgbg image

            file_id = self.tree_files.selection()[0]
            room_item = self.tree_levels.selection()[0]
            room_id = self.tree_levels.parent(
                room_item
            )  # checks which room is being opened to see if a special bg is needed
            factor = 0.6  # darkens the image
            if self.lvl_bg_path == self.textures_dir / "bg_ice.png":
                if str(self.tree_levels.item(room_id, option="text")).startswith(
                    r"\.mothership"
                ):
                    self.lvl_bgbg_path = self.textures_dir / "bg_mothership.png"
                    factor = 1.0  # keeps image the same
                else:
                    factor = 2.5  # brightens the image for ices caves
            elif str(self.tree_files.item(file_id, option="text")).startswith(
                "blackmark"
            ):
                factor = 2.5  # brightens the image for black market
            elif (
                str(self.tree_files.item(file_id, option="text")).startswith("generic")
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "cosmic"
                )
                or str(self.tree_files.item(file_id, option="text")).startswith("duat")
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "palace"
                )
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "ending_hard"
                )
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "challenge_m"
                )
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "challenge_st"
                )
            ):
                factor = 0  # darkens the image for cosmic ocean and duat and others

            image_dual = Image.open(self.lvl_bgbg_path)
            image_dual = image_dual.resize(
                (int(canvas["width"]), int(canvas["height"])), Image.BILINEAR
            )  ## The (250, 250) is (height, width)
            enhancer = ImageEnhance.Brightness(image_dual)

            self.im_output_dual = enhancer.enhance(factor)

            self.lvl_bgbg = ImageTk.PhotoImage(self.im_output_dual)
            canvas.create_image(0, 0, image=self.lvl_bgbg, anchor="nw")

        # finishes by drawing grid on top
        for i in range(0, cols + 2):
            canvas.create_line(
                (i) * self.mag,
                0,
                (i) * self.mag,
                (rows) * self.mag,
                fill="#F0F0F0",
            )
        for i in range(0, rows):
            canvas.create_line(
                0,
                (i) * self.mag,
                self.mag * (cols + 2),
                (i) * self.mag,
                fill="#F0F0F0",
            )

    def room_select(self, _event):  # Loads room when click if not parent node
        self.dual_mode = False
        item_iid = self.tree_levels.selection()[0]
        parent_iid = self.tree_levels.parent(item_iid)
        if parent_iid:
            self.last_selected_room = item_iid
            self.canvas.delete("all")
            self.canvas_dual.delete("all")
            current_settings = self.tree_levels.item(item_iid, option="values")[0] # Room settings
            current_room = self.tree_levels.item(item_iid, option="values") # Room foreground
            current_room_tiles = []
            current_settings = []

            for cr_line in current_room:
                if str(cr_line).startswith(r"\!"):
                    print("found tag " + str(cr_line))
                    current_settings.append(cr_line)
                else:
                    print("appending " + str(cr_line))
                    current_room_tiles.append(str(cr_line))
                    for char in str(cr_line):
                        if str(char) == " ":
                            self.dual_mode = True

            print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
            print(current_room_tiles)
            print(current_settings)

            if "\!dual" in current_settings:
                self.dual_mode = True
                self.var_dual.set(1)
            else:
                self.dual_mode = False
                self.var_dual.set(0)

            if "\!flip" in current_settings:
                self.var_flip.set(1)
            else:
                self.var_flip.set(0)

            if "\!onlyflip" in current_settings:
                self.var_only_flip.set(1)
            else:
                self.var_only_flip.set(0)

            if "\!ignore" in current_settings:
                self.var_ignore.set(1)
            else:
                self.var_ignore.set(0)

            if "\!rare" in current_settings:
                self.var_rare.set(1)
            else:
                self.var_rare.set(0)

            if "\!hard" in current_settings:
                self.var_hard.set(1)
            else:
                self.var_hard.set(0)

            if "\!liquid" in current_settings:
                self.var_liquid.set(1)
            else:
                self.var_liquid.set(0)


            self.rows = len(current_room_tiles)
            self.cols = len(str(current_room_tiles[0]))

            print(
                str(self.rows)
                + " "
                + str(self.cols)
                + "-------------------------------------------------"
            )

            # self.mag = self.canvas.winfo_height() / self.rows - 30
            if not self.dual_mode:
                self._draw_grid(
                    self.cols, self.rows, self.canvas, False
                )  # cols rows canvas dual(True/False)
                self.canvas_dual["width"] = 0
                self.canvas_dual["height"] = 0
                self.canvas.grid()
                self.canvas_dual.grid_remove()  # hides it for now
                self.foreground_label.grid_remove()
                self.background_label.grid_remove()
            else:
                self.canvas.grid()
                self.canvas_dual.grid()  # brings it back
                self._draw_grid(
                    int((self.cols - 1) / 2), self.rows, self.canvas, False
                )  # cols rows canvas dual(True/False)
                self._draw_grid(
                    int((self.cols - 1) / 2), self.rows, self.canvas_dual, True
                )
                self.foreground_label.grid()
                self.background_label.grid()

            # Create a grid of None to store the references to the tiles
            self.tiles = [
                [None for _ in range(self.cols)] for _ in range(self.rows)
            ]  # tile image displays
            self.tiles_meta = [
                [None for _ in range(self.cols)] for _ in range(self.rows)
            ]  # meta for tile

            currow = -1
            curcol = 0
            for room_row in current_room_tiles:
                curcol = 0
                currow = currow + 1
                tile_image = None
                print(room_row)
                for block in str(room_row):
                    if str(block) != " ":
                        tile_name = ""
                        for pallete_block in self.tile_pallete_ref_in_use:
                            if any(
                                str(" " + block) in str(self.c[0])
                                for self.c in self.tile_pallete_ref_in_use
                            ):
                                tile_image = self.c[1]
                                tile_name = str(self.c[0]).split(" ", 1)[0]
                            else:
                                print(
                                    str(block) + " Not Found"
                                )  # There's a missing tile id somehow
                        if self.dual_mode and curcol > int((self.cols - 1) / 2):
                            xx = int(curcol - ((self.cols - 1) / 2) - 1)
                            x = 0
                            y = 0
                            for tile_name_ref in self.draw_mode:
                                if tile_name == str(tile_name_ref[0]):
                                    x, y = self.adjust_texture_xy(tile_image.width(), tile_image.height(), tile_name_ref[1])
                            self.tiles[currow][curcol] = self.canvas_dual.create_image(
                                xx * self.mag - x,
                                currow * self.mag - y,
                                image=tile_image,
                                anchor="nw",
                            )
                            coords = (
                                xx * self.mag,
                                currow * self.mag,
                                xx * self.mag + 50,
                                currow * self.mag + 50,
                            )
                            self.tiles_meta[currow][curcol] = block
                        else:
                            x = 0
                            y = 0
                            for tile_name_ref in self.draw_mode:
                                if tile_name == str(tile_name_ref[0]):
                                    x, y = self.adjust_texture_xy(tile_image.width(), tile_image.height(), tile_name_ref[1])
                            self.tiles[currow][curcol] = self.canvas.create_image(
                                curcol * self.mag - x,
                                currow * self.mag - y,
                                image=tile_image,
                                anchor="nw",
                            )
                            coords = (
                                curcol * self.mag,
                                currow * self.mag,
                                curcol * self.mag + 50,
                                currow * self.mag + 50,
                            )
                            self.tiles_meta[currow][curcol] = block
                        # print("loaded layer col " + str(curcol) + " " + str(self.c[0]) + " out of " + str(len(str(room_row))))

                    curcol = curcol + 1

    def read_lvl_file(self, lvl):
        self.last_selected_room = None
        self.usable_codes_string = "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~€‚ƒ„…†‡ˆ‰Š‹Œ Ž‘’“”•–—™š›œžŸ¡¢£¤¥¦§¨©ª«¬-®¯°±²³´µ¶·¸¹°»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ"
        self.usable_codes = []
        for code in self.usable_codes_string:
            self.usable_codes.append(code)

        for (
            widget
        ) in (
            self.tile_pallete.scrollable_frame.winfo_children()
        ):  # removes any old tiles that might be there from the last file
            widget.destroy()

        for (
            i
        ) in (
            self.tree.get_children()
        ):  # removes any old rules that might be there from the last file
            self.tree.delete(i)

        self.tree.delete(*self.tree.get_children())
        self.tree_levels.delete(*self.tree_levels.get_children())

        # Enables widgets to use
        self.scale["state"] = tk.NORMAL
        self.combobox["state"] = tk.NORMAL
        self.combobox_alt["state"] = tk.NORMAL
        self.button_tilecode_del["state"] = tk.NORMAL
        self.button_tilecode_del_secondary["state"] = tk.NORMAL

        self.combobox_alt.grid_remove()
        self.scale.set(100)
        self.combobox.set(r"empty")
        self.combobox_alt.set(r"empty")

        self.tree_levels.bind("<ButtonRelease-1>", self.room_select)
        self.tile_pallete_ref_in_use = []

        self.lvl_biome = "cave" # cave by default, depicts what background and sprites will be loaded
        self.lvl_bg_path = self.textures_dir / "bg_cave.png"
        if (lvl.startswith("abzu.lvl")
        or lvl.startswith("lake")
        or lvl.startswith("tide")
        or lvl.startswith("end")
        or lvl.startswith("tiamat")):
            self.lvl_biome = "tidepool"
            self.lvl_bg_path = self.textures_dir / "bg_tidepool.png"
        elif (
            lvl.startswith("babylon")
            or lvl.startswith("hallofu")
        ):
            self.lvl_biome = "babylon"
            self.lvl_bg_path = self.textures_dir / "bg_babylon.png"
        elif lvl.startswith("basecamp"):
            self.lvl_biome = "cave"
        elif lvl.startswith("beehive"):
            self.lvl_biome = "jungle"
            self.lvl_bg_path = self.textures_dir / "bg_beehive.png"
        elif (
            lvl.startswith("blackmark")
            or lvl.startswith("jungle")
            or lvl.startswith("challenge_moon")
        ):
            self.lvl_biome = "jungle"
            self.lvl_bg_path = self.textures_dir / "bg_jungle.png"
        elif (lvl.startswith("challenge_star")
            or lvl.startswith("temple")):
            self.lvl_biome = "temple"
            self.lvl_bg_path = self.textures_dir / "bg_temple.png"
        elif (
            lvl.startswith("challenge_sun")
            or lvl.startswith("sunken")
            or lvl.startswith("hundun")
            or lvl.startswith("ending_hard")
        ):
            self.lvl_biome = "sunken"
            self.lvl_bg_path = self.textures_dir / "bg_sunken.png"
        elif lvl.startswith("city"):
            self.lvl_biome = "gold"
            self.lvl_bg_path = self.textures_dir / "bg_gold.png"
        elif lvl.startswith("egg"):
            self.lvl_biome = "eggplant"
            self.lvl_bg_path = self.textures_dir / "bg_eggplant.png"
        elif lvl.startswith("ice"):
            self.lvl_biome = "ice"
            self.lvl_bg_path = self.textures_dir / "bg_ice.png"
        elif lvl.startswith("olmec"):
            self.lvl_biome = "stone"
            self.lvl_bg_path = self.textures_dir / "bg_stone.png"
        elif lvl.startswith("vlad"):
            self.lvl_biome = "volcano"
            self.lvl_bg_path = self.textures_dir / "bg_vlad.png"
        elif lvl.startswith("volcano"):
            self.lvl_biome = "volcano"
            self.lvl_bg_path = self.textures_dir / "bg_volcano.png"

        if not self.extracts_mode:
            #file1 = open(self.lvls_path + "/" + lvl, 'r', encoding= 'cp1252')
            lvl_path = self.lvls_path + "/" + lvl
        else:
            if (self.overrides_path / lvl).exists():
                print("Found this lvl in overrides; loading it instead")
                lvl_path = self.overrides_path / lvl
            else:
                lvl_path = self.lvls_path / lvl


        levels = [] # Levels to load dependancy tilecodes from
        if not lvl.startswith("base"):
            levels.append(LevelFile.from_path(Path(self.lvls_path / "generic.lvl")))
        if lvl.startswith("base"):
            levels.append(LevelFile.from_path(Path(self.lvls_path / "basecamp.lvl")))
        elif lvl.startswith("cave"):
            levels.append(LevelFile.from_path(Path(self.lvls_path / "dwellingarea.lvl")))
        elif (lvl.startswith("blackmark") or lvl.startswith("beehive") or lvl.startswith("challenge_moon")):
            levels.append(LevelFile.from_path(Path(self.lvls_path / "junglearea.lvl")))
        elif lvl.startswith("vlads"):
            levels.append(LevelFile.from_path(Path(self.lvls_path / "volcanoarea.lvl")))
        elif (lvl.startswith("lake") or lvl.startswith("challenge_star")):
            levels.append(LevelFile.from_path(Path(self.lvls_path / "tidepoolarea.lvl")))
        elif (lvl.startswith("hallofush") or lvl.startswith("challenge_star") or lvl.startswith("babylonarea_1") or lvl.startswith("palace")):
            levels.append(LevelFile.from_path(Path(self.lvls_path / "babylonarea.lvl")))
        elif lvl.startswith("challenge_sun"):
            levels.append(LevelFile.from_path(Path(self.lvls_path / "sunkencityarea.lvl")))
        elif lvl.startswith("end"):
            levels.append(LevelFile.from_path(Path(self.lvls_path / "ending.lvl")))
        levels.append(LevelFile.from_path(Path(lvl_path)))

        for level in levels:
            level_tilecodes = level.tile_codes.all()
            for tilecode in level_tilecodes:
                tilecode_item = []
                tilecode_item.append(str(tilecode.name) + " " + str(tilecode.value))
                print("item: " + tilecode.name + " biome: " + str(self.lvl_biome))
                img = self._sprite_fetcher.get(tilecode.name, str(self.lvl_biome))
                if img is None:
                    img = Image.open(BASE_DIR / "static/images/unknown.png")
                width, height = img.size
                width = int(width/2.65) # 2.65 is the scale to get the typical 128 tile size down to the needed 50
                height = int(height/2.65)

                scale = 1
                if (tilecode.name == "door2" or tilecode.name == "door2_secret"): # for some reason these are sized differently then everything elses typical universal scale
                    width = int(width/2)
                    height = int(height/2)

                if (width < 50 and height < 50): # since theres rounding involved, this makes sure each tile is size correctly by making up for what was rounded off
                    difference = 0
                    if width > height:
                        difference = 50-width
                    else:
                        difference = 50-height

                    width = width + difference
                    height = height + difference

                img = img.resize((width, height), Image.ANTIALIAS)
                tilecode_item.append(ImageTk.PhotoImage(img))


                for i in self.tile_pallete_ref_in_use:
                    if str(i[0]).split(" ", 1)[1] == str(tilecode.value):
                        self.tile_pallete_ref_in_use.remove(i)
                        print("removed " + str(i[0]))

                for i in self.usable_codes:
                    if str(i) == str(tilecode.value):
                        self.usable_codes.remove(i)
                        print("removed " + str(i))

                self.tile_pallete_ref_in_use.append(tilecode_item)
                print("appending " + str(tilecode_item[0]))
        if lvl.startswith("generic"): # adds tilecodes to generic that it relies on yet doesn't provide
            generic_needs = [
                ["4", r"\?push_block"],
                ["t", r"\?treasure"],
                ["1", r"\?floor"],
                ["6", r"\?chunk_air"],
                ["=", r"\?minewood_floor"],
            ]
            for need in generic_needs:
                for code in self.usable_codes:
                    if str(code) == need[0] and not any(
                        need[0] in str(code_in_use[0].split(" ", 3)[1])
                        for code_in_use in self.tile_pallete_ref_in_use
                    ):
                        for i in self.usable_codes:
                            if str(i) == str(need[0]):
                                self.usable_codes.remove(i)
                            i = i + 1
                        tilecode_item = []
                        tilecode_item.append(str(need[0]) + " " + need[1])
                        img = self._sprite_fetcher.get(str(need[1].split(1, "?")[1]), self.lvl_biome)
                        if img is None:
                            img = Image.open(BASE_DIR / "static/images/unknown.png")
                        img = img.resize((50, 50), Image.ANTIALIAS)
                        tilecode_item.append(ImageTk.PhotoImage(img))
                        self.tile_pallete_ref_in_use.append(tilecode_item)
        self.populate_tilecode_pallete()


        level_rules = level.level_settings.all()
        for rules in level_rules:
            self.tree.insert(
                "",
                "end",
                text="L1",
                values=(str(rules.name), str(rules.value), str(rules.comment)),
            )


        level_templates = level.level_templates.all()

        for template in level_templates:
            entry = self.node = self.tree_levels.insert(
                "", "end", text=str(template.name)
            )
            for room in template.chunks:
                room_string = [] #makes room data into string for storing

                for setting in room.settings:
                    room_string.append("\!" + str(setting).split(".", 1)[1].lower())

                i = 0
                for line in room.foreground:
                    foreground = ""
                    background = ""
                    for code in line:
                        foreground+=str(code)
                    if len(room.background)>0:
                        background += " "
                        for code in room.background[i]:
                            background+=str(code)
                    room_string.append(foreground + background)
                    i = i + 1

                self.node = self.tree_levels.insert(
                    entry, "end", values=room_string, text="room"
                )

        #lines = file1.readlines()


    def adjust_texture_xy(event, width, height, mode): # slight adjustments of textures for tile preview # 1 = resize by half # 2 = draw from bottom left # 3 center
        x = 0
        y = 0
        if mode == 1:
            y = (height*-1)/2
        elif mode == 2:
            y = height/2
        elif mode == 3:
            x = width/3.2
            y = height/2
        return x, y

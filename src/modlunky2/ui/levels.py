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

logger = logging.getLogger("modlunky2")


class LevelsTab(Tab):
    def __init__(self, tab_control, install_dir, *args, **kwargs):
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

    def load_editor(self):
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

        self.tab_control.add(  # Rules Tab ----------------------------------------------------
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

        self.tab_control.add(  # Level Editor Tab -------------------------------------------------
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
        self.canvas_grids.grid(row=0, column=1, rowspan=4, columnspan=2, sticky="nwse")

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
        self.vbar.grid(row=0, column=2, rowspan=4, columnspan=1, sticky="nse")
        self.hbar = ttk.Scrollbar(
            self.tab2, orient="horizontal", command=self.canvas_grids.xview
        )
        self.hbar.grid(row=0, column=1, rowspan=4, columnspan=2, sticky="wes")

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
        self.tile_pallete.grid(row=2, column=3, columnspan=4, rowspan=3, sticky="swne")
        self.tile_pallete.scrollable_frame["width"] = 50

        self.tile_label = tk.Label(
            self.tab2,
            text="Primary Tile:",
        )  # shows selected tile. Important because this is used for more than just user convenience; we can grab the currently used tile here
        self.tile_label.grid(row=0, column=4, columnspan=1, sticky="we")
        self.tile_label_secondary = tk.Label(
            self.tab2,
            text="Secondary Tile:",
        )  # shows selected tile. Important because this is used for more than just user convenience; we can grab the currently used tile here
        self.tile_label_secondary.grid(row=1, column=4, columnspan=1, sticky="we")

        self.button_tilecode_del = tk.Button(
            self.tab2,
            text="Del",
            bg="red",
            fg="white",
            width=10,
            command=self.del_tilecode,
        )
        self.button_tilecode_del.grid(row=0, column=3, sticky="e")
        self.button_tilecode_del["state"] = tk.DISABLED

        self.button_tilecode_del_secondary = tk.Button(
            self.tab2,
            text="Del",
            bg="red",
            fg="white",
            width=10,
            command=self.del_tilecode_secondary,
        )
        self.button_tilecode_del_secondary.grid(row=1, column=3, sticky="e")
        self.button_tilecode_del_secondary["state"] = tk.DISABLED

        self.img_sel = ImageTk.PhotoImage(
            Image.open(BASE_DIR / "static/images/tilecodetextures.png")
        )
        self.panel_sel = tk.Label(
            self.tab2, image=self.img_sel, width=50
        )  # shows selected tile image
        self.panel_sel.grid(row=0, column=5)
        self.panel_sel_secondary = tk.Label(
            self.tab2, image=self.img_sel, width=50
        )  # shows selected tile image
        self.panel_sel_secondary.grid(row=1, column=5)

        self.combobox = ttk.Combobox(self.tab2, height=20)
        self.combobox.grid(row=4, column=3, columnspan=1, sticky="nswe")
        self.combobox["state"] = tk.DISABLED
        self.combobox_alt = ttk.Combobox(self.tab2, height=40)
        self.combobox_alt.grid(row=4, column=4, columnspan=1, sticky="nswe")
        self.combobox_alt.grid_remove()
        self.combobox_alt["state"] = tk.DISABLED

        self.scale = tk.Scale(
            self.tab2, from_=0, to=100, orient=tk.HORIZONTAL, command=self.update_value
        )  # scale for the percent of a selected tile
        self.scale.grid(row=3, column=3, columnspan=2, sticky="we")
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
            row=3, column=5, rowspan=2, columnspan=2, sticky="nswe"
        )

        self.tags = tk.Text(
            self.tab2, height=2, width=30, bg="black", fg="white"
        )  # text box for tags each room has like \!dual for example
        self.tags.grid(row=4, column=1, columnspan=2, sticky="we")

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
        base_im = Image.open(BASE_DIR / "static/images/tilecodetextures.png")
        for line in tile_lines:
            line = line.strip()
            self.uni_tile_code_list.append(str(line))
            im = base_im.crop((count * 50, y * 50, 5000 - (x * 50), (1 + y) * 50))
            self.tile_texture = ImageTk.PhotoImage(im)
            self.texture_images.append(self.tile_texture)
            tile_ref = []
            tile_ref.append(line)
            tile_ref.append(self.texture_images[count_total])
            self.tile_pallete_ref.append(tile_ref)
            count = count + 1
            x -= 1
            if (
                count == 100
            ):  # theres a 100 tiles in each row on the image so this lets me know when to start grabbing from the next row
                y += 1
                x = 99
                count = 0
            count_total = count_total + 1
        self.panel_sel["image"] = self.texture_images[0]
        self.tile_label["text"] = "Primary Tile: " + r"\?empty a"
        self.panel_sel_secondary["image"] = self.texture_images[0]
        self.tile_label_secondary["text"] = "Secondary Tile: " + r"\?empty a"

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
            f = open(path, "w")
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
                if len(self.tags.get(1.0, tk.END).split("!", 5)) <= 1:
                    new_room_data = ""
                else:
                    tag_count = -1
                    for tag in self.tags.get(1.0, tk.END).strip().split(" ", 6):
                        if str(tag).startswith(r"\!"):
                            if tag_count >= 0:
                                new_room_data += "\n" + str(tag)
                            else:
                                new_room_data += str(tag)
                        tag_count = tag_count + 1
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

    def read_lvl_file(self, lvl):
        self.last_selected_room = None
        self.usable_codes_string = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ<>?,./;':][{}-=_+()0123456789!@#$%^&*`~"
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

        if not self.extracts_mode:
            file1 = open(self.lvls_path + "/" + lvl)
        else:
            if (self.overrides_path / lvl).exists():
                print("Found this lvl in overrides; loading it instead")
                file1 = open(self.overrides_path / lvl)
            else:
                file1 = open(self.lvls_path / lvl)
        lines = file1.readlines()

        self.lvl_bg_path = self.textures_dir / "bg_cave.png"  # bg of main level grid
        if lvl == "abzu.lvl" or lvl.startswith("lake") or lvl.startswith("tide"):
            self.lvl_bg_path = self.textures_dir / "bg_tidepool.png"
        elif (
            lvl.startswith("babylon")
            or lvl.startswith("hallofu")
            or lvl.startswith("tiamat")
        ):
            self.lvl_bg_path = self.textures_dir / "bg_babylon.png"
        elif lvl.startswith("basecamp"):
            self.lvl_bg_path = self.textures_dir / "bg_cave.png"
        elif lvl.startswith("beehive"):
            self.lvl_bg_path = self.textures_dir / "bg_beehive.png"
        elif (
            lvl.startswith("blackmark")
            or lvl.startswith("jungle")
            or lvl.startswith("challenge_moon")
        ):
            self.lvl_bg_path = self.textures_dir / "bg_jungle.png"
        elif lvl.startswith("challenge_star"):
            self.lvl_bg_path = self.textures_dir / "bg_temple.png"
        elif (
            lvl.startswith("challenge_sun")
            or lvl.startswith("sunken")
            or lvl.startswith("hundun")
        ):
            self.lvl_bg_path = self.textures_dir / "bg_sunken.png"
        elif lvl.startswith("city"):
            self.lvl_bg_path = self.textures_dir / "bg_gold.png"
        elif lvl.startswith("egg"):
            self.lvl_bg_path = self.textures_dir / "bg_eggplant.png"
        elif lvl.startswith("ending_hard"):
            self.lvl_bg_path = self.textures_dir / "bg_cave.png"
        elif lvl.startswith("end"):
            self.lvl_bg_path = self.textures_dir / "bg_cave.png"
        elif lvl.startswith("ice"):
            self.lvl_bg_path = self.textures_dir / "bg_ice.png"
        elif lvl.startswith("olmec"):
            self.lvl_bg_path = self.textures_dir / "bg_stone.png"
        elif lvl.startswith("temple"):
            self.lvl_bg_path = self.textures_dir / "bg_temple.png"
        elif lvl.startswith("vlad"):
            self.lvl_bg_path = self.textures_dir / "bg_vlad.png"
        elif lvl.startswith("volcano"):
            self.lvl_bg_path = self.textures_dir / "bg_volcano.png"

        # Strips the newline character
        self.tree.delete(*self.tree.get_children())
        self.tree_levels.delete(*self.tree_levels.get_children())
        # pointer = 0
        # pointed = False

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
        self.node = self.tree_levels.insert("", "end", text="placeholder")

        def parse_lvl_file(lines, grab_parent_tilecode):
            load_mode = ""
            # blocks = []
            # cur_item = self.tree.focus()
            self.child = None
            self.rooms = []
            pointer = 0
            pointed = False
            # tile_count = 0
            # tl_col = 0
            # color_base = int(random.random())
            self.tile_convert = []
            line_count = 0
            line_total_count = len(lines)

            count = 0
            self.count_col = 0
            self.count_row = 0
            count_total = 0
            x = 99
            # y = 0

            for line in lines:
                line_raw = line
                line = " ".join(line.split())  # remove duplicate spaces
                line = line.strip()
                line_count = line_count + 1
                print("parsing " + line)
                if (
                    line == "// ------------------------------"
                    and not pointed
                    and pointer == 0
                    and load_mode != "Templates"
                    and line
                ):
                    pointer = pointer + 1
                    if not grab_parent_tilecode:
                        self.tree.insert(
                            "",
                            "end",
                            text="L1",
                            values=("COMMENT", "", str(line_raw)),
                        )
                elif pointer == 1 and not pointed and load_mode != "Templates" and line:
                    load_mode = "RoomChances"  # default because its usually at the top
                    pointed = True
                    if line == "// TILE CODES" and line:
                        load_mode = "TileCodes"
                    elif line == "// LEVEL CHANCES" and line:
                        load_mode = "LevelChances"
                    elif line == "// MONSTER CHANCES" and line:
                        load_mode = "MonsterChances"
                    elif (
                        line == "// TEMPLATES"
                        and line
                        or line == "// BASE CAMP (UNLOCKED SURFACE)"
                        and line
                    ):
                        load_mode = "Templates"
                    if not grab_parent_tilecode:
                        self.tree.insert(
                            "",
                            "end",
                            text="L1",
                            values=("COMMENT", "", str(line_raw)),
                        )
                elif (
                    line == "// ------------------------------"
                    and pointer == 1
                    # and load_mode != "Templates"
                    and line
                ):
                    pointer = 0
                    pointed = False
                    if not grab_parent_tilecode:
                        self.tree.insert(
                            "",
                            "end",
                            text="L1",
                            values=("COMMENT", "", str(line_raw)),
                        )
                elif (
                    load_mode == "RoomChances"
                    and not pointed
                    and pointer == 0
                    and line
                    and not grab_parent_tilecode
                ):
                    data = line.split(" ", 2)
                    comment = ""
                    value = ""
                    if len(data) > 1:
                        if str(data[0]) != r"\-size":
                            value = str(data[1])
                        else:
                            value = (
                                str(data[1]) + " " + str(str(data[2]).split("//", 1)[0])
                            )
                    comments = line.split("//", 1)
                    if len(comments) > 1:  # Makes sure a comment even exists
                        comment = "//   " + str(comments[1]).split("//", 2)[0]
                    self.tree.insert(
                        "",
                        "end",
                        text="L1",
                        values=(str(data[0]), str(value), str(comment)),
                    )
                elif load_mode == "TileCodes" and not pointed and pointer == 0 and line:
                    data = line.split(
                        " ", 2
                    )  # [0] = id [1] = tilecode [2] = comment if it exists
                    if not (
                        str(data[0]).startswith("//")
                    ):  # doesn't add tilecodes commented out
                        if not any(
                            " " + str(data[1]) in self.t[0]
                            for self.t in self.tile_pallete_ref_in_use
                        ):  # makes sure the code isn't in use already
                            tile_image = self.tile_pallete_ref[0][1]
                            if any(
                                str(data[0] + " ") in self.d
                                for self.d in self.uni_tile_code_list
                            ):  # compares tilecode id to its universal tilecode counterpart
                                if any(
                                    str(data[0] + " ") in self.b[0]
                                    for self.b in self.tile_pallete_ref
                                ):  # compares tile id to tile ids in pallete list
                                    tile_image = self.b[1]
                                ii = 0
                                for code in self.usable_codes:
                                    if str(data[1]) == str(
                                        code
                                    ):  # this removes the codes from the usable codes list cause it is now taken
                                        self.usable_codes.remove(code)
                                        print(str(code) + " is now taken!")
                                    ii = ii + 1
                                tile_ref = []
                                tile_ref.append(str(data[0]) + " " + str(data[1]))
                                tile_ref.append(tile_image)
                                self.tile_pallete_ref_in_use.append(tile_ref)
                                self.panel_sel["image"] = tile_image
                                self.tile_label["text"] = (
                                    "Primary Tile: " + str(data[0]) + " " + str(data[1])
                                )
                                self.panel_sel_secondary["image"] = tile_image
                                self.tile_label_secondary["text"] = (
                                    "Secondary Tile: "
                                    + str(data[0])
                                    + " "
                                    + str(data[1])
                                )
                            else:
                                try:
                                    if (
                                        len(str(data[0]).split("%", 2)) == 2
                                    ):  # tile with already existing percent
                                        if any(
                                            str(data[0]).split("%", 2)[0] + " "
                                            in self.e[0]
                                            for self.e in self.tile_pallete_ref
                                        ):  # compares tile id to tile ids in pallete list
                                            tile_image = self.e[1]
                                        tile_image._PhotoImage__photo.write("temp.png")
                                        self.ImageTk_image = Image.open(
                                            "temp.png"
                                        ).convert("RGBA")
                                        # make a blank image for the text, initialized to transparent text color
                                        txt = Image.new(
                                            "RGBA",
                                            self.ImageTk_image.size,
                                            (255, 255, 255, 0),
                                        )

                                        # get a drawing context
                                        d = ImageDraw.Draw(txt)

                                        # draw text, half opacity
                                        d.text(
                                            (4, 36),
                                            str(str(data[0]).split("%", 2)[1] + "%"),
                                            fill=(0, 0, 0, 255),
                                        )
                                        d.text(
                                            (6, 36),
                                            str(str(data[0]).split("%", 2)[1] + "%"),
                                            fill=(0, 0, 0, 255),
                                        )
                                        d.text(
                                            (4, 34),
                                            str(str(data[0]).split("%", 2)[1] + "%"),
                                            fill=(0, 0, 0, 255),
                                        )
                                        d.text(
                                            (6, 34),
                                            str(str(data[0]).split("%", 2)[1] + "%"),
                                            fill=(0, 0, 0, 255),
                                        )
                                        d.text(
                                            (5, 35),
                                            str(str(data[0]).split("%", 2)[1] + "%"),
                                            fill=(255, 255, 255, 255),
                                        )

                                        out = Image.alpha_composite(
                                            self.ImageTk_image, txt
                                        )
                                        self.done = ImageTk.PhotoImage(out)
                                        ii = 0
                                        for code in self.usable_codes:
                                            if str(data[1]) == str(
                                                code
                                            ):  # this removes the codes from the usable codes list cause it is now taken
                                                self.usable_codes.remove(code)
                                                print(str(code) + " is now taken!")
                                            ii = ii + 1
                                        tile_ref = []
                                        tile_ref.append(
                                            str(data[0]) + " " + str(data[1])
                                        )
                                        tile_ref.append(self.done)
                                        self.tile_pallete_ref_in_use.append(tile_ref)
                                        self.panel_sel["image"] = tile_image
                                        self.tile_label["text"] = (
                                            "Primary Tile: "
                                            + str(data[0])
                                            + " "
                                            + str(data[1])
                                        )
                                        self.panel_sel_secondary["image"] = tile_image
                                        self.tile_label_secondary["text"] = (
                                            "Secondary Tile: "
                                            + str(data[0])
                                            + " "
                                            + str(data[1])
                                        )
                                        if any(
                                            str(data[0]) + " " in self.e[0]
                                            for self.e in self.tile_pallete_ref_in_use
                                        ):  # compares tile id to tile ids in pallete list
                                            tile_image = self.e[1]
                                    elif (
                                        len(str(data[0]).split("%", 3)) == 3
                                    ):  # tile with already existing percent and alt tile
                                        tile_image = self.tile_pallete_ref[0][1]
                                        if any(
                                            str(data[0]).split("%", 2)[0] + " "
                                            in self.e[0]
                                            for self.e in self.tile_pallete_ref
                                        ):  # compares tile id to tile ids in pallete list
                                            tile_image = self.e[1]
                                        if any(
                                            r"\?" + str(data[0]).split("%", 2)[2] + " "
                                            in self.g[0]
                                            for self.g in self.tile_pallete_ref
                                        ):  # compares tile id to tile ids in pallete list
                                            tile_image_alt = self.g[1]

                                        tile_image._PhotoImage__photo.write("temp.png")
                                        tile_image_alt._PhotoImage__photo.write(
                                            "temp2.png"
                                        )

                                        self.ImageTk_image1 = Image.open(
                                            "temp.png"
                                        ).convert("RGBA")
                                        self.ImageTk_image2 = Image.open(
                                            "temp2.png"
                                        ).convert("RGBA")
                                        self.ImageTk_image2.crop([25, 0, 50, 50]).save(
                                            "temp2.png"
                                        )
                                        self.ImageTk_image2 = Image.open(
                                            "temp2.png"
                                        ).convert("RGBA")

                                        offset = (25, 0)
                                        self.ImageTk_image1.paste(
                                            self.ImageTk_image2, offset
                                        )
                                        # make a blank image for the text, initialized to transparent text color
                                        txt = Image.new(
                                            "RGBA", (50, 50), (255, 255, 255, 0)
                                        )

                                        # get a drawing context
                                        d = ImageDraw.Draw(txt)

                                        # draw text, half opacity
                                        d.text(
                                            (6, 34),
                                            str(
                                                str(data[0]).split("%", 2)[1]
                                                + "%/"
                                                + str(
                                                    100
                                                    - int(str(data[0]).split("%", 2)[1])
                                                )
                                                + "%"
                                            ),
                                            fill=(0, 0, 0, 255),
                                        )
                                        d.text(
                                            (4, 34),
                                            str(
                                                str(data[0]).split("%", 2)[1]
                                                + "%/"
                                                + str(
                                                    100
                                                    - int(str(data[0]).split("%", 2)[1])
                                                )
                                                + "%"
                                            ),
                                            fill=(0, 0, 0, 255),
                                        )
                                        d.text(
                                            (6, 36),
                                            str(
                                                str(data[0]).split("%", 2)[1]
                                                + "%/"
                                                + str(
                                                    100
                                                    - int(str(data[0]).split("%", 2)[1])
                                                )
                                                + "%"
                                            ),
                                            fill=(0, 0, 0, 255),
                                        )
                                        d.text(
                                            (4, 36),
                                            str(
                                                str(data[0]).split("%", 2)[1]
                                                + "%/"
                                                + str(
                                                    100
                                                    - int(str(data[0]).split("%", 2)[1])
                                                )
                                                + "%"
                                            ),
                                            fill=(0, 0, 0, 255),
                                        )
                                        d.text(
                                            (5, 35),
                                            str(
                                                str(data[0]).split("%", 2)[1]
                                                + "%/"
                                                + str(
                                                    100
                                                    - int(str(data[0]).split("%", 2)[1])
                                                )
                                                + "%"
                                            ),
                                            fill=(255, 255, 255, 255),
                                        )

                                        out = Image.alpha_composite(
                                            self.ImageTk_image1, txt
                                        )
                                        self.done = ImageTk.PhotoImage(out)
                                        ii = 0
                                        for code in self.usable_codes:
                                            if str(data[1]) == str(
                                                code
                                            ):  # this removes the codes from the usable codes list cause it is now taken
                                                self.usable_codes.remove(code)
                                                print(str(code) + " is now taken!")
                                            ii = ii + 1
                                        tile_ref = []
                                        tile_ref.append(
                                            str(data[0]) + " " + str(data[1])
                                        )
                                        tile_ref.append(self.done)
                                        self.tile_pallete_ref_in_use.append(tile_ref)
                                        self.panel_sel["image"] = tile_image
                                        self.tile_label["text"] = (
                                            "Primary Tile: "
                                            + str(data[0])
                                            + " "
                                            + str(data[1])
                                        )
                                        self.panel_sel_secondary["image"] = tile_image
                                        self.tile_label_secondary["text"] = (
                                            "Secondary Tile: "
                                            + str(data[0])
                                            + " "
                                            + str(data[1])
                                        )
                                        if any(
                                            str(data[0]) + " " in self.r[0]
                                            for self.r in self.tile_pallete_ref_in_use
                                        ):  # compares tile id to tile ids in pallete list
                                            tile_image = self.r[1]
                                except Exception as err:  # pylint: disable=broad-except
                                    tkMessageBox.showinfo(
                                        "Uh Oh!",
                                        "skipped " + str(data[0]) + "\n" + str(err),
                                    )  # A tilecode id thats missing from the universal database and needs to be added
                                    # structure (id tilecode percent-without-percent-sign second-tile)

                            # new_image = ImageTk.PhotoImage(tile_image)
                            # new_image = new_image.text((10,10), "My Text", font=self.myFont, fill=(255,255,0))
                            if tile_image is not None:
                                count_row = 0
                                count_col = -1
                                for i in self.tile_pallete_ref_in_use:
                                    if count_col == 7:
                                        count_col = -1
                                        count_row = count_row + 1
                                    count_col = count_col + 1

                                new_tile = tk.Button(
                                    self.tile_pallete.scrollable_frame,
                                    text=str(
                                        data[0] + " " + data[1]
                                    ),  # keep seperate by space cause I use that for splitting
                                    width=40,
                                    height=40,
                                    image=tile_image,
                                )
                                new_tile.grid(row=count_row, column=count_col)
                                new_tile.bind(
                                    "<Button-1>",
                                    lambda event, r=count_row, c=count_col: self.tile_pick(
                                        event, r, c
                                    ),
                                )
                                new_tile.bind(
                                    "<Button-3>",
                                    lambda event, r=count_row, c=count_col: self.tile_pick_secondary(
                                        event, r, c
                                    ),
                                )
                                count = count + 1
                                self.count_col = self.count_col + 1
                                x -= 1
                                if self.count_col > 7:
                                    self.count_row = self.count_row + 1
                                    self.count_col = 0
                                count_total = count_total + 1
                elif (
                    load_mode == "LevelChances"
                    and not pointed
                    and pointer == 0
                    and line
                    and not grab_parent_tilecode
                ):
                    data = line.split(" ", 1)
                    comment = ""
                    value = ""
                    if len(data) > 1:
                        value = str(data[1]).split("//", 1)[0]
                    comments = line.split("//", 1)
                    if len(comments) > 1:  # Makes sure a comment even exists
                        comment = "//   " + comments[1]
                    self.tree.insert(
                        "",
                        "end",
                        text="L1",
                        values=(str(data[0]), str(value), str(comment)),
                    )
                elif (
                    load_mode == "MonsterChances"
                    and not pointed
                    and pointer == 0
                    and line
                    and not grab_parent_tilecode
                ):
                    data = line.split(" ", 1)
                    comment = ""
                    value = ""
                    if len(data) > 1:
                        value = str(data[1]).split("//", 1)[0]
                    comments = line.split("//", 1)
                    if len(comments) > 1:  # Makes sure a comment even exists
                        comment = "//   " + comments[1]
                    self.tree.insert(
                        "",
                        "end",
                        text="L1",
                        values=(str(data[0]), str(value), str(comment)),
                    )
                elif load_mode == "Templates" and not grab_parent_tilecode:
                    if line == "/" * 80 and not pointed and pointer == 0:
                        pointer = 1
                    elif not pointed and pointer == 1 and line.startswith(r"\."):
                        if (
                            self.tree_levels.item(self.tree_levels.get_children()[0])[
                                "text"
                            ]
                            == "placeholder"
                        ):
                            self.tree_levels.item(
                                self.tree_levels.get_children()[0],
                                values=line,
                                text=line,
                            )
                        else:
                            self.node = self.tree_levels.insert(
                                "", "end", values=line, text=line
                            )
                        pointed = True
                    elif line == "/" * 80 and pointed and pointer == 1:
                        pointed = False
                        pointer = 0
                    elif line.startswith("//") and not pointed and line:
                        self.tree.insert(
                            "", "end", text="L1", values=("COMMENT", "", line_raw)
                        )
                    elif not line and len(self.rooms) > 0:
                        self.new_room = self.tree_levels.insert(
                            self.node, "end", values=self.rooms, text="room"
                        )
                        self.rooms.clear()
                    elif line == "":
                        pointer = 0
                    elif line_count == line_total_count and len(self.rooms) > 0:
                        if line:
                            self.rooms.append(str(line))
                        self.new_room = self.tree_levels.insert(
                            self.node, "end", values=self.rooms, text="room"
                        )
                        self.rooms.clear()
                    elif line:
                        self.rooms.append(str(line))
                        print(str(line) + " parsed")

            file_id = self.tree_files.selection()[0]
            if str(self.tree_files.item(file_id, option="text")).startswith(
                "generic"
            ):  # adds tilecodes to generic that it relies on yet doesn't provide
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
                            if any(
                                need[1]
                                in str(str(self.universal_code[0]).split(" ", 3)[0])
                                for self.universal_code in self.tile_pallete_ref
                            ):
                                tile_ref = []
                                tile_ref.append(
                                    str(str(self.universal_code[0]).split(" ", 3)[0])
                                    + " "
                                    + need[0]
                                )
                                tile_ref.append(self.universal_code[1])
                                self.tile_pallete_ref_in_use.append(tile_ref)
                                print("Gave generic needed tilecode: " + need[1])
                self.populate_tilecode_pallete()

        parse_lvl_file(lines, False)  # parses to levels contents
        file_id = self.tree_files.selection()[0]
        lines_again = ""
        if str(self.tree_files.item(file_id, option="text")).startswith(
            "blackmark"
        ):  # goes back to grab levels parent data used in game
            if not self.extracts_mode:
                if os.path.isdir(self.lvls_path + "/" + "junglearea.lvl"):
                    lines_again = open(self.lvls_path + "/" + "junglearea.lvl")
                else:
                    print(
                        "local dependancy lvl not found, attempting load from extracts"
                    )
                    lines_again = open(self.extracts_path / "junglearea.lvl")
            else:
                if os.path.isdir(self.overrides_path / "junglearea.lvl"):
                    lines_again = open(self.overrides_path / "junglearea.lvl")
                else:
                    lines_again = open(self.lvls_path / "junglearea.lvl")
            parse_lvl_file(lines_again.readlines(), True)
        elif str(self.tree_files.item(file_id, option="text")).startswith(
            "vlads"
        ) or str(self.tree_files.item(file_id, option="text")).startswith(
            "challenge_moon"
        ):
            if not self.extracts_mode:
                if os.path.isdir(self.lvls_path + "/" + "volcanoarea.lvl"):
                    lines_again = open(self.lvls_path + "/" + "volcanoarea.lvl")
                else:
                    print(
                        "local dependancy lvl not found, attempting load from extracts"
                    )
                    lines_again = open(self.extracts_path / "volcanoarea.lvl")
            else:
                if os.path.isdir(self.overrides_path / "volcanoarea.lvl"):
                    lines_again = open(self.overrides_path / "volcanoarea.lvl")
                else:
                    lines_again = open(self.lvls_path / "volcanoarea.lvl")
            parse_lvl_file(lines_again.readlines(), True)
        elif (
            str(self.tree_files.item(file_id, option="text")).startswith("hallofush")
            or str(self.tree_files.item(file_id, option="text")).startswith(
                "babylonarea_1"
            )
            or str(self.tree_files.item(file_id, option="text")).startswith("palace")
        ):
            if not self.extracts_mode:
                if os.path.isdir(self.lvls_path + "/" + "babylonarea.lvl"):
                    lines_again = open(self.lvls_path + "/" + "babylonarea.lvl")
                else:
                    print(
                        "local dependancy lvl not found, attempting load from extracts"
                    )
                    lines_again = open(self.extracts_path / "babylonarea.lvl")
            else:
                if os.path.isdir(self.overrides_path / "babylonarea.lvl"):
                    lines_again = open(self.overrides_path / "babylonarea.lvl")
                else:
                    lines_again = open(self.lvls_path / "babylonarea.lvl")
            parse_lvl_file(lines_again.readlines(), True)
        elif str(self.tree_files.item(file_id, option="text")).startswith(
            "lake"
        ) or str(self.tree_files.item(file_id, option="text")).startswith(
            "challenge_star"
        ):
            if not self.extracts_mode:
                if os.path.isdir(self.lvls_path + "/" + "tidepoolarea.lvl"):
                    lines_again = open(self.lvls_path + "/" + "tidepoolarea.lvl")
                else:
                    print(
                        "local dependancy lvl not found, attempting load from extracts"
                    )
                    lines_again = open(self.extracts_path / "tidepoolarea.lvl")
            else:
                if os.path.isdir(self.overrides_path / "tidepoolarea.lvl"):
                    lines_again = open(self.overrides_path / "tidepoolarea.lvl")
                else:
                    lines_again = open(self.lvls_path / "tidepoolarea.lvl")
            parse_lvl_file(lines_again.readlines(), True)
        elif str(self.tree_files.item(file_id, option="text")).startswith("basecamp"):
            if not self.extracts_mode:
                if os.path.isdir(self.lvls_path + "/" + "basecamp.lvl"):
                    lines_again = open(self.lvls_path + "/" + "basecamp.lvl")
                else:
                    print(
                        "local dependancy lvl not found, attempting load from extracts"
                    )
                    lines_again = open(self.extracts_path / "basecamp.lvl")
            else:
                if os.path.isdir(self.overrides_path / "basecamp.lvl"):
                    lines_again = open(self.overrides_path / "basecamp.lvl")
                else:
                    lines_again = open(self.lvls_path / "basecamp.lvl")
            parse_lvl_file(lines_again.readlines(), True)
        elif str(self.tree_files.item(file_id, option="text")).startswith(
            "challenge_sun"
        ):
            if not self.extracts_mode:
                if os.path.isdir(self.lvls_path + "/" + "sunkencityarea.lvl"):
                    lines_again = open(self.lvls_path + "/" + "sunkencityarea.lvl")
                else:
                    print(
                        "local dependancy lvl not found, attempting load from extracts"
                    )
                    lines_again = open(self.extracts_path / "sunkencityarea.lvl")
            else:
                if os.path.isdir(self.overrides_path / "sunkencityarea.lvl"):
                    lines_again = open(self.overrides_path / "sunkencityarea.lvl")
                else:
                    lines_again = open(self.lvls_path / "sunkencityarea.lvl")
            parse_lvl_file(lines_again.readlines(), True)
        if not str(self.tree_files.item(file_id, option="text")).startswith(
            "basecamp"
        ) and not str(self.tree_files.item(file_id, option="text")).startswith(
            "generic"
        ):
            if not self.extracts_mode:
                if os.path.isdir(self.lvls_path + "/" + "generic.lvl"):
                    lines_again = open(self.lvls_path + "/" + "generic.lvl")
                else:
                    print(
                        "local dependancy lvl not found, attempting load from extracts"
                    )
                    lines_again = open(self.extracts_path / "generic.lvl")
            else:
                if os.path.isdir(self.overrides_path / "generic.lvl"):
                    lines_again = open(self.overrides_path / "generic.lvl")
                else:
                    lines_again = open(self.lvls_path / "generic.lvl")
            parse_lvl_file(
                lines_again.readlines(), True
            )  # finishes by grabbing parent generics tildecode data

        combo_tile_ids = []
        for tile_info in self.uni_tile_code_list:
            combo_tile_ids.append(str(tile_info).split(" ", 2)[0].replace(r"\?", ""))

        self.combobox["values"] = sorted(combo_tile_ids, key=str.lower)
        self.combobox_alt["values"] = sorted(combo_tile_ids, key=str.lower)
        # if self.tree.item(0, option="text")=="placeholder":
        # tree.delete(0)

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
            current_room = self.tree_levels.item(item_iid, option="values")
            current_room_tiles = []
            tags = ""
            self.tags.delete(1.0, "end")
            for cr_line in current_room:
                if str(cr_line).startswith(r"\!"):
                    print("found tag " + str(cr_line))
                    tags += cr_line + " "
                else:
                    print("appending " + str(cr_line))
                    current_room_tiles.append(str(cr_line))
                    for char in str(cr_line):
                        if str(char) == " ":
                            self.dual_mode = True

            self.tags.insert(1.0, tags)

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
                        for pallete_block in self.tile_pallete_ref_in_use:
                            if any(
                                str(" " + block) in str(self.c[0])
                                for self.c in self.tile_pallete_ref_in_use
                            ):
                                tile_image = self.c[1]
                            else:
                                print(
                                    str(block) + " Not Found"
                                )  # There's a missing tile id somehow
                        if self.dual_mode and curcol > int((self.cols - 1) / 2):
                            x = int(curcol - ((self.cols - 1) / 2) - 1)
                            self.tiles[currow][curcol] = self.canvas_dual.create_image(
                                x * self.mag,
                                currow * self.mag,
                                image=tile_image,
                                anchor="nw",
                            )
                            coords = (
                                x * self.mag,
                                currow * self.mag,
                                x * self.mag + 50,
                                currow * self.mag + 50,
                            )
                            self.tiles_meta[currow][curcol] = block
                        else:
                            self.tiles[currow][curcol] = self.canvas.create_image(
                                curcol * self.mag,
                                currow * self.mag,
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

    def on_double_click(self, tree_view):
        # First check if a blank space was selected
        entry_index = tree_view.focus()
        if entry_index == "":
            return

        # Set up window
        win = tk.Toplevel()
        win.title("Edit Entry")
        win.attributes("-toolwindow", True)
        self.center(win)

        ####
        # Set up the window's other attributes and geometry
        ####

        # Grab the entry's values
        for child in tree_view.get_children():
            if child == entry_index:
                values = tree_view.item(child)["values"]
                break

        col1_lbl = tk.Label(win, text="Entry: ")
        col1_ent = tk.Entry(win)
        col1_ent.insert(0, values[0])  # Default is column 1's current value
        col1_lbl.grid(row=0, column=0)
        col1_ent.grid(row=0, column=1)

        col2_lbl = tk.Label(win, text="Value: ")
        col2_ent = tk.Entry(win)
        col2_ent.insert(0, values[1])  # Default is column 2's current value
        col2_lbl.grid(row=0, column=2)
        col2_ent.grid(row=0, column=3)

        col3_lbl = tk.Label(win, text="Note: ")
        col3_ent = tk.Entry(win)
        col3_ent.insert(0, values[2])  # Default is column 3's current value
        col3_lbl.grid(row=0, column=4)
        col3_ent.grid(row=0, column=5)

        def update_then_destroy():
            if self.confirm_entry(
                tree_view, col1_ent.get(), col2_ent.get(), col3_ent.get()
            ):
                win.destroy()

        ok_button = tk.Button(win, text="Ok")
        ok_button.bind("<Button-1>", lambda e: update_then_destroy())
        ok_button.grid(row=1, column=2)

        cancel_button = tk.Button(win, text="Cancel")
        cancel_button.bind("<Button-1>", lambda c: win.destroy())
        cancel_button.grid(row=1, column=4)

    def confirm_entry(self, tree_view, entry1, entry2, entry3):
        ####
        # Whatever validation you need
        ####

        # Grab the current index in the tree
        current_index = tree_view.index(tree_view.focus())

        # Remove it from the tree
        self.delete_current_entry(tree_view)

        # Put it back in with the upated values
        tree_view.insert("", current_index, values=(entry1, entry2, entry3))
        self.save_needed = True

        return True

    def delete_current_entry(self, tree_view):
        curr = tree_view.focus()

        if curr == "":
            return

        tree_view.delete(curr)

    def center(self, toplevel):
        toplevel.update_idletasks()

        # Tkinter way to find the screen resolution
        # screen_width = toplevel.winfo_screenwidth()
        # screen_height = toplevel.winfo_screenheight()

        # find the screen resolution
        screen_width = int(self.screen_width)
        screen_height = int(self.screen_height)

        size = tuple(int(_) for _ in toplevel.geometry().split("+")[0].split("x"))
        x = screen_width / 2 - size[0] / 2
        y = screen_height / 2 - size[1] / 2

        toplevel.geometry("+%d+%d" % (x, y))

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

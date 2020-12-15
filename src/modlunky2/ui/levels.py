import logging
import os
import random
import tkinter as tk
import tkinter.messagebox as tkMessageBox
from tkinter import filedialog, ttk

from PIL import Image, ImageTk

from modlunky2.constants import BASE_DIR
from modlunky2.ui.widgets import ScrollableFrame, Tab

logger = logging.getLogger("modlunky2")


class LevelsTab(Tab):
    def __init__(self, tab_control, install_dir, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.install_dir = install_dir
        self.textures_dir = install_dir / "Mods/Extracted/Data/Textures"

        self.lvl_editor_start_canvas = tk.Canvas(self)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.lvl_editor_start_canvas.grid(row=0, column=0, sticky="nswe")
        self.lvl_editor_start_canvas.columnconfigure(0, weight=1)
        self.lvl_editor_start_canvas.rowconfigure(0, weight=1)

        self.welcome_label = tk.Label(
            self.lvl_editor_start_canvas,
            text=(
                "Welcome to the Spelunky 2 Level Editor! "
                "created by JackHasWifi with lots of help from "
                "garebear, fingerspit, wolfo, and the community\n\n "
                "NOTICE: Saving when viewing extracts will save the "
                "changes to a new file in overrides"
            ),
            anchor="center",
        )
        self.welcome_label.grid(row=0, column=0, sticky="nswe", ipady=30, padx=(10, 10))

        def select_lvl_folder():
            dirname = filedialog.askdirectory(
                parent=self, initialdir="/", title="Please select a directory"
            )
            if not dirname:
                return
            else:
                self.load_editor(dirname)

        def load_extracts_lvls():
            extracts_path = self.install_dir / "Mods" / "Extracted" / "Data" / "Levels"
            if os.path.isdir(extracts_path):
                self.load_editor(extracts_path)

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

    def load_editor(self, lvls_path):
        self.lvl_editor_start_canvas.grid_remove()
        self.columnconfigure(0, minsize=200)  # Column 0 = Level List
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)  # Column 1 = Everything Else
        self.rowconfigure(0, weight=1)  # Row 0 = List box / Label

        # Loads lvl Files
        self.tree_files = ttk.Treeview(self, selectmode="browse")
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
        self.my_list = os.listdir(lvls_path)
        self.tree_files.grid(row=0, column=0, rowspan=3, sticky="nswe")
        self.vsb_tree_files.grid(row=0, column=0, sticky="nse")

        for (
            file
        ) in (
            self.my_list
        ):  # Loads list of all the lvl files in the left farthest treeview
            self.tree_files.insert("", "end", values=str(file), text=str(file))

        # Seperates Level Rules and Level Editor into two tabs
        self.tab_control = ttk.Notebook(self)

        self.tab1 = ttk.Frame(self.tab_control)  # Tab 1 shows a lvl files rules
        self.tab2 = ttk.Frame(self.tab_control)  # Tab 2 is the actual level editor

        self.tab_control.add(  # Rules Tab ----------------------------------------------------
            self.tab1, text="Rules"
        )

        self.tab1.columnconfigure(0, weight=1)  # Column 1 = Everything Else
        self.tab1.rowconfigure(0, weight=1)  # Row 0 = List box / Label

        self.tree = ttk.Treeview(self.tab1, selectmode="browse")
        self.tree.place(x=30, y=95)
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

        self.tree_levels = ttk.Treeview(self.tab2, selectmode="browse")
        self.tree_levels.place(x=30, y=95)
        self.vsb_tree_levels = ttk.Scrollbar(
            self, orient="vertical", command=self.tree_levels.yview
        )
        self.vsb_tree_levels.place(x=30 + 200 + 2, y=95, height=200 + 20)
        self.tree_levels.configure(yscrollcommand=self.vsb_tree_files.set)
        self.my_list = os.listdir(
            self.install_dir / "Mods" / "Extracted" / "Data" / "Levels"
        )
        self.tree_levels.grid(row=0, column=0, rowspan=4, sticky="nswe")
        self.vsb_tree_levels.grid(row=0, column=0, sticky="nse")
        self.tab_control.grid(row=0, column=1, sticky="nwse")

        self.mag = 50  # the size of each tiles in the grid; 50 is optimal
        self.rows = (
            15  # default values, could be set to none and still work I think lol
        )
        self.cols = (
            15  # default values, could be set to none and still work I think lol
        )

        self.canvas = tk.Canvas(  # this is the main level editor grid
            self.tab2,
            width=self.mag * self.cols,
            height=self.mag * self.rows,
            bg="white",
        )
        self.canvas.grid(row=0, column=1, rowspan=3, columnspan=1)
        self.canvas_dual = tk.Canvas(  # this is for dual level, it shows the back area
            self.tab2,
            width=0,
            bg="white",
        )
        self.canvas_dual.grid(row=0, column=2, rowspan=3, columnspan=1, padx=(0, 50))

        self.tile_pallete = ScrollableFrame(  # the tile palletes are loaded into here as buttons with their image as a tile and txt as their value to grab when needed
            self.tab2, text="Tile Pallete", width=50
        )
        self.tile_pallete.grid(row=2, column=3, columnspan=2, rowspan=2, sticky="swne")
        self.tile_pallete.scrollable_frame["width"] = 50

        self.tile_label = tk.Label(
            self.tab2, text="Selected Tile:", width=40
        )  # shows selected tile. Important because this is used for more than just user convenience; we can grab the currently used tile here
        self.tile_label.grid(row=0, column=3, sticky="w")

        self.img_sel = ImageTk.PhotoImage(
            Image.open(BASE_DIR / "static/images/tilecodetextures.png")
        )
        self.panel_sel = tk.Label(
            self.tab2, image=self.img_sel, width=50
        )  # shows selected tile image
        self.panel_sel.grid(row=0, column=4)

        self.scale = tk.Scale(
            self.tab2, from_=0, to=100, orient=tk.HORIZONTAL
        )  # scale for the percent of a selected tile
        self.scale.grid(row=1, column=3, columnspan=2, sticky="n")

        self.tags = tk.Text(
            self.tab2, height=2, width=30
        )  # text box for tags each room has like \!dual for example
        self.tags.grid(row=3, column=1, columnspan=2, sticky="nswe")

        # the tilecodes are in the same order as the tiles in the image(50x50, left to right)
        self.texture_images = []
        file_tile_codes = open(BASE_DIR / "tilecodes.txt", encoding="utf8")
        lines = file_tile_codes.readlines()
        count = 0
        self.count_col = 0
        self.count_row = 0
        count_total = 0
        x = 99
        y = 0
        # color_base = int(random.random())
        self.uni_tile_code_list = []
        self.tile_pallete_ref = []
        for line in lines:
            line = line.strip()
            self.uni_tile_code_list.append(line)
            im = Image.open(BASE_DIR / "static/images/tilecodetextures.png")
            im = im.crop((count * 50, y * 50, 5000 - (x * 50), (1 + y) * 50))
            self.tile_texture = ImageTk.PhotoImage(im)
            self.texture_images.append(self.tile_texture)
            # r = int(color_base * 256 + (256 / (count + 1)))
            # g = int(color_base * 256 + (256 / (count + 1)))
            # b = int(color_base * 256 + (256 / (count + 1)))
            tile_ref = []
            tile_ref.append(line)
            tile_ref.append(self.texture_images[count_total])
            tk.Button(
                self.tile_pallete.scrollable_frame,
                text=line,
                width=40,
                height=40,
                image=self.texture_images[count_total],
                command=lambda r=self.count_row, c=self.count_col: self.tile_pick(r, c),
            ).grid(row=self.count_row, column=self.count_col)
            self.tile_pallete_ref.append(tile_ref)
            count = count + 1
            self.count_col = self.count_col + 1
            x -= 1
            if self.count_col > 7:
                self.count_row = self.count_row + 1
                self.count_col = 0
            if (
                count == 100
            ):  # theres a 100 tiles in each row on the image so this lets me know when to start grabbing from the next row
                y += 1
                x = 99
                count = 0
            count_total = count_total + 1
        self.panel_sel["image"] = self.texture_images[0]
        self.tile_label["text"] = "Selected Tile: " + r"\?empty a"

        def canvas_click(event, canvas):  # when the level editor grid is clicked
            # Get rectangle diameters
            col_width = self.mag
            row_height = self.mag
            # Calculate column and row number
            col = event.x // col_width
            row = event.y // row_height
            # If the tile is not filled, create a rectangle
            canvas.delete(self.tiles[int(row)][int(col)])
            self.tiles[row][col] = canvas.create_image(
                int(col) * self.mag,
                int(row) * self.mag,
                image=self.panel_sel["image"],
                anchor="nw",
            )
            # coords = (
            #    col * self.mag,
            #    row * self.mag,
            #    col * self.mag + 50,
            #    row * self.mag + 50,
            # )
            print(
                str(self.tiles_meta[row][col])
                + " replaced with "
                + self.tile_label["text"].split(" ", 4)[3]
            )
            self.tiles_meta[row][col] = self.tile_label["text"].split(" ", 4)[3]

        self.canvas.bind("<Button-1>", lambda event: canvas_click(event, self.canvas))
        self.canvas_dual.bind(
            "<Button-1>", lambda event: canvas_click(event, self.canvas_dual)
        )

        def tree_filesitemclick(_event):
            # Using readlines()
            item_text = ""
            for item in self.tree_files.selection():
                item_text = self.tree_files.item(item, "text")
                self.read_lvl_file(lvls_path, item_text)

        self.tree_files.bind("<ButtonRelease-1>", tree_filesitemclick)

    def tile_pick(
        self, button_row, button_col
    ):  # When a tile is selected from the tile pallete
        selected_tile = self.tile_pallete.scrollable_frame.grid_slaves(
            button_row, button_col
        )[0]
        self.panel_sel["image"] = selected_tile["image"]
        self.tile_label["text"] = "Selected Tile: " + selected_tile["text"]

    def read_lvl_file(self, lvls_path, lvl):
        file1 = open(lvls_path / lvl, encoding="utf8")
        lines = file1.readlines()

        lvl_bg_path = self.textures_dir / "bg_cave.png"
        if lvl == "abzu.lvl":
            lvl_bg_path = self.textures_dir / "bg_tidepool.png"
        elif lvl.startswith("babylon"):
            lvl_bg_path = self.textures_dir / "bg_babylon.png"
        elif lvl.startswith("basecamp"):
            lvl_bg_path = self.textures_dir / "bg_cave.png"
        elif lvl.startswith("beehive"):
            lvl_bg_path = self.textures_dir / "bg_beehive.png"
        elif lvl.startswith("blackmark"):
            lvl_bg_path = self.textures_dir / "bg_jungle.png"
        elif lvl.startswith("caveboss"):
            lvl_bg_path = self.textures_dir / "bg_cave.png"
        elif lvl.startswith("challenge_moon"):
            lvl_bg_path = self.textures_dir / "bg_jungle.png"
        elif lvl.startswith("challenge_star"):
            lvl_bg_path = self.textures_dir / "bg_temple.png"
        elif lvl.startswith("challenge_sun"):
            lvl_bg_path = self.textures_dir / "bg_sunken.png"
        elif lvl.startswith("city"):
            lvl_bg_path = self.textures_dir / "bg_gold.png"
        elif lvl.startswith("cosmic"):
            lvl_bg_path = self.textures_dir / "bg_cave.png"
        elif lvl.startswith("duat"):
            lvl_bg_path = self.textures_dir / "bg_cave.png"
        elif lvl.startswith("dwelling"):
            lvl_bg_path = self.textures_dir / "bg_cave.png"
        elif lvl.startswith("egg"):
            lvl_bg_path = self.textures_dir / "bg_eggplant.png"
        elif lvl.startswith("ending_hard"):
            lvl_bg_path = self.textures_dir / "bg_cave.png"
        elif lvl.startswith("end"):
            lvl_bg_path = self.textures_dir / "bg_cave.png"
        elif lvl.startswith("hallofu"):
            lvl_bg_path = self.textures_dir / "bg_babylon.png"
        elif lvl.startswith("hundun"):
            lvl_bg_path = self.textures_dir / "bg_sunken.png"
        elif lvl.startswith("ice"):
            lvl_bg_path = self.textures_dir / "bg_ice.png"
        elif lvl.startswith("jungle"):
            lvl_bg_path = self.textures_dir / "bg_jungle.png"
        elif lvl.startswith("lake"):
            lvl_bg_path = self.textures_dir / "bg_tidepool.png"
        elif lvl.startswith("olmec"):
            lvl_bg_path = self.textures_dir / "bg_stone.png"
        elif lvl.startswith("palace"):
            lvl_bg_path = self.textures_dir / "bg_cave.png"
        elif lvl.startswith("sunken"):
            lvl_bg_path = self.textures_dir / "bg_sunken.png"
        elif lvl.startswith("tiamat"):
            lvl_bg_path = self.textures_dir / "bg_tidepool.png"
        elif lvl.startswith("temple"):
            lvl_bg_path = self.textures_dir / "bg_temple.png"
        elif lvl.startswith("tide"):
            lvl_bg_path = self.textures_dir / "bg_tidepool.png"
        elif lvl.startswith("vlad"):
            lvl_bg_path = self.textures_dir / "bg_vlad.png"
        elif lvl.startswith("volcano"):
            lvl_bg_path = self.textures_dir / "bg_volcano.png"

        lvl_bg = ImageTk.PhotoImage(Image.open(lvl_bg_path))
        self.canvas.create_image(0, 0, image=lvl_bg, anchor="nw")

        # Strips the newline character
        self.tree.delete(*self.tree.get_children())
        self.tree_levels.delete(*self.tree_levels.get_children())
        pointer = 0
        pointed = False
        load_mode = ""
        blocks = []
        # cur_item = self.tree.focus()
        self.node = self.tree_levels.insert("", "end", text="placeholder")
        self.child = None
        self.rooms = []
        # room_found = False
        def room_select(_event):  # Loads room when click if not parent node
            self.dual_mode = False
            item_iid = self.tree_levels.selection()[0]
            parent_iid = self.tree_levels.parent(item_iid)
            if parent_iid:
                self.canvas.delete("all")
                self.canvas_dual.delete("all")
                lvl_bg = ImageTk.PhotoImage(Image.open(lvl_bg_path))
                self.canvas.create_image(0, 0, image=lvl_bg, anchor="nw")
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
                    self.__draw_grid(self.cols, self.rows, self.canvas)
                    self.canvas_dual["width"] = 0
                else:
                    self.__draw_grid(int((self.cols - 1) / 2), self.rows, self.canvas)
                    self.__draw_grid(
                        int((self.cols - 1) / 2), self.rows, self.canvas_dual
                    )

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
                            for pallete_block in self.tile_pallete_ref:
                                if any(
                                    str(" " + block) in self.c[0]
                                    for self.c in self.tile_pallete_ref
                                ):
                                    tile_image = self.c[1]
                                else:
                                    print(
                                        str(block) + " " + self.c[0] + " Not Found"
                                    )  # There's a missing tile id somehow
                            if self.dual_mode and curcol > int((self.cols - 1) / 2):
                                x = int(curcol - ((self.cols - 1) / 2) - 1)
                                self.tiles[currow][
                                    curcol
                                ] = self.canvas_dual.create_image(
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

        self.tree_levels.bind("<ButtonRelease-1>", room_select)

        tile_count = 0
        tl_col = 0
        color_base = int(random.random())
        self.tile_convert = []
        for line in lines:
            line = " ".join(line.split())  # remove duplicate spaces
            line = line.strip()
            print("parsing " + line)
            if (
                line == "// ------------------------------"
                and not pointed
                and pointer == 0
                and load_mode != "Templates"
                and line
            ):
                pointer = pointer + 1
                self.tree.insert(
                    "",
                    "end",
                    text="L1",
                    values=("COMMENT", "", str(line)),
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
                elif line == "// TEMPLATES" and line:
                    load_mode = "Templates"
                self.tree.insert(
                    "",
                    "end",
                    text="L1",
                    values=("COMMENT", "", str(line)),
                )
            elif (
                line == "// ------------------------------"
                and pointer == 1
                # and load_mode != "Templates"
                and line
            ):
                pointer = 0
                pointed = False
                self.tree.insert(
                    "",
                    "end",
                    text="L1",
                    values=("COMMENT", "", str(line)),
                )
            elif load_mode == "RoomChances" and not pointed and pointer == 0 and line:
                data = line.split(" ", 4)
                comment = ""
                value = ""
                if str(data[1]):
                    value = str(data[1])
                comments = line.split("//", 1)
                if len(comments) > 1:  # Makes sure a comment even exists
                    comment = comments[1]
                self.tree.insert(
                    "",
                    "end",
                    text="L1",
                    values=(str(data[0]), str(value), str(comment)),
                )
            elif load_mode == "TileCodes" and not pointed and pointer == 0 and line:
                data = line.split(" ", 4)
                if any(
                    str(data[0]) in self.s for self.s in self.uni_tile_code_list
                ):  # compares tilecode id to its universal tilecode counterpart
                    self.tile_convert.append(
                        str(line) + " 100"
                    )  # adds tilecode to be converted into universal TileCodes; has no percent value so its 100% likely to spawn
                    print(
                        "gonna change " + str(line) + " 100"
                    )  # structure (id tilecode percent-without-percent-sign)
                else:
                    try:
                        if (
                            len(data[0].split("%", 2)) == 2
                        ):  # tile with already existing percent
                            self.tile_convert.append(
                                str(data[0].split("%", 2)[0])
                                + " "
                                + str(data[1])
                                + " "
                                + str(data[0].split("%", 2)[1].split(" ", 2)[0])
                                + " None"
                            )
                            print(
                                "gonna change "
                                + str(data[0].split("%", 2)[0])
                                + " "
                                + str(data[1])
                                + " "
                                + str(data[0].split("%", 2)[1].split(" ", 2)[0])
                                + " None"
                            )
                            tkMessageBox.showinfo(
                                "Debug",
                                str(data[0].split("%", 2)[0])
                                + " "
                                + str(data[1])
                                + " "
                                + str(data[0].split("%", 2)[1].split(" ", 2)[0])
                                + " None",
                            )  # 100 default percent value and None default alt tile value
                        elif (
                            len(data[0].split("%", 2)) == 3
                        ):  # tile with already existing percent and alt tile
                            self.tile_convert.append(
                                str(data[0].split("%", 2)[0])
                                + " "
                                + str(data[1])
                                + " "
                                + str(data[0].split("%", 2)[1])
                                + " "
                                + str(data[0].split("%", 2)[2].split(" ", 2)[0])
                            )
                            print(
                                "gonna change "
                                + str(data[0].split("%", 2)[0])
                                + " "
                                + str(data[1])
                                + " "
                                + str(data[0].split("%", 2)[1])
                                + " "
                                + str(data[0].split("%", 2)[2].split(" ", 2)[0])
                            )
                            tkMessageBox.showinfo(
                                "Debug",
                                str(data[0].split("%", 2)[0])
                                + " "
                                + str(data[1])
                                + " "
                                + str(
                                    data[0].split("%", 2)[1]
                                    + " "
                                    + str(data[0].split("%", 2)[2].split(" ", 2)[0])
                                ),
                            )
                    except:
                        tkMessageBox.showinfo(
                            "Uh Oh!", "skipped " + str(data[0])
                        )  # A tilecode id thats missing from the universal database and needs to be added
                        # structure (id tilecode percent-without-percent-sign second-tile)

                comment = ""
                value = ""
                if str(data[1]):
                    value = str(data[1])
                comments = line.split("//", 1)
                if len(comments) > 1:  # Makes sure a comment even exists
                    comment = comments[1]
                self.tree.insert(
                    "",
                    "end",
                    text="L1",
                    values=(str(data[0]), str(value), str(comment)),
                )
            elif load_mode == "LevelChances" and not pointed and pointer == 0 and line:
                data = line.split(" ", 4)
                comment = ""
                value = ""
                if str(data[1]):
                    value = str(data[1])
                comments = line.split("//", 1)
                if len(comments) > 1:  # Makes sure a comment even exists
                    comment = comments[1]
                self.tree.insert(
                    "",
                    "end",
                    text="L1",
                    values=(str(data[0]), str(value), str(comment)),
                )
            elif (
                load_mode == "MonsterChances" and not pointed and pointer == 0 and line
            ):
                data = line.split(" ", 1)
                comment = ""
                value = ""
                if str(data[1]):
                    value = str(data[1])
                comments = line.split("//", 1)
                if len(comments) > 1:  # Makes sure a comment even exists
                    comment = comments[1]
                self.tree.insert(
                    "",
                    "end",
                    text="L1",
                    values=(str(data[0]), str(value), str(comment)),
                )
            elif load_mode == "Templates":
                if line == "/" * 80 and not pointed and pointer == 0:
                    pointer = 1
                elif not pointed and pointer == 1 and line.startswith("\."):
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
                    self.tree.insert("", "end", text="L1", values=("COMMENT", "", line))
                elif not line and len(self.rooms) > 0:
                    self.new_room = self.tree_levels.insert(
                        self.node, "end", values=self.rooms, text="room"
                    )
                    self.rooms.clear()
                elif line == "":
                    pointer = 0
                elif line:
                    converted_room_row = ""
                    if not str(line).startswith("\!"):
                        for char in str(line):  # read each character in room row
                            new_char = str(char)
                            if any(
                                str(" " + char) in self.a
                                for self.a in self.tile_convert
                            ):  # finds the char in tiles listed for conversion earlier
                                parse = self.a.split(
                                    " ", 3
                                )  # splits code from its id [0] = id [1] = code [2] = percent value [3] = alt tile
                                if any(
                                    str(parse[0] + " ") in self.b
                                    for self.b in self.uni_tile_code_list
                                ):  # finds id of tile needing conversion in the universal tile code list
                                    parseb = self.b.split(
                                        " ", 2
                                    )  # splits code from its id [0] = id [1] = code
                                    print(
                                        str(parse[0])
                                        + " converted to "
                                        + str(parseb[0])
                                    )
                                    new_char = str(
                                        parseb[1]
                                    )  # replaces char with tile code from universal lists
                                # # notes line as needing conversion
                                # self.tile_convert.append(str(line))

                            converted_room_row += str(new_char)
                    else:
                        converted_room_row = str(line)
                    self.rooms.append(str(converted_room_row))
                    print(str(converted_room_row) + " completed")

    def __draw_grid(self, rows, cols, canvas):
        for i in range(0, cols + 2):
            canvas.create_line(
                (i) * self.mag, 0, (i) * self.mag, (rows) * self.mag, fill="#fffff1"
            )
        for i in range(0, rows):
            canvas.create_line(
                0, (i) * self.mag, self.mag * (cols + 2), (i) * self.mag, fill="#fffff1"
            )
        canvas["width"] = self.mag * rows
        canvas["height"] = self.mag * cols

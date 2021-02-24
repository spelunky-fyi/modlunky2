from pathlib import Path
import re

##p = Path(
##    r"C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2\Mods\Extracted\Data\Levels"
##)

##tile_code_re = re.compile(
##    r"^\\\?(?P<name>\w+)(%(?P<pct>\d{2})(?P<second_name>\w+)?)?\s+(?P<code>.)"
##)

##codes = set()

##for lvl_file in p.glob("*lvl"):
##    for line in lvl_file.read_text().splitlines():
##        m = tile_code_re.match(line)
##        if m:
##            mdict = m.groupdict()
##            codes.add(mdict.get("name"))
##            if mdict.get("pct") and mdict.get("second_name"):
##                codes.add(mdict.get("second_name"))

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
            file1 = open(self.lvls_path + "/" + lvl, 'r', encoding= 'cp1252')
        else:
            if (self.overrides_path / lvl).exists():
                print("Found this lvl in overrides; loading it instead")
                file1 = open(self.overrides_path / lvl, 'r', encoding= 'cp1252')
            else:
                file1 = open(self.lvls_path / lvl, 'r', encoding= 'cp1252')
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
                    lines_again = open(self.lvls_path + "/" + "junglearea.lvl", 'r', encoding= 'cp1252')
                else:
                    print(
                        "local dependancy lvl not found, attempting load from extracts"
                    )
                    lines_again = open(self.extracts_path / "junglearea.lvl", 'r', encoding= 'cp1252')
            else:
                if os.path.isdir(self.overrides_path / "junglearea.lvl"):
                    lines_again = open(self.overrides_path / "junglearea.lvl", 'r', encoding= 'cp1252')
                else:
                    lines_again = open(self.lvls_path / "junglearea.lvl", 'r', encoding= 'cp1252')
            parse_lvl_file(lines_again.readlines(), True)
        elif str(self.tree_files.item(file_id, option="text")).startswith(
            "vlads"
        ) or str(self.tree_files.item(file_id, option="text")).startswith(
            "challenge_moon"
        ):
            if not self.extracts_mode:
                if os.path.isdir(self.lvls_path + "/" + "volcanoarea.lvl"):
                    lines_again = open(self.lvls_path + "/" + "volcanoarea.lvl", 'r', encoding= 'cp1252')
                else:
                    print(
                        "local dependancy lvl not found, attempting load from extracts"
                    )
                    lines_again = open(self.extracts_path / "volcanoarea.lvl", 'r', encoding= 'cp1252')
            else:
                if os.path.isdir(self.overrides_path / "volcanoarea.lvl"):
                    lines_again = open(self.overrides_path / "volcanoarea.lvl", 'r', encoding= 'cp1252')
                else:
                    lines_again = open(self.lvls_path / "volcanoarea.lvl", 'r', encoding= 'cp1252')
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
                    lines_again = open(self.lvls_path + "/" + "babylonarea.lvl", 'r', encoding= 'cp1252')
                else:
                    print(
                        "local dependancy lvl not found, attempting load from extracts"
                    )
                    lines_again = open(self.extracts_path / "babylonarea.lvl", 'r', encoding= 'cp1252')
            else:
                if os.path.isdir(self.overrides_path / "babylonarea.lvl"):
                    lines_again = open(self.overrides_path / "babylonarea.lvl", 'r', encoding= 'cp1252')
                else:
                    lines_again = open(self.lvls_path / "babylonarea.lvl", 'r', encoding= 'cp1252')
            parse_lvl_file(lines_again.readlines(), True)
        elif str(self.tree_files.item(file_id, option="text")).startswith(
            "lake"
        ) or str(self.tree_files.item(file_id, option="text")).startswith(
            "challenge_star"
        ):
            if not self.extracts_mode:
                if os.path.isdir(self.lvls_path + "/" + "tidepoolarea.lvl"):
                    lines_again = open(self.lvls_path + "/" + "tidepoolarea.lvl", 'r', encoding= 'cp1252')
                else:
                    print(
                        "local dependancy lvl not found, attempting load from extracts"
                    )
                    lines_again = open(self.extracts_path / "tidepoolarea.lvl", 'r', encoding= 'cp1252')
            else:
                if os.path.isdir(self.overrides_path / "tidepoolarea.lvl"):
                    lines_again = open(self.overrides_path / "tidepoolarea.lvl", 'r', encoding= 'cp1252')
                else:
                    lines_again = open(self.lvls_path / "tidepoolarea.lvl", 'r', encoding= 'cp1252')
            parse_lvl_file(lines_again.readlines(), True)
        elif str(self.tree_files.item(file_id, option="text")).startswith("basecamp"):
            if not self.extracts_mode:
                if os.path.isdir(self.lvls_path + "/" + "basecamp.lvl"):
                    lines_again = open(self.lvls_path + "/" + "basecamp.lvl", 'r', encoding= 'cp1252')
                else:
                    print(
                        "local dependancy lvl not found, attempting load from extracts"
                    )
                    lines_again = open(self.extracts_path / "basecamp.lvl", 'r', encoding= 'cp1252')
            else:
                if os.path.isdir(self.overrides_path / "basecamp.lvl"):
                    lines_again = open(self.overrides_path / "basecamp.lvl", 'r', encoding= 'cp1252')
                else:
                    lines_again = open(self.lvls_path / "basecamp.lvl", 'r', encoding= 'cp1252')
            parse_lvl_file(lines_again.readlines(), True)
        elif str(self.tree_files.item(file_id, option="text")).startswith(
            "challenge_sun"
        ):
            if not self.extracts_mode:
                if os.path.isdir(self.lvls_path + "/" + "sunkencityarea.lvl"):
                    lines_again = open(self.lvls_path + "/" + "sunkencityarea.lvl", 'r', encoding= 'cp1252')
                else:
                    print(
                        "local dependancy lvl not found, attempting load from extracts"
                    )
                    lines_again = open(self.extracts_path / "sunkencityarea.lvl", 'r', encoding= 'cp1252')
            else:
                if os.path.isdir(self.overrides_path / "sunkencityarea.lvl"):
                    lines_again = open(self.overrides_path / "sunkencityarea.lvl", 'r', encoding= 'cp1252')
                else:
                    lines_again = open(self.lvls_path / "sunkencityarea.lvl", 'r', encoding= 'cp1252')
            parse_lvl_file(lines_again.readlines(), True)
        if not str(self.tree_files.item(file_id, option="text")).startswith(
            "basecamp"
        ) and not str(self.tree_files.item(file_id, option="text")).startswith(
            "generic"
        ):
            if not self.extracts_mode:
                if os.path.isdir(self.lvls_path + "/" + "generic.lvl"):
                    lines_again = open(self.lvls_path + "/" + "generic.lvl", 'r', encoding= 'cp1252')
                else:
                    print(
                        "local dependancy lvl not found, attempting load from extracts"
                    )
                    lines_again = open(self.extracts_path / "generic.lvl", 'r', encoding= 'cp1252')
            else:
                if os.path.isdir(self.overrides_path / "generic.lvl"):
                    lines_again = open(self.overrides_path / "generic.lvl", 'r', encoding= 'cp1252')
                else:
                    lines_again = open(self.lvls_path / "generic.lvl", 'r', encoding= 'cp1252')
            parse_lvl_file(
                lines_again.readlines(), True
            )  # finishes by grabbing parent generics tildecode data

        combo_tile_ids = []
        for tile_info in self.uni_tile_code_list:
            combo_tile_ids.append(str(tile_info).split(" ", 2)[0].replace(r"\?", ""))

        self.combobox["values"] = sorted(combo_tile_ids, key=str.lower)
        self.combobox_alt["values"] = sorted(combo_tile_ids, key=str.lower)

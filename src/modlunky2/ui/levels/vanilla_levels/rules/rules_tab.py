import tkinter as tk
from tkinter import ttk

from modlunky2.config import Config
from modlunky2.levels.level_chances import LevelChance, LevelChances
from modlunky2.levels.level_settings import LevelSetting, LevelSettings
from modlunky2.levels.monster_chances import MonsterChance, MonsterChances
from modlunky2.ui.levels.vanilla_levels.rules.rules_tree import RulesTree
from modlunky2.ui.widgets import PopupWindow

class RulesTab(ttk.Frame):
    def __init__(self, parent, modlunky_config: Config, on_edit, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.modlunky_config = modlunky_config
        self.on_edit = on_edit

        self.columnconfigure(0, weight=1)  # Column 1 = Everything Else
        self.rowconfigure(0, weight=1)  # Row 0 = List box / Label

        self.tree_level_settings = RulesTree(self, on_edit, selectmode="browse")  # This tree shows rules parsed from the lvl file.
        self.tree_level_settings.bind("<Double-1>", lambda e: self.on_double_click(self.tree_level_settings))
        self.tree_level_settings.place(x=30, y=95)
        # style = ttk.Style(self)
        self.vsb_level_settings = ttk.Scrollbar(
            self, orient="vertical", command=self.tree_level_settings.yview
        )
        self.vsb_level_settings.place(x=30 + 200 + 2, y=95, height=200 + 20)
        self.tree_level_settings.configure(yscrollcommand=self.vsb_level_settings.set)
        self.tree_level_settings["columns"] = ("1", "2", "3")
        self.tree_level_settings["show"] = "headings"
        self.tree_level_settings.column("1", width=100, anchor="w")
        self.tree_level_settings.column("2", width=10, anchor="w")
        self.tree_level_settings.column("3", width=100, anchor="w")
        self.tree_level_settings.heading("1", text="Level Settings")
        self.tree_level_settings.heading("2", text="Value")
        self.tree_level_settings.heading("3", text="Notes")
        self.tree_level_settings.grid(row=0, column=0, sticky="nwse")
        self.vsb_level_settings.grid(row=0, column=1, sticky="nse")

        self.tree_level_chances = RulesTree(
            self, on_edit, selectmode="browse"
        )  # This tree shows rules parses from the lvl file
        self.tree_level_chances.bind(
            "<Double-1>", lambda e: self.on_double_click(self.tree_level_chances)
        )
        self.tree_level_chances.place(x=30, y=95)
        # style = ttk.Style(self)
        self.vsb_level_chances = ttk.Scrollbar(
            self, orient="vertical", command=self.tree_level_chances.yview
        )
        self.vsb_level_chances.place(x=30 + 200 + 2, y=95, height=200 + 20)
        self.tree_level_chances.configure(yscrollcommand=self.vsb_level_chances.set)
        self.tree_level_chances["columns"] = ("1", "2", "3")
        self.tree_level_chances["show"] = "headings"
        self.tree_level_chances.column("1", width=100, anchor="w")
        self.tree_level_chances.column("2", width=10, anchor="w")
        self.tree_level_chances.column("3", width=100, anchor="w")
        self.tree_level_chances.heading("1", text="Level Chances")
        self.tree_level_chances.heading("2", text="Value")
        self.tree_level_chances.heading("3", text="Notes")
        self.tree_level_chances.grid(row=1, column=0, sticky="nwse")
        self.vsb_level_chances.grid(row=1, column=1, sticky="nse")

        self.tree_monster_chances = RulesTree(
            self, on_edit, selectmode="browse"
        )  # This tree shows rules parses from the lvl file
        self.tree_monster_chances.bind(
            "<Double-1>", lambda e: self.on_double_click(self.tree_monster_chances)
        )
        self.tree_monster_chances.place(x=30, y=95)
        # style = ttk.Style(self)
        self.vsb_chances_monsters = ttk.Scrollbar(
            self, orient="vertical", command=self.tree_monster_chances.yview
        )
        self.vsb_chances_monsters.place(x=30 + 200 + 2, y=95, height=200 + 20)
        self.tree_monster_chances.configure(yscrollcommand=self.vsb_chances_monsters.set)
        self.tree_monster_chances["columns"] = ("1", "2", "3")
        self.tree_monster_chances["show"] = "headings"
        self.tree_monster_chances.column("1", width=100, anchor="w")
        self.tree_monster_chances.column("2", width=10, anchor="w")
        self.tree_monster_chances.column("3", width=100, anchor="w")
        self.tree_monster_chances.heading("1", text="Monster Chances")
        self.tree_monster_chances.heading("2", text="Value")
        self.tree_monster_chances.heading("3", text="Notes")
        self.tree_monster_chances.grid(row=2, column=0, sticky="nwse")
        self.vsb_chances_monsters.grid(row=2, column=1, sticky="nse")


    def on_double_click(self, tree_view):
        # First check if a blank space was selected
        entry_index = tree_view.focus()
        if entry_index == "":
            return

        win = PopupWindow("Edit Entry", self.modlunky_config)
        win.columnconfigure(1, minsize=500)

        # Grab the entry's values
        for child in tree_view.get_children():
            if child == entry_index:
                values = tree_view.item(child)["values"]
                break

        col1_lbl = ttk.Label(win, text="Entry: ")
        col1_ent = ttk.Entry(win)
        col1_ent.insert(0, values[0])  # Default is column 1's current value
        col1_lbl.grid(row=0, column=0, padx=2, pady=2, sticky="nse")
        col1_ent.grid(row=0, column=1, padx=2, pady=2, sticky="nsew")

        col2_lbl = ttk.Label(win, text="Value: ")
        col2_ent = ttk.Entry(win)
        col2_ent.insert(0, values[1])  # Default is column 2's current value
        col2_lbl.grid(row=1, column=0, padx=2, pady=2, sticky="nse")
        col2_ent.grid(row=1, column=1, padx=2, pady=2, sticky="nsew")

        col3_lbl = ttk.Label(win, text="Comment: ")
        col3_ent = ttk.Entry(win)
        col3_ent.insert(0, values[2])  # Default is column 3's current value
        col3_lbl.grid(row=2, column=0, padx=2, pady=2, sticky="nse")
        col3_ent.grid(row=2, column=1, padx=2, pady=2, sticky="nsew")

        def update_then_destroy():
            if self.confirm_entry(
                tree_view, col1_ent.get(), col2_ent.get(), col3_ent.get()
            ):
                win.destroy()
                self.on_edit()

        separator = ttk.Separator(win)
        separator.grid(row=3, column=0, columnspan=3, pady=5, sticky="nsew")

        buttons = ttk.Frame(win)
        buttons.grid(row=4, column=0, columnspan=2, sticky="nsew")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        ok_button = ttk.Button(buttons, text="Ok", command=update_then_destroy)
        ok_button.grid(row=0, column=0, pady=5, sticky="nsew")

        cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
        cancel_button.grid(row=0, column=1, pady=5, sticky="nsew")

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

        return True

    def delete_current_entry(self, tree_view):
        curr = tree_view.focus()

        if curr == "":
            return

        tree_view.delete(curr)
        self.on_edit()

    def reset(self):
        # removes any old rules that might be there from the last file
        for i in self.tree_level_chances.get_children():
            self.tree_level_chances.delete(i)

        # removes any old rules that might be there from the last file
        for i in self.tree_monster_chances.get_children():
            self.tree_monster_chances.delete(i)

        # removes any old rules that might be there from the last file
        for i in self.tree_level_settings.get_children():
            self.tree_level_settings.delete(i)

        self.tree_level_settings.delete(*self.tree_level_settings.get_children())

    def get_level_settings(self):
        level_settings = LevelSettings()

        bad_chars = ["[", "]", "'", '"', ","]
        for entry in self.tree_level_settings.get_children():
            values = self.tree_level_settings.item(entry)["values"]
            value_final = str(values[1])
            for i in bad_chars:
                value_final = value_final.replace(i, "")
            level_settings.set_obj(
                LevelSetting(
                    name=str(values[0]),
                    value=value_final,
                    comment=str(values[2]),
                )
            )
        return level_settings

    def load_level_settings(self, level_settings):
        rules = level_settings.all()
        bad_chars = ["[", "]", '"', "'", "(", ")"]
        for rule in rules:
            value_final = str(rule.value)
            for i in bad_chars:
                value_final = value_final.replace(i, "")
            self.tree_level_settings.insert(
                "",
                "end",
                text="L1",
                values=(str(rule.name), value_final, str(rule.comment)),
            )

    def get_level_chances(self):
        level_chances = LevelChances()

        bad_chars = ["[", "]", "'", '"']
        for entry in self.tree_level_chances.get_children():
            values = self.tree_level_chances.item(entry)["values"]
            value_final = str(values[1])
            for i in bad_chars:
                value_final = value_final.replace(i, "")
            level_chances.set_obj(
                LevelChance(
                    name=str(values[0]),
                    value=value_final,
                    comment=str(values[2]),
                )
            )
        return level_chances

    def load_level_chances(self, level_chances: LevelChances):
        rules = level_chances.all()
        for rule in rules:
            self.tree_level_chances.insert(
                "",
                "end",
                text="L1",
                values=(
                    str(rule.name),
                    str(rule.value)
                        .strip("[")
                        .strip("]")
                        .strip("(")
                        .strip(")")
                        .strip('"'),
                    str(rule.comment),
                ),
            )

    def get_monster_chances(self):
        monster_chances = MonsterChances()

        bad_chars = ["[", "]", "'", '"']
        for entry in self.tree_monster_chances.get_children():
            values = self.tree_monster_chances.item(entry)["values"]
            value_final = str(values[1])
            for i in bad_chars:
                value_final = value_final.replace(i, "")
            monster_chances.set_obj(
                MonsterChance(
                    name=str(values[0]),
                    value=value_final,
                    comment=str(values[2]),
                )
            )
        return monster_chances

    def load_monster_chances(self, monster_chances: MonsterChances):
        rules = monster_chances.all()
        for rule in rules:
            self.tree_monster_chances.insert(
                "",
                "end",
                text="L1",
                values=(
                    str(rule.name),
                    str(rule.value)
                        .strip("[")
                        .strip("]")
                        .strip("(")
                        .strip(")")
                        .strip('"'),
                    str(rule.comment),
                ),
            )

    def get_full_size(self):
        for entry in self.tree_level_settings.get_children():
            if self.tree_level_settings.item(entry, option="values")[0] == "size":
                return self.tree_level_settings.item(entry, option="values")[1]
        return None
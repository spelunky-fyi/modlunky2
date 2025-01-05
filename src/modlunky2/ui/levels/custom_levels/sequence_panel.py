import tkinter as tk
from tkinter import ttk


class SequencePanel(ttk.Frame):
    def __init__(self, parent, on_update_sequence, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.lvls_path = None
        self.level_order = None
        self.all_levels = None

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

    def update_pack(self, lvls_path, level_order, all_levels):
        self.lvls_path = lvls_path
        self.level_order = level_order
        self.all_levels = all_levels

        self.refresh_lists()

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
        print(index)
        print(self.unused_levels)
        print(self.all_levels)
        print(self.level_order)
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

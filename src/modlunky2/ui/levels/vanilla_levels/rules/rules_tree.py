import tkinter as tk
from tkinter import ttk

class RulesTree(ttk.Treeview):
    def __init__(self, parent, on_edit, *args, **kwargs):
        ttk.Treeview.__init__(self, parent, *args, **kwargs)
        self.on_edit = on_edit

        self.popup_menu = tk.Menu(self, tearoff=0)
        self.popup_menu_parent = tk.Menu(self, tearoff=0)
        self.popup_menu.add_command(label="Add", command=self.add)
        self.popup_menu_parent.add_command(label="Add", command=self.add)
        self.popup_menu.add_command(label="Delete", command=self.delete_selected)

        self.bind("<Button-3>", self.popup)  # Button-2 on Aqua

    def popup(self, event):
        try:
            if len(self.selection()) == 1:
                self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
            else:
                self.popup_menu_parent.tk_popup(event.x_root, event.y_root, 0)
        finally:
            self.popup_menu.grab_release()

    def delete_selected(self):
        msg_box = tk.messagebox.askquestion(
            "Delete?",
            "Delete this rule?",
            icon="warning",
        )
        if msg_box == "yes":
            item_iid = self.selection()[0]
            self.delete(item_iid)
            self.on_edit()

    def add(self):
        _edited = self.insert(
            "",
            "end",
            values=["RULE_NAME", "VAL", "// COMMENT"],
        )

        self.on_edit()

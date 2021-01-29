import logging
import os
import queue
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

logger = logging.getLogger("modlunky2")


class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)


# Adapted from https://beenje.github.io/blog/posts/logging-to-a-tkinter-scrolledtext-widget/
class ConsoleWindow(tk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create a ScrolledText wdiget
        self.scrolled_text = ScrolledText(self, height=7, state="disabled")
        self.scrolled_text.pack(expand=True, fill="both")
        self.scrolled_text.configure(font="TkFixedFont")
        self.scrolled_text.tag_config("INFO", foreground="green")
        self.scrolled_text.tag_config("DEBUG", foreground="gray")
        self.scrolled_text.tag_config("WARNING", foreground="orange")
        self.scrolled_text.tag_config("ERROR", foreground="red")
        self.scrolled_text.tag_config("CRITICAL", foreground="red", underline=1)

        # Create a logging handler using a queue
        self.log_queue = queue.Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter("%(asctime)s: %(message)s")
        self.queue_handler.setFormatter(formatter)
        logger.addHandler(self.queue_handler)

        # Start polling messages from the queue
        self.after(100, self.poll_log_queue)

    def display(self, record):
        msg = self.queue_handler.format(record)
        self.scrolled_text.configure(state="normal")
        self.scrolled_text.insert(tk.END, msg + "\n", record.levelname)
        self.scrolled_text.configure(state="disabled")
        self.scrolled_text.yview(tk.END)

    def poll_log_queue(self):
        # Check every 100ms if there is a new message in the queue to display
        while True:
            try:
                record = self.log_queue.get(block=False)
            except queue.Empty:
                break
            else:
                self.display(record)
        self.after(100, self.poll_log_queue)

    def close(self):
        pass


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text

        self.widget.bind('<Enter>', self.on_enter)
        self.widget.bind('<Leave>', self.on_leave)

        self.tooltip = None
        self.label = None

    def on_enter(self, event):
        self.tooltip = tk.Toplevel()
        self.tooltip.overrideredirect(True)
        self.tooltip.geometry(f'+{event.x_root+15}+{event.y_root+10}')

        self.label = tk.Label(self.tooltip,text=self.text)
        self.label.pack()

    def on_leave(self, _event):
        self.tooltip.destroy()


class Tab(ttk.Frame):
    """ Base class that all tabs should inherit from."""

    def on_load(self):
        """ Called whenever the tab is loaded."""


class ScrollableFrame(ttk.LabelFrame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.scrollable_frame = tk.Frame(self.canvas)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Enter>", self._bind_to_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_from_mousewheel)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(self, event):
        scroll_dir = None
        if event.num == 5 or event.delta == -120:
            scroll_dir = 1
        elif event.num == 4 or event.delta == 120:
            scroll_dir = -1

        if scroll_dir is None:
            return

        # If the scrollbar is max size don't bother scrolling
        if self.scrollbar.get() == (0.0, 1.0):
            return

        self.canvas.yview_scroll(scroll_dir, "units")

    def _bind_to_mousewheel(self, _event):
        if "nt" in os.name:
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        else:
            self.canvas.bind_all("<Button-4>", self._on_mousewheel)
            self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_from_mousewheel(self, _event):
        if "nt" in os.name:
            self.canvas.unbind_all("<MouseWheel>")
        else:
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")


class ToggledFrame(tk.Frame):
    def __init__(self, parent, text, *args, **options):
        tk.Frame.__init__(self, parent, *args, **options)

        self.show = tk.IntVar()
        self.show.set(0)

        self.title_frame = ttk.Frame(self)
        self.title_frame.pack(fill="x", expand=1)

        ttk.Label(self.title_frame, text=text).pack(side="left", fill="x", expand=1)

        self.toggle_button = ttk.Checkbutton(
            self.title_frame,
            width=2,
            text="+",
            command=self.toggle,
            variable=self.show,
            style="Toolbutton",
        )
        self.toggle_button.pack(side="left")

        self.sub_frame = tk.Frame(self, relief="sunken", borderwidth=1)

    def toggle(self):
        if bool(self.show.get()):
            self.sub_frame.pack(fill="x", expand=1)
            self.toggle_button.configure(text="-")
        else:
            self.sub_frame.forget()
            self.toggle_button.configure(text="+")


class LevelsTree(ttk.Treeview):
    def __init__(self, parent, *args, **kwargs):
        ttk.Treeview.__init__(self, parent, *args, **kwargs)

        self.popup_menu = tk.Menu(self, tearoff=0)
        # self.popup_menu.add_command(label="Rename List Node",
        #            command=self.rename)
        # self.popup_menu.add_command(label="Delete Room", command=self.delete_selected)
        # self.popup_menu.add_command(label="Add Room", command=self.add_room)

        self.bind("<Button-3>", self.popup)  # Button-2 on Aqua

    def popup(self, event):
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
        finally:
            self.popup_menu.grab_release()

    def rename(self):
        for i in self.selection()[::-1]:
            self.rename_dialog()

    # def delete_selected(self):
    #    item_iid = self.selection()[0]
    #    parent_iid = self.parent(item_iid)  # gets selected room
    #    if parent_iid:
    #        if (item_iid==LevelsTab.last_selected_room):
    #            LevelsTab.canvas.grid_remove()
    #            LevelsTab.canvas_dual.grid_remove()
    #            LevelsTab.foreground_label.grid_remove()
    #            LevelsTab.background_label.grid_remove()
    #        self.delete(item_iid)
    #
    # def add_room(self):
    #    item_iid = self.tree_levels.selection()[0]
    #    parent_iid = self.tree_levels.parent(item_iid)  # gets selected room
    #    if parent_iid:
    #        edited = self.insert(
    #            parent_iid,
    #            self.tree_levels.index(item_iid),
    #            text="room",
    #            values=room_save,
    #        )
    #    #self.selection_set(0, 'end')

    def rename_dialog(self):
        # First check if a blank space was selected
        entry_index = self.focus()
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
        for child in self.get_children():
            if child == entry_index:
                values = self.item(child)["values"]
                break

        entry_name = str(values[0])
        entry_note = ""
        entry = str(values[0]).split("//", 2)
        if len(entry) > 1:
            entry_name = entry[0]
            entry_note = entry[1]

        col1_lbl = tk.Label(win, text="Entry: ")
        col1_ent = tk.Entry(win)
        col1_ent.insert(0, entry_name)  # Default is column 1's current value
        col1_lbl.grid(row=0, column=0)
        col1_ent.grid(row=0, column=1)

        col2_lbl = tk.Label(win, text="Note Name: ")
        col2_ent = tk.Entry(win)
        col2_ent.insert(0, entry_note)  # Default is column 2's current value
        col2_lbl.grid(row=0, column=2)
        col2_ent.grid(row=0, column=3)

        def update_then_destroy():
            if self.confirm_entry(self, col1_ent.get(), col2_ent.get()):
                win.destroy()

        ok_button = tk.Button(win, text="Ok")
        ok_button.bind("<Button-1>", lambda e: update_then_destroy())
        ok_button.grid(row=1, column=1)

        cancel_button = tk.Button(win, text="Cancel")
        cancel_button.bind("<Button-1>", lambda c: win.destroy())
        cancel_button.grid(row=1, column=3)

    def confirm_entry(self, entry1, entry2, entry3):
        ####
        # Whatever validation you need
        ####

        # Grab the current index in the tree
        current_index = self.index(self.focus())

        # Remove it from the tree
        self.delete(self.focus())

        # Put it back in with the upated values
        self.insert(
            "", current_index, values=(str("\\" + str(entry1) + " //" + str(entry2)))
        )
        self.save_needed = True

        return True

    def center(self, toplevel):
        toplevel.update_idletasks()

        # Tkinter way to find the screen resolution
        # screen_width = toplevel.winfo_screenwidth()
        # screen_height = toplevel.winfo_screenheight()

        # find the screen resolution
        screen_width = 1280
        screen_height = 720

        size = tuple(int(_) for _ in toplevel.geometry().split("+")[0].split("x"))
        x = screen_width / 2 - size[0] / 2
        y = screen_height / 2 - size[1] / 2

        toplevel.geometry("+%d+%d" % (x, y))


class RulesTree(ttk.Treeview):
    def __init__(self, parent, *args, **kwargs):
        ttk.Treeview.__init__(self, parent, *args, **kwargs)

        self.popup_menu = tk.Menu(self, tearoff=0)
        self.popup_menu.add_command(label="Add", command=self.add)
        self.popup_menu.add_command(label="Delete", command=self.delete_selected)

        self.bind("<Button-3>", self.popup)  # Button-2 on Aqua

    def popup(self, event):
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
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

    def add(self):
        edited = self.insert(
            "",
            "end",
            values=["COMMENT", "VAL", "// COMMENT"],
        )
        # self.selection_set(0, 'end')

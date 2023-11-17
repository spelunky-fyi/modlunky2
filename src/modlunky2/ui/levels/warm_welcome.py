import tkinter as tk
from tkinter import ttk


class WarmWelcome(tk.Frame):
    def __init__(self, parent, on_open, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main_frame = tk.Frame(self, bg="black")
        main_frame.grid(row=0, column=0, sticky="news")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        self.welcome_label_title = tk.Label(
            main_frame,
            text=("Spelunky 2 Level Editor"),
            anchor="center",
            bg="black",
            fg="white",
            font=("Arial", 45),
        )
        self.welcome_label_title.grid(
            row=0, column=0, sticky="nwe", ipady=30, padx=(10, 10)
        )

        self.welcome_label = tk.Label(
            main_frame,
            text=(
                "Welcome to the Spelunky 2 Level Editor!\n"
                "Created by JackHasWifi with lots of help from "
                "Garebear, Fingerspit, Wolfo, and the community.\n\n "
                "NOTICE: Saving will save "
                "changes to a file in your selected pack and never overwrite its extracts counterpart.\n"
                "BIGGER NOTICE: Please make backups of your files. This is still in beta stages.."
            ),
            anchor="center",
            bg="black",
            fg="white",
            font=("Arial", 12),
        )
        self.welcome_label.grid(row=1, column=0, sticky="nwe", ipady=30, padx=(10, 10))

        self.button_open = ttk.Button(main_frame, text="Open Editor", command=on_open)
        self.button_open.grid(
            row=2, column=0, sticky="news", ipady=30, padx=(20, 20), pady=(20, 20)
        )

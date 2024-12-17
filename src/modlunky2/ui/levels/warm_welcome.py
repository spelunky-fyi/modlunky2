import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

from modlunky2.constants import BASE_DIR

IMAGE_PATH = BASE_DIR / "static/images"


class WarmWelcome(tk.Frame):
    def __init__(self, parent, on_open, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main_frame = tk.Frame(self, bg="black")
        main_frame.grid(row=0, column=0, sticky="news")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        self.img = Image.open(IMAGE_PATH / "leveleditor.png")
        self.background_image = ImageTk.PhotoImage(self.img)

        self.background_image_label = tk.Label(main_frame, image=self.background_image)

        def resize_image(event):
            new_width = event.width
            new_height = event.height

            img = self.img.resize((new_width, new_height))
            background_image = ImageTk.PhotoImage(img)

            self.background_image_label.config(image=background_image)
            self.background_image_label.image = background_image

        self.background_image_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.background_image_label.bind("<Configure>", resize_image)

        self.button_open = ttk.Button(main_frame, text="Open Editor", command=on_open)
        self.button_open.grid(
            row=2, column=0, sticky="ews", ipady=20, padx=(20, 20), pady=(10, 10)
        )

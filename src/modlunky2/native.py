import logging
from tkinter import CENTER, Button, Label, Tk
from webbrowser import open_new_tab

from PIL import Image, ImageTk

from .constants import APP_DIR


class NativeUI:
    def __init__(self, url):
        self._shutdown_handlers = []
        self._shutting_down = False
        self.url = url

        self.root = Tk()
        self.root.title("Modlunky 2")
        self.root.geometry('200x100')
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.resizable(False, False)

        self.bg_img = ImageTk.PhotoImage(Image.open(APP_DIR / "static/images/bg_cave.png"))
        self.background = Label(self.root, image=self.bg_img)
        self.background.place(x=0, y=0, relwidth=1, relheight=1)

        self.open_button = Button(
            self.background, text="Open UI",
            justify=CENTER,
            command=self.open_url,
        )
        self.open_button.pack(expand=True)

    def open_url(self):
        open_new_tab(self.url)

    def quit(self):
        if self._shutting_down:
            return

        self._shutting_down = True
        logging.info("Shutting Down.")
        for handler in self._shutdown_handlers:
            handler()

        self.root.quit()
        self.root.destroy()

    def register_shutdown_handler(self, func):
        self._shutdown_handlers.append(func)

    def mainloop(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.quit()

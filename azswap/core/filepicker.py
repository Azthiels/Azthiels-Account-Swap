"""Native Windows file-open dialog (tkinter), run from a worker thread."""
from .paths import DATA_DIR


def pick_file(filetypes, title: str) -> str | None:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        path = filedialog.askopenfilename(title=title, filetypes=list(filetypes), initialdir=str(DATA_DIR))
    finally:
        root.destroy()
    return path or None

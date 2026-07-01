#!/usr/bin/env python3
"""
GRB Data Inspector - a click-to-run window for data_inspect.py.

No command line needed. Launch this file (or "Data Inspector (GUI).bat"),
click "Open .data file(s)...", and see the typed resources inside each GRB
`.data`: name, TYPE (Mesh / TextureMap / BuildTable / Cloth / ...), ClassID,
and size.

GRB `.data` payloads are Oodle-compressed. The tool loads the game's
`oo2core_7_win64.dll` to read them - it auto-finds the DLL by searching up from
the file you open (it lives in the game folder). If it can't find it, use
"Set Oodle DLL..." to point at it once. See ../reference/resource-type-ids.md.
"""
import os, sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, font

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_inspect

INTRO = (
    "GRB Data Inspector\n"
    "Open one or more GRB `.data` files (the unpacked forge entries, named\n"
    "like  30091_-_WI_HDG_P12_Main.data ) and it lists the typed resources\n"
    "inside each: name, TYPE, ClassID, and size.\n\n"
    "  -  Open .data file(s)...   inspect one or many\n"
    "  -  Set Oodle DLL...        only if the DLL can't be auto-found\n\n"
    "GRB .data is Oodle-compressed; the tool uses the game's oo2core_7_win64.dll\n"
    "(auto-located from the file's folder) to read it.\n"
)

DATA_TYPES = [("GRB data", "*.data"), ("All files", "*.*")]
DLL_TYPES = [("Oodle DLL", "oo2core_7_win64.dll"), ("DLL", "*.dll"), ("All files", "*.*")]


class App:
    def __init__(self, root):
        self.root = root
        self.oodle_override = None
        root.title("GRB Data Inspector")
        root.geometry("900x640")
        root.minsize(680, 480)

        bar = tk.Frame(root)
        bar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=8)
        tk.Button(bar, text="Open .data file(s)...", command=self.open_files,
                  width=20).pack(side=tk.LEFT)
        tk.Button(bar, text="Set Oodle DLL...", command=self.set_oodle,
                  width=16).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(bar, text="Save report...", command=self.save).pack(side=tk.RIGHT)
        tk.Button(bar, text="Clear", command=self.clear).pack(side=tk.RIGHT, padx=(0, 8))

        mono = font.nametofont("TkFixedFont").copy()
        mono.configure(size=10)
        self.out = scrolledtext.ScrolledText(root, wrap=tk.NONE, font=mono)
        self.out.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.out.insert(tk.END, INTRO)
        self.out.configure(state=tk.DISABLED)

        self.status = tk.Label(root, text="Ready.", anchor="w", relief=tk.SUNKEN)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def _show(self, text):
        self.out.configure(state=tk.NORMAL)
        self.out.delete("1.0", tk.END)
        self.out.insert(tk.END, text)
        self.out.configure(state=tk.DISABLED)

    def clear(self):
        self._show(INTRO)
        self.status.config(text="Ready.")

    def set_oodle(self):
        p = filedialog.askopenfilename(title="Locate oo2core_7_win64.dll (in your GRB folder)",
                                       filetypes=DLL_TYPES)
        if p:
            self.oodle_override = p
            self.status.config(text=f"Oodle DLL set: {p}")

    def open_files(self):
        paths = filedialog.askopenfilenames(title="Open GRB .data file(s)",
                                            filetypes=DATA_TYPES)
        if paths:
            self.inspect(list(paths))

    def inspect(self, paths):
        try:
            dll = data_inspect.find_oodle(paths[0], self.oodle_override)
            oodle = data_inspect.Oodle(dll)
            reports = [data_inspect.inspect(p, oodle) for p in paths]
            self._show("\n".join(reports))
            if not oodle.ok:
                self.status.config(text="No Oodle DLL found - compressed resources "
                                        "won't read. Use 'Set Oodle DLL...'.")
            else:
                self.status.config(text=f"{len(paths)} file(s)  |  Oodle: {os.path.basename(dll)}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save(self):
        text = self.out.get("1.0", tk.END)
        p = filedialog.asksaveasfilename(defaultextension=".txt",
                                         filetypes=[("Text", "*.txt")],
                                         title="Save report as...")
        if p:
            open(p, "w", encoding="utf-8").write(text)
            self.status.config(text=f"Saved: {p}")


def main():
    root = tk.Tk()
    app = App(root)
    args = [a for a in sys.argv[1:] if os.path.isfile(a)]
    if args:
        root.after(200, lambda: app.inspect(args))
    root.mainloop()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
GRB Cloth Inspector — a click-to-run window for cloth_inspect.py.

No command line needed. Launch this file (or "Cloth Inspector (GUI).bat"),
click "Open a cloth file...", and read what the cloth is. Use "Compare two..."
to diff two cloths side by side.

It reads GRB MotionCloth (.cloth) resources — the raw unpacked cloth `.data`
files (named like *_Cloth or Cloth_*). See ../docs/11-cloth-and-physics.md.
"""
import os, sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, font

# import the shared logic (same folder)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cloth_inspect

INTRO = (
    "GRB Cloth Inspector\n"
    "Point it at a GRB cloth file - a  *.Cloth  (what ATK writes when you unpack a\n"
    "cloth .data) or the cloth  .data  itself - and it tells you, in plain terms:\n"
    "how many cloth pieces (LODs), the mesh each is bound to, and the sim-cage size.\n\n"
    "  •  Open a cloth file…        inspect one cloth\n"
    "  •  Compare two cloth files…  see two cloths side by side\n\n"
    "Reskin note: the visible garment is a SEPARATE skeleton-skinned mesh that follows\n"
    "the low-res sim cage via a stored wrap (not yet validated in-game); rebinding a\n"
    "brand-new mesh is unsolved for GRB. Reshaping the vanilla garment while keeping the\n"
    "cage's points in order is the route that works today.\n\n"
    "Tip: a piece named  Sim_<Mesh>_LOD<n>  is bound to that exact mesh + LOD.\n"
)

CLOTH_TYPES = [("Cloth files", "*.Cloth"), ("Cloth data", "*.data"), ("All files", "*.*")]

class App:
    def __init__(self, root):
        self.root = root
        root.title("GRB Cloth Inspector")
        root.geometry("860x620")
        root.minsize(640, 460)

        bar = tk.Frame(root)
        bar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=8)
        tk.Button(bar, text="Open a cloth file…", command=self.open_one,
                  width=20).pack(side=tk.LEFT)
        tk.Button(bar, text="Compare two cloth files…", command=self.open_two,
                  width=24).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(bar, text="Save report…", command=self.save).pack(side=tk.RIGHT)
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

    def open_one(self):
        p = filedialog.askopenfilename(title="Open a GRB cloth (.data) file",
                                       filetypes=CLOTH_TYPES)
        if p:
            self.inspect(p)

    def open_two(self):
        a = filedialog.askopenfilename(title="Choose the FIRST cloth (A)",
                                       filetypes=CLOTH_TYPES)
        if not a:
            return
        b = filedialog.askopenfilename(title="Choose the SECOND cloth (B)",
                                       filetypes=CLOTH_TYPES)
        if not b:
            return
        self.compare(a, b)

    def inspect(self, path):
        try:
            self._show(cloth_inspect.report(path))
            self.status.config(text=os.path.basename(path))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def compare(self, a, b):
        try:
            self._show(cloth_inspect.diff(a, b))
            self.status.config(text=f"{os.path.basename(a)}  vs  {os.path.basename(b)}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save(self):
        text = self.out.get("1.0", tk.END)
        p = filedialog.asksaveasfilename(defaultextension=".txt",
                                         filetypes=[("Text", "*.txt")],
                                         title="Save report as…")
        if p:
            open(p, "w", encoding="utf-8").write(text)
            self.status.config(text=f"Saved: {p}")

def main():
    root = tk.Tk()
    app = App(root)
    # Files passed on the command line (e.g. dragged onto the .bat launcher)
    args = [a for a in sys.argv[1:] if os.path.isfile(a)]
    if len(args) == 1:
        root.after(200, lambda: app.inspect(args[0]))
    elif len(args) >= 2:
        root.after(200, lambda: app.compare(args[0], args[1]))
    root.mainloop()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
GRB Forge Inspector - a click-to-run window for forge_inspect.py.

No command line needed. Launch this file (or "Forge Inspector (GUI).bat").

  -  Open a forge...        summary: version, entry count, resource-type histogram
  -  Compare two forges...  diff by real file ID -> shared IDs are mod CONFLICTS
                            (or overrides, if one is a patch of the other)
  -  Save entries as CSV... dump every entry (id, type, name) of one forge

It reads only the forge INDEX, so even the 23 GB resources forge opens in a
moment. No Oodle DLL needed. See ../docs/06-game-load-and-reassembly.md and
../reference/resource-type-ids.md.
"""
import os, sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, font

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forge_inspect

INTRO = (
    "GRB Forge Inspector\n"
    "Open a .forge to see what's in it, or compare two to find conflicts.\n\n"
    "  -  Open a forge...         version, entry count, resource-type histogram\n"
    "  -  Compare two forges...   shared real file IDs = mod CONFLICTS\n"
    "                             (or overrides, if one is a patch of the other)\n"
    "  -  Save entries as CSV...  dump every entry (id, type, name)\n\n"
    "Reads only the forge index - fast even on the 23 GB resources forge.\n"
)

FORGE_TYPES = [("GRB forge", "*.forge"), ("All files", "*.*")]


class App:
    def __init__(self, root):
        self.root = root
        self.last_forge = None
        root.title("GRB Forge Inspector")
        root.geometry("900x640")
        root.minsize(680, 480)

        bar = tk.Frame(root)
        bar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=8)
        tk.Button(bar, text="Open a forge...", command=self.open_one, width=16).pack(side=tk.LEFT)
        tk.Button(bar, text="Compare two forges...", command=self.open_two, width=20).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(bar, text="Save entries as CSV...", command=self.save_csv, width=20).pack(side=tk.LEFT, padx=(8, 0))
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
        self._show(INTRO); self.status.config(text="Ready.")

    def open_one(self):
        p = filedialog.askopenfilename(title="Open a GRB .forge", filetypes=FORGE_TYPES)
        if not p:
            return
        self.status.config(text="Reading index..."); self.root.update_idletasks()
        try:
            self.last_forge = p
            self._show(forge_inspect.summary(p))
            self.status.config(text=os.path.basename(p))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def open_two(self):
        a = filedialog.askopenfilename(title="Choose forge A", filetypes=FORGE_TYPES)
        if not a:
            return
        b = filedialog.askopenfilename(title="Choose forge B", filetypes=FORGE_TYPES)
        if not b:
            return
        self.status.config(text="Diffing..."); self.root.update_idletasks()
        try:
            self._show(forge_inspect.diff(a, b))
            self.status.config(text=f"{os.path.basename(a)}  vs  {os.path.basename(b)}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save_csv(self):
        src = self.last_forge or filedialog.askopenfilename(title="Forge to export", filetypes=FORGE_TYPES)
        if not src:
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                         title="Save entries as CSV")
        if p:
            try:
                self.status.config(text=forge_inspect.to_csv(src, p))
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def save(self):
        text = self.out.get("1.0", tk.END)
        p = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")],
                                         title="Save report as...")
        if p:
            open(p, "w", encoding="utf-8").write(text)
            self.status.config(text=f"Saved: {p}")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

import tkinter as tk
from tkinter import ttk, messagebox
import csv
from datetime import datetime
import os

FILE_NAME = "expenses.csv"

# ---------------- CATEGORIES ----------------
CATEGORIES = {
    "Groceries": ["Food", "Drinks"],
    "Cosmetics": ["Makeup", "Skincare"],
    "Pharmaceuticals": ["Medicine"],
    "Toys": ["Kids toys"],
    "Car": ["Fuel", "Maintenance"],
    "Clothes": ["Adults", "Kids"]
}


class ExpenseTracker(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Expense Tracker")
        self.geometry("800x550")

        self.breakdown = []

        self.ensure_file()
        self.create_widgets()

    # ---------------- FILE ----------------
    def ensure_file(self):
        if not os.path.exists(FILE_NAME):
            with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["date", "store", "total", "category", "sub_category", "amount"]
                )

    # ---------------- UI ----------------
    def create_widgets(self):

        # ========= EXPENSE FORM =========
        form = ttk.LabelFrame(self, text="Expense")
        form.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        self.columnconfigure(0, weight=1)

        for i in range(6):
            form.columnconfigure(i, weight=1)

        ttk.Label(form, text="Date").grid(row=0, column=0, sticky="w")
        self.date_entry = ttk.Entry(form)
        self.date_entry.grid(row=0, column=1, sticky="ew")
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))

        ttk.Label(form, text="Store / Recipient").grid(row=0, column=2, sticky="w")
        self.store_entry = ttk.Entry(form)
        self.store_entry.grid(row=0, column=3, columnspan=3, sticky="ew")

        ttk.Label(form, text="Total amount").grid(row=1, column=0, sticky="w")
        self.total_entry = ttk.Entry(form)
        self.total_entry.grid(row=1, column=1, sticky="ew")

        # ========= CATEGORY MANAGER =========
        cat_frame = ttk.LabelFrame(self, text="Manage categories")
        cat_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        for i in range(6):
            cat_frame.columnconfigure(i, weight=1)

        ttk.Label(cat_frame, text="Category").grid(row=0, column=0, sticky="w")
        self.new_cat_entry = ttk.Entry(cat_frame)
        self.new_cat_entry.grid(row=0, column=1, sticky="ew")

        ttk.Label(cat_frame, text="Sub-category").grid(row=0, column=2, sticky="w")
        self.new_sub_entry = ttk.Entry(cat_frame)
        self.new_sub_entry.grid(row=0, column=3, sticky="ew")

        ttk.Button(cat_frame, text="Add / Update",
                   command=self.add_category).grid(row=0, column=4, padx=5)

        # ========= BREAKDOWN =========
        bd_frame = ttk.LabelFrame(self, text="Breakdown by purpose")
        bd_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        for i in range(8):
            bd_frame.columnconfigure(i, weight=1)

        ttk.Label(bd_frame, text="Category").grid(row=0, column=0, sticky="w")
        self.category_cb = ttk.Combobox(
            bd_frame, values=list(CATEGORIES.keys()), state="readonly"
        )
        self.category_cb.grid(row=0, column=1, sticky="ew")
        self.category_cb.bind("<<ComboboxSelected>>", self.update_subcats)

        ttk.Label(bd_frame, text="Sub-category").grid(row=0, column=2, sticky="w")
        self.subcat_cb = ttk.Combobox(bd_frame, state="readonly")
        self.subcat_cb.grid(row=0, column=3, sticky="ew")

        ttk.Label(bd_frame, text="Amount").grid(row=0, column=4, sticky="w")
        self.amount_entry = ttk.Entry(bd_frame, width=10)
        self.amount_entry.grid(row=0, column=5, sticky="ew")

        ttk.Button(bd_frame, text="Add part",
                   command=self.add_breakdown).grid(row=0, column=6, padx=5)

        # ========= TABLE =========
        self.tree = ttk.Treeview(
            self, columns=("cat", "sub", "amt"), show="headings", height=8
        )
        self.tree.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)

        self.rowconfigure(3, weight=1)

        self.tree.heading("cat", text="Category")
        self.tree.heading("sub", text="Sub-category")
        self.tree.heading("amt", text="Amount")

        # ========= SAVE =========
        ttk.Button(self, text="Save expense",
                   command=self.save_expense).grid(row=4, column=0, pady=10)

    # ---------------- CATEGORY LOGIC ----------------
    def add_category(self):
        cat = self.new_cat_entry.get().strip()
        sub = self.new_sub_entry.get().strip()

        if not cat:
            messagebox.showerror("Error", "Category name required.")
            return

        if cat not in CATEGORIES:
            CATEGORIES[cat] = []

        if sub:
            if sub not in CATEGORIES[cat]:
                CATEGORIES[cat].append(sub)

        self.category_cb["values"] = list(CATEGORIES.keys())

        self.new_cat_entry.delete(0, tk.END)
        self.new_sub_entry.delete(0, tk.END)

        messagebox.showinfo("Saved", "Category updated.")

    # ---------------- BREAKDOWN ----------------
    def update_subcats(self, _):
        cat = self.category_cb.get()
        self.subcat_cb["values"] = CATEGORIES.get(cat, [])
        self.subcat_cb.set("")

    def add_breakdown(self):
        cat = self.category_cb.get()
        sub = self.subcat_cb.get()
        amt = self.amount_entry.get()

        if not cat or not sub or not amt:
            messagebox.showerror("Error", "Fill all breakdown fields.")
            return

        try:
            amt = float(amt)
        except ValueError:
            messagebox.showerror("Error", "Amount must be numeric.")
            return

        self.breakdown.append((cat, sub, amt))
        self.tree.insert("", "end", values=(cat, sub, f"{amt:.2f}"))
        self.amount_entry.delete(0, tk.END)

    # ---------------- SAVE ----------------
    def save_expense(self):
        date = self.date_entry.get()
        store = self.store_entry.get()
        total = self.total_entry.get()

        if not date or not store or not total:
            messagebox.showerror("Error", "Fill date, store and total.")
            return

        try:
            total = float(total)
        except ValueError:
            messagebox.showerror("Error", "Total must be numeric.")
            return

        if not self.breakdown:
            messagebox.showerror("Error", "Add at least one breakdown line.")
            return

        s = sum(x[2] for x in self.breakdown)
        if round(s, 2) != round(total, 2):
            messagebox.showerror(
                "Error",
                f"Breakdown sum {s:.2f} does not match total {total:.2f}"
            )
            return

        with open(FILE_NAME, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for cat, sub, amt in self.breakdown:
                writer.writerow([date, store, total, cat, sub, amt])

        messagebox.showinfo("Saved", "Expense saved.")

        self.breakdown.clear()
        for i in self.tree.get_children():
            self.tree.delete(i)

        self.total_entry.delete(0, tk.END)
        self.store_entry.delete(0, tk.END)


if __name__ == "__main__":
    app = ExpenseTracker()
    app.mainloop()

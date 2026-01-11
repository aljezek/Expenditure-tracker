import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import json, os, csv
from datetime import datetime

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "people": f"{DATA_DIR}/people.json",
    "stores": f"{DATA_DIR}/stores.json",
    "categories": f"{DATA_DIR}/categories.json",
    "settings": f"{DATA_DIR}/settings.json",
}

EXPENSE_FILE = "expenses.csv"


# ---------------- DEFAULT DATA ----------------
DEFAULT_DATA = {
    "people": ["Tinka", "Aljaž"],
    "categories": {
        "Groceries": ["Food", "Drinks"],
        "Cosmetics": ["Makeup", "Skincare"],
        "Pharmaceuticals": ["Medicine"],
    },
    "stores": {
        "DM": {"category": "Cosmetics", "sub": "Makeup"},
        "Spar": {"category": "Groceries", "sub": "Food"},
    },
    "settings": {
        "currency": "€",
        "date_format": "%d.%m.%Y",
    },
}


# ---------------- UTIL ----------------
def load_json(name):
    if not os.path.exists(FILES[name]):
        save_json(name, DEFAULT_DATA[name])
    with open(FILES[name], "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(name, data):
    with open(FILES[name], "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------------- APP ----------------
class ExpenseTracker(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Expense Tracker Pro")
        self.geometry("900x650")

        # load data
        self.people = load_json("people")
        self.categories = load_json("categories")
        self.stores = load_json("stores")
        self.settings = load_json("settings")

        self.breakdown = []

        self.ensure_expense_file()
        self.create_menu()
        self.create_tabs()

    # ---------------- FILE ----------------
    def ensure_expense_file(self):
        if not os.path.exists(EXPENSE_FILE):
            with open(EXPENSE_FILE, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["date", "person", "store", "total",
                     "category", "sub_category", "amount"]
                )

    # ---------------- MENU ----------------
    def create_menu(self):
        menubar = tk.Menu(self)

        settings_menu = tk.Menu(menubar, tearoff=0)
        for cur in ["€", "$", "£", "CHF"]:
            settings_menu.add_command(
                label=f"Currency: {cur}",
                command=lambda c=cur: self.set_currency(c),
            )
        menubar.add_cascade(label="Settings", menu=settings_menu)

        self.config(menu=menubar)

    def set_currency(self, cur):
        self.settings["currency"] = cur
        save_json("settings", self.settings)
        self.currency_label.config(text=cur)

    # ---------------- TABS ----------------
    def create_tabs(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)

        self.tab_expense = ttk.Frame(self.tabs)
        self.tab_manage = ttk.Frame(self.tabs)

        self.tabs.add(self.tab_expense, text="Expenses")
        self.tabs.add(self.tab_manage, text="Management")

        self.build_expense_tab()
        self.build_manage_tab()

    # ==========================================================
    # EXPENSE TAB
    # ==========================================================
    def build_expense_tab(self):
        f = self.tab_expense
        for i in range(6):
            f.columnconfigure(i, weight=1)

        # ---- HEADER ----
        ttk.Label(f, text="Person").grid(row=0, column=0, sticky="w")
        self.person_cb = ttk.Combobox(f, values=self.people, state="readonly")
        self.person_cb.grid(row=0, column=1, sticky="ew")
        self.person_cb.set(self.people[0])

        ttk.Label(f, text="Store").grid(row=0, column=2, sticky="w")
        self.store_cb = ttk.Combobox(f, values=list(self.stores.keys()), state="readonly")
        self.store_cb.grid(row=0, column=3, sticky="ew")
        self.store_cb.bind("<<ComboboxSelected>>", self.apply_store_defaults)

        ttk.Label(f, text="Date").grid(row=0, column=4, sticky="w")
        self.date_entry = DateEntry(
            f, date_pattern="dd.mm.yyyy"
        )
        self.date_entry.grid(row=0, column=5, sticky="ew")

        # ---- TOTAL ----
        ttk.Label(f, text="Total").grid(row=1, column=0, sticky="w")
        self.total_entry = ttk.Entry(f)
        self.total_entry.grid(row=1, column=1, sticky="ew")
        self.total_entry.bind("<KeyRelease>", self.update_remainder)

        self.currency_label = ttk.Label(f, text=self.settings["currency"])
        self.currency_label.grid(row=1, column=2, sticky="w")

        self.remainder_label = ttk.Label(f, text="Remainder: 0.00")
        self.remainder_label.grid(row=1, column=3, columnspan=2, sticky="w")

        # ---- BREAKDOWN ----
        ttk.Label(f, text="Category").grid(row=2, column=0, sticky="w")
        self.cat_cb = ttk.Combobox(f, values=list(self.categories.keys()), state="readonly")
        self.cat_cb.grid(row=2, column=1, sticky="ew")
        self.cat_cb.bind("<<ComboboxSelected>>", self.update_subcats)

        ttk.Label(f, text="Sub-category").grid(row=2, column=2, sticky="w")
        self.sub_cb = ttk.Combobox(f, state="readonly")
        self.sub_cb.grid(row=2, column=3, sticky="ew")

        ttk.Label(f, text="Amount").grid(row=2, column=4, sticky="w")
        self.amount_entry = ttk.Entry(f)
        self.amount_entry.grid(row=2, column=5, sticky="ew")

        ttk.Button(f, text="Add part", command=self.add_breakdown)\
            .grid(row=3, column=5, sticky="e")

        # ---- TABLE ----
        self.tree = ttk.Treeview(
            f, columns=("cat", "sub", "amt"), show="headings", height=10
        )
        self.tree.grid(row=4, column=0, columnspan=6, sticky="nsew", pady=5)

        self.tree.heading("cat", text="Category")
        self.tree.heading("sub", text="Sub")
        self.tree.heading("amt", text=f"Amount ({self.settings['currency']})")

        f.rowconfigure(4, weight=1)

        ttk.Button(f, text="Save Expense", command=self.save_expense)\
            .grid(row=5, column=5, sticky="e", pady=10)

    # ---------------- EXPENSE LOGIC ----------------
    def apply_store_defaults(self, _):
        store = self.store_cb.get()
        if store in self.stores:
            d = self.stores[store]
            self.cat_cb.set(d["category"])
            self.update_subcats()
            self.sub_cb.set(d.get("sub", ""))

    def update_subcats(self, _=None):
        cat = self.cat_cb.get()
        self.sub_cb["values"] = self.categories.get(cat, [])
        self.sub_cb.set("")

    def add_breakdown(self):
        cat = self.cat_cb.get()
        sub = self.sub_cb.get()
        amt = self.amount_entry.get()

        if not cat or not sub or not amt:
            messagebox.showerror("Error", "Fill category, sub-category and amount.")
            return
        try:
            amt = float(amt)
        except ValueError:
            messagebox.showerror("Error", "Amount must be numeric.")
            return

        self.breakdown.append((cat, sub, amt))
        self.tree.insert("", "end", values=(cat, sub, f"{amt:.2f}"))
        self.amount_entry.delete(0, tk.END)
        self.update_remainder()

    def update_remainder(self, _=None):
        try:
            total = float(self.total_entry.get())
        except:
            total = 0

        used = sum(x[2] for x in self.breakdown)
        rem = total - used
        self.remainder_label.config(
            text=f"Remainder: {rem:.2f} {self.settings['currency']}"
        )

    def save_expense(self):
        if not self.breakdown:
            messagebox.showerror("Error", "No breakdown added.")
            return

        try:
            total = float(self.total_entry.get())
        except:
            messagebox.showerror("Error", "Invalid total.")
            return

        used = sum(x[2] for x in self.breakdown)
        if round(total, 2) != round(used, 2):
            messagebox.showerror("Error", "Breakdown does not match total.")
            return

        date = self.date_entry.get()
        person = self.person_cb.get()
        store = self.store_cb.get()

        with open(EXPENSE_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for cat, sub, amt in self.breakdown:
                w.writerow([date, person, store, total, cat, sub, amt])

        messagebox.showinfo("Saved", "Expense saved.")

        self.breakdown.clear()
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.total_entry.delete(0, tk.END)
        self.update_remainder()

    # ==========================================================
    # MANAGEMENT TAB
    # ==========================================================
    def build_manage_tab(self):
        f = self.tab_manage

        ttk.Label(f, text="Add person").grid(row=0, column=0, sticky="w")
        self.new_person = ttk.Entry(f)
        self.new_person.grid(row=0, column=1)
        ttk.Button(f, text="Add", command=self.add_person).grid(row=0, column=2)

        ttk.Label(f, text="Add store").grid(row=1, column=0, sticky="w")
        self.new_store = ttk.Entry(f)
        self.new_store.grid(row=1, column=1)

        ttk.Label(f, text="Default category").grid(row=1, column=2)
        self.store_cat = ttk.Combobox(f, values=list(self.categories.keys()))
        self.store_cat.grid(row=1, column=3)

        ttk.Label(f, text="Default sub").grid(row=1, column=4)
        self.store_sub = ttk.Entry(f)
        self.store_sub.grid(row=1, column=5)

        ttk.Button(f, text="Add store", command=self.add_store)\
            .grid(row=1, column=6)

    # ---------------- MANAGEMENT LOGIC ----------------
    def add_person(self):
        p = self.new_person.get().strip()
        if not p:
            return
        if p not in self.people:
            self.people.append(p)
            save_json("people", self.people)
            self.person_cb["values"] = self.people
        self.new_person.delete(0, tk.END)

    def add_store(self):
        name = self.new_store.get().strip()
        cat = self.store_cat.get().strip()
        sub = self.store_sub.get().strip()

        if not name or not cat:
            messagebox.showerror("Error", "Store and category required.")
            return

        self.stores[name] = {"category": cat, "sub": sub}
        save_json("stores", self.stores)

        self.store_cb["values"] = list(self.stores.keys())

        self.new_store.delete(0, tk.END)
        self.store_sub.delete(0, tk.END)


if __name__ == "__main__":
    app = ExpenseTracker()
    app.mainloop()

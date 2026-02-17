import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import uuid4

import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import DateEntry

from data_store import CSV_HEADERS
from utils import decimal_to_str, parse_decimal


class ExpensesMixin:
    def build_expense_tab(self):
        f = self.tab_expense
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)

        setup = ttk.LabelFrame(f, text="Setup", padding=10)
        setup.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        for i in range(6):
            setup.columnconfigure(i, weight=1)

        ttk.Label(setup, text="Person").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.person_cb = ttk.Combobox(setup, values=self.people, state="readonly")
        self.person_cb.grid(row=0, column=1, sticky="ew", padx=6, pady=4)
        if self.people:
            self.person_cb.set(self.people[0])

        ttk.Label(setup, text="Store").grid(row=0, column=2, sticky="w", padx=6, pady=4)
        self.store_cb = ttk.Combobox(setup, values=list(self.stores.keys()), state="readonly")
        self.store_cb.grid(row=0, column=3, sticky="ew", padx=6, pady=4)
        self.store_cb.bind("<<ComboboxSelected>>", self.apply_store_defaults)

        ttk.Label(setup, text="Date").grid(row=0, column=4, sticky="w", padx=6, pady=4)
        self.date_entry = DateEntry(setup, date_pattern="dd.mm.yyyy")
        self.date_entry.grid(row=0, column=5, sticky="ew", padx=6, pady=4)

        ttk.Label(setup, text="Total").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.total_entry = ttk.Entry(setup)
        self.total_entry.grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        self.total_entry.bind("<KeyRelease>", self.update_remainder)

        self.currency_label = ttk.Label(setup, text=self.settings.get("currency", "EUR"))
        self.currency_label.grid(row=1, column=2, sticky="w", padx=6, pady=4)

        self.remainder_label = ttk.Label(setup, text="Remainder: 0.00")
        self.remainder_label.grid(row=1, column=3, columnspan=3, sticky="w", padx=6, pady=4)

        ttk.Label(setup, text="Category").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        self.cat_cb = ttk.Combobox(setup, values=list(self.categories.keys()), state="readonly")
        self.cat_cb.grid(row=2, column=1, sticky="ew", padx=6, pady=4)
        self.cat_cb.bind("<<ComboboxSelected>>", self.update_subcats)

        ttk.Label(setup, text="Sub-category").grid(row=2, column=2, sticky="w", padx=6, pady=4)
        self.sub_cb = ttk.Combobox(setup, state="readonly")
        self.sub_cb.grid(row=2, column=3, sticky="ew", padx=6, pady=4)

        ttk.Label(setup, text="Amount").grid(row=2, column=4, sticky="w", padx=6, pady=4)
        self.amount_entry = ttk.Entry(setup)
        self.amount_entry.grid(row=2, column=5, sticky="ew", padx=6, pady=4)

        btn_row = ttk.Frame(setup)
        btn_row.grid(row=3, column=0, columnspan=6, sticky="e", padx=6, pady=4)
        ttk.Button(btn_row, text="Add part", command=self.add_breakdown).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Remove selected", command=self.remove_selected_breakdown).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Clear", command=self.clear_expense_form).pack(side="left", padx=4)

        grid_frame = ttk.LabelFrame(f, text="Breakdown", padding=8)
        grid_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(grid_frame, columns=("cat", "sub", "amt"), show="headings", height=6)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.heading("cat", text="Category")
        self.tree.heading("sub", text="Sub")
        self.tree.heading("amt", text=f"Amount ({self.settings.get('currency', 'EUR')})")

        scrollbar = ttk.Scrollbar(grid_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        action_row = ttk.Frame(f)
        action_row.grid(row=2, column=0, sticky="e", padx=6, pady=(0, 6))
        ttk.Button(action_row, text="Save Expense", command=self.save_expense).pack(side="left")

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
            amt = parse_decimal(amt)
            if amt <= 0:
                raise InvalidOperation
        except (ValueError, InvalidOperation):
            messagebox.showerror("Error", "Amount must be a positive number.")
            return

        self.breakdown.append((cat, sub, amt))
        self.tree.insert("", "end", values=(cat, sub, decimal_to_str(amt)))
        self.amount_entry.delete(0, tk.END)
        self.update_remainder()

    def remove_selected_breakdown(self):
        selected = self.tree.selection()
        if not selected:
            return

        indexes = sorted((self.tree.index(item) for item in selected), reverse=True)
        for item in selected:
            self.tree.delete(item)
        for idx in indexes:
            if 0 <= idx < len(self.breakdown):
                del self.breakdown[idx]
        self.update_remainder()

    def clear_expense_form(self):
        self.breakdown.clear()
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.total_entry.delete(0, tk.END)
        self.amount_entry.delete(0, tk.END)
        self.cat_cb.set("")
        self.sub_cb.set("")
        self.store_cb.set("")
        self.update_remainder()

    def update_remainder(self, _=None):
        try:
            total = parse_decimal(self.total_entry.get())
        except (ValueError, InvalidOperation):
            total = Decimal("0.00")

        used = sum((x[2] for x in self.breakdown), Decimal("0.00"))
        rem = total - used
        self.remainder_label.config(
            text=f"Remainder: {decimal_to_str(rem)} {self.settings.get('currency', 'EUR')}"
        )

    def save_expense(self):
        if not self.breakdown:
            messagebox.showerror("Error", "No breakdown added.")
            return

        try:
            total = parse_decimal(self.total_entry.get())
            if total <= 0:
                raise InvalidOperation
        except (ValueError, InvalidOperation):
            messagebox.showerror("Error", "Invalid total.")
            return

        used = sum((x[2] for x in self.breakdown), Decimal("0.00"))
        if total != used:
            messagebox.showerror("Error", "Breakdown does not match total.")
            return

        date = self.date_entry.get()
        person = self.person_cb.get()
        store = self.store_cb.get()
        expense_id = uuid4().hex[:8]
        created_at = datetime.now().isoformat(timespec="seconds")
        line_count = len(self.breakdown)

        with open("expenses.csv", "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            for cat, sub, amt in self.breakdown:
                w.writerow(
                    {
                        "date": date,
                        "person": person,
                        "store": store,
                        "total": decimal_to_str(total),
                        "category": cat,
                        "sub_category": sub,
                        "amount": decimal_to_str(amt),
                        "expense_id": expense_id,
                        "created_at": created_at,
                    }
                )

        messagebox.showinfo("Saved", "Expense saved.")
        self.set_status(f"Saved expense {expense_id} with {line_count} lines.")
        self.clear_expense_form()
        self.refresh_history()

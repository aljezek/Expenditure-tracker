import csv
import json
import os
import tkinter as tk
from datetime import datetime
from decimal import Decimal, InvalidOperation
from tkinter import filedialog, messagebox, ttk
from uuid import uuid4

from tkcalendar import DateEntry

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "people": f"{DATA_DIR}/people.json",
    "stores": f"{DATA_DIR}/stores.json",
    "categories": f"{DATA_DIR}/categories.json",
    "settings": f"{DATA_DIR}/settings.json",
}

EXPENSE_FILE = "expenses.csv"
CSV_HEADERS = [
    "date",
    "person",
    "store",
    "total",
    "category",
    "sub_category",
    "amount",
    "expense_id",
    "created_at",
]


# ---------------- DEFAULT DATA ----------------
DEFAULT_DATA = {
    "people": ["Tinka", "Aljaz"],
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
        "currency": "EUR",
        "date_format": "%d.%m.%Y",
    },
}


# ---------------- UTIL ----------------
def load_json(name):
    if not os.path.exists(FILES[name]):
        save_json(name, DEFAULT_DATA[name])
    try:
        with open(FILES[name], "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        save_json(name, DEFAULT_DATA[name])
        return DEFAULT_DATA[name]


def save_json(name, data):
    with open(FILES[name], "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def parse_decimal(value):
    normalized = str(value).strip().replace(",", ".")
    amount = Decimal(normalized)
    return amount.quantize(Decimal("0.01"))


def decimal_to_str(value):
    return f"{value:.2f}"


# ---------------- APP ----------------
class ExpenseTracker(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Expense Tracker MVP")
        self.geometry("1220x780")
        self.minsize(980, 680)

        self.people = load_json("people")
        self.categories = load_json("categories")
        self.stores = load_json("stores")
        self.settings = load_json("settings")

        self.breakdown = []
        self.filtered_records = []

        self.ensure_expense_file()
        self.create_menu()
        self.create_tabs()

    # ---------------- FILE ----------------
    def ensure_expense_file(self):
        if not os.path.exists(EXPENSE_FILE):
            with open(EXPENSE_FILE, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                writer.writeheader()
            return

        with open(EXPENSE_FILE, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            old_headers = reader.fieldnames or []
            rows = list(reader)

        if old_headers == CSV_HEADERS:
            return

        migrated_rows = []
        for row in rows:
            migrated = {h: "" for h in CSV_HEADERS}
            for h in old_headers:
                if h in migrated:
                    migrated[h] = row.get(h, "")
            if not migrated["person"]:
                migrated["person"] = "Unknown"
            if not migrated["expense_id"]:
                migrated["expense_id"] = uuid4().hex[:8]
            if not migrated["created_at"]:
                migrated["created_at"] = datetime.now().isoformat(timespec="seconds")
            migrated_rows.append(migrated)

        with open(EXPENSE_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
            writer.writerows(migrated_rows)

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
        self.tree.heading("amt", text=f"Amount ({cur})")
        self.history_tree.heading("amount", text=f"Amount ({cur})")
        self.history_tree.heading("total", text=f"Expense total ({cur})")
        self.update_remainder()
        self.refresh_history()

    # ---------------- TABS ----------------
    def create_tabs(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)

        self.tab_expense = ttk.Frame(self.tabs, padding=10)
        self.tab_history = ttk.Frame(self.tabs, padding=10)
        self.tab_manage = ttk.Frame(self.tabs, padding=10)

        self.tabs.add(self.tab_expense, text="Expenses")
        self.tabs.add(self.tab_history, text="History")
        self.tabs.add(self.tab_manage, text="Management")

        self.build_expense_tab()
        self.build_history_tab()
        self.build_manage_tab()

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, anchor="w").pack(fill="x", padx=8, pady=(0, 8))

    def set_status(self, text):
        self.status_var.set(text)

    # ==========================================================
    # EXPENSE TAB
    # ==========================================================
    def build_expense_tab(self):
        f = self.tab_expense
        for i in range(6):
            f.columnconfigure(i, weight=1)
        f.rowconfigure(4, weight=1)

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

        self.currency_label = ttk.Label(f, text=self.settings.get("currency", "EUR"))
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
        ttk.Button(f, text="Remove selected", command=self.remove_selected_breakdown)\
            .grid(row=3, column=4, sticky="e")
        ttk.Button(f, text="Clear", command=self.clear_expense_form)\
            .grid(row=3, column=3, sticky="e")

        # ---- TABLE ----
        self.tree = ttk.Treeview(
            f, columns=("cat", "sub", "amt"), show="headings", height=10
        )
        self.tree.grid(row=4, column=0, columnspan=6, sticky="nsew", pady=5)

        self.tree.heading("cat", text="Category")
        self.tree.heading("sub", text="Sub")
        self.tree.heading("amt", text=f"Amount ({self.settings.get('currency', 'EUR')})")

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

        with open(EXPENSE_FILE, "a", newline="", encoding="utf-8") as f:
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

    def read_expenses(self):
        with open(EXPENSE_FILE, "r", newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def write_expenses(self, rows):
        with open(EXPENSE_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
            writer.writerows(rows)

    def parse_date_for_filter(self, date_str):
        for fmt in [self.settings.get("date_format", "%d.%m.%Y"), "%d.%m.%Y", "%Y-%m-%d", "%m/%d/%Y"]:
            try:
                return datetime.strptime(str(date_str).strip(), fmt).date()
            except ValueError:
                continue
        return None

    def get_selected_expense_id(self):
        selected = self.history_tree.selection()
        if not selected:
            return None
        return self.history_tree.item(selected[0], "values")[7]

    def refresh_history(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        records = self.read_expenses()
        from_date = self.parse_date_for_filter(self.filter_from.get()) if self.use_date_filter_var.get() else None
        to_date = self.parse_date_for_filter(self.filter_to.get()) if self.use_date_filter_var.get() else None
        selected_person = self.filter_person.get()

        self.filtered_records = []
        total_amount = Decimal("0.00")

        for row in records:
            row_date = self.parse_date_for_filter(row.get("date", ""))
            if row_date is None:
                continue
            if from_date and row_date < from_date:
                continue
            if to_date and row_date > to_date:
                continue
            if selected_person and selected_person != "All" and row.get("person", "") != selected_person:
                continue

            try:
                amount = parse_decimal(row.get("amount", "0"))
            except (ValueError, InvalidOperation):
                amount = Decimal("0.00")

            total_amount += amount
            self.filtered_records.append(row)

            self.history_tree.insert(
                "",
                "end",
                values=(
                    row.get("date", ""),
                    row.get("person", "Unknown"),
                    row.get("store", ""),
                    row.get("category", ""),
                    row.get("sub_category", ""),
                    row.get("amount", "0.00"),
                    row.get("total", "0.00"),
                    row.get("expense_id", ""),
                ),
            )

        cur = self.settings.get("currency", "EUR")
        self.history_summary.config(
            text=f"Records: {len(self.filtered_records)} | Total breakdown amount: {decimal_to_str(total_amount)} {cur}"
        )
        self.update_analytics(self.filtered_records)

    def reset_history_filters(self):
        self.use_date_filter_var.set(False)
        self.filter_person["values"] = ["All"] + self.people
        self.filter_person.set("All")
        self.refresh_history()

    def export_filtered_history(self):
        if not self.filtered_records:
            messagebox.showerror("Export", "No rows to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Export filtered history",
        )
        if not file_path:
            return

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
            writer.writerows(self.filtered_records)

        self.set_status(f"Exported {len(self.filtered_records)} rows to {file_path}")
        messagebox.showinfo("Export", f"Exported {len(self.filtered_records)} rows.")

    def open_edit_expense_dialog(self):
        expense_id = self.get_selected_expense_id()
        if not expense_id:
            messagebox.showerror("Edit", "Select a row first.")
            return

        all_rows = self.read_expenses()
        target_rows = [r for r in all_rows if r.get("expense_id", "") == expense_id]
        if not target_rows:
            messagebox.showerror("Edit", "Expense not found.")
            self.refresh_history()
            return

        first = target_rows[0]
        lines = []
        for row in target_rows:
            try:
                amount = parse_decimal(row.get("amount", "0"))
            except (ValueError, InvalidOperation):
                amount = Decimal("0.00")
            lines.append((row.get("category", ""), row.get("sub_category", ""), amount))

        dialog = tk.Toplevel(self)
        dialog.title(f"Edit Expense {expense_id}")
        dialog.geometry("760x500")
        dialog.transient(self)
        dialog.grab_set()
        for i in range(6):
            dialog.columnconfigure(i, weight=1)
        dialog.rowconfigure(2, weight=1)

        ttk.Label(dialog, text="Date").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        date_entry = DateEntry(dialog, date_pattern="dd.mm.yyyy")
        parsed_date = self.parse_date_for_filter(first.get("date", ""))
        if parsed_date:
            date_entry.set_date(parsed_date)
        date_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=6)

        ttk.Label(dialog, text="Person").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        person_cb = ttk.Combobox(dialog, values=self.people, state="readonly")
        person_cb.set(first.get("person", ""))
        person_cb.grid(row=0, column=3, sticky="ew", padx=(0, 8), pady=6)

        ttk.Label(dialog, text="Store").grid(row=0, column=4, sticky="w", padx=8, pady=6)
        store_cb = ttk.Combobox(dialog, values=list(self.stores.keys()), state="readonly")
        store_cb.set(first.get("store", ""))
        store_cb.grid(row=0, column=5, sticky="ew", padx=(0, 8), pady=6)

        line_tree = ttk.Treeview(dialog, columns=("cat", "sub", "amt"), show="headings", height=11)
        line_tree.grid(row=2, column=0, columnspan=6, sticky="nsew", padx=8, pady=6)
        line_tree.heading("cat", text="Category")
        line_tree.heading("sub", text="Sub-category")
        line_tree.heading("amt", text=f"Amount ({self.settings.get('currency', 'EUR')})")
        for cat, sub, amount in lines:
            line_tree.insert("", "end", values=(cat, sub, decimal_to_str(amount)))

        add_row = ttk.Frame(dialog)
        add_row.grid(row=3, column=0, columnspan=6, sticky="ew", padx=8)
        for i in range(6):
            add_row.columnconfigure(i, weight=1)
        ttk.Label(add_row, text="Category").grid(row=0, column=0, sticky="w")
        cat_cb = ttk.Combobox(add_row, values=list(self.categories.keys()), state="readonly")
        cat_cb.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Label(add_row, text="Sub").grid(row=0, column=2, sticky="w")
        sub_cb = ttk.Combobox(add_row, state="readonly")
        sub_cb.grid(row=0, column=3, sticky="ew", padx=(0, 8))
        ttk.Label(add_row, text="Amount").grid(row=0, column=4, sticky="w")
        amt_entry = ttk.Entry(add_row)
        amt_entry.grid(row=0, column=5, sticky="ew")

        def update_subs_in_dialog(_=None):
            sub_cb["values"] = self.categories.get(cat_cb.get(), [])
            sub_cb.set("")

        cat_cb.bind("<<ComboboxSelected>>", update_subs_in_dialog)

        total_var = tk.StringVar(value="")
        ttk.Label(dialog, textvariable=total_var).grid(row=4, column=0, columnspan=6, sticky="w", padx=8)

        def recompute_label():
            total = sum((line[2] for line in lines), Decimal("0.00"))
            total_var.set(
                f"Expense total: {decimal_to_str(total)} {self.settings.get('currency', 'EUR')} | Lines: {len(lines)}"
            )

        def add_line():
            category = cat_cb.get().strip()
            sub = sub_cb.get().strip()
            raw = amt_entry.get()
            if not category or not sub:
                messagebox.showerror("Edit", "Category and sub-category are required.", parent=dialog)
                return
            try:
                amount = parse_decimal(raw)
                if amount <= 0:
                    raise InvalidOperation
            except (ValueError, InvalidOperation):
                messagebox.showerror("Edit", "Amount must be a positive number.", parent=dialog)
                return
            lines.append((category, sub, amount))
            line_tree.insert("", "end", values=(category, sub, decimal_to_str(amount)))
            amt_entry.delete(0, tk.END)
            recompute_label()

        def remove_lines():
            selected = line_tree.selection()
            if not selected:
                return
            indexes = sorted((line_tree.index(item) for item in selected), reverse=True)
            for item in selected:
                line_tree.delete(item)
            for idx in indexes:
                if 0 <= idx < len(lines):
                    del lines[idx]
            recompute_label()

        footer = ttk.Frame(dialog)
        footer.grid(row=5, column=0, columnspan=6, sticky="e", padx=8, pady=(8, 8))
        ttk.Button(footer, text="Add line", command=add_line).pack(side="left", padx=4)
        ttk.Button(footer, text="Remove lines", command=remove_lines).pack(side="left", padx=4)

        def save_changes():
            if not lines:
                messagebox.showerror("Edit", "Expense must have at least one line.", parent=dialog)
                return
            person = person_cb.get().strip()
            store = store_cb.get().strip()
            if not person or not store:
                messagebox.showerror("Edit", "Person and store are required.", parent=dialog)
                return

            total = sum((line[2] for line in lines), Decimal("0.00"))
            created_at = first.get("created_at", datetime.now().isoformat(timespec="seconds"))
            replacement = []
            for cat, sub, amount in lines:
                replacement.append(
                    {
                        "date": date_entry.get().strip(),
                        "person": person,
                        "store": store,
                        "total": decimal_to_str(total),
                        "category": cat,
                        "sub_category": sub,
                        "amount": decimal_to_str(amount),
                        "expense_id": expense_id,
                        "created_at": created_at,
                    }
                )

            kept = [r for r in all_rows if r.get("expense_id", "") != expense_id]
            kept.extend(replacement)
            self.write_expenses(kept)
            dialog.destroy()
            self.refresh_history()
            self.set_status(f"Updated expense {expense_id}.")

        ttk.Button(footer, text="Save changes", command=save_changes).pack(side="left", padx=4)
        ttk.Button(footer, text="Cancel", command=dialog.destroy).pack(side="left", padx=4)
        recompute_label()

    def delete_selected_expense(self):
        expense_id = self.get_selected_expense_id()
        if not expense_id:
            messagebox.showerror("Delete", "Select a row first.")
            return

        all_rows = self.read_expenses()
        targets = [r for r in all_rows if r.get("expense_id", "") == expense_id]
        if not targets:
            self.refresh_history()
            return

        confirm = messagebox.askyesno(
            "Delete",
            f"Delete expense {expense_id} ({len(targets)} lines)? This cannot be undone.",
        )
        if not confirm:
            return

        kept = [r for r in all_rows if r.get("expense_id", "") != expense_id]
        self.write_expenses(kept)
        self.refresh_history()
        self.set_status(f"Deleted expense {expense_id}.")

    def update_analytics(self, rows):
        month_totals = {}
        category_totals_this_month = {}
        current_month = datetime.now().strftime("%Y-%m")
        currency = self.settings.get("currency", "EUR")

        for row in rows:
            row_date = self.parse_date_for_filter(row.get("date", ""))
            if not row_date:
                continue
            month_key = row_date.strftime("%Y-%m")
            try:
                amount = parse_decimal(row.get("amount", "0"))
            except (ValueError, InvalidOperation):
                amount = Decimal("0.00")
            month_totals[month_key] = month_totals.get(month_key, Decimal("0.00")) + amount
            if month_key == current_month:
                cat = row.get("category", "Unknown") or "Unknown"
                category_totals_this_month[cat] = category_totals_this_month.get(cat, Decimal("0.00")) + amount

        now = datetime.now()
        if now.month == 1:
            last_key = f"{now.year - 1}-12"
        else:
            last_key = f"{now.year}-{now.month - 1:02d}"

        this_total = month_totals.get(current_month, Decimal("0.00"))
        last_total = month_totals.get(last_key, Decimal("0.00"))
        if last_total == 0:
            change_text = "MoM: +100.00% (from 0)" if this_total > 0 else "MoM: 0.00%"
        else:
            pct = ((this_total - last_total) / last_total) * Decimal("100")
            sign = "+" if pct >= 0 else ""
            change_text = f"MoM: {sign}{decimal_to_str(pct)}%"

        top_category = "-"
        if category_totals_this_month:
            top = max(category_totals_this_month, key=category_totals_this_month.get)
            top_category = f"{top} ({decimal_to_str(category_totals_this_month[top])} {currency})"

        self.card_this_month.set(f"This month: {decimal_to_str(this_total)} {currency}")
        self.card_last_month.set(f"Last month: {decimal_to_str(last_total)} {currency}")
        self.card_change.set(change_text)
        self.card_top_category.set(f"Top category: {top_category}")
        self.render_monthly_chart(rows)

    def render_monthly_chart(self, rows):
        canvas = self.chart_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 600)
        height = max(canvas.winfo_height(), 170)

        month_totals = {}
        for row in rows:
            row_date = self.parse_date_for_filter(row.get("date", ""))
            if not row_date:
                continue
            key = row_date.strftime("%Y-%m")
            try:
                amount = parse_decimal(row.get("amount", "0"))
            except (ValueError, InvalidOperation):
                amount = Decimal("0.00")
            month_totals[key] = month_totals.get(key, Decimal("0.00")) + amount

        keys = sorted(month_totals.keys())[-6:]
        if not keys:
            canvas.create_text(width // 2, height // 2, text="No data for chart", fill="#666")
            return

        values = [month_totals[k] for k in keys]
        max_val = max(values)
        if max_val <= 0:
            max_val = Decimal("1")

        left, right, bottom, top = 40, 20, 28, 16
        chart_w = width - left - right
        chart_h = height - top - bottom
        step = chart_w / len(keys)
        bar_w = max(20, int(step * 0.55))

        canvas.create_line(left, height - bottom, width - right, height - bottom, fill="#bbbbbb")
        for idx, key in enumerate(keys):
            value = values[idx]
            bar_h = int(chart_h * float(value / max_val))
            x_center = left + int(step * idx + step / 2)
            x1, x2 = x_center - bar_w // 2, x_center + bar_w // 2
            y1, y2 = height - bottom - bar_h, height - bottom
            canvas.create_rectangle(x1, y1, x2, y2, fill="#2d8cff", outline="")
            canvas.create_text(x_center, y1 - 8, text=decimal_to_str(value), font=("Segoe UI", 8), fill="#1f4d8f")
            canvas.create_text(x_center, height - 12, text=key[2:], font=("Segoe UI", 8), fill="#444")

    # ==========================================================
    # HISTORY TAB
    # ==========================================================
    def build_history_tab(self):
        f = self.tab_history
        for i in range(7):
            f.columnconfigure(i, weight=1)
        f.rowconfigure(3, weight=1)

        ttk.Label(f, text="From").grid(row=0, column=0, sticky="w")
        self.filter_from = DateEntry(f, date_pattern="dd.mm.yyyy")
        self.filter_from.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ttk.Label(f, text="To").grid(row=0, column=2, sticky="w")
        self.filter_to = DateEntry(f, date_pattern="dd.mm.yyyy")
        self.filter_to.grid(row=0, column=3, sticky="ew", padx=(0, 10))

        ttk.Label(f, text="Person").grid(row=0, column=4, sticky="w")
        self.filter_person = ttk.Combobox(f, values=["All"] + self.people, state="readonly")
        self.filter_person.grid(row=0, column=5, sticky="ew", padx=(0, 10))
        self.filter_person.set("All")

        self.use_date_filter_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Use date range", variable=self.use_date_filter_var)\
            .grid(row=1, column=0, columnspan=2, sticky="w")

        btn_bar = ttk.Frame(f)
        btn_bar.grid(row=0, column=6, rowspan=2, sticky="e")
        ttk.Button(btn_bar, text="Apply", command=self.refresh_history).pack(side="left", padx=2)
        ttk.Button(btn_bar, text="Reset", command=self.reset_history_filters).pack(side="left", padx=2)

        self.history_summary = ttk.Label(f, text="Records: 0 | Total: 0.00")
        self.history_summary.grid(row=2, column=0, columnspan=7, sticky="w", pady=6)

        cols = ("date", "person", "store", "category", "sub", "amount", "total", "id")
        self.history_tree = ttk.Treeview(f, columns=cols, show="headings", height=14)
        self.history_tree.grid(row=3, column=0, columnspan=7, sticky="nsew")

        self.history_tree.heading("date", text="Date")
        self.history_tree.heading("person", text="Person")
        self.history_tree.heading("store", text="Store")
        self.history_tree.heading("category", text="Category")
        self.history_tree.heading("sub", text="Sub-category")
        self.history_tree.heading("amount", text=f"Amount ({self.settings.get('currency', 'EUR')})")
        self.history_tree.heading("total", text=f"Expense total ({self.settings.get('currency', 'EUR')})")
        self.history_tree.heading("id", text="Expense ID")

        lower = ttk.Frame(f)
        lower.grid(row=4, column=0, columnspan=7, sticky="e", pady=6)
        ttk.Button(lower, text="Edit selected expense", command=self.open_edit_expense_dialog)\
            .pack(side="left", padx=4)
        ttk.Button(lower, text="Delete selected expense", command=self.delete_selected_expense)\
            .pack(side="left", padx=4)
        ttk.Button(lower, text="Export filtered CSV", command=self.export_filtered_history)\
            .pack(side="left", padx=4)

        analytics = ttk.LabelFrame(f, text="Monthly Analytics", padding=8)
        analytics.grid(row=5, column=0, columnspan=7, sticky="ew", pady=(4, 0))
        for i in range(4):
            analytics.columnconfigure(i, weight=1)

        self.card_this_month = tk.StringVar(value="This month: 0.00")
        self.card_last_month = tk.StringVar(value="Last month: 0.00")
        self.card_change = tk.StringVar(value="MoM: 0.00%")
        self.card_top_category = tk.StringVar(value="Top category: -")

        ttk.Label(analytics, textvariable=self.card_this_month).grid(row=0, column=0, sticky="w")
        ttk.Label(analytics, textvariable=self.card_last_month).grid(row=0, column=1, sticky="w")
        ttk.Label(analytics, textvariable=self.card_change).grid(row=0, column=2, sticky="w")
        ttk.Label(analytics, textvariable=self.card_top_category).grid(row=0, column=3, sticky="w")

        self.chart_canvas = tk.Canvas(
            analytics, height=170, bg="#ffffff", highlightthickness=1, highlightbackground="#d0d0d0"
        )
        self.chart_canvas.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        self.chart_canvas.bind("<Configure>", lambda _: self.render_monthly_chart(self.filtered_records))

        self.refresh_history()

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
            self.filter_person["values"] = ["All"] + self.people
            self.set_status(f"Added person: {p}")
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
        self.set_status(f"Saved store: {name}")

        self.new_store.delete(0, tk.END)
        self.store_sub.delete(0, tk.END)


if __name__ == "__main__":
    app = ExpenseTracker()
    app.mainloop()

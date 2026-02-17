import os
import tkinter as tk
from tkinter import ttk

from data_store import ensure_expense_file, load_json, save_json
from expenses_mixin import ExpensesMixin
from history_mixin import HistoryMixin
from management_mixin import ManagementMixin


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


class ExpenseTracker(ExpensesMixin, HistoryMixin, ManagementMixin, tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Expense Tracker MVP")
        self.geometry("1220x780")
        self.minsize(980, 680)
        self.set_window_icon()

        self.people = load_json("people", DEFAULT_DATA)
        self.categories = load_json("categories", DEFAULT_DATA)
        self.stores = load_json("stores", DEFAULT_DATA)
        self.settings = load_json("settings", DEFAULT_DATA)

        self.breakdown = []
        self.filtered_records = []

        ensure_expense_file()
        self.create_menu()
        self.create_tabs()

    def create_menu(self):
        menubar = tk.Menu(self)

        settings_menu = tk.Menu(menubar, tearoff=0)
        for cur in ["EUR", "USD", "GBP", "CHF"]:
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

    def set_window_icon(self):
        icon_path = os.path.join("assets", "app_icon.ico")
        if not os.path.exists(icon_path):
            return
        try:
            self.iconbitmap(default=icon_path)
        except tk.TclError:
            pass

    def debug_log(self, message):
        if not self.settings.get("debug_calendar", False):
            return
        print(f"[calendar] {message}")

    def _install_calendar_focus_guard(self, date_entry):
        cal = getattr(date_entry, "_calendar", None)
        if cal is None:
            return
        cal.unbind("<FocusOut>")
        cal.bind("<FocusOut>", lambda _e, de=date_entry: self._on_calendar_focus_out(de))

    def _on_calendar_focus_out(self, date_entry):
        top = getattr(date_entry, "_top_cal", None)
        if top is None or not top.winfo_exists():
            return
        focus = self.focus_get()
        if focus is None:
            top.withdraw()
            date_entry.state(["!pressed"])
            return
        if focus == date_entry:
            return
        if focus.winfo_toplevel() == top:
            return
        top.withdraw()
        date_entry.state(["!pressed"])


if __name__ == "__main__":
    app = ExpenseTracker()
    app.mainloop()

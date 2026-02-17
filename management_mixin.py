from tkinter import messagebox, ttk

from data_store import save_json


class ManagementMixin:
    def build_manage_tab(self):
        f = self.tab_manage

        ttk.Label(f, text="Add person").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.new_person = ttk.Entry(f)
        self.new_person.grid(row=0, column=1, padx=6, pady=4)
        ttk.Button(f, text="Add", command=self.add_person).grid(row=0, column=2, padx=6, pady=4)

        ttk.Label(f, text="Add store").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.new_store = ttk.Entry(f)
        self.new_store.grid(row=1, column=1, padx=6, pady=4)

        ttk.Label(f, text="Default category").grid(row=1, column=2, padx=6, pady=4, sticky="w")
        self.store_cat = ttk.Combobox(f, values=list(self.categories.keys()))
        self.store_cat.grid(row=1, column=3, padx=6, pady=4)

        ttk.Label(f, text="Default sub").grid(row=1, column=4, padx=6, pady=4, sticky="w")
        self.store_sub = ttk.Entry(f)
        self.store_sub.grid(row=1, column=5, padx=6, pady=4)

        ttk.Button(f, text="Add store", command=self.add_store).grid(row=1, column=6, padx=6, pady=4)

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
        self.new_person.delete(0, "end")

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

        self.new_store.delete(0, "end")
        self.store_sub.delete(0, "end")

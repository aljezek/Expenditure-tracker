import csv
import math
import tkinter as tk
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from tkinter import filedialog, messagebox, ttk

from tkcalendar import DateEntry

from analytics import aggregate_by_bucket, aggregate_pie
from data_store import CSV_HEADERS, read_expenses, write_expenses
from utils import decimal_to_str, parse_date, parse_decimal


class HistoryMixin:
    def parse_date_for_filter(self, date_str):
        formats = [self.settings.get("date_format", "%d.%m.%Y"), "%d.%m.%Y", "%Y-%m-%d", "%m/%d/%Y"]
        return parse_date(date_str, formats)

    def get_selected_expense_id(self):
        selected = self.history_tree.selection()
        if not selected:
            return None
        return self.history_tree.item(selected[0], "values")[7]

    def on_from_selected(self, _event=None):
        self.after(1, self._apply_from_selected)

    def on_to_selected(self, _event=None):
        self.after(1, self._apply_to_selected)

    def _apply_from_selected(self):
        current = self.filter_from.get().strip()
        self.debug_log(f"[From] Date changed from {self.from_last_value} to {current}")
        if current == self.from_last_value:
            return
        self.from_last_value = current
        self.from_enabled_var.set(True)
        self.refresh_after_calendar_closes(self.filter_from)

    def _apply_to_selected(self):
        current = self.filter_to.get().strip()
        self.debug_log(f"[To] Date changed from {self.to_last_value} to {current}")
        if current == self.to_last_value:
            return
        self.to_last_value = current
        self.to_enabled_var.set(True)
        self.refresh_after_calendar_closes(self.filter_to)

    def on_from_typed(self, _event=None):
        self.from_last_value = self.from_var.get().strip()
        self.debug_log(f"from typed: {self.from_last_value}")
        self.from_enabled_var.set(True)
        self.refresh_history()

    def on_to_typed(self, _event=None):
        self.to_last_value = self.to_var.get().strip()
        self.debug_log(f"to typed: {self.to_last_value}")
        self.to_enabled_var.set(True)
        self.refresh_history()

    def refresh_after_calendar_closes(self, date_entry):
        top_cal = getattr(date_entry, "_top_cal", None)
        is_open = False
        if top_cal is not None:
            try:
                is_open = bool(top_cal.winfo_viewable())
            except tk.TclError:
                is_open = False
        if is_open:
            self.after(80, lambda: self.refresh_after_calendar_closes(date_entry))
            return
        self.refresh_history()

    def update_range_controls_visibility(self):
        if self.period_var.get() == "select range":
            self.range_frame.grid()
        else:
            self.range_frame.grid_remove()

    def apply_period_preset(self):
        today = datetime.now().date()
        period = self.period_var.get()
        self.update_range_controls_visibility()

        if period == "select range":
            self.from_enabled_var.set(True)
            self.to_enabled_var.set(True)
            self.refresh_history()
            return

        if period == "today":
            start = today
            end = today
        elif period == "this week":
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
        elif period == "this month":
            start = today.replace(day=1)
            if start.month == 12:
                nxt = start.replace(year=start.year + 1, month=1, day=1)
            else:
                nxt = start.replace(month=start.month + 1, day=1)
            end = nxt - timedelta(days=1)
        elif period == "last month":
            first_this = today.replace(day=1)
            end = first_this - timedelta(days=1)
            start = end.replace(day=1)
        elif period == "this year":
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
        elif period == "last year":
            start = today.replace(year=today.year - 1, month=1, day=1)
            end = today.replace(year=today.year - 1, month=12, day=31)
        else:
            start = today
            end = today

        self.from_enabled_var.set(True)
        self.to_enabled_var.set(True)
        self.filter_from.set_date(start)
        self.filter_to.set_date(end)
        self.from_last_value = self.filter_from.get().strip()
        self.to_last_value = self.filter_to.get().strip()
        self.refresh_history()

    def refresh_history(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        records = read_expenses()
        from_date = self.parse_date_for_filter(self.filter_from.get()) if self.from_enabled_var.get() else None
        to_date = self.parse_date_for_filter(self.filter_to.get()) if self.to_enabled_var.get() else None
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
        self.selected_bucket = None
        self.update_analytics(self.filtered_records)

    def reset_history_filters(self):
        self.filter_person["values"] = ["All"] + self.people
        self.filter_person.set("All")
        self.period_var.set("this month")
        self.apply_period_preset()

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

        all_rows = read_expenses()
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
            write_expenses(kept)
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

        all_rows = read_expenses()
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
        write_expenses(kept)
        self.refresh_history()
        self.set_status(f"Deleted expense {expense_id}.")

    def update_analytics(self, rows):
        formats = [self.settings.get("date_format", "%d.%m.%Y"), "%d.%m.%Y", "%Y-%m-%d", "%m/%d/%Y"]
        dates = [self.parse_date_for_filter(r.get("date", "")) for r in rows]
        dates = [d for d in dates if d]

        if not dates:
            self.card_range_total.set("Range total: 0.00")
            self.card_range_days.set("Range days: 0")
            self.card_avg_day.set("Avg/day: 0.00")
            self.card_top_group.set("Top group: -")
            self.bucket_ranges = []
            self.bucket_labels = []
            self.bucket_totals = []
            self.render_bar_chart([], [])
            self.render_pie_chart({})
            return

        start = min(dates)
        end = max(dates)
        if self.from_enabled_var.get():
            f = self.parse_date_for_filter(self.filter_from.get())
            if f:
                start = f
        if self.to_enabled_var.get():
            t = self.parse_date_for_filter(self.filter_to.get())
            if t:
                end = t

        range_days = (end - start).days + 1
        short_range = range_days < 60
        options = ["day", "week_monday", "week_rolling", "month"] if short_range else ["week_monday", "week_rolling", "month"]

        self.granularity_cb["values"] = options
        if self.granularity_var.get() not in options:
            self.granularity_var.set(options[0])

        mode = self.granularity_var.get()
        buckets, labels, totals = aggregate_by_bucket(rows, start, end, mode, formats)
        self.bucket_ranges = buckets
        self.bucket_labels = labels
        self.bucket_totals = totals

        currency = self.settings.get("currency", "EUR")
        total_sum = sum(totals, Decimal("0.00"))
        avg_day = total_sum / Decimal(range_days) if range_days else Decimal("0.00")
        self.card_range_total.set(f"Range total: {decimal_to_str(total_sum)} {currency}")
        self.card_range_days.set(f"Range days: {range_days}")
        self.card_avg_day.set(f"Avg/day: {decimal_to_str(avg_day)} {currency}")

        bucket_start, bucket_end = start, end
        has_selected_bucket = self.selected_bucket is not None and 0 <= self.selected_bucket < len(buckets)
        if has_selected_bucket:
            bucket_start, bucket_end = buckets[self.selected_bucket]
            self.bucket_label_var.set(
                f"Selected bucket: {bucket_start.strftime('%d.%m.%Y')} - {bucket_end.strftime('%d.%m.%Y')}"
            )
        else:
            self.bucket_label_var.set("Selected bucket: whole range")

        pie_start, pie_end = start, end
        if has_selected_bucket:
            pie_start, pie_end = bucket_start, bucket_end

        pie_data = aggregate_pie(rows, pie_start, pie_end, self.grouping_var.get(), formats)
        if pie_data:
            top_key = max(pie_data, key=pie_data.get)
            self.card_top_group.set(f"Top group: {top_key} ({decimal_to_str(pie_data[top_key])} {currency})")
        else:
            self.card_top_group.set("Top group: -")
        if self.selected_pie_label and self.selected_pie_label not in pie_data:
            self.selected_pie_label = None

        self.render_bar_chart(labels, totals)
        self.render_pie_chart(pie_data)

    def render_bar_chart(self, labels, totals):
        canvas = self.chart_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 600)
        height = max(canvas.winfo_height(), 170)

        if not labels:
            canvas.create_text(width // 2, height // 2, text="No data for chart", fill="#666")
            return

        max_val = max(totals) if totals else Decimal("1")
        if max_val <= 0:
            max_val = Decimal("1")

        left, right, bottom, top = 40, 20, 28, 16
        chart_w = width - left - right
        chart_h = height - top - bottom
        step = chart_w / len(labels)
        bar_w = max(20, int(step * 0.6))

        canvas.create_line(left, height - bottom, width - right, height - bottom, fill="#bbbbbb")
        for idx, label in enumerate(labels):
            value = totals[idx]
            bar_h = int(chart_h * float(value / max_val))
            x_center = left + int(step * idx + step / 2)
            x1, x2 = x_center - bar_w // 2, x_center + bar_w // 2
            y1, y2 = height - bottom - bar_h, height - bottom
            fill = "#2d8cff" if self.selected_bucket == idx else "#5aa5ff"
            canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline="")
            canvas.create_text(x_center, y1 - 8, text=decimal_to_str(value), font=("Segoe UI", 8), fill="#1f4d8f")
            canvas.create_text(x_center, height - 12, text=label, font=("Segoe UI", 8), fill="#444")

    def render_pie_chart(self, pie_data):
        canvas = self.pie_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 240)
        height = max(canvas.winfo_height(), 170)
        self.pie_slices = []
        self.pie_geometry = None

        if not pie_data:
            canvas.create_text(width // 2, height // 2, text="No data for pie", fill="#666")
            return

        total = sum(pie_data.values(), Decimal("0.00"))
        if total <= 0:
            canvas.create_text(width // 2, height // 2, text="No data for pie", fill="#666")
            return

        colors = ["#2d8cff", "#8bc34a", "#ff9800", "#e91e63", "#9c27b0", "#00bcd4", "#795548", "#607d8b"]
        start = 0
        pie_width = int(width * 0.5)
        base_radius = max(35, min(pie_width // 2 - 8, height // 2 - 10))
        radius = int(base_radius * self.pie_zoom)
        radius = max(20, min(radius, min(pie_width // 2 - 4, height // 2 - 4)))
        cx, cy = pie_width // 2, height // 2
        legend_x = pie_width + 10
        legend_y = 12

        ranked = sorted(pie_data.items(), key=lambda x: x[1], reverse=True)
        for idx, (key, value) in enumerate(ranked[:8]):
            extent = float(value / total) * 360
            color = colors[idx % len(colors)]
            is_selected = key == self.selected_pie_label
            canvas.create_arc(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                start=start,
                extent=extent,
                fill=color,
                outline="#222" if is_selected else "white",
                width=2 if is_selected else 1,
            )
            self.pie_slices.append(
                {
                    "start": start,
                    "extent": extent,
                    "label": key,
                    "value": value,
                    "color": color,
                }
            )
            pct = (value / total) * Decimal("100")
            y = legend_y + (idx * 18)
            canvas.create_rectangle(legend_x, y, legend_x + 10, y + 10, fill=color, outline="")
            canvas.create_text(
                legend_x + 16,
                y + 5,
                anchor="w",
                text=f"{key}: {decimal_to_str(value)} ({decimal_to_str(pct)}%)",
                font=("Segoe UI", 8),
                fill="#333",
            )
            start += extent

        self.pie_geometry = {"cx": cx, "cy": cy, "radius": radius}
        self._draw_pie_selection_text(canvas, width, height, total)

    def _draw_pie_selection_text(self, canvas, width, height, total):
        if not self.selected_pie_label or not self.pie_slices:
            return

        selected = None
        for seg in self.pie_slices:
            if seg["label"] == self.selected_pie_label:
                selected = seg
                break
        if not selected:
            return

        pct = (selected["value"] / total) * Decimal("100")
        text = f"{selected['label']}: {decimal_to_str(selected['value'])} ({decimal_to_str(pct)}%)"
        canvas.create_text(
            width - 8,
            height - 8,
            anchor="se",
            text=text,
            font=("Segoe UI", 8, "bold"),
            fill="#222",
        )

    def on_chart_click(self, event):
        if not self.bucket_labels:
            return
        width = max(self.chart_canvas.winfo_width(), 600)
        height = max(self.chart_canvas.winfo_height(), 170)
        left, right = 40, 20
        bottom, top = 28, 16
        chart_w = width - left - right
        chart_h = height - top - bottom
        if chart_w <= 0 or chart_h <= 0:
            return
        step = chart_w / len(self.bucket_labels)
        bar_w = max(20, int(step * 0.6))
        max_val = max(self.bucket_totals) if self.bucket_totals else Decimal("1")
        if max_val <= 0:
            max_val = Decimal("1")

        clicked_idx = None
        for idx, value in enumerate(self.bucket_totals):
            bar_h = int(chart_h * float(value / max_val))
            x_center = left + int(step * idx + step / 2)
            x1, x2 = x_center - bar_w // 2, x_center + bar_w // 2
            y1, y2 = height - bottom - bar_h, height - bottom
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                clicked_idx = idx
                break

        if clicked_idx is not None:
            self.selected_bucket = clicked_idx
        else:
            self.selected_bucket = None
        self.update_analytics(self.filtered_records)

    def on_pie_click(self, event):
        if not self.pie_geometry or not self.pie_slices:
            return

        cx = self.pie_geometry["cx"]
        cy = self.pie_geometry["cy"]
        radius = self.pie_geometry["radius"]
        dx = event.x - cx
        dy = event.y - cy
        if (dx * dx + dy * dy) > (radius * radius):
            self.selected_pie_label = None
            self.update_analytics(self.filtered_records)
            return

        angle = math.degrees(math.atan2(-dy, dx))
        if angle < 0:
            angle += 360

        for seg in self.pie_slices:
            start = seg["start"]
            end = start + seg["extent"]
            if start <= angle < end:
                self.selected_pie_label = seg["label"]
                self.update_analytics(self.filtered_records)
                return

        self.selected_pie_label = None
        self.update_analytics(self.filtered_records)

    def on_pie_wheel(self, event):
        delta = 0
        if hasattr(event, "delta") and event.delta:
            delta = 1 if event.delta > 0 else -1
        elif getattr(event, "num", None) == 4:
            delta = 1
        elif getattr(event, "num", None) == 5:
            delta = -1
        if delta == 0:
            return
        self.pie_zoom = min(2.5, max(0.6, self.pie_zoom + (0.1 * delta)))
        self.update_analytics(self.filtered_records)

    def set_pie_zoom(self, value):
        self.pie_zoom = min(2.5, max(0.6, value))
        self.update_analytics(self.filtered_records)

    def build_history_tab(self):
        f = self.tab_history
        for i in range(7):
            f.columnconfigure(i, weight=1)
        f.rowconfigure(4, weight=1)

        ttk.Label(f, text="Period").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.period_var = tk.StringVar(value="this month")
        self.period_cb = ttk.Combobox(
            f,
            textvariable=self.period_var,
            state="readonly",
            values=[
                "this month",
                "last month",
                "today",
                "this week",
                "this year",
                "last year",
                "select range",
            ],
        )
        self.period_cb.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=4)

        btn_bar = ttk.Frame(f)
        btn_bar.grid(row=0, column=6, sticky="e")
        ttk.Button(btn_bar, text="Reset", command=self.reset_history_filters).pack(side="left", padx=2)

        self.range_frame = ttk.Frame(f)
        self.range_frame.grid(row=1, column=0, columnspan=7, sticky="ew")
        for i in range(7):
            self.range_frame.columnconfigure(i, weight=1)

        ttk.Label(self.range_frame, text="From").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.from_var = tk.StringVar()
        self.filter_from = DateEntry(self.range_frame, date_pattern="dd.mm.yyyy", textvariable=self.from_var)
        self.filter_from.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=4)
        self._install_calendar_focus_guard(self.filter_from)
        if getattr(self.filter_from, "_calendar", None) is not None:
            self.filter_from._calendar.bind("<<CalendarSelected>>", lambda _e: self.on_from_selected(), add="+")

        ttk.Label(self.range_frame, text="To").grid(row=0, column=3, sticky="w", padx=6, pady=4)
        self.to_var = tk.StringVar()
        self.filter_to = DateEntry(self.range_frame, date_pattern="dd.mm.yyyy", textvariable=self.to_var)
        self.filter_to.grid(row=0, column=4, sticky="ew", padx=(0, 10), pady=4)
        self._install_calendar_focus_guard(self.filter_to)
        if getattr(self.filter_to, "_calendar", None) is not None:
            self.filter_to._calendar.bind("<<CalendarSelected>>", lambda _e: self.on_to_selected(), add="+")

        self.from_enabled_var = tk.BooleanVar(value=True)
        self.to_enabled_var = tk.BooleanVar(value=True)

        ttk.Label(f, text="Person").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        self.filter_person = ttk.Combobox(f, values=["All"] + self.people, state="readonly")
        self.filter_person.grid(row=2, column=1, sticky="ew", padx=(0, 10), pady=4)
        self.filter_person.set("All")

        ttk.Label(f, text="Group by").grid(row=2, column=3, sticky="w", padx=6, pady=4)
        self.grouping_var = tk.StringVar(value="category")
        self.grouping_cb = ttk.Combobox(
            f,
            textvariable=self.grouping_var,
            values=["store", "person", "category", "subcategory"],
            state="readonly",
        )
        self.grouping_cb.grid(row=2, column=4, sticky="ew", padx=(0, 10), pady=4)

        self.history_summary = ttk.Label(f, text="Records: 0 | Total: 0.00")
        self.history_summary.grid(row=3, column=0, columnspan=7, sticky="w", padx=6, pady=6)

        cols = ("date", "person", "store", "category", "sub", "amount", "total", "id")
        self.history_tree = ttk.Treeview(f, columns=cols, show="headings", height=14)
        self.history_tree.grid(row=4, column=0, columnspan=7, sticky="nsew")

        self.history_tree.heading("date", text="Date")
        self.history_tree.heading("person", text="Person")
        self.history_tree.heading("store", text="Store")
        self.history_tree.heading("category", text="Category")
        self.history_tree.heading("sub", text="Sub-category")
        self.history_tree.heading("amount", text=f"Amount ({self.settings.get('currency', 'EUR')})")
        self.history_tree.heading("total", text=f"Expense total ({self.settings.get('currency', 'EUR')})")
        self.history_tree.heading("id", text="Expense ID")

        lower = ttk.Frame(f)
        lower.grid(row=5, column=0, columnspan=7, sticky="e", pady=6)
        ttk.Button(lower, text="Edit selected expense", command=self.open_edit_expense_dialog).pack(side="left", padx=4)
        ttk.Button(lower, text="Delete selected expense", command=self.delete_selected_expense).pack(side="left", padx=4)
        ttk.Button(lower, text="Export filtered CSV", command=self.export_filtered_history).pack(side="left", padx=4)

        analytics = ttk.LabelFrame(f, text="Analytics", padding=8)
        analytics.grid(row=6, column=0, columnspan=7, sticky="ew", pady=(4, 0))
        for i in range(4):
            analytics.columnconfigure(i, weight=1)

        self.card_range_total = tk.StringVar(value="Range total: 0.00")
        self.card_range_days = tk.StringVar(value="Range days: 0")
        self.card_avg_day = tk.StringVar(value="Avg/day: 0.00")
        self.card_top_group = tk.StringVar(value="Top group: -")

        ttk.Label(analytics, textvariable=self.card_range_total).grid(row=0, column=0, sticky="w")
        ttk.Label(analytics, textvariable=self.card_range_days).grid(row=0, column=1, sticky="w")
        ttk.Label(analytics, textvariable=self.card_avg_day).grid(row=0, column=2, sticky="w")
        ttk.Label(analytics, textvariable=self.card_top_group).grid(row=0, column=3, sticky="w")

        self.chart_canvas = tk.Canvas(analytics, height=170, bg="#ffffff", highlightthickness=1, highlightbackground="#d0d0d0")
        self.chart_canvas.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        self.pie_canvas = tk.Canvas(analytics, height=170, bg="#ffffff", highlightthickness=1, highlightbackground="#d0d0d0")
        self.pie_canvas.grid(row=1, column=2, columnspan=2, sticky="ew", pady=(8, 0))

        ttk.Label(analytics, text="Bar granularity").grid(row=2, column=0, sticky="w")
        self.granularity_var = tk.StringVar(value="month")
        self.granularity_cb = ttk.Combobox(
            analytics,
            textvariable=self.granularity_var,
            state="readonly",
            width=16,
        )
        self.granularity_cb.grid(row=2, column=1, sticky="w")

        self.pie_zoom_out_btn = ttk.Button(
            self.pie_canvas, text="-", width=3, command=lambda: self.set_pie_zoom(self.pie_zoom - 0.1)
        )
        self.pie_zoom_in_btn = ttk.Button(
            self.pie_canvas, text="+", width=3, command=lambda: self.set_pie_zoom(self.pie_zoom + 0.1)
        )
        self.pie_zoom_in_btn.place(x=8, y=8, anchor="nw")
        self.pie_zoom_out_btn.place(x=8, y=40, anchor="nw")

        self.bucket_label_var = tk.StringVar(value="Selected bucket: whole range")
        ttk.Label(analytics, textvariable=self.bucket_label_var).grid(row=4, column=0, columnspan=4, sticky="w")

        self.chart_canvas.bind("<Configure>", lambda _: self.update_analytics(self.filtered_records))
        self.chart_canvas.bind("<Button-1>", self.on_chart_click)
        self.pie_canvas.bind("<Configure>", lambda _: self.update_analytics(self.filtered_records))
        self.pie_canvas.bind("<Button-1>", self.on_pie_click)
        self.pie_canvas.bind("<MouseWheel>", self.on_pie_wheel)
        self.pie_canvas.bind("<Button-4>", self.on_pie_wheel)
        self.pie_canvas.bind("<Button-5>", self.on_pie_wheel)

        self.filter_from.bind("<Return>", self.on_from_typed)
        self.filter_to.bind("<Return>", self.on_to_typed)
        self.period_cb.bind("<<ComboboxSelected>>", lambda _e: self.apply_period_preset())
        self.filter_person.bind("<<ComboboxSelected>>", lambda _e: self.refresh_history())
        self.grouping_cb.bind("<<ComboboxSelected>>", lambda _e: self.update_analytics(self.filtered_records))
        self.granularity_cb.bind("<<ComboboxSelected>>", lambda _e: self.update_analytics(self.filtered_records))

        self.selected_bucket = None
        self.selected_pie_label = None
        self.pie_slices = []
        self.pie_geometry = None
        self.pie_zoom = 1.0
        self.from_last_value = self.from_var.get()
        self.to_last_value = self.to_var.get()

        self.apply_period_preset()

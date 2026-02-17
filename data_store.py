import csv
import json
import os
from datetime import datetime
from uuid import uuid4


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


def load_json(name, default_data):
    if not os.path.exists(FILES[name]):
        save_json(name, default_data[name])
    try:
        with open(FILES[name], "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        save_json(name, default_data[name])
        return default_data[name]


def save_json(name, data):
    with open(FILES[name], "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def ensure_expense_file():
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


def read_expenses():
    with open(EXPENSE_FILE, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_expenses(rows):
    with open(EXPENSE_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

from datetime import date, timedelta
from decimal import Decimal

from utils import parse_date


def daterange_days(start, end):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def bucket_ranges(start, end, mode):
    buckets = []
    if mode == "day":
        for d in daterange_days(start, end):
            buckets.append((d, d))
        return buckets

    if mode == "week_monday":
        cur = start
        cur -= timedelta(days=cur.weekday())
        while cur <= end:
            b_start = max(cur, start)
            b_end = min(cur + timedelta(days=6), end)
            buckets.append((b_start, b_end))
            cur += timedelta(days=7)
        return buckets

    if mode == "week_rolling":
        cur = start
        while cur <= end:
            b_start = cur
            b_end = min(cur + timedelta(days=6), end)
            buckets.append((b_start, b_end))
            cur += timedelta(days=7)
        return buckets

    if mode == "month":
        cur = date(start.year, start.month, 1)
        while cur <= end:
            if cur.month == 12:
                nxt = date(cur.year + 1, 1, 1)
            else:
                nxt = date(cur.year, cur.month + 1, 1)
            b_start = max(cur, start)
            b_end = min(nxt - timedelta(days=1), end)
            buckets.append((b_start, b_end))
            cur = nxt
        return buckets

    return buckets


def label_for_range(start, end, mode):
    if mode == "day":
        return start.strftime("%d.%m")
    if mode in {"week_monday", "week_rolling"}:
        return f"{start.strftime('%d.%m')}-{end.strftime('%d.%m')}"
    return start.strftime("%b %Y")


def group_key(row, grouping):
    if grouping == "store":
        return row.get("store", "Unknown") or "Unknown"
    if grouping == "person":
        return row.get("person", "Unknown") or "Unknown"
    if grouping == "category":
        return row.get("category", "Unknown") or "Unknown"
    if grouping == "subcategory":
        cat = row.get("category", "Unknown") or "Unknown"
        sub = row.get("sub_category", "Unknown") or "Unknown"
        return f"{cat} > {sub}"
    return "Unknown"


def aggregate_by_bucket(rows, start, end, mode, date_formats):
    buckets = bucket_ranges(start, end, mode)
    totals = [Decimal("0.00") for _ in buckets]

    for row in rows:
        d = parse_date(row.get("date", ""), date_formats)
        if not d or d < start or d > end:
            continue
        amount = Decimal(str(row.get("amount", "0") or "0").replace(",", "."))
        for idx, (b_start, b_end) in enumerate(buckets):
            if b_start <= d <= b_end:
                totals[idx] += amount
                break

    labels = [label_for_range(b[0], b[1], mode) for b in buckets]
    return buckets, labels, totals


def aggregate_pie(rows, start, end, grouping, date_formats):
    totals = {}
    for row in rows:
        d = parse_date(row.get("date", ""), date_formats)
        if not d or d < start or d > end:
            continue
        key = group_key(row, grouping)
        amount = Decimal(str(row.get("amount", "0") or "0").replace(",", "."))
        totals[key] = totals.get(key, Decimal("0.00")) + amount
    return totals

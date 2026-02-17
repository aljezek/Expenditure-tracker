from datetime import datetime
from decimal import Decimal


def parse_decimal(value):
    normalized = str(value).strip().replace(",", ".")
    amount = Decimal(normalized)
    return amount.quantize(Decimal("0.01"))


def decimal_to_str(value):
    return f"{value:.2f}"


def parse_date(date_str, formats):
    raw = str(date_str).strip()
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None

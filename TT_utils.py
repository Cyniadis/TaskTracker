from datetime import date, datetime
import os

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))


def normalize_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        if "/" in value:
            return datetime.strptime(value, "%d/%m/%Y").date()
        return datetime.fromisoformat(value).date()
    raise TypeError(f"Unsupported date value: {type(value)!r}")


def date_to_string(value) -> str:
    normalized = normalize_date(value)
    if normalized is None:
        return None
    return normalized.isoformat()


def string_to_date(string):
    return normalize_date(string)


def frequency_to_days(frequency : str) -> float:
    try:
        number, period = frequency.lower().split('x')
        number = int(number)
        if period == 'jour':
            return 1.0 / number
        if period == 'semaine':
            return 7.0 / number
        if period == 'mois':
            return 30.4 / number
        if period in ('an', 'ans'):
            return 365.0 / number
    except Exception:
        pass
    return 1.0


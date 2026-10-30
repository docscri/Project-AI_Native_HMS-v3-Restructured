"""Input checks used across features."""
import re
from datetime import date as Date

from .errors import Invalid


def valid_day(day: str | None, required: bool = True) -> str | None:
    if not day and not required:
        return None
    try:
        return Date.fromisoformat(str(day)).isoformat() if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(day)) else Date.fromisoformat("x")
    except ValueError:
        raise Invalid("Check the dates.")


def clean_email(email: str) -> str:
    email = (email or "").strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise Invalid("Enter a valid email address.")
    return email


def clean_phone(phone: str | None) -> str:
    phone = re.sub(r"[\s-]", "", phone or "")
    if phone and not re.fullmatch(r"\+?\d{10,13}", phone):
        raise Invalid("Enter a valid phone number.")
    return phone

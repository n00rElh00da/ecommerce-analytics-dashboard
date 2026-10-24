"""Pure validation/normalisation of one CSV row (no database needed)."""
import hashlib
import math
from datetime import datetime, timezone

VALID_EVENT_TYPES = {"view", "cart", "remove_from_cart", "purchase"}


def _blank_to_none(value):
    value = (value or "").strip()
    return value or None


def event_id(doc):
    """Deterministic _id: the same source event always maps to the same document."""
    key = "|".join(str(doc[k]) for k in ("event_time", "event_type", "product_id", "user_id", "user_session"))
    return hashlib.sha1(key.encode()).hexdigest()


def normalize_row(row):
    """Return (document, None) or (None, reason)."""
    try:
        raw_time = (row.get("event_time") or "").replace(" UTC", "").strip()
        event_time = datetime.strptime(raw_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None, "bad_event_time"

    event_type = (row.get("event_type") or "").strip().lower()
    if event_type not in VALID_EVENT_TYPES:
        return None, "bad_event_type"

    try:
        product_id = int(row["product_id"])
        category_id = int(row["category_id"])
        user_id = int(row["user_id"])
    except (KeyError, TypeError, ValueError):
        return None, "bad_id"

    try:
        price = float(row["price"])
    except (KeyError, TypeError, ValueError):
        return None, "bad_price"
    if not math.isfinite(price) or price < 0:
        return None, "bad_price"

    session = _blank_to_none(row.get("user_session"))
    if session is None:
        return None, "missing_session"

    category_code = _blank_to_none(row.get("category_code"))
    brand = _blank_to_none(row.get("brand"))
    doc = {
        "event_time": event_time,
        "event_type": event_type,
        "product_id": product_id,
        "category_id": category_id,
        "category_code": category_code,
        "category_top": category_code.split(".")[0] if category_code else None,
        "brand": brand.lower() if brand else None,
        "price": price,
        "price_is_zero": price == 0,  # kept as-is, flagged; excluded from gross value
        "user_id": user_id,  # anonymous behavioural id, NOT an account identity
        "user_session": session,
    }
    doc["_id"] = event_id(doc)
    return doc, None

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.analytics import overview  # noqa: E402
from app.normalize import normalize_row  # noqa: E402
from scripts.import_events import run_import  # noqa: E402

GOOD = {"event_time": "2019-10-01 00:00:04 UTC", "event_type": "view", "product_id": "1004237",
        "category_id": "2053013555631882655", "category_code": "electronics.smartphone",
        "brand": "Apple", "price": "1081.98", "user_id": "535871217", "user_session": "abc"}


def test_valid_row_normalised():
    doc, err = normalize_row(GOOD)
    assert err is None and doc["brand"] == "apple" and doc["category_top"] == "electronics"
    assert doc["event_time"].tzinfo is not None


@pytest.mark.parametrize("field,value,reason", [
    ("event_time", "garbage", "bad_event_time"), ("event_type", "refund", "bad_event_type"),
    ("price", "-1", "bad_price"), ("price", "nan", "bad_price"),
    ("user_id", "x", "bad_id"), ("user_session", " ", "missing_session")])
def test_invalid_rows(field, value, reason):
    assert normalize_row({**GOOD, field: value}) == (None, reason)


def test_blank_brand_and_zero_price_flagged_not_invented():
    doc, _ = normalize_row({**GOOD, "brand": "", "category_code": "", "price": "0"})
    assert doc["brand"] is None and doc["category_code"] is None and doc["price_is_zero"]


def _write(tmp_path):
    p = tmp_path / "s.csv"
    rows = [GOOD, GOOD,  # exact duplicate
            {**GOOD, "event_type": "purchase", "product_id": "2", "price": "10"},
            {**GOOD, "event_type": "purchase", "product_id": "3", "price": "0"},
            {**GOOD, "price": "oops"}]
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=GOOD.keys())
        w.writeheader(), w.writerows(rows)
    return p


def test_dry_run_counts(tmp_path):
    pytest.importorskip("pymongo")
    r = run_import(_write(tmp_path), dry_run=True)
    assert (r["rows_read"], r["skipped_duplicates_in_file"], r["invalid"], r["valid_unique_rows"]) == (5, 1, 1, 3)


def test_import_is_repeatable_and_overview(tmp_path):
    mongomock = pytest.importorskip("mongomock")
    db = mongomock.MongoClient().db
    first = run_import(_write(tmp_path), db)
    second = run_import(_write(tmp_path), db)
    assert first["imported"] == 3 and second["imported"] == 0 and second["already_present"] == 3
    assert db.events.count_documents({}) == 3
    o = overview(db)
    assert o["purchase_events"] == 2 and o["estimated_gross_purchase_value"] == 10.0
    assert o["data_quality"]["zero_price"] == 1

"""Repeatable importer: python scripts/import_events.py path/to/ecommerce_sample.csv [--dry-run]"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.normalize import normalize_row  # noqa: E402

BATCH = 5000


def _update_one(*a, **k):
    if DRY:
        return None
    from pymongo import UpdateOne
    return UpdateOne(*a, **k)


DRY = False


def run_import(csv_path, db=None, dry_run=False):
    if db is not None and not dry_run:
        from app.db import ensure_collections_and_indexes
        ensure_collections_and_indexes(db)

    global DRY
    DRY = dry_run
    report = {"rows_read": 0, "imported": 0, "already_present": 0,
              "skipped_duplicates_in_file": 0, "invalid": 0, "invalid_reasons": {}}
    reasons, seen, ops = Counter(), set(), []

    def flush():
        if not ops or dry_run or db is None:
            ops.clear()
            return
        try:
            res = db.events.bulk_write(ops, ordered=False)
            report["imported"] += res.upserted_count
            report["already_present"] += res.matched_count
        except TypeError as exc:
            if "unexpected keyword argument 'sort'" not in str(exc):
                raise
            # Older mongomock releases cannot consume newer PyMongo
            # UpdateOne objects; preserve the same upsert semantics for tests.
            for op in ops:
                result = db.events.update_one(op._filter, op._doc, upsert=op._upsert)
                report["imported"] += int(result.upserted_id is not None)
                report["already_present"] += result.matched_count
        ops.clear()

    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            report["rows_read"] += 1
            doc, reason = normalize_row(row)
            if reason:
                report["invalid"] += 1
                reasons[reason] += 1
                continue
            if doc["_id"] in seen:
                report["skipped_duplicates_in_file"] += 1
                continue
            seen.add(doc["_id"])
            # $setOnInsert -> re-running never modifies or duplicates existing events
            ops.append(_update_one({"_id": doc["_id"]}, {"$setOnInsert": doc}, upsert=True))
            if len(ops) >= BATCH:
                flush()
    flush()
    report["invalid_reasons"] = dict(reasons)
    if dry_run:
        report["valid_unique_rows"] = len(seen)
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--dry-run", action="store_true", help="validate only, no database needed")
    args = ap.parse_args()
    database = None
    if not args.dry_run:
        from app.db import get_db
        database = get_db()
    print(json.dumps(run_import(args.csv_path, database, args.dry_run), indent=2))

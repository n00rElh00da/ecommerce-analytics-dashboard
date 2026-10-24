"""MongoDB aggregation-pipeline analytics. Filters: date_from, date_to, category, brand, event_type."""
import re

GROSS_VALUE_DEFINITION = ("Sum of `price` over purchase events with price > 0. Each purchase event is one item "
                          "line, not a unique order, so this is an estimate of gross purchase value.")


def build_match(date_from=None, date_to=None, category=None, brand=None, event_type=None):
    m = {}
    if date_from or date_to:
        m["event_time"] = {}
        if date_from:
            m["event_time"]["$gte"] = date_from
        if date_to:
            m["event_time"]["$lte"] = date_to
    if category:
        m["category_code"] = {"$regex": "^" + re.escape(category)}
    if brand:
        m["brand"] = brand.strip().lower()
    if event_type:
        m["event_type"] = event_type
    return m


def _count_users(db, match, extra=None):
    out = list(db.events.aggregate([{"$match": match}, *(extra or []),
                                    {"$group": {"_id": "$user_id"}}, {"$count": "n"}]))
    return out[0]["n"] if out else 0


def overview(db, **filters):
    match = build_match(**filters)
    by_type = {r["_id"]: r["count"] for r in db.events.aggregate(
        [{"$match": match}, {"$group": {"_id": "$event_type", "count": {"$sum": 1}}}])}
    purchases = {"event_type": "purchase"}
    gross = list(db.events.aggregate([
        {"$match": match}, {"$match": {**purchases, "price": {"$gt": 0}}},
        {"$group": {"_id": None, "total": {"$sum": "$price"}}}]))
    span = list(db.events.aggregate([
        {"$match": match}, {"$group": {"_id": None, "first": {"$min": "$event_time"},
                                       "last": {"$max": "$event_time"}}}]))
    q = list(db.events.aggregate([{"$match": match}, {"$group": {
        "_id": None, "total": {"$sum": 1},
        "missing_brand": {"$sum": {"$cond": [{"$eq": ["$brand", None]}, 1, 0]}},
        "missing_category": {"$sum": {"$cond": [{"$eq": ["$category_code", None]}, 1, 0]}},
        "zero_price": {"$sum": {"$cond": ["$price_is_zero", 1, 0]}}}}]))
    return {
        "period": {"first_event": span[0]["first"], "last_event": span[0]["last"]} if span else None,
        "total_events": sum(by_type.values()),
        "views": by_type.get("view", 0),
        "cart_additions": by_type.get("cart", 0),
        "cart_removals": by_type.get("remove_from_cart", 0),
        "purchase_events": by_type.get("purchase", 0),
        "distinct_active_users": _count_users(db, match),
        "distinct_purchasing_users": _count_users(db, match, [{"$match": purchases}]),
        "estimated_gross_purchase_value": round(gross[0]["total"], 2) if gross else 0.0,
        "gross_purchase_value_definition": GROSS_VALUE_DEFINITION,
        "data_quality": {k: v for k, v in (q[0] if q else {}).items() if k != "_id"},
    }


def _t(name):
    return {"$sum": {"$cond": [{"$eq": ["$event_type", name]}, 1, 0]}}


COUNTS = {"views": _t("view"), "carts": _t("cart"), "purchases": _t("purchase")}
_GROSS = {"$sum": {"$cond": [{"$and": [{"$eq": ["$event_type", "purchase"]}, {"$gt": ["$price", 0]}]}, "$price", 0]}}


def _clean(rows, rename=None):
    return [{("name" if k == "_id" else k): v for k, v in r.items()} for r in rows]


def activity(db, bucket="hour", **f):
    fmt = "%Y-%m-%d %H:00" if bucket == "hour" else "%Y-%m-%d"
    rows = db.events.aggregate([
        {"$match": build_match(**f)},
        {"$group": {"_id": {"$dateToString": {"format": fmt, "date": "$event_time"}}, **COUNTS, "gross": _GROSS}},
        {"$sort": {"_id": 1}}])
    return [{**r, "gross": round(r["gross"], 2)} for r in _clean(rows)]


def breakdown(db, field, limit=15, **f):
    rows = db.events.aggregate([
        {"$match": build_match(**f)}, {"$group": {"_id": "$" + field, **COUNTS}},
        {"$sort": {"purchases": -1, "views": -1}}, {"$limit": limit}])
    return [{**r, "name": r["name"] or "Unknown"} for r in _clean(rows)]


_PRODUCT = {"_id": "$product_id", **COUNTS, "brand": {"$first": "$brand"}, "category": {"$first": "$category_code"},
            "avg_price": {"$avg": {"$cond": [{"$gt": ["$price", 0]}, "$price", None]}}}


def _products(rows):
    return [{**r, "product_id": r.pop("name"), "avg_price": round(r["avg_price"], 2) if r["avg_price"] else None}
            for r in _clean(rows)]


def top_products(db, limit=10, skip=0, **f):
    return _products(db.events.aggregate([
        {"$match": build_match(**f)}, {"$group": _PRODUCT},
        {"$sort": {"purchases": -1, "views": -1}}, {"$skip": skip}, {"$limit": limit}]))


def underperforming(db, min_views=5, limit=10, **f):
    """Products with many views and a low purchase-event/view ratio."""
    return _products(db.events.aggregate([
        {"$match": build_match(**f)}, {"$group": _PRODUCT}, {"$match": {"views": {"$gte": min_views}}},
        {"$addFields": {"purchase_rate": {"$divide": ["$purchases", "$views"]}}},
        {"$sort": {"purchase_rate": 1, "views": -1}}, {"$limit": limit}]))


def funnel(db, **f):
    """Distinct users who performed each event at least once (not a strict sequence)."""
    rows = db.events.aggregate([
        {"$match": build_match(**f)}, {"$group": {"_id": "$user_id", "t": {"$addToSet": "$event_type"}}},
        {"$unwind": "$t"}, {"$group": {"_id": "$t", "users": {"$sum": 1}}}])
    n = {r["_id"]: r["users"] for r in rows}
    base = n.get("view", 0)
    return [{"stage": s, "users": n.get(e, 0), "pct_of_viewers": round(100 * n.get(e, 0) / base, 2) if base else None}
            for s, e in (("Viewed", "view"), ("Added to cart", "cart"), ("Purchased", "purchase"))]


def customers_summary(db, **f):
    """Repeat purchasing user = anonymous user_id with purchase events in 2+ distinct sessions."""
    f = {**f, "event_type": "purchase"}
    rows = list(db.events.aggregate([
        {"$match": build_match(**f)},
        {"$group": {"_id": "$user_id", "sessions": {"$addToSet": "$user_session"}}},
        {"$group": {"_id": None, "purchasing_users": {"$sum": 1},
                    "repeat_users": {"$sum": {"$cond": [{"$gte": [{"$size": "$sessions"}, 2]}, 1, 0]}}}}]))
    r = rows[0] if rows else {"purchasing_users": 0, "repeat_users": 0}
    return {"purchasing_users": r["purchasing_users"], "repeat_purchasing_users": r["repeat_users"],
            "definition": "Anonymous user_id values with purchase events in 2+ distinct sessions within the "
                          "selected window. The sample window is short, so repeat purchasing is understated."}


def catalog(db, search=None, page=1, page_size=12):
    m = {}
    if search:
        rx = {"$regex": re.escape(search.strip()), "$options": "i"}
        m["$or"] = [{"brand": rx}, {"category_code": rx}]
    rows = db.events.aggregate([
        {"$match": m}, {"$group": _PRODUCT}, {"$sort": {"views": -1}},
        {"$skip": (page - 1) * page_size}, {"$limit": page_size}])
    return _products(rows)

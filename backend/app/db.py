from pymongo import ASCENDING, MongoClient

from .config import MONGODB_DB, MONGODB_URI

EVENTS_VALIDATOR = {"$jsonSchema": {
    "bsonType": "object",
    "required": ["event_time", "event_type", "product_id", "price", "user_id", "user_session"],
    "properties": {
        "event_time": {"bsonType": "date"},
        "event_type": {"enum": ["view", "cart", "remove_from_cart", "purchase"]},
        "product_id": {"bsonType": ["int", "long"]},
        "user_id": {"bsonType": ["int", "long"]},
        "price": {"bsonType": ["double", "int", "long"], "minimum": 0},
        "user_session": {"bsonType": "string"},
    },
}}


def get_db(uri=MONGODB_URI, name=MONGODB_DB):
    return MongoClient(uri)[name]


def ensure_collections_and_indexes(db):
    if "events" not in db.list_collection_names():
        try:
            db.create_collection("events", validator=EVENTS_VALIDATOR)
        except NotImplementedError:
            # mongomock does not implement collection validators; application
            # validation still happens before writes in the importer.
            db.create_collection("events")
    ev = db.events
    ev.create_index([("event_time", ASCENDING)])
    ev.create_index([("event_type", ASCENDING), ("event_time", ASCENDING)])
    ev.create_index([("product_id", ASCENDING)])
    ev.create_index([("user_id", ASCENDING)])
    ev.create_index([("category_code", ASCENDING)])
    ev.create_index([("brand", ASCENDING)])
    # Required by the spec; populated by later features (auth / favorites / orders).
    db.users.create_index("google_sub", unique=True)
    db.favorites.create_index([("user_sub", ASCENDING), ("product_id", ASCENDING)], unique=True)


from functools import lru_cache  # noqa: E402


@lru_cache(maxsize=1)
def shared_db():
    return get_db()

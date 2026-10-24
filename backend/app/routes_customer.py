from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from . import analytics as a
from .auth import current_user, db_dep, public

router = APIRouter(prefix="/api/customer")
HISTORY_NOTE = ("Historical dataset events are tied to anonymous behavioural IDs, not Google accounts, "
                "so they are not shown as your personal history.")


class FavoriteIn(BaseModel):
    product_id: int


@router.get("/me")
def me(user=Depends(current_user), db=Depends(db_dep)):
    return {**public(user), "favorites_count": db.favorites.count_documents({"user_sub": user["google_sub"]}),
            "member_since": user.get("created_at"), "historical_history_note": HISTORY_NOTE}


@router.get("/products")
def browse(search: Optional[str] = None, page: int = Query(1, ge=1), user=Depends(current_user), db=Depends(db_dep)):
    return a.catalog(db, search, page)


@router.get("/favorites")
def favorites(user=Depends(current_user), db=Depends(db_dep)):
    favs = list(db.favorites.find({"user_sub": user["google_sub"]}, {"_id": 0}).sort("created_at", -1))
    info = {p["product_id"]: p for p in a._products(db.events.aggregate(
        [{"$match": {"product_id": {"$in": [x["product_id"] for x in favs]}}}, {"$group": a._PRODUCT}]))}
    return [{**f, **info.get(f["product_id"], {})} for f in favs]


@router.post("/favorites", status_code=201)
def add_favorite(body: FavoriteIn, user=Depends(current_user), db=Depends(db_dep)):
    if not db.events.find_one({"product_id": body.product_id}, {"_id": 1}):
        raise HTTPException(404, "Unknown product")
    db.favorites.update_one({"user_sub": user["google_sub"], "product_id": body.product_id},
                            {"$setOnInsert": {"created_at": datetime.now(timezone.utc)}}, upsert=True)
    return {"product_id": body.product_id}


@router.delete("/favorites/{product_id}", status_code=204)
def remove_favorite(product_id: int, user=Depends(current_user), db=Depends(db_dep)):
    db.favorites.delete_one({"user_sub": user["google_sub"], "product_id": product_id})

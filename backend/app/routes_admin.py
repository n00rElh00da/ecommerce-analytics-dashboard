from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from . import analytics as a
from .auth import db_dep, require_admin

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])


def filters(date_from: Optional[datetime] = None, date_to: Optional[datetime] = None,
            category: Optional[str] = None, brand: Optional[str] = None,
            event_type: Optional[Literal["view", "cart", "remove_from_cart", "purchase"]] = None):
    return dict(date_from=date_from, date_to=date_to, category=category, brand=brand, event_type=event_type)


@router.get("/options")
def options(db=Depends(db_dep)):
    brands = db.events.aggregate([{"$match": {"brand": {"$ne": None}}}, {"$group": {"_id": "$brand", "n": {"$sum": 1}}},
                                  {"$sort": {"n": -1}}, {"$limit": 100}])
    return {"categories": sorted(c for c in db.events.distinct("category_top") if c),
            "brands": [r["_id"] for r in brands]}


@router.get("/overview")
def overview(f=Depends(filters), db=Depends(db_dep)):
    return a.overview(db, **f)


@router.get("/sales")
def sales(bucket: Literal["hour", "day"] = "hour", f=Depends(filters), db=Depends(db_dep)):
    return a.activity(db, bucket, **f)


@router.get("/products/top")
def top(limit: int = Query(10, ge=1, le=100), skip: int = Query(0, ge=0), f=Depends(filters), db=Depends(db_dep)):
    return a.top_products(db, limit, skip, **f)


@router.get("/products/underperforming")
def under(min_views: int = Query(5, ge=1), limit: int = Query(10, ge=1, le=100), f=Depends(filters), db=Depends(db_dep)):
    return a.underperforming(db, min_views, limit, **f)


@router.get("/categories")
def categories(limit: int = Query(15, ge=1, le=100), f=Depends(filters), db=Depends(db_dep)):
    return a.breakdown(db, "category_code", limit, **f)


@router.get("/brands")
def brands(limit: int = Query(15, ge=1, le=100), f=Depends(filters), db=Depends(db_dep)):
    return a.breakdown(db, "brand", limit, **f)


@router.get("/funnel")
def funnel(f=Depends(filters), db=Depends(db_dep)):
    return a.funnel(db, **f)


@router.get("/customers/summary")
def customers(f=Depends(filters), db=Depends(db_dep)):
    return a.customers_summary(db, **f)

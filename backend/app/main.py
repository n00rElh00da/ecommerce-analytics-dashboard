from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pymongo.errors import PyMongoError

from . import auth, config
from .db import ensure_collections_and_indexes, shared_db
from .routes_admin import router as admin_router
from .routes_customer import router as customer_router


@asynccontextmanager
async def lifespan(app):
    config.require_secrets()
    ensure_collections_and_indexes(shared_db())
    yield


app = FastAPI(title="E-commerce Analytics API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[config.FRONTEND_ORIGIN], allow_credentials=True,
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type"])
app.include_router(admin_router)
app.include_router(customer_router)


@app.exception_handler(PyMongoError)
async def mongo_error(_, exc):
    return JSONResponse({"detail": "Database unavailable. Check that MongoDB is running."}, status_code=503)


class GoogleLogin(BaseModel):
    credential: str


@app.post("/api/auth/google")
def google_login(body: GoogleLogin, response: Response, db=Depends(auth.db_dep)):
    try:
        info = auth.verify_google_credential(body.credential)
    except ValueError:
        raise HTTPException(401, "Google sign-in could not be verified")
    user = auth.upsert_user(db, info)
    response.set_cookie(auth.COOKIE, auth.make_session_token(user["google_sub"]), httponly=True, samesite="lax",
                        secure=config.COOKIE_SECURE, max_age=auth.SESSION_SECONDS, path="/")
    return auth.public(user)


@app.get("/api/auth/me")
def whoami(user=Depends(auth.current_user)):
    return auth.public(user)


@app.post("/api/auth/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(auth.COOKIE, path="/")

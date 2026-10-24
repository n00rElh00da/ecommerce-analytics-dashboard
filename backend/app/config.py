import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # optional; real env vars still work
    pass

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "ecommerce_analytics")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
JWT_SECRET = os.getenv("JWT_SECRET", "")
ADMIN_EMAILS = {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()}
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"


def require_secrets():
    if not GOOGLE_CLIENT_ID:
        raise RuntimeError("GOOGLE_CLIENT_ID is not set (see backend/.env.example)")
    if len(JWT_SECRET) < 32:
        raise RuntimeError("JWT_SECRET must be set to 32+ random characters")

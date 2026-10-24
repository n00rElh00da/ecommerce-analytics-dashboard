# Shopper Signals: e-commerce analytics (FastAPI + MongoDB + React)

Analytics on the Kaggle "eCommerce behavior data, October 2019" sample (`ecommerce_sample.csv`, 100,000 events).
Stack: React + Vite, FastAPI, MongoDB, Google sign-in, GSAP/ScrollTrigger, Lenis, Recharts.

## Dataset facts
- The sample covers **2019-10-01 00:00 to 04:28 UTC** only, not the full month. The dashboard labels the period from the imported data.
- Event types present: `view`, `cart`, `purchase`. No `remove_from_cart` events exist, so cart removals show 0.
- 17 exact duplicates are collapsed on import; 119 zero-price rows are kept, flagged and excluded from gross value.
- `user_id` values are anonymous behavioural IDs, never mapped to Google accounts. Purchase events are item lines, not unique orders.

## Prerequisites
Python 3.11+, Node 18+, MongoDB 6+ running locally (or a MongoDB Atlas URI).

## 1. MongoDB
Install MongoDB Community Server (Windows service starts automatically) or create a free Atlas cluster.
Local URI: `mongodb://localhost:27017`. The database and indexes are created automatically.

## 2. Google OAuth
1. Google Cloud Console > APIs & Services > OAuth consent screen: configure it (External, add yourself as a test user).
2. Credentials > Create credentials > **OAuth client ID** > type **Web application**.
3. Authorized JavaScript origins: `http://localhost:5173`. No redirect URI is needed (Google Identity Services ID-token flow).
4. Copy the client ID into `backend/.env` (`GOOGLE_CLIENT_ID`) and `frontend/.env` (`VITE_GOOGLE_CLIENT_ID`). There is no client secret in this flow.

## 3. Backend (PowerShell)
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets;print(secrets.token_urlsafe(48))"   # paste into JWT_SECRET in .env
notepad .env   # set GOOGLE_CLIENT_ID, JWT_SECRET, ADMIN_EMAILS
```
**Admins** are exactly the emails listed in `ADMIN_EMAILS` (comma-separated, server-side only). Everyone else is a `customer`. Roles are re-evaluated from this setting on every request; no endpoint accepts a role from the client.

## 4. Import the dataset
Copy `ecommerce_sample.csv` to `data\ecommerce_sample.csv`, then:
```powershell
python scripts/import_events.py ..\data\ecommerce_sample.csv --dry-run   # validate only
python scripts/import_events.py ..\data\ecommerce_sample.csv             # import; safe to re-run
```
The report lists rows read, imported, already present, in-file duplicates skipped and invalid rows.

## 5. Run
```powershell
# terminal 1 (backend/, venv active)
uvicorn app.main:app --reload --port 8000
# terminal 2
cd frontend
Copy-Item .env.example .env   # set VITE_GOOGLE_CLIENT_ID
npm install
npm run dev                   # http://localhost:5173
```

## 6. Tests
```powershell
cd backend; python -m pytest        # import, analytics, API auth/role tests
cd ..\frontend; npm run build      # compile check
```

## Known limitations
See the summary in the delivery message for what has and has not been verified, and what is not implemented
(React Bits components, app-created orders).

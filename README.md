# CryptoTrack Backend

FastAPI backend for the CryptoTrack cryptocurrency portfolio tracker. Provides authenticated CRUD APIs for managing crypto assets with real-time price data from CoinGecko.

## Tech Stack

- **Framework:** FastAPI (async Python)
- **Database:** PostgreSQL via async SQLAlchemy + asyncpg
- **Auth:** Clerk JWT verification (RS256 / JWKS)
- **Migrations:** Alembic (async)
- **Prices:** CoinGecko free API (60s in-memory cache)

---

## Project Structure

```
crypto-track-backend/
│
├── app/                  # Main application package
│   ├── __init__.py
│   ├── main.py           # App entry point
│   ├── config.py         # Centralized settings
│   │
│   ├── core/             # Infrastructure
│   │   ├── auth.py       # Clerk JWT verification
│   │   └── database.py   # Database engine
│   │
│   ├── models/           # ORM models
│   │   └── asset.py
│   │
│   ├── schemas/          # Pydantic schemas
│   │   └── asset.py
│   │
│   ├── crud/             # Database operations
│   │   └── asset.py
│   │
│   ├── services/         # External services
│   │   └── coingecko.py
│   │
│   └── routes/           # API routes
│       ├── assets.py
│       └── dashboard.py
│
├── alembic/              # Migrations (stays at root)
├── alembic.ini           # Alembic config
├── requirements.txt
├── .env
└── README.md
```

## Setup

### 1. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate      # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
CORS_ORIGINS=http://localhost:3000
```

### 3. Run database migrations

```bash
alembic upgrade head
```

### 4. Start the server

```bash
# Development (auto-reload)
uvicorn app.main:app --reload

# Production
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Server runs at `http://localhost:8000`

- Swagger docs: `http://localhost:8000/docs`

---

## How to Test

### 1. API Verification (Swagger UI)
The easiest way to test the backend in isolation is via the auto-generated Swagger UI:

1.  **Run the server**: `uvicorn app.main:app --reload`
2.  **Open**: [http://localhost:8000/docs](http://localhost:8000/docs)
3.  **Authorize**: Click the "Authorize" button and paste a valid Clerk JWT (you can get one from the frontend browser console `window.Clerk.session.getToken()`).
4.  **Execute**: Try the `GET /api/assets` endpoint to see your data.

### 2. Full Flow
Run the **Frontend** (see frontend README) and interact with the UI. The specific flow is:
1.  **Login** via Clerk.
2.  **Dashboard** loads -> calls `GET /api/assets` and `GET /api/dashboard/stats`.
3.  **Add Asset** -> calls `POST /api/assets`.
4.  **Edit/Delete** -> calls `PUT` / `DELETE`.

## Authentication

All `/api/*` endpoints require a **Clerk JWT token** in the Authorization header:

```
Authorization: Bearer <clerk_session_token>
```

The backend verifies this token using Clerk's JWKS (JSON Web Key Set) endpoint. The `sub` claim in the JWT is extracted as the `user_id` to scope all data.

**Flow:**
1. Frontend calls `getToken()` from `@clerk/nextjs`
2. Sends token as `Authorization: Bearer <token>`
3. Backend `auth.py` fetches Clerk's public keys (cached 1 hour)
4. Verifies the JWT signature (RS256), expiry, and issuer
5. Extracts `sub` → used as `user_id` for all DB queries

---

## API Endpoints

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | API info + version |
| `GET` | `/health` | Health check (`{"status": "healthy"}`) |

No authentication required.

---

### Assets — `/api/assets`

All endpoints require `Authorization: Bearer <token>`.

#### `GET /api/assets`

Returns all assets for the authenticated user, enriched with live prices.

**Response** `200`:
```json
[
  {
    "id": 1,
    "user_id": "user_abc",
    "symbol": "bitcoin",
    "ticker": "BTC",
    "quantity": 0.5,
    "buy_price": 60000.0,
    "created_at": "2026-01-15T10:30:00",
    "current_price": 96721.0,
    "total_value": 48360.5,
    "profit_loss": 18360.5,
    "profit_loss_percent": 61.2
  }
]
```

#### `POST /api/assets`

Creates a new asset.

**Request body:**
```json
{
  "symbol": "bitcoin",
  "ticker": "BTC",
  "quantity": 0.5,
  "buy_price": 60000
}
```

**Validation rules:**
- `symbol`: 1–100 chars, auto-lowercased
- `ticker`: 1–10 chars, auto-uppercased
- `quantity`: > 0, max 1,000,000,000
- `buy_price`: > 0, max 100,000,000

**Response** `201`: Created asset with live price data.

#### `PUT /api/assets/{id}`

Updates quantity and/or buy_price for an existing asset.

**Request body:**
```json
{
  "quantity": 1.0,
  "buy_price": 55000
}
```

**Response** `200`: Updated asset with live price data.
**Error** `404`: Asset not found or doesn't belong to user.

#### `DELETE /api/assets/{id}`

Deletes an asset.

**Response** `204`: No content.
**Error** `404`: Asset not found or doesn't belong to user.

---

### Dashboard — `/api/dashboard/stats`

#### `GET /api/dashboard/stats`

Returns portfolio summary with allocation breakdown.

**Response** `200`:
```json
{
  "total_portfolio_value": 85240.50,
  "total_invested": 65000.00,
  "total_profit_loss": 20240.50,
  "total_profit_loss_percent": 31.14,
  "asset_count": 3,
  "allocations": [
    {
      "symbol": "bitcoin",
      "ticker": "BTC",
      "value": 48360.50,
      "percentage": 56.7
    },
    {
      "symbol": "ethereum",
      "ticker": "ETH",
      "value": 36880.00,
      "percentage": 43.3
    }
  ]
}
```

Allocations are sorted by value (descending). If a user holds the same coin in multiple entries, values are aggregated.

---

## Database

### Assets Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Unique identifier |
| `user_id` | String | NOT NULL, indexed | Clerk user ID |
| `symbol` | String | NOT NULL | CoinGecko coin ID (e.g., `bitcoin`) |
| `ticker` | String | NOT NULL | Display ticker (e.g., `BTC`) |
| `quantity` | Float | NOT NULL | Amount held |
| `buy_price` | Float | NOT NULL | Purchase price (USD) |
| `created_at` | Timestamp | auto, UTC | Creation timestamp |

### Migrations

Managed by **Alembic** (not `create_all`).

```bash
# Check current migration
alembic current

# Create a new migration after changing models.py
alembic revision --autogenerate -m "description_of_change"

# Apply pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

---

## Common CoinGecko Symbol IDs

| Crypto | Symbol ID |
|--------|-----------|
| Bitcoin | `bitcoin` |
| Ethereum | `ethereum` |
| Solana | `solana` |
| Cardano | `cardano` |
| Polygon | `matic-network` |
| Ripple | `ripple` |
| Dogecoin | `dogecoin` |
| Polkadot | `polkadot` |

Full list: https://api.coingecko.com/api/v3/coins/list

---

## Error Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `204` | Deleted (no content) |
| `401` | Unauthorized — missing or invalid JWT |
| `404` | Asset not found |
| `422` | Validation error — bad input |
| `429` | CoinGecko rate limited (handled internally with cache fallback) |
| `503` | Auth service unavailable (JWKS fetch failed) |

---

## License

MIT

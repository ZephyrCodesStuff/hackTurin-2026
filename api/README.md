# Traffic Camera API

Quick-start notes for the hackathon.

---

## 1. Quick Start

### Option A: Docker (Recommended)
```sh
docker compose up --build
```
API runs at **http://localhost:8000**  
Swagger docs at **http://localhost:8000/docs**

### Option B: Local Dev
```sh
uv sync
uv run fastapi dev src/traffic_api/main.py
```

---

## 2. Generate a Camera JWT

Tokens are signed locally with the private key (from `.env`):

```sh
# Generate token for a camera UUID:
uv run python scripts/jwt.py 550e8400-e29b-41d4-a716-446655440000

# With custom subject & lifetime (hours):
uv run python scripts/jwt.py 550e8400-e29b-41d4-a716-446655440000 --subject north-cam --expires-hours 12
```

---

## 3. Photo Upload & Retrieval

Before reporting a crash, upload the image to get a server-generated `photo_id` (UUIDv4):

### Upload Photo
```sh
curl -X POST http://localhost:8000/cameras/550e8400-e29b-41d4-a716-446655440000/photos \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: image/jpeg" \
  --data-binary "@crash.jpg"
```
**Response (`200 OK`):**
```json
{
  "photo_id": "a135904d-e7ec-4c96-8a1e-427e49015163",
  "camera_id": "550e8400-e29b-41d4-a716-446655440000",
  "bytes_received": 52410
}
```

### View / Download Photo
```sh
curl -O http://localhost:8000/photos/a135904d-e7ec-4c96-8a1e-427e49015163
```

---

## 4. Test Ingest Endpoint

Send data for an authorized camera:

```sh
TOKEN="<paste-token-here>"

curl -X POST http://localhost:8000/cameras/550e8400-e29b-41d4-a716-446655440000/ingest \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {"type": "light_change", "color": "red"},
      {"type": "illegal_crossing"},
      {"type": "object_detected", "velocity": 34.2},
      {"type": "crash", "photo_id": "6ba7b810-9dad-41d1-80b4-00c04fd430c8"}
    ]
  }'
```

> **Note:** If the camera doesn't exist yet, it is automatically created in `CAMERA`.

### Supported Event Types (`events: [...]`)

| `type` | Required Fields | Optional Fields | Description |
|---|---|---|---|
| `"light_change"` | `color`: `"red"` \| `"amber"` \| `"green"` | `timestamp`: epoch ms | Traffic signal state changes |
| `"illegal_crossing"` | *(none)* | `timestamp`: epoch ms | Jaywalking / crossing violation |
| `"object_detected"` | *(none)* | `velocity`: float, `timestamp`: epoch ms | Moving vehicle / pedestrian detected |
| `"crash"` | `photo_id`: UUIDv4 | `timestamp`: epoch ms | Incident photo capture |

* `timestamp` defaults to current server Unix epoch milliseconds if omitted.
* Any mixture of event types can be sent in a single `events` array.

#### Example Request Body
```json
{
  "events": [
    {
      "type": "light_change",
      "color": "green",
      "timestamp": 1700000000000
    },
    {
      "type": "illegal_crossing"
    },
    {
      "type": "object_detected",
      "velocity": 45.8
    },
    {
      "type": "crash",
      "photo_id": "6ba7b810-9dad-41d1-80b4-00c04fd430c8"
    }
  ]
}
```

#### Example Success Response (`200 OK`)
```json
{
  "message": "Successfully ingested 4 event(s)",
  "camera_id": "550e8400-e29b-41d4-a716-446655440000",
  "submitted_by": "local-camera-authorizer",
  "counts": {
    "crashes": 1,
    "light_changes": 1,
    "illegal_crossings": 1,
    "objects_detected": 1
  }
}
```

#### Error Responses
* **`401 Unauthorized`**: Token missing, expired, or signature invalid.
  ```json
  {"detail": "Invalid or expired bearer token"}
  ```
* **`403 Forbidden`**: Token is valid, but not authorized for this specific `camera_id`.
  ```json
  {"detail": "Token is not authorized for this camera"}
  ```
* **`422 Unprocessable Entity`**: Invalid payload (e.g. invalid UUID, unsupported event type, invalid traffic color).

---

## 5. Auth & Keys TL;DR

* **API** only knows the **Public Key** (`JWT_PUBLIC_KEY_B64` in `.env`).
* **CLI** signs tokens using the **Private Key** (`JWT_PRIVATE_KEY_B64` in `.env`).
* If you ever need to regenerate keys:
  ```sh
  openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out jwt-private.pem
  openssl pkey -in jwt-private.pem -pubout -out jwt-public.pem
  echo "JWT_PRIVATE_KEY_B64=\"$(base64 < jwt-private.pem | tr -d '\n')\"" > .env
  echo "JWT_PUBLIC_KEY_B64=\"$(base64 < jwt-public.pem | tr -d '\n')\"" >> .env
  ```

---

## 6. Database

* SQLite file is at `data/traffic.db` (auto-created on startup with `schema.sql`).
* To inspect DB directly:
  ```sh
  sqlite3 data/traffic.db "SELECT * FROM CAMERA;"
  ```

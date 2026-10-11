# Traffic Camera API

Internal hackathon reference. This is the contract between the **camera firmware** and the backend.

- **Base URL (local):** `http://localhost:8000`
- **Base URL (Docker):** `http://api:8000` from inside the website container, `http://localhost:8000` from your machine
- **Interactive docs / request builder:** `http://localhost:8000/docs`
- All request/response bodies are **JSON** unless noted (the photo upload is raw bytes).
- Timestamps are **Unix epoch milliseconds** (`int`). If you omit a `timestamp`, the server stamps it with its own clock.
- Camera IDs are **UUIDv4** strings. `photo_id` values are also UUIDv4.

---

## 1. Run it

```sh
# Local dev (auto-reloads):
uv sync
uv run fastapi dev src/traffic_api/main.py        # -> http://localhost:8000

# Or everything (API + website) via Docker from the repo root:
docker compose up --build                          # API :8000, website :3000
```

---

## 2. Firmware auth in 30 seconds

The camera endpoints (heartbeat, ingest, photo upload) require a **bearer token**. It's a JWT signed with a **shared secret** (`CAMERA_JWT_SECRET` in `api/.env`), using **HS256**.

The token carries the list of camera UUIDs it is allowed to act for. The API rejects a request if the camera ID in the URL is not in that list.

### Generate a token for your camera

```sh
# One camera, default 24h lifetime:
uv run python scripts/auth.py 550e8400-e29b-41d4-a716-446655440001

# Multiple cameras (comma-separated), custom subject + lifetime:
uv run python scripts/auth.py 550e8400-...-001,550e8400-...-002 \
  --subject north-gate-cam --expires-hours 72
```

It prints the token to stdout. Use it as:

```
Authorization: Bearer <token>
```

Keep the firmware's clock roughly correct — expired or not-yet-valid tokens are rejected.

> If you need to understand or regenerate the token yourself, the payload is:
> ```json
> {
>   "sub": "<device name>",
>   "iss": "traffic-camera-api",
>   "iat": <epoch>,
>   "exp": <epoch>,
>   "authorized_camera_ids": ["<uuid>", ...],
>   "type": "camera_token"
> }
> ```
> signed HS256 with the secret in `api/.env` (`CAMERA_JWT_SECRET`).

---

## 3. Endpoint cheat sheet

| Method | Path | Auth | Who calls it |
|---|---|---|---|
| `POST` | `/cameras/{camera_id}/heartbeat` | Bearer (camera) | **Firmware** |
| `POST` | `/cameras/{camera_id}/ingest` | Bearer (camera) | **Firmware** |
| `POST` | `/cameras/{camera_id}/photos` | Bearer (camera) | **Firmware** |
| `GET`  | `/photos/{photo_id}` | none | Website / anyone |
| `GET`  | `/cameras` | none | Website |
| `GET`  | `/cameras/{camera_id}` | none | Website |
| `GET`  | `/cameras/{camera_id}/events` | none | Website |
| `PATCH`| `/cameras/{camera_id}/edit` | none | Website |
| `POST` | `/crashes/{crash_id}/resolve` | none | Website |

> **Firmware only needs the three Bearer rows.** The rest are for the dashboard.

Common error codes on the camera endpoints:
- `401` — token missing, malformed, or expired.
- `403` — token is valid but not authorized for this `camera_id`.
- `409` — camera state is `offline` (taken down). Heartbeats, ingest, and photo upload are all rejected until it's set back online.
- `422` — body failed validation (bad UUID, unknown event type, out-of-range value).

---

## 4. Firmware: heartbeat

Send periodically (e.g. every few seconds) so the dashboard knows the camera is alive and healthy.

```
POST /cameras/{camera_id}/heartbeat
Authorization: Bearer <token>
Content-Type: application/json
```

**Body (all fields optional):**
```json
{
  "last_event_timestamp": 1700000045000,
  "battery_level": 88.5,
  "firmware_version": "1.0.4",
  "wifi_signal": -65
}
```

| Field | Type | Notes |
|---|---|---|
| `last_heartbeat` | int (epoch ms) | Defaults to server time if omitted |
| `last_event_timestamp` | int (epoch ms) | When this camera last saw an event |
| `battery_level` | float | `0.0`–`100.0` |
| `firmware_version` | string | e.g. `"1.0.4"` |
| `wifi_signal` | int | RSSI in dBm, e.g. `-65` |

> `name`, `location`, and `state` are **not** settable via heartbeat (deprecated). Use `PATCH /cameras/{camera_id}/edit`.

**Response (`200`):**
```json
{
  "message": "Heartbeat updated successfully",
  "camera_id": "550e8400-e29b-41d4-a716-446655440001",
  "submitted_by": "north-gate-cam",
  "camera": { "...": "full camera record" }
}
```

**curl:**
```sh
curl -X POST http://localhost:8000/cameras/550e8400-e29b-41d4-a716-446655440001/heartbeat \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"battery_level": 88.5, "firmware_version": "1.0.4", "wifi_signal": -65}'
```

---

## 5. Firmware: ingest events

Report what the camera detected. Send one or many events in a single call. If the camera doesn't exist yet in the DB, it's auto-created.

```
POST /cameras/{camera_id}/ingest
Authorization: Bearer <token>
Content-Type: application/json
```

**Body:**
```json
{
  "events": [
    { "type": "light_change", "color": "red" },
    { "type": "illegal_crossing", "entity_type": "pedestrian" },
    { "type": "object_detected", "entity_type": "car", "velocity": 34.2 },
    { "type": "crash", "photo_id": "6ba7b810-9dad-41d1-80b4-00c04fd430c8" }
  ]
}
```

**Event types** (`events` must have at least one entry):

| `type` | Required fields | Optional fields |
|---|---|---|
| `light_change` | `color`: `"red"` \| `"amber"` \| `"green"` | `timestamp` |
| `illegal_crossing` | `entity_type` (see below) | `timestamp` |
| `object_detected` | `entity_type` (see below) | `velocity` (float), `timestamp` |
| `crash` | `photo_id` (UUIDv4 — upload the photo first, see §6) | `timestamp` |

`entity_type` is one of: `pedestrian`, `car`, `motorbike`, `bike`, `truck`, `animal`.

**Response (`200`):**
```json
{
  "message": "Successfully ingested 4 event(s)",
  "camera_id": "550e8400-e29b-41d4-a716-446655440001",
  "submitted_by": "north-gate-cam",
  "counts": { "crashes": 1, "light_changes": 1, "illegal_crossings": 1, "objects_detected": 1 }
}
```

**curl:**
```sh
curl -X POST http://localhost:8000/cameras/550e8400-e29b-41d4-a716-446655440001/ingest \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"events":[{"type":"object_detected","entity_type":"car","velocity":34.2}]}'
```

---

## 6. Firmware: crash photo upload

A `crash` event needs a `photo_id`. Get one by uploading the image **first**, then put the returned `photo_id` in the crash event.

```
POST /cameras/{camera_id}/photos
Authorization: Bearer <token>
Content-Type: image/jpeg          (or image/png, image/webp)
<raw image bytes as the request body>
```

The body is the **raw image bytes**, not JSON. Empty bodies are rejected (`400`).

**Response (`200`):**
```json
{
  "photo_id": "a135904d-e7ec-4c96-8a1e-427e49015163",
  "camera_id": "550e8400-e29b-41d4-a716-446655440001",
  "bytes_received": 52410
}
```

**Typical firmware flow for a crash:**
```sh
# 1. upload the frame, capture the photo_id
PHOTO_ID=$(curl -s -X POST http://localhost:8000/cameras/$CAM/photos \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: image/jpeg" \
  --data-binary "@crash.jpg" | jq -r .photo_id)

# 2. report the crash referencing that photo_id
curl -X POST http://localhost:8000/cameras/$CAM/ingest \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"events\":[{\"type\":\"crash\",\"photo_id\":\"$PHOTO_ID\"}]}"
```

Fetch a stored image (no auth): `GET /photos/{photo_id}` returns the raw bytes with the right content type.

---

## 7. Dashboard endpoints (reference)

Firmware doesn't need these, but they're the other half of the contract.

**`GET /cameras`** — list cameras.
**`GET /cameras/{camera_id}`** — one camera record.
**`GET /cameras/{camera_id}/events`** — all events for a camera, newest first:
```json
{
  "camera_id": "...",
  "camera": { "...": "camera record" },
  "total_events": 2,
  "events": [
    { "type": "crash", "id": 1, "photo_id": "...", "timestamp": 1700000000000,
      "resolved": false, "resolved_at": null, "resolved_by": null, "dispatched_units": [] },
    { "type": "light_change", "id": 2, "color": "red", "timestamp": 1699999990000 }
  ]
}
```

**`PATCH /cameras/{camera_id}/edit`** — update `name`, location, and `state` (`"online"` | `"maintenance"` | `"offline"`). Location can be sent as `latitude`/`longitude` floats, a `[lat, lon]` array, or a string. Send any subset of fields.
```json
{ "name": "Piazza Castello", "latitude": 45.0710, "longitude": 7.6865, "state": "online" }
```

**`POST /crashes/{crash_id}/resolve`** — mark a crash resolved and record which emergency units were dispatched. `{crash_id}` is the numeric event `id` from the events list.
```json
{ "dispatched_units": [1, 2] }
```
`dispatched_units` are integer codes: `1`=Polizia Locale, `2`=Emergenza Sanitaria (118), `3`=Vigili del Fuoco (115), `4`=Carabinieri (112), `5`=Polizia di Stato (113), `6`=Soccorso Stradale (ACI), `7`=Protezione Civile.

---

## 8. Database & demo data

- SQLite file: `data/traffic.db` (auto-created on startup from `schema.sql`).
- Uploaded photos: `data/photos/`.

```sh
uv run python scripts/demo.py nuke          # wipe DB + photos
uv run python scripts/demo.py build         # seed realistic cameras, events, crash photos
uv run python scripts/demo.py build --events-per-camera 30
uv run python scripts/demo.py live          # live traffic-signal simulation
uv run python scripts/demo.py live --interval 2.0

# Point any of the above at a remote API:
uv run python scripts/demo.py build --api-url https://api.myhackathon.dev

# Inspect the DB directly:
sqlite3 data/traffic.db "SELECT * FROM CAMERA;"
```

`nuke` hits the `POST /nuke` endpoint, which only works when the API runs with `DEVELOPMENT_MODE=true` (set in `compose.yaml`).
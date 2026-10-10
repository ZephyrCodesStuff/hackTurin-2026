import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { Camera } from "./types";
import { MOCK_CAMERAS } from "./api";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Whether a camera monitors a signalized (traffic-light) crossing.
 * Derived from the API-computed `camera_type`: "traffic_light" means the camera
 * has reported light changes; "camera" (or unset) means an unsignalized crossing
 * that should render with a neutral, signal-free treatment.
 */
export function isSignalized(camera: Camera): boolean {
  return camera.camera_type === "traffic_light";
}

export function formatRelativeTime(timestampMs: number | null | undefined): string {
  if (!timestampMs) return "Unknown";
  const now = Date.now();
  const diffSec = Math.floor((now - timestampMs) / 1000);

  if (diffSec < 5) return "just now";
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDays = Math.floor(diffHr / 24);
  return `${diffDays}d ago`;
}

export function formatDateTime(timestampMs: number | null | undefined): string {
  if (!timestampMs) return "N/A";
  const date = new Date(timestampMs);
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

/**
 * Safely parse or resolve geographic coordinates [lat, lon] for a camera.
 * Handles array coordinates [lat, lon], number fields (latitude, longitude),
 * string coordinates "(45.06, 7.69)", and seed fallback.
 */
export function getCameraCoordinates(camera: Camera | null | undefined): [number, number] | null {
  if (!camera) return null;

  // 1. Array format [lat, lon]
  if (Array.isArray(camera.location) && camera.location.length >= 2) {
    const lat = Number(camera.location[0]);
    const lon = Number(camera.location[1]);
    if (!isNaN(lat) && !isNaN(lon)) return [lat, lon];
  }

  // 2. Numerical fields latitude / longitude
  if (typeof camera.latitude === "number" && typeof camera.longitude === "number") {
    return [camera.latitude, camera.longitude];
  }

  // 3. String formatted location like "(45.0645, 7.6953)" or "45.0645, 7.6953"
  if (typeof camera.location === "string") {
    const matches = camera.location.match(/[-+]?\d*\.?\d+/g);
    if (matches && matches.length >= 2) {
      const lat = parseFloat(matches[0]);
      const lon = parseFloat(matches[1]);
      if (!isNaN(lat) && !isNaN(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
        return [lat, lon];
      }
    }
  }

  // 4. Fallback from seed MOCK_CAMERAS if known by ID
  const seed = MOCK_CAMERAS.find((c) => c.id === camera.id);
  if (seed && Array.isArray(seed.location) && seed.location.length >= 2) {
    return [Number(seed.location[0]), Number(seed.location[1])];
  }

  return null;
}

/**
 * Returns valid coordinates, falling back to Turin city center with a deterministic
 * jitter based on camera ID if coordinates are completely absent.
 */
export function getCameraCoordinatesWithFallback(camera: Camera | null | undefined): [number, number] {
  const coords = getCameraCoordinates(camera);
  if (coords) return coords;

  const baseLat = 45.0703;
  const baseLon = 7.6869;
  if (!camera?.id) return [baseLat, baseLon];

  let hash = 0;
  for (let i = 0; i < camera.id.length; i++) {
    hash = (hash * 31 + camera.id.charCodeAt(i)) & 0xffffffff;
  }
  const latOffset = ((Math.abs(hash) % 1000) / 1000 - 0.5) * 0.02;
  const lonOffset = (((Math.abs(hash >> 8)) % 1000) / 1000 - 0.5) * 0.02;
  return [baseLat + latOffset, baseLon + lonOffset];
}


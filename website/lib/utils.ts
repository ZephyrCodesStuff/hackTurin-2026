import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { Camera } from "./types";

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

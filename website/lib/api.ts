import { Camera, CameraEventsResponse, CameraEvent, CameraState, CrashEvent } from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Fallback seed cameras for demo resiliency (Turin, Italy)
export const MOCK_CAMERAS: Camera[] = [
  {
    id: "550e8400-e29b-41d4-a716-446655440001",
    name: "Piazza Castello / Via Po",
    location: [45.0710, 7.6865],
    state: "online",
    last_heartbeat: Date.now() - 4000,
    last_event_timestamp: Date.now() - 32000,
    battery_level: 94.5,
    firmware_version: "2.1.0",
    wifi_signal: -58,
    current_light: "green",
    current_light_timestamp: Date.now() - 32000,
    camera_type: "traffic_light",
  },
  {
    id: "550e8400-e29b-41d4-a716-446655440002",
    name: "Piazza San Carlo / Via Roma",
    location: [45.0678, 7.6825],
    state: "online",
    last_heartbeat: Date.now() - 12000,
    last_event_timestamp: Date.now() - 14000,
    battery_level: 82.0,
    firmware_version: "2.1.0",
    wifi_signal: -64,
    current_light: "red",
    current_light_timestamp: Date.now() - 14000,
    camera_type: "traffic_light",
  },
  {
    id: "550e8400-e29b-41d4-a716-446655440003",
    name: "Piazza Vittorio Veneto",
    location: [45.0645, 7.6953],
    state: "online",
    last_heartbeat: Date.now() - 8000,
    last_event_timestamp: Date.now() - 55000,
    battery_level: 78.4,
    firmware_version: "2.0.8",
    wifi_signal: -71,
    current_light: "green",
    current_light_timestamp: Date.now() - 55000,
    camera_type: "traffic_light",
  },
  {
    id: "550e8400-e29b-41d4-a716-446655440004",
    name: "Porta Nuova / Corso Vittorio",
    location: [45.0620, 7.6780],
    state: "online",
    last_heartbeat: Date.now() - 25000,
    last_event_timestamp: Date.now() - 45000,
    battery_level: 88.0,
    firmware_version: "2.1.0",
    wifi_signal: -62,
    current_light: "amber",
    current_light_timestamp: Date.now() - 45000,
    camera_type: "traffic_light",
  },
  {
    id: "550e8400-e29b-41d4-a716-446655440005",
    name: "Porta Susa / C.so Inghilterra",
    location: [45.0725, 7.6655],
    state: "online",
    last_heartbeat: Date.now() - 15000,
    last_event_timestamp: Date.now() - 28000,
    battery_level: 91.2,
    firmware_version: "2.1.0",
    wifi_signal: -66,
    current_light: "green",
    current_light_timestamp: Date.now() - 28000,
    camera_type: "traffic_light",
  },
  {
    id: "550e8400-e29b-41d4-a716-446655440006",
    name: "Piazza Statuto",
    location: [45.0768, 7.6713],
    state: "maintenance",
    last_heartbeat: Date.now() - 120000,
    last_event_timestamp: Date.now() - 180000,
    battery_level: 31.0,
    firmware_version: "1.9.4",
    wifi_signal: -82,
    current_light: "red",
    current_light_timestamp: Date.now() - 180000,
    camera_type: "traffic_light",
  },
  {
    id: "550e8400-e29b-41d4-a716-446655440007",
    name: "Rondò della Forca / C.so Regina",
    location: [45.0815, 7.6775],
    state: "online",
    last_heartbeat: Date.now() - 18000,
    last_event_timestamp: Date.now() - 36000,
    battery_level: 96.0,
    firmware_version: "2.1.0",
    wifi_signal: -55,
    current_light: null,
    current_light_timestamp: null,
    camera_type: "camera",
  },
  {
    id: "550e8400-e29b-41d4-a716-446655440008",
    name: "Piazza Bernini / Corso Francia",
    location: [45.0755, 7.6525],
    state: "offline",
    last_heartbeat: Date.now() - 950000,
    last_event_timestamp: Date.now() - 890000,
    battery_level: 12.2,
    firmware_version: "1.8.2",
    wifi_signal: -90,
    current_light: "red",
    current_light_timestamp: Date.now() - 890000,
    camera_type: "traffic_light",
  },
];

export const MOCK_EVENTS: Record<string, CameraEvent[]> = {
  "550e8400-e29b-41d4-a716-446655440001": [
    {
      type: "crash",
      id: 101,
      photo_id: "6f75c1a6-3f5f-42be-903b-f9d3cdc341cb",
      timestamp: Date.now() - 45000,
    },
    {
      type: "light_change",
      id: 102,
      color: "red",
      timestamp: Date.now() - 65000,
    },
    {
      type: "object_detected",
      id: 103,
      entity_type: "car",
      velocity: 54.2,
      timestamp: Date.now() - 110000,
    },
    {
      type: "illegal_crossing",
      id: 104,
      entity_type: "pedestrian",
      timestamp: Date.now() - 145000,
    },
    {
      type: "light_change",
      id: 105,
      color: "green",
      timestamp: Date.now() - 210000,
    },
  ],
};

export async function fetchCameras(): Promise<{ cameras: Camera[]; isMock: boolean }> {
  try {
    const url = typeof window !== "undefined" ? "/cameras" : `${API_BASE_URL}/cameras`;
    const res = await fetch(url, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return { cameras: data.cameras || [], isMock: false };
  } catch (error) {
    console.warn("Failed to reach API at", API_BASE_URL, "- using seed cameras", error);
    return { cameras: MOCK_CAMERAS, isMock: true };
  }
}

export async function fetchCameraEvents(
  cameraId: string
): Promise<{ data: CameraEventsResponse; isMock: boolean }> {
  try {
    const url =
      typeof window !== "undefined"
        ? `/cameras/${cameraId}/events`
        : `${API_BASE_URL}/cameras/${cameraId}/events`;
    const res = await fetch(url, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data: CameraEventsResponse = await res.json();
    return { data, isMock: false };
  } catch (error) {
    console.warn(`Failed to fetch events for camera ${cameraId}`, error);
    const mockCamera =
      MOCK_CAMERAS.find((c) => c.id === cameraId) || {
        id: cameraId,
        name: `Camera ${cameraId.slice(0, 8)}`,
        location: [52.52, 13.405],
        state: "online",
        last_heartbeat: Date.now(),
        last_event_timestamp: Date.now(),
        battery_level: 85,
        firmware_version: "2.1.0",
        wifi_signal: -65,
        camera_type: "traffic_light",
      };

    const mockEventsList = MOCK_EVENTS[cameraId] || [
      {
        type: "light_change",
        id: 991,
        color: "green",
        timestamp: Date.now() - 30000,
      },
      {
        type: "object_detected",
        id: 992,
        entity_type: "car",
        velocity: 42.1,
        timestamp: Date.now() - 75000,
      },
    ];

    return {
      data: {
        camera_id: cameraId,
        camera: mockCamera,
        total_events: mockEventsList.length,
        events: mockEventsList,
      },
      isMock: true,
    };
  }
}

export function getPhotoUrl(photoId: string): string {
  if (typeof window !== "undefined") {
    return `/photos/${photoId}`;
  }
  return `${API_BASE_URL}/photos/${photoId}`;
}

export async function updateCamera(
  cameraId: string,
  payload: {
    name?: string;
    latitude?: number;
    longitude?: number;
    state?: CameraState;
  }
): Promise<{ camera: Camera }> {
  const url =
    typeof window !== "undefined"
      ? `/cameras/${cameraId}`
      : `${API_BASE_URL}/cameras/${cameraId}`;

  const bodyPayload: Record<string, unknown> = { ...payload };
  if (payload.latitude !== undefined && payload.longitude !== undefined) {
    bodyPayload.location = [payload.latitude, payload.longitude];
  }

  const res = await fetch(url, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(bodyPayload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    let msg = `HTTP ${res.status}`;
    if (typeof err.detail === "string") {
      msg = err.detail;
    } else if (Array.isArray(err.detail)) {
      msg = err.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join(", ");
    } else if (typeof err.error === "string") {
      msg = err.error;
    }
    throw new Error(msg);
  }

  const data = await res.json();
  return { camera: data.camera };
}

export async function dispatchEmsUnits(
  crashId: number | string,
  dispatchedUnits: number[]
): Promise<{ crash: CrashEvent }> {
  const url =
    typeof window !== "undefined"
      ? `/crashes/${crashId}/resolve`
      : `${API_BASE_URL}/crashes/${crashId}/resolve`;

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ dispatched_units: dispatchedUnits }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    let msg = `HTTP ${res.status}`;
    if (typeof err.detail === "string") {
      msg = err.detail;
    } else if (Array.isArray(err.detail)) {
      msg = err.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join(", ");
    } else if (typeof err.error === "string") {
      msg = err.error;
    }
    throw new Error(msg);
  }

  const data = await res.json();
  return { crash: data.crash };
}

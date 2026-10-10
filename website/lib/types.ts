export type CameraState = "online" | "maintenance" | "offline";

export type CameraType = "traffic_light" | "camera";

export interface Camera {
  id: string;
  name: string;
  location: [number, number] | string | null;
  latitude?: number | null;
  longitude?: number | null;
  state: CameraState;
  last_heartbeat: number | null;
  last_event_timestamp: number | null;
  battery_level: number | null;
  firmware_version: string | null;
  wifi_signal: number | null;
  current_light?: TrafficLightColor | null;
  current_light_timestamp?: number | null;
  // "traffic_light" if the camera has ever reported a light change,
  // otherwise "camera" (monitors an unsignalized crossing).
  camera_type?: CameraType;
}

export type TrafficLightColor = "red" | "amber" | "green";

export type EntityType =
  | "pedestrian"
  | "car"
  | "motorbike"
  | "bike"
  | "truck"
  | "animal";

export interface CrashEvent {
  type: "crash";
  id: number;
  photo_id: string;
  timestamp: number;
}

export interface LightChangeEvent {
  type: "light_change";
  id: number;
  color: TrafficLightColor;
  timestamp: number;
}

export interface IllegalCrossingEvent {
  type: "illegal_crossing";
  id: number;
  entity_type: EntityType;
  timestamp: number;
}

export interface ObjectDetectedEvent {
  type: "object_detected";
  id: number;
  entity_type: EntityType;
  velocity: number | null;
  timestamp: number;
}

export type CameraEvent =
  | CrashEvent
  | LightChangeEvent
  | IllegalCrossingEvent
  | ObjectDetectedEvent;

export interface CameraEventsResponse {
  camera_id: string;
  camera: Camera;
  total_events: number;
  events: CameraEvent[];
}

export interface CamerasListResponse {
  cameras: Camera[];
}

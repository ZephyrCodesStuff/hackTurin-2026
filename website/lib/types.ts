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

export enum EmergencyUnit {
  POLIZIA_LOCALE = 1,
  EMERGENZA_SANITARIA = 2,
  VIGILI_DEL_FUOCO = 3,
  CARABINIERI = 4,
  POLIZIA_DI_STATO = 5,
  SOCCORSO_STRADALE = 6,
  PROTEZIONE_CIVILE = 7,
}

export const EMERGENCY_UNIT_CONFIG: Record<
  EmergencyUnit,
  { name: string; shortName: string; code: string; description: string }
> = {
  [EmergencyUnit.EMERGENZA_SANITARIA]: {
    code: "118",
    shortName: "118 Emergenza Sanitaria",
    name: "118 Emergenza Sanitaria (Ambulanza)",
    description: "Ambulanza medicalizzata / Croce Rossa & Croce Verde Torino",
  },
  [EmergencyUnit.POLIZIA_LOCALE]: {
    code: "PL",
    shortName: "Polizia Locale",
    name: "Polizia Locale di Torino",
    description: "Centrale Operativa - Rilievi sinistri e gestione viabilità",
  },
  [EmergencyUnit.VIGILI_DEL_FUOCO]: {
    code: "115",
    shortName: "115 Vigili del Fuoco",
    name: "115 Vigili del Fuoco (Soccorso Tecnico)",
    description: "Comando Provinciale Torino - Estricazione e messa in sicurezza",
  },
  [EmergencyUnit.CARABINIERI]: {
    code: "112",
    shortName: "112 Carabinieri",
    name: "112 Carabinieri (Pronto Intervento)",
    description: "Pronto Intervento e ordine pubblico",
  },
  [EmergencyUnit.POLIZIA_DI_STATO]: {
    code: "113",
    shortName: "113 Polizia di Stato",
    name: "113 Polizia di Stato (Squadra Volante)",
    description: "Questura di Torino / Controllo territorio",
  },
  [EmergencyUnit.SOCCORSO_STRADALE]: {
    code: "ACI",
    shortName: "Soccorso Stradale ACI",
    name: "Soccorso Stradale ACI (Rimozione Veicoli)",
    description: "Carro attrezzi, rimozione veicoli e ripristino carreggiata",
  },
  [EmergencyUnit.PROTEZIONE_CIVILE]: {
    code: "PC",
    shortName: "Protezione Civile",
    name: "Protezione Civile Torino",
    description: "Supporto logistico e deviazione grandi arterie",
  },
};

export interface CrashEvent {
  type: "crash";
  id: number;
  photo_id: string;
  timestamp: number;
  resolved?: boolean;
  resolved_at?: number | null;
  resolved_by?: string | null;
  dispatched_units?: number[] | null;
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

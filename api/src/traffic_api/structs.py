from enum import Enum, IntEnum
import time
from typing import Annotated, List, Literal, Optional, Union
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


def current_time_ms() -> int:
    return int(time.time() * 1000)


class LightColor(str, Enum):
    RED = "red"
    AMBER = "amber"
    GREEN = "green"


class CameraState(str, Enum):
    ONLINE = "online"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"


class EntityType(str, Enum):
    PEDESTRIAN = "pedestrian"
    CAR = "car"
    MOTORBIKE = "motorbike"
    BIKE = "bike"
    TRUCK = "truck"
    ANIMAL = "animal"


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CrashEvent(StrictBaseModel):
    type: Literal["crash"] = "crash"
    photo_id: UUID
    timestamp: int = Field(default_factory=current_time_ms)

    @field_validator("photo_id")
    @classmethod
    def validate_uuidv4(cls, v: UUID) -> UUID:
        if v.version != 4:
            raise ValueError(f"photo_id must be a UUIDv4 (got version {v.version})")
        return v


class LightChangeEvent(StrictBaseModel):
    type: Literal["light_change"] = "light_change"
    color: LightColor
    timestamp: int = Field(default_factory=current_time_ms)


class IllegalCrossingEvent(StrictBaseModel):
    type: Literal["illegal_crossing"] = "illegal_crossing"
    entity_type: EntityType = Field(..., description="Type of entity performing illegal crossing")
    timestamp: int = Field(default_factory=current_time_ms)


class ObjectDetectedEvent(StrictBaseModel):
    type: Literal["object_detected"] = "object_detected"
    entity_type: EntityType = Field(..., description="Type of entity detected")
    velocity: Optional[float] = None
    timestamp: int = Field(default_factory=current_time_ms)


Event = Annotated[
    Union[CrashEvent, LightChangeEvent, IllegalCrossingEvent, ObjectDetectedEvent],
    Field(discriminator="type"),
]


class IngestPayload(StrictBaseModel):
    events: List[Event] = Field(..., min_length=1, description="List of events to ingest")


class CameraHeartbeatPayload(StrictBaseModel):
    name: Optional[str] = Field(None, description="Camera friendly name or intersection")
    state: CameraState = Field(default=CameraState.ONLINE, description="Current camera operational state")
    location: Optional[tuple[float, float]] = Field(
        None, description="Current GPS coordinates as (latitude, longitude)"
    )
    last_heartbeat: int = Field(default_factory=current_time_ms, description="Epoch ms timestamp of heartbeat")
    last_event_timestamp: Optional[int] = Field(None, description="Epoch ms timestamp of last detected event")
    battery_level: Optional[float] = Field(None, ge=0.0, le=100.0, description="Battery percentage (0-100)")
    firmware_version: Optional[str] = Field(None, description="Device firmware version string")
    wifi_signal: Optional[int] = Field(None, description="Signal strength RSSI in dBm")


class CameraEditPayload(StrictBaseModel):
    camera_id: Optional[UUID] = Field(None, description="Camera UUID (required if not provided in URL path)")
    name: Optional[str] = Field(None, description="Updated friendly name for the camera")
    location: Optional[Union[tuple[float, float], List[float], str]] = Field(
        None, description="Updated coordinates [latitude, longitude] or location string"
    )
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Latitude coordinate (-90 to 90)")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Longitude coordinate (-180 to 180)")
    state: Optional[CameraState] = Field(None, description="Updated camera operational state")


class EmergencyUnit(IntEnum):
    POLIZIA_LOCALE = 1
    EMERGENZA_SANITARIA = 2
    VIGILI_DEL_FUOCO = 3
    CARABINIERI = 4
    POLIZIA_DI_STATO = 5
    SOCCORSO_STRADALE = 6
    PROTEZIONE_CIVILE = 7


class ResolveCrashPayload(StrictBaseModel):
    dispatched_units: List[int] = Field(
        default_factory=list,
        description="List of integer enum IDs representing dispatched emergency units",
    )
    notes: Optional[str] = Field(None, description="Optional dispatch notes")
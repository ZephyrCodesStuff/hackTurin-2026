from enum import Enum
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
    timestamp: int = Field(default_factory=current_time_ms)


class ObjectDetectedEvent(StrictBaseModel):
    type: Literal["object_detected"] = "object_detected"
    velocity: Optional[float] = None
    timestamp: int = Field(default_factory=current_time_ms)


Event = Annotated[
    Union[CrashEvent, LightChangeEvent, IllegalCrossingEvent, ObjectDetectedEvent],
    Field(discriminator="type"),
]


class IngestPayload(StrictBaseModel):
    events: List[Event] = Field(..., min_length=1, description="List of events to ingest")
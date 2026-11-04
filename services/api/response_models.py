"""Response contracts shared across API resources."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    service: Literal["nexova-api"]


class DeletionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(gt=0, strict=True)
    deleted: Literal[True]

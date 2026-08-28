from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


TrackingState = Literal[
    "active",
    "stopped",
]


class TechnicianLocationUpdateRequest(
    BaseModel
):
    service_job_id: int | None = Field(
        default=None,
        ge=1,
    )

    latitude: Decimal | None = Field(
        default=None,
        ge=Decimal("-90"),
        le=Decimal("90"),
        max_digits=9,
        decimal_places=6,
    )

    longitude: Decimal | None = Field(
        default=None,
        ge=Decimal("-180"),
        le=Decimal("180"),
        max_digits=9,
        decimal_places=6,
    )

    accuracy_meters: Decimal | None = (
        Field(
            default=None,
            ge=Decimal("0"),
            le=Decimal("100000"),
            max_digits=10,
            decimal_places=2,
        )
    )

    client_recorded_at: (
        datetime | None
    ) = None

    tracking_state: TrackingState = (
        "active"
    )

    @model_validator(
        mode="after"
    )
    def validate_coordinates(
        self,
    ):
        latitude_present = (
            self.latitude
            is not None
        )

        longitude_present = (
            self.longitude
            is not None
        )

        if (
            latitude_present
            != longitude_present
        ):
            raise ValueError(
                "Latitude and longitude "
                "must be provided together"
            )

        if (
            self.tracking_state
            == "active"
            and not latitude_present
        ):
            raise ValueError(
                "Active tracking requires "
                "latitude and longitude"
            )

        return self


class TechnicianLocationResponse(
    BaseModel
):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    technician_id: int

    service_job_id: (
        int | None
    )

    latitude: Decimal | None
    longitude: Decimal | None

    accuracy_meters: (
        Decimal | None
    )

    client_recorded_at: (
        datetime | None
    )

    recorded_at: datetime

    tracking_state: str
    source: str


class TechnicianLocationAdminResponse(
    TechnicianLocationResponse
):
    technician_name: str

    service_job_number: (
        str | None
    )

    presence_status: Literal[
        "live",
        "stale",
        "offline",
    ]

    age_seconds: int

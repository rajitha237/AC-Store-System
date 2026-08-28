from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.main import app
from app.models import (
    TechnicianLocation,
)
from app.schemas.technician_location import (
    TechnicianLocationUpdateRequest,
)


def test_location_model_table_contract():
    assert (
        TechnicianLocation
        .__tablename__
        == "technician_locations"
    )

    columns = {
        column.name
        for column
        in TechnicianLocation
        .__table__.columns
    }

    assert {
        "id",
        "technician_id",
        "service_job_id",
        "latitude",
        "longitude",
        "accuracy_meters",
        "client_recorded_at",
        "recorded_at",
        "tracking_state",
        "source",
    }.issubset(columns)


def test_active_location_requires_coordinates():
    with pytest.raises(
        ValidationError
    ):
        TechnicianLocationUpdateRequest(
            tracking_state="active",
        )


def test_valid_active_location():
    payload = (
        TechnicianLocationUpdateRequest(
            service_job_id=1,
            latitude=(
                Decimal("6.927079")
            ),
            longitude=(
                Decimal("79.861244")
            ),
            accuracy_meters=(
                Decimal("12.50")
            ),
            tracking_state="active",
        )
    )

    assert (
        payload.latitude
        == Decimal("6.927079")
    )

    assert (
        payload.longitude
        == Decimal("79.861244")
    )


def test_stopped_location_can_omit_coordinates():
    payload = (
        TechnicianLocationUpdateRequest(
            tracking_state="stopped",
        )
    )

    assert (
        payload.latitude
        is None
    )

    assert (
        payload.longitude
        is None
    )


def test_location_openapi_routes():
    schema = app.openapi()

    write_path = (
        "/api/v1/service/"
        "technician/location"
    )

    read_path = (
        "/api/v1/service/"
        "technicians/locations"
    )

    assert (
        write_path
        in schema["paths"]
    )

    assert (
        "post"
        in schema["paths"][
            write_path
        ]
    )

    assert (
        read_path
        in schema["paths"]
    )

    assert (
        "get"
        in schema["paths"][
            read_path
        ]
    )

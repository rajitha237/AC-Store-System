from pathlib import Path

from sqlalchemy import (
    inspect,
)

from app.models.service_job_location_record import (
    ServiceJobLocationRecord,
)


SERVICE_PATH = Path(
    "app/services/service.py"
)

MIGRATION_PATH = Path(
    "alembic/versions/"
    "d7e31a5b9f42_add_service_job_location_records.py"
)


def test_service_job_location_record_table_contract():
    mapper = inspect(
        ServiceJobLocationRecord
    )

    table = mapper.local_table

    assert (
        table.name
        == "service_job_location_records"
    )

    expected_columns = {
        "id",
        "service_job_id",
        "technician_id",
        "latitude",
        "longitude",
        "accuracy_meters",
        "completed_at",
        "recorded_at",
    }

    assert (
        set(table.columns.keys())
        == expected_columns
    )

    assert (
        table.c.service_job_id.nullable
        is False
    )

    assert (
        table.c.technician_id.nullable
        is False
    )

    assert (
        table.c.latitude.nullable
        is False
    )

    assert (
        table.c.longitude.nullable
        is False
    )

    assert (
        table.c.completed_at.nullable
        is False
    )


def test_service_job_location_record_numeric_precision():
    table = (
        ServiceJobLocationRecord
        .__table__
    )

    assert (
        table.c.latitude.type.precision
        == 9
    )
    assert (
        table.c.latitude.type.scale
        == 6
    )

    assert (
        table.c.longitude.type.precision
        == 9
    )
    assert (
        table.c.longitude.type.scale
        == 6
    )

    assert (
        table.c.accuracy_meters
        .type.precision
        == 10
    )
    assert (
        table.c.accuracy_meters
        .type.scale
        == 2
    )


def test_service_job_location_record_foreign_keys():
    table = (
        ServiceJobLocationRecord
        .__table__
    )

    job_fk = next(
        iter(
            table.c.service_job_id
            .foreign_keys
        )
    )

    technician_fk = next(
        iter(
            table.c.technician_id
            .foreign_keys
        )
    )

    assert (
        job_fk.target_fullname
        == "service_job_cards.id"
    )
    assert (
        job_fk.ondelete
        == "CASCADE"
    )

    assert (
        technician_fk.target_fullname
        == "users.id"
    )
    assert (
        technician_fk.ondelete
        == "RESTRICT"
    )


def test_service_job_location_record_unique_per_job():
    table = (
        ServiceJobLocationRecord
        .__table__
    )

    unique_column_sets = {
        tuple(
            column.name
            for column
            in constraint.columns
        )
        for constraint
        in table.constraints
        if constraint.__class__.__name__
        == "UniqueConstraint"
    }

    assert (
        ("service_job_id",)
        in unique_column_sets
    )


def test_completion_service_contains_gps_gate_and_snapshot():
    source = SERVICE_PATH.read_text()

    required_tokens = [
        "TechnicianLocation",
        "ServiceJobLocationRecord",
        "completion_location",
        "technician_id",
        "current_user.id",
        "service_job_id",
        "job.id",
        "latitude",
        "longitude",
        "accuracy_meters",
        "completion_snapshot",
        "completed_at",
        "session.add",
    ]

    for token in required_tokens:
        assert token in source


def test_completion_snapshot_occurs_before_commit():
    source = SERVICE_PATH.read_text()

    start = source.index(
        "async def complete_service_job"
    )

    completion_source = source[start:]

    snapshot_position = (
        completion_source.index(
            "completion_snapshot"
        )
    )

    commit_position = (
        completion_source.index(
            "await session.commit()"
        )
    )

    assert (
        snapshot_position
        < commit_position
    )


def test_completion_requires_exact_job_association():
    source = SERVICE_PATH.read_text()

    start = source.index(
        "async def complete_service_job"
    )

    completion_source = source[start:]

    assert (
        ".service_job_id"
        in completion_source
    )

    assert (
        "!= job.id"
        in completion_source
    )

    assert (
        "must be associated with this"
        in completion_source
    )


def test_completion_has_duplicate_snapshot_guard():
    source = SERVICE_PATH.read_text()

    start = source.index(
        "async def complete_service_job"
    )

    completion_source = source[start:]

    assert (
        "existing_snapshot"
        in completion_source
    )

    assert (
        "already exists for this"
        in completion_source
    )


def test_migration_revision_chain_structurally():
    source = MIGRATION_PATH.read_text()

    namespace = {}

    exec(
        compile(
            source,
            str(MIGRATION_PATH),
            "exec",
        ),
        namespace,
    )

    assert (
        namespace["revision"]
        == "d7e31a5b9f42"
    )

    assert (
        namespace["down_revision"]
        == "c2f4e8a91b63"
    )


def test_migration_targets_completion_location_table():
    source = (
        MIGRATION_PATH.read_text()
    )

    assert (
        "service_job_location_records"
        in source
    )

    required_columns = [
        "service_job_id",
        "technician_id",
        "latitude",
        "longitude",
        "accuracy_meters",
        "completed_at",
        "recorded_at",
    ]

    for column in required_columns:
        assert column in source

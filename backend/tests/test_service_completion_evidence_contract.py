from pathlib import Path

from app.models.service_completion_evidence import (
    ServiceCompletionEvidence,
)


def test_completion_evidence_table_name() -> None:
    assert (
        ServiceCompletionEvidence.__tablename__
        == "service_completion_evidence"
    )


def test_completion_evidence_required_columns() -> None:
    columns = {
        column.name
        for column
        in ServiceCompletionEvidence.__table__.columns
    }

    assert {
        "id",
        "job_card_id",
        "evidence_type",
        "sequence_number",
        "content_type",
        "file_name",
        "content",
        "uploaded_by_id",
        "created_at",
    }.issubset(columns)


def test_completion_evidence_content_is_binary() -> None:
    column = (
        ServiceCompletionEvidence
        .__table__
        .columns["content"]
    )

    assert (
        column.type.__class__.__name__
        in {
            "LargeBinary",
            "BYTEA",
        }
    )


def test_completion_evidence_job_fk() -> None:
    column = (
        ServiceCompletionEvidence
        .__table__
        .columns["job_card_id"]
    )

    targets = {
        fk.target_fullname
        for fk in column.foreign_keys
    }

    assert (
        "service_job_cards.id"
        in targets
    )


def test_completion_evidence_uploader_fk() -> None:
    column = (
        ServiceCompletionEvidence
        .__table__
        .columns["uploaded_by_id"]
    )

    targets = {
        fk.target_fullname
        for fk in column.foreign_keys
    }

    assert "users.id" in targets


def test_completion_evidence_unique_contract() -> None:
    unique_names = {
        constraint.name
        for constraint
        in ServiceCompletionEvidence
        .__table__
        .constraints
        if constraint.name
    }

    assert (
        "uq_service_completion_evidence_"
        "job_type_sequence"
        in unique_names
    )


def test_completion_evidence_api_contract_present() -> None:
    source = Path(
        "app/api/v1/service.py"
    ).read_text()

    assert (
        '"/jobs/{job_id}/completion-evidence"'
        in source
    )

    assert (
        '"work_photo"'
        in source
    )

    assert (
        '"customer_signature"'
        in source
    )

    assert (
        "len(photos) < 1"
        in source
    )

    assert (
        "len(photos) > 5"
        in source
    )


def test_completion_gate_requires_evidence() -> None:
    source = Path(
        "app/services/service.py"
    ).read_text()

    assert (
        "ServiceCompletionEvidence"
        in source
    )

    assert (
        '"work_photo"'
        in source
    )

    assert (
        '"customer_signature"'
        in source
    )

    assert (
        "work_photo_count < 1"
        in source
    )

    assert (
        "signature_count != 1"
        in source
    )


def test_frontend_upload_before_gps_before_complete() -> None:
    source = Path(
        "../frontend/src/app/technician/jobs/[jobId]/page.tsx"
    ).read_text()

    upload_position = source.index(
        "uploadServiceCompletionEvidence("
    )

    gps_position = source.index(
        "navigator.geolocation.getCurrentPosition",
        upload_position,
    )

    complete_position = source.index(
        "await completeServiceJob(",
        gps_position,
    )

    assert (
        upload_position
        < gps_position
        < complete_position
    )


def test_frontend_requires_photo_and_signature() -> None:
    source = Path(
        "../frontend/src/app/technician/jobs/[jobId]/page.tsx"
    ).read_text()

    assert (
        "workPhotos.length < 1"
        in source
    )

    assert (
        "workPhotos.length > 5"
        in source
    )

    assert (
        "!signatureHasInk"
        in source
    )

    assert (
        'capture="environment"'
        in source
    )


from io import BytesIO
from unittest.mock import patch

import pytest
from pypdf import PdfReader, PdfWriter
from sqlalchemy.orm import Session

from app.models.drm import DownloadRecord
from app.models.resource import Resource, ResourceFile
from app.models.user import User


def make_test_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.fixture
def drm_resource(test_engine, librarian):
    with Session(test_engine) as db:
        resource = Resource(
            title="Protected Academic Resource",
            resource_type="book",
            uploaded_by=librarian,
            is_published=True,
            is_archived=False,
        )
        db.add(resource)
        db.flush()

        file_record = ResourceFile(
            resource_id=resource.id,
            storage_path="resources/test/sample.pdf",
            original_filename="sample.pdf",
            mime_type="application/pdf",
            file_size_bytes=100,
            is_primary=True,
        )
        db.add(file_record)
        db.commit()

        return resource.id


def student_headers(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "student@test.com",
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 200
    return {
        "Authorization": (
            f"Bearer {response.json()['access_token']}"
        )
    }


@patch("app.services.drm_service.download_private_pdf")
def test_student_can_read_watermarked_pdf(
    mock_download,
    client,
    student,
    drm_resource,
    test_engine,
):
    mock_download.return_value = make_test_pdf()

    response = client.get(
        f"/resources/{drm_resource}/read",
        headers=student_headers(client),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "private, no-store"
    assert "inline" in response.headers["content-disposition"]

    reader = PdfReader(BytesIO(response.content))
    assert len(reader.pages) == 1

    text = reader.pages[0].extract_text()
    assert "UNN E-Library" in text
    assert f"User ID: {student}" in text
    assert "UTC" in text

    with Session(test_engine) as db:
        events = db.query(DownloadRecord).all()
        assert len(events) == 1
        assert events[0].access_type == "view"
        assert events[0].user_id == student

    mock_download.assert_called_once()


@patch("app.services.drm_service.download_private_pdf")
def test_student_can_download_watermarked_pdf(
    mock_download,
    client,
    student,
    drm_resource,
    test_engine,
):
    mock_download.return_value = make_test_pdf()

    response = client.get(
        f"/resources/{drm_resource}/download",
        headers=student_headers(client),
    )

    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]

    reader = PdfReader(BytesIO(response.content))
    assert f"User ID: {student}" in (
        reader.pages[0].extract_text()
    )

    with Session(test_engine) as db:
        event = db.query(DownloadRecord).one()
        assert event.access_type == "download"


@pytest.mark.parametrize("action", ["read", "download"])
def test_unauthenticated_pdf_access_is_denied(
    client,
    drm_resource,
    action,
):
    response = client.get(
        f"/resources/{drm_resource}/{action}"
    )
    assert response.status_code == 401


@pytest.mark.parametrize("field", [
    "is_published",
    "is_archived",
])
@patch("app.services.drm_service.download_private_pdf")
def test_unavailable_resource_access_is_blocked(
    mock_download,
    field,
    client,
    student,
    drm_resource,
    test_engine,
):
    with Session(test_engine) as db:
        resource = db.get(Resource, drm_resource)
        if field == "is_published":
            resource.is_published = False
        else:
            resource.is_archived = True
            resource.is_published = False
        db.commit()

    response = client.get(
        f"/resources/{drm_resource}/read",
        headers=student_headers(client),
    )

    assert response.status_code == 403
    mock_download.assert_not_called()

    with Session(test_engine) as db:
        record = db.query(DownloadRecord).one()
        assert record.access_type == "blocked"


@patch("app.services.drm_service.download_private_pdf")
def test_missing_resource_is_not_downloaded(
    mock_download,
    client,
    student,
    test_engine,
):
    response = client.get(
        "/resources/999999/download",
        headers=student_headers(client),
    )

    assert response.status_code == 404
    mock_download.assert_not_called()


@patch("app.services.drm_service.download_private_pdf")
def test_storage_failure_does_not_log_success(
    mock_download,
    client,
    student,
    drm_resource,
    test_engine,
):
    mock_download.side_effect = RuntimeError(
        "Simulated storage failure"
    )

    response = client.get(
        f"/resources/{drm_resource}/read",
        headers=student_headers(client),
    )

    assert response.status_code == 502
    assert "Simulated storage failure" not in response.text

    with Session(test_engine) as db:
        assert db.query(DownloadRecord).count() == 0

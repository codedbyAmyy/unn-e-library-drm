import pytest

from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from app.models.user import User
from app.utils.security import hash_password
from app.models.resource import ResourceFile, Resource
from app.services.storage_service import (
    MAX_FILE_SIZE_BYTES,
    calculate_sha256,
    generate_storage_path,
    validate_resource_file,
    upload_resource_file,
    upload_and_register_resource_file,
)


@pytest.fixture
def storage_test_librarian(test_engine, test_department):
    with Session(test_engine) as db:
        user = User(
            full_name="Storage Test Librarian",
            email="storage-librarian@test.com",
            password_hash=hash_password("TestPassword123!"),
            role="librarian",
            department_id=test_department,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        librarian_id = user.id

    return librarian_id

VALID_PDF = b"%PDF-1.7\nTest PDF content"


def test_valid_pdf_passes_validation():
    validate_resource_file(
        filename="lecture-notes.pdf",
        content_type="application/pdf",
        file_content=VALID_PDF,
    )


def test_empty_filename_is_rejected():
    with pytest.raises(ValueError, match="filename"):
        validate_resource_file(
            filename=" ",
            content_type="application/pdf",
            file_content=VALID_PDF,
        )


def test_non_pdf_content_type_is_rejected():
    with pytest.raises(ValueError, match="Only PDF"):
        validate_resource_file(
            filename="notes.txt",
            content_type="text/plain",
            file_content=b"Some text",
        )


def test_empty_file_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        validate_resource_file(
            filename="empty.pdf",
            content_type="application/pdf",
            file_content=b"",
        )


def test_file_larger_than_limit_is_rejected():
    oversized_content = b"%PDF-" + (
        b"x" * MAX_FILE_SIZE_BYTES
    )

    with pytest.raises(ValueError, match="50 MB"):
        validate_resource_file(
            filename="large.pdf",
            content_type="application/pdf",
            file_content=oversized_content,
        )


def test_invalid_pdf_content_is_rejected():
    with pytest.raises(ValueError, match="valid PDF"):
        validate_resource_file(
            filename="fake.pdf",
            content_type="application/pdf",
            file_content=b"This is not a PDF",
        )


def test_sha256_checksum_is_consistent():
    checksum = calculate_sha256(VALID_PDF)

    assert checksum == calculate_sha256(VALID_PDF)
    assert len(checksum) == 64


def test_storage_path_contains_resource_id():
    path = generate_storage_path(
        resource_id=12,
        filename="lecture-notes.pdf",
    )

    assert path.startswith("resources/12/")
    assert path.endswith(".pdf")


def test_storage_paths_are_unique():
    first_path = generate_storage_path(12, "notes.pdf")
    second_path = generate_storage_path(12, "notes.pdf")

    assert first_path != second_path


def test_invalid_resource_id_is_rejected():
    with pytest.raises(ValueError, match="positive integer"):
        generate_storage_path(0, "notes.pdf")


@patch("app.services.storage_service.supabase")
def test_upload_resource_file_returns_file_metadata(mock_supabase):
    mock_supabase.storage.from_.return_value.upload.return_value = {
        "Key": "resources/12/test.pdf"
    }

    result = upload_resource_file(
        filename="lecture-notes.pdf",
        file_content=VALID_PDF,
        storage_path="resources/12/test.pdf",
        content_type="application/pdf",
    )

    assert result["storage_path"] == "resources/12/test.pdf"
    assert result["original_filename"] == "lecture-notes.pdf"
    assert result["file_size_bytes"] == len(VALID_PDF)
    assert result["mime_type"] == "application/pdf"
    assert len(result["checksum_sha256"]) == 64

    mock_supabase.storage.from_.return_value.upload.assert_called_once()


@patch("app.services.storage_service.supabase")
def test_invalid_file_is_not_uploaded(mock_supabase):
    with pytest.raises(ValueError, match="Only PDF"):
        upload_resource_file(
            filename="notes.txt",
            file_content=b"Some text",
            storage_path="resources/12/notes.txt",
            content_type="text/plain",
        )

    mock_supabase.storage.from_.return_value.upload.assert_not_called()


@patch("app.services.storage_service.supabase")
def test_upload_failure_propagates(mock_supabase):
    mock_supabase.storage.from_.return_value.upload.side_effect = (
        RuntimeError("Simulated storage failure")
    )

    with pytest.raises(RuntimeError, match="Simulated storage failure"):
        upload_resource_file(
            filename="lecture-notes.pdf",
            file_content=VALID_PDF,
            storage_path="resources/12/test.pdf",
            content_type="application/pdf",
        )

@patch("app.services.storage_service.upload_resource_file")
def test_upload_and_register_resource_file_saves_metadata(
    mock_upload,
    test_engine,
    storage_test_librarian,
    test_department,
):
    with Session(test_engine) as db:
        resource = Resource(
            title="Test PDF Resource",
            resource_type="book",
            language="English",
            uploaded_by=storage_test_librarian,
            department_id=test_department,
        )
        db.add(resource)
        db.commit()
        db.refresh(resource)

        resource_id = resource.id

    file_content = b"%PDF-1.7\nTest PDF content"

    with Session(test_engine) as db:
        result = upload_and_register_resource_file(
            db=db,
            resource_id=resource_id,
            filename="test-book.pdf",
            file_content=file_content,
            content_type="application/pdf",
            is_primary=True,
        )

        assert result.id is not None
        assert result.resource_id == resource_id
        assert result.original_filename == "test-book.pdf"
        assert result.mime_type == "application/pdf"
        assert result.file_size_bytes == len(file_content)
        assert result.is_primary is True
        assert len(result.checksum_sha256) == 64

    mock_upload.assert_called_once()


@patch("app.services.storage_service.upload_resource_file")
def test_upload_and_register_rejects_missing_resource(
    mock_upload,
    test_engine,
):
    with Session(test_engine) as db:
        with pytest.raises(
            ValueError,
            match="resource does not exist",
        ):
            upload_and_register_resource_file(
                db=db,
                resource_id=999999,
                filename="test-book.pdf",
                file_content=b"%PDF-1.7\nTest PDF content",
                content_type="application/pdf",
            )

    mock_upload.assert_not_called()


def test_database_failure_rolls_back_and_removes_uploaded_file():
    mock_db = MagicMock()
    mock_db.get.return_value = object()
    mock_db.commit.side_effect = RuntimeError(
        "Database write failed"
    )

    with (
        patch(
            "app.services.storage_service.upload_resource_file"
        ) as mock_upload,
        patch(
            "app.services.storage_service.supabase"
        ) as mock_supabase,
    ):
        with pytest.raises(
            RuntimeError,
            match="Database write failed",
        ):
            upload_and_register_resource_file(
                db=mock_db,
                resource_id=12,
                filename="test-book.pdf",
                file_content=VALID_PDF,
                content_type="application/pdf",
            )

        storage_path = mock_upload.call_args.kwargs[
            "storage_path"
        ]

        mock_db.rollback.assert_called_once()

        mock_supabase.storage.from_.return_value.remove.assert_called_once_with(
            [storage_path]
        )

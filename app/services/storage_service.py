import hashlib
from sqlalchemy.orm import Session

from app.config import settings
from app.models.resource import Resource, ResourceFile
from supabase import create_client

from uuid import uuid4

supabase = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY,
)

BUCKET_NAME = "library-resources"


def calculate_sha256(file_content: bytes) -> str:
    """Return the SHA-256 checksum of a file."""
    return hashlib.sha256(file_content).hexdigest()


def upload_resource_file(
    filename: str,
    file_content: bytes,
    storage_path: str,
    content_type: str,
) -> dict:
    """Validate and upload a file to the private Supabase Storage bucket."""
    validate_resource_file(
        filename=filename,
        content_type=content_type,
        file_content=file_content,
    )
    checksum = calculate_sha256(file_content)

    response = supabase.storage.from_(BUCKET_NAME).upload(
        path=storage_path,
        file=file_content,
        file_options={
            "content-type": content_type,
            "upsert": "false",
        },
    )

    return {
        "storage_path": storage_path,
        "original_filename": filename,
        "file_size_bytes": len(file_content),
        "mime_type": content_type,
        "checksum_sha256": checksum,
    }

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"application/pdf"}

def validate_resource_file(
    filename: str,
    content_type: str,
    file_content: bytes,
) -> None:
    """Validate an uploaded resource file."""
    if not filename or not filename.strip():
        raise ValueError("Afilename is required.")
    
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Only PDF files are allowed.")
    
    if not file_content:
        raise ValueError("The uploaded file is empty.")
    
    if len(file_content) > MAX_FILE_SIZE_BYTES:
        raise ValueError("The file must not exceed 50 MB.")
    
    if not file_content.startswith(b"%PDF-"):
        raise ValueError("The uploaded file is not a valid PDF.")
    
def generate_storage_path(resource_id: int, filename: str) -> str:
    """Generate a unique storage path for a resource PDF."""
    if resource_id <= 0:
        raise ValueError("Resource ID must be a positive integer.")
    
    if not filename or not filename.strip():
        raise ValueError("A filename is required.")
    
    return f"resources/{resource_id}/{uuid4().hex}.pdf"

def upload_and_register_resource_file(
    db: Session,
    resource_id: int,
    filename: str,
    file_content: bytes,
    content_type: str,
    is_primary: bool = False,
) -> ResourceFile:
    """Uploads a PDF and register its metadata in PostgreSQL"""
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise ValueError("The selected resource does not exist.")
    storage_path = generate_storage_path(resource_id, filename)
    upload_resource_file(
        filename=filename,
        file_content=file_content,
        storage_path=storage_path,
        content_type=content_type,
    )
    file_record = ResourceFile(
        resource_id=resource_id,
        storage_path=storage_path,
        original_filename=filename,
        mime_type=content_type,
        file_size_bytes=len(file_content),
        checksum_sha256=calculate_sha256(file_content),
        is_primary=is_primary,
    )
    try:
        db.add(file_record)
        db.commit()
        db.refresh(file_record)
    except Exception:
        db.rollback()
        try:
            supabase.storage.from_(BUCKET_NAME).remove([storage_path])
        except Exception:
            pass
        raise
    return file_record

def download_private_pdf(storage_path: str) -> bytes:
    """Retrieve a PDF from protected Supabase Storage."""
    if not storage_path:
        raise ValueError("A storage path is required.")
    return supabase.storage.from_(BUCKET_NAME).download(
        storage_path
    )
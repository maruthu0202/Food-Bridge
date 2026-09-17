"""StorageService — abstraction over Google Cloud Storage with local fallback.

When GCS_BUCKET_NAME env var is set and google-cloud-storage is configured,
files are uploaded to GCS. Otherwise files are saved to LOCAL_UPLOAD_FOLDER.
This allows the app to run in local dev without any cloud credentials.
"""
import logging
import mimetypes
import os
import uuid
from typing import Optional
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_MIMETYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class StorageError(Exception):
    pass


class StorageService:
    def __init__(self, app=None):
        self._bucket_name: Optional[str] = None
        self._local_folder: Optional[str] = None
        self._use_gcs: bool = False
        if app:
            self.init_app(app)

    def init_app(self, app):
        self._bucket_name = app.config.get("GCS_BUCKET_NAME", "")
        self._local_folder = app.config.get("LOCAL_UPLOAD_FOLDER", "uploads")
        self._use_gcs = bool(self._bucket_name)
        os.makedirs(self._local_folder, exist_ok=True)

    # ------------------------------------------------------------------ #
    #  Public API                                                           #
    # ------------------------------------------------------------------ #

    def upload_food_image(self, file: FileStorage) -> str:
        """Validate and upload a food image. Returns the stored path/key."""
        self._validate(file)
        ext = self._safe_extension(file.filename)
        object_name = f"donations/{uuid.uuid4().hex}.{ext}"

        if self._use_gcs:
            return self._upload_to_gcs(file, object_name)
        return self._save_locally(file, object_name)

    def get_image_url(self, path: Optional[str]) -> Optional[str]:
        """Return a URL suitable for <img src="...">."""
        if not path:
            return None
        if self._use_gcs:
            return f"https://storage.googleapis.com/{self._bucket_name}/{path}"
        # Local: path stored as relative, served via /uploads/<path>
        return f"/uploads/{path}"

    def delete_image(self, path: Optional[str]):
        """Best-effort delete — logs but doesn't crash on failure."""
        if not path:
            return
        try:
            if self._use_gcs:
                self._delete_from_gcs(path)
            else:
                self._delete_local(path)
        except Exception as exc:
            logger.warning("Failed to delete image %s: %s", path, exc)

    # ------------------------------------------------------------------ #
    #  Validation                                                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _validate(file: FileStorage):
        if not file or not file.filename:
            raise StorageError("No file provided.")

        ext = StorageService._safe_extension(file.filename)
        if ext not in ALLOWED_EXTENSIONS:
            raise StorageError(f"File type '.{ext}' is not allowed.")

        # Validate MIME type from content (not just filename)
        file.stream.seek(0)
        header = file.stream.read(512)
        file.stream.seek(0)
        mime = _sniff_mime(header)
        if mime and mime not in ALLOWED_MIMETYPES:
            raise StorageError(f"File content type '{mime}' is not allowed.")

        # Size check
        file.stream.seek(0, 2)
        size = file.stream.tell()
        file.stream.seek(0)
        if size > MAX_FILE_SIZE_BYTES:
            raise StorageError(
                f"File size {size // 1024}KB exceeds the 10MB limit."
            )

    @staticmethod
    def _safe_extension(filename: str) -> str:
        if "." not in filename:
            return "bin"
        return filename.rsplit(".", 1)[1].lower()

    # ------------------------------------------------------------------ #
    #  GCS backend                                                          #
    # ------------------------------------------------------------------ #

    def _upload_to_gcs(self, file: FileStorage, object_name: str) -> str:
        from google.cloud import storage as gcs_storage  # lazy import

        client = gcs_storage.Client()
        bucket = client.bucket(self._bucket_name)
        blob = bucket.blob(object_name)
        blob.upload_from_file(file.stream, content_type=file.content_type)
        logger.info("Uploaded to GCS: gs://%s/%s", self._bucket_name, object_name)
        return object_name

    def _delete_from_gcs(self, path: str):
        from google.cloud import storage as gcs_storage

        client = gcs_storage.Client()
        bucket = client.bucket(self._bucket_name)
        bucket.blob(path).delete()
        logger.info("Deleted from GCS: %s", path)

    # ------------------------------------------------------------------ #
    #  Local backend                                                        #
    # ------------------------------------------------------------------ #

    def _save_locally(self, file: FileStorage, object_name: str) -> str:
        dest = os.path.join(self._local_folder, object_name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        file.save(dest)
        logger.info("Saved locally: %s", dest)
        return object_name

    def _delete_local(self, path: str):
        dest = os.path.join(self._local_folder, path)
        if os.path.exists(dest):
            os.remove(dest)


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def _sniff_mime(header: bytes) -> Optional[str]:
    """Minimal magic-byte MIME detection without external deps."""
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if header[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if header[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    return None


# Module-level singleton — registered with app in create_app if needed
storage_service = StorageService()

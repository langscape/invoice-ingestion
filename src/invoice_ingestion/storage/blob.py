"""Azure Blob Storage wrapper for invoice files and extraction results."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from functools import partial

from azure.storage.blob import BlobSasPermissions, BlobServiceClient, generate_blob_sas

_executor = ThreadPoolExecutor(max_workers=4)


class BlobStorageClient:
    """Thin async-friendly wrapper around the synchronous Azure Blob SDK."""

    def __init__(
        self,
        connection_string: str,
        imported_container: str = "imported",
        extracted_container: str = "extracted",
    ):
        self._client = BlobServiceClient.from_connection_string(connection_string)
        self._imported = imported_container
        self._extracted = extracted_container
        # Ensure containers exist
        for name in (self._imported, self._extracted):
            try:
                self._client.create_container(name)
            except Exception:
                # Container may already exist
                pass

    # ── Downloads ─────────────────────────────────────────────────────────

    def download_invoice(self, blob_name: str) -> bytes:
        """Download an invoice PDF/image from the *imported* container."""
        blob = self._client.get_blob_client(container=self._imported, blob=blob_name)
        return blob.download_blob().readall()

    # ── Uploads ──────────────────────────────────────────────────────────

    def upload_result(self, extraction_id: str, result_json: dict) -> str:
        """Serialise *result_json* and upload to the *extracted* container.

        Returns the blob name of the uploaded result.
        """
        blob_name = f"{extraction_id}/result.json"
        blob = self._client.get_blob_client(container=self._extracted, blob=blob_name)
        data = json.dumps(result_json, ensure_ascii=False, indent=2).encode("utf-8")
        blob.upload_blob(data, overwrite=True, content_settings=_json_content_settings())
        return blob_name

    def upload_images(self, extraction_id: str, page_images: list[bytes]) -> list[str]:
        """Upload rendered page images to the *extracted* container.

        Returns a list of blob names for the uploaded images.
        """
        blob_names: list[str] = []
        for idx, image_data in enumerate(page_images):
            blob_name = f"{extraction_id}/pages/page_{idx:03d}.png"
            blob = self._client.get_blob_client(container=self._extracted, blob=blob_name)
            blob.upload_blob(image_data, overwrite=True, content_settings=_png_content_settings())
            blob_names.append(blob_name)
        return blob_names

    # ── SAS URLs ─────────────────────────────────────────────────────────

    def get_invoice_url(self, blob_name: str, expiry_hours: int = 1) -> str:
        """Generate a time-limited SAS URL for an invoice in the *imported* container."""
        return self._generate_sas_url(self._imported, blob_name, expiry_hours)

    def get_image_url(self, blob_path: str, expiry_hours: int = 1) -> str:
        """Generate a time-limited SAS URL for a page image in the *extracted* container."""
        return self._generate_sas_url(self._extracted, blob_path, expiry_hours)

    # ── Internal ─────────────────────────────────────────────────────────

    def _generate_sas_url(self, container: str, blob_name: str, expiry_hours: int) -> str:
        account_name = self._client.account_name
        account_key = self._client.credential.account_key

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
        )
        return f"https://{account_name}.blob.core.windows.net/{container}/{blob_name}?{sas_token}"


# ── Helpers ──────────────────────────────────────────────────────────────────


def _json_content_settings():
    from azure.storage.blob import ContentSettings

    return ContentSettings(content_type="application/json")


def _png_content_settings():
    from azure.storage.blob import ContentSettings

    return ContentSettings(content_type="image/png")

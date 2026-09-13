"""Durable campaign-run storage for request-driven deployments.

The local app deliberately keeps runs in memory. Vercel container Functions,
however, scale to zero and can send two requests to different instances. When
``BLOB_READ_WRITE_TOKEN`` is present, this module stores the result metadata,
generated artifact, and source assets in a public Vercel Blob store so a later
instance can restore the run.

The Blob store is public because generated posters and reels are displayed by
the public, password-free owner UI. Write access still requires the server-only
token. Local development keeps its existing no-token, in-memory behavior.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field
from vercel.blob import BlobClient, BlobNotFoundError

from advantage import CampaignResult


class RunStoreError(RuntimeError):
    """Raised when configured durable storage cannot save or restore a run."""


class StoredFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: Literal["artifact", "logo_asset", "photo_assets", "footage_assets"]
    index: int = 0
    url: str
    pathname: str
    filename: str


class StoredRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    result: CampaignResult
    artifact: StoredFile
    inputs: list[StoredFile] = Field(default_factory=list)


class BlobRunStore:
    """Persist and rehydrate ``CampaignResult`` objects with Vercel Blob."""

    _ROOT = "campaign-runs"
    _MULTIPART_THRESHOLD = 4 * 1024 * 1024

    def __init__(
        self,
        token: str,
        *,
        client_factory: Callable[[str], Any] = BlobClient,
    ) -> None:
        if not token.strip():
            raise ValueError("A non-empty Vercel Blob token is required.")
        self._token = token
        self._client_factory = client_factory

    @classmethod
    def from_environment(cls, environ: dict[str, str] | os._Environ[str] = os.environ):
        token = environ.get("BLOB_READ_WRITE_TOKEN", "").strip()
        return cls(token) if token else None

    def save(self, run_id: str, result: CampaignResult) -> StoredRun:
        client = self._client_factory(self._token)
        try:
            artifact_path = Path(result.artifact.file_path)
            artifact = self._upload_file(
                client,
                artifact_path,
                f"{self._ROOT}/{run_id}/artifact/{artifact_path.name}",
                target="artifact",
                content_type=(
                    "image/png" if result.artifact.format.value == "poster" else "video/mp4"
                ),
            )

            inputs: list[StoredFile] = []
            request = result.request
            if request.logo_asset is not None and request.logo_asset.local_ref:
                inputs.append(
                    self._upload_asset(
                        client, run_id, "logo_asset", 0, request.logo_asset.local_ref,
                        request.logo_asset.mime_type,
                    )
                )
            for field in ("photo_assets", "footage_assets"):
                for index, asset in enumerate(getattr(request, field)):
                    if asset.local_ref:
                        inputs.append(
                            self._upload_asset(
                                client, run_id, field, index, asset.local_ref, asset.mime_type
                            )
                        )

            stored = StoredRun(result=result, artifact=artifact, inputs=inputs)
            client.put(
                self._manifest_path(run_id),
                stored.model_dump_json().encode("utf-8"),
                access="public",
                content_type="application/json",
                overwrite=True,
            )
            return stored
        except RunStoreError:
            raise
        except Exception as exc:
            raise RunStoreError(f"Could not persist campaign run {run_id!r}.") from exc
        finally:
            client.close()

    def load(self, run_id: str) -> StoredRun | None:
        client = self._client_factory(self._token)
        try:
            blob = client.get(self._manifest_path(run_id), access="public", use_cache=False)
            if blob is None:
                return None
            return StoredRun.model_validate_json(blob.content)
        except BlobNotFoundError:
            return None
        except Exception as exc:
            raise RunStoreError(f"Could not restore campaign run {run_id!r}.") from exc
        finally:
            client.close()

    def materialize_inputs(self, stored: StoredRun, destination: Path) -> None:
        """Download any source assets a regenerated render needs."""
        client = self._client_factory(self._token)
        try:
            for remote in stored.inputs:
                target = destination / remote.target / f"{remote.index}-{remote.filename}"
                if not target.exists():
                    client.download_file(remote.url, target, access="public")
                request = stored.result.request
                if remote.target == "logo_asset":
                    if request.logo_asset is not None:
                        request.logo_asset.local_ref = str(target)
                else:
                    assets = getattr(request, remote.target)
                    if remote.index < len(assets):
                        assets[remote.index].local_ref = str(target)
        except Exception as exc:
            raise RunStoreError("Could not restore the campaign's source media.") from exc
        finally:
            client.close()

    def materialize_artifact(self, stored: StoredRun, destination: Path) -> Path:
        """Download a generated file for an operation that requires a local path."""
        target = destination / stored.artifact.filename
        if target.exists():
            stored.result.artifact.file_path = str(target)
            return target

        client = self._client_factory(self._token)
        try:
            client.download_file(stored.artifact.url, target, access="public")
        except Exception as exc:
            raise RunStoreError("Could not restore the generated campaign artifact.") from exc
        finally:
            client.close()
        stored.result.artifact.file_path = str(target)
        return target

    def _upload_asset(
        self,
        client: Any,
        run_id: str,
        field: Literal["logo_asset", "photo_assets", "footage_assets"],
        index: int,
        local_ref: str,
        content_type: str,
    ) -> StoredFile:
        path = Path(local_ref)
        return self._upload_file(
            client,
            path,
            f"{self._ROOT}/{run_id}/inputs/{field}/{index}-{path.name}",
            target=field,
            index=index,
            content_type=content_type,
        )

    def _upload_file(
        self,
        client: Any,
        local_path: Path,
        pathname: str,
        *,
        target: Literal["artifact", "logo_asset", "photo_assets", "footage_assets"],
        index: int = 0,
        content_type: str,
    ) -> StoredFile:
        if not local_path.is_file():
            raise RunStoreError(f"Campaign file is missing: {local_path.name}")
        uploaded = client.upload_file(
            local_path,
            pathname,
            access="public",
            content_type=content_type,
            overwrite=True,
            multipart=local_path.stat().st_size > self._MULTIPART_THRESHOLD,
        )
        return StoredFile(
            target=target,
            index=index,
            url=uploaded.url,
            pathname=uploaded.pathname,
            filename=local_path.name,
        )

    @classmethod
    def _manifest_path(cls, run_id: str) -> str:
        return f"{cls._ROOT}/{run_id}/result.json"

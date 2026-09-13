from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from advantage import (
    CampaignArtifact,
    CampaignRequest,
    CampaignResult,
    CreativeFormat,
    VerificationResult,
)
from advantage.integrations.google_drive import AssetKind, IntakeAsset, IntakeStatus
from cricket_posts.run_store import BlobRunStore


class FakeBlobBackend:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.uploads: list[dict] = []

    def client(self, token: str):
        assert token == "test-token"
        backend = self

        class Client:
            def upload_file(self, local_path, pathname, **kwargs):
                backend.objects[pathname] = Path(local_path).read_bytes()
                backend.uploads.append({"pathname": pathname, **kwargs})
                return SimpleNamespace(url=f"https://blob.test/{pathname}", pathname=pathname)

            def put(self, pathname, body, **kwargs):
                backend.objects[pathname] = bytes(body)
                return SimpleNamespace(url=f"https://blob.test/{pathname}", pathname=pathname)

            def get(self, pathname, **kwargs):
                content = backend.objects.get(pathname)
                return None if content is None else SimpleNamespace(content=content)

            def download_file(self, url, local_path, **kwargs):
                pathname = url.removeprefix("https://blob.test/")
                target = Path(local_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(backend.objects[pathname])
                return str(target)

            def close(self):
                return None

        return Client()


def _result(tmp_path: Path) -> tuple[CampaignResult, Path, Path]:
    artifact_path = tmp_path / "poster.png"
    artifact_path.write_bytes(b"poster-bytes")
    logo_path = tmp_path / "logo.png"
    logo_path.write_bytes(b"logo-bytes")
    logo = IntakeAsset(
        source_ref="logo-ref",
        kind=AssetKind.LOGO,
        mime_type="image/png",
        local_ref=str(logo_path),
        status=IntakeStatus.IMPORTED,
    )
    result = CampaignResult(
        request=CampaignRequest(
            business_name="22Yards",
            brief_text="Free-trial poster",
            format=CreativeFormat.POSTER,
            logo_asset=logo,
        ),
        artifact=CampaignArtifact(
            format=CreativeFormat.POSTER,
            file_path=str(artifact_path),
            width=1080,
            height=1350,
        ),
        verification=VerificationResult(passed=True),
    )
    return result, artifact_path, logo_path


def test_blob_run_store_round_trips_metadata_and_files(tmp_path: Path) -> None:
    backend = FakeBlobBackend()
    store = BlobRunStore("test-token", client_factory=backend.client)
    result, artifact_path, logo_path = _result(tmp_path)

    stored = store.save("run123", result)

    assert stored.artifact.url.endswith("campaign-runs/run123/artifact/poster.png")
    assert backend.objects["campaign-runs/run123/artifact/poster.png"] == b"poster-bytes"
    assert "campaign-runs/run123/result.json" in backend.objects

    artifact_path.unlink()
    logo_path.unlink()
    restored = store.load("run123")
    assert restored is not None
    assert restored.result.request.business_name == "22Yards"

    store.materialize_inputs(restored, tmp_path / "restored-inputs")
    restored_logo = Path(restored.result.request.logo_asset.local_ref)  # type: ignore[union-attr]
    assert restored_logo.read_bytes() == b"logo-bytes"

    restored_artifact = store.materialize_artifact(restored, tmp_path / "restored-artifact")
    assert restored_artifact.read_bytes() == b"poster-bytes"
    assert restored.result.artifact.file_path == str(restored_artifact)


def test_blob_run_store_returns_none_for_unknown_run() -> None:
    backend = FakeBlobBackend()
    store = BlobRunStore("test-token", client_factory=backend.client)

    assert store.load("missing") is None


def test_blob_run_store_uses_multipart_for_large_files(tmp_path: Path) -> None:
    backend = FakeBlobBackend()
    store = BlobRunStore("test-token", client_factory=backend.client)
    result, artifact_path, _ = _result(tmp_path)
    artifact_path.write_bytes(b"x" * (4 * 1024 * 1024 + 1))

    store.save("large", result)

    artifact_upload = next(
        upload for upload in backend.uploads if "/artifact/" in upload["pathname"]
    )
    assert artifact_upload["multipart"] is True

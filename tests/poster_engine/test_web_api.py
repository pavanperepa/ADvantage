from __future__ import annotations

from fastapi.testclient import TestClient

from cricket_posts.studio import PosterStudio
from cricket_posts.web import create_app


def test_healthcheck(tmp_path):
    studio = PosterStudio(database_path=tmp_path / "studio.db")
    response = TestClient(create_app(studio)).get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_structured_api_workflow_generates_and_exports_one_poster(
    tmp_path,
    load_content,
):
    studio = PosterStudio(
        database_path=tmp_path / "studio.db",
        output_root=tmp_path / "projects",
    )
    brand = studio.ensure_default_brand()
    app = create_app(studio)
    client = TestClient(app)

    created = client.post(
        "/api/projects",
        json={
            "brand_id": brand.id,
            "content": load_content("lane-rental.json").model_dump(mode="json"),
            "use_ai_planner": False,
        },
    )
    assert created.status_code == 201
    project_id = created.json()["id"]

    accepted = client.post(
        f"/api/projects/{project_id}/generate",
        json={
            "use_ideogram": False,
            "use_critic": False,
            "color_mode": "light",
            "font_preset": "modern",
        },
    )
    assert accepted.status_code == 202
    assert accepted.json()["status"] == "accepted"

    project = client.get(f"/api/projects/{project_id}")
    assert project.status_code == 200
    assert project.json()["status"] == "complete"
    assert project.json()["audit"]["valid"] is True
    assert project.json()["design"]["color_mode"] == "light"
    assert project.json()["design"]["font_preset"] == "modern"

    poster = client.get(f"/projects/{project_id}/poster.png")
    assert poster.status_code == 200
    assert poster.headers["content-type"] == "image/png"

    exported = client.get(f"/api/projects/{project_id}/export")
    assert exported.status_code == 200
    assert exported.headers["content-type"] == "application/zip"

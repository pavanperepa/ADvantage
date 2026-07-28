from __future__ import annotations

from cricket_posts.models import (
    BrandProfile,
    InformationContent,
    PosterProject,
    ProjectStatus,
    protect_all_copy,
)
from cricket_posts.storage import StudioDatabase


def test_sqlite_persists_brands_projects_and_recovers_interrupted_jobs(tmp_path):
    database = StudioDatabase(tmp_path / "studio.db")
    brand = database.save_brand(BrandProfile(name="Boundary Cricket"))
    project = PosterProject(
        brand_id=brand.id,
        content=protect_all_copy(InformationContent(title="Summer Hours")),
        status=ProjectStatus.RENDERING,
    )
    database.save_project(project)

    restarted = StudioDatabase(tmp_path / "studio.db")
    assert restarted.recover_interrupted() == 1
    restored = restarted.get_project(project.id)
    assert restored.status == ProjectStatus.READY
    assert restored.error == "Generation was interrupted and can be resumed."
    assert restarted.get_brand(brand.id).name == "Boundary Cricket"

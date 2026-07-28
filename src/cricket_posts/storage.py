from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from .models import BrandProfile, PosterProject, ProjectStatus


def _now() -> str:
    return datetime.now(UTC).isoformat()


class StudioDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS brands (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    brand_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (brand_id) REFERENCES brands(id)
                );
                CREATE INDEX IF NOT EXISTS idx_projects_status
                    ON projects(status, updated_at);
                CREATE INDEX IF NOT EXISTS idx_projects_brand
                    ON projects(brand_id, updated_at);
                """
            )

    def save_brand(self, brand: BrandProfile) -> BrandProfile:
        payload = brand.model_dump_json()
        now = _now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO brands (id, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    payload=excluded.payload,
                    updated_at=excluded.updated_at
                """,
                (brand.id, payload, now, now),
            )
        return brand

    def get_brand(self, brand_id: str) -> BrandProfile:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT payload FROM brands WHERE id = ?", (brand_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown brand: {brand_id}")
        return BrandProfile.model_validate_json(row["payload"])

    def list_brands(self) -> list[BrandProfile]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM brands ORDER BY updated_at DESC"
            ).fetchall()
        return [BrandProfile.model_validate_json(row["payload"]) for row in rows]

    def save_project(self, project: PosterProject) -> PosterProject:
        payload = project.model_dump_json()
        now = _now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO projects (id, brand_id, status, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    brand_id=excluded.brand_id,
                    status=excluded.status,
                    payload=excluded.payload,
                    updated_at=excluded.updated_at
                """,
                (
                    project.id,
                    project.brand_id,
                    project.status.value,
                    payload,
                    now,
                    now,
                ),
            )
        return project

    def get_project(self, project_id: str) -> PosterProject:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT payload FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown project: {project_id}")
        return PosterProject.model_validate_json(row["payload"])

    def list_projects(self, limit: int = 100) -> list[PosterProject]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM projects ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [PosterProject.model_validate_json(row["payload"]) for row in rows]

    def delete_project(self, project_id: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    def recover_interrupted(self) -> int:
        interrupted = {
            ProjectStatus.GENERATING_ART.value,
            ProjectStatus.RENDERING.value,
            ProjectStatus.VALIDATING.value,
        }
        placeholders = ", ".join("?" for _ in interrupted)
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT payload FROM projects WHERE status IN ({placeholders})",
                tuple(interrupted),
            ).fetchall()
            for row in rows:
                payload = json.loads(row["payload"])
                payload["status"] = ProjectStatus.READY.value
                payload["error"] = "Generation was interrupted and can be resumed."
                project = PosterProject.model_validate(payload)
                connection.execute(
                    """
                    UPDATE projects SET status = ?, payload = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        project.status.value,
                        project.model_dump_json(),
                        _now(),
                        project.id,
                    ),
                )
        return len(rows)

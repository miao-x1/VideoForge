"""Wave 1: Alembic 基础设施。只使用临时库，不改 storage/videoforge.db。"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from app.core.config import PROJECT_ROOT, settings
from app.db.alembic_runtime import (
    BASELINE_REVISION,
    HEAD_REVISION,
    current_revision,
    downgrade_base,
    heads,
    history_revision_ids,
    stamp_revision,
    upgrade_head,
)
from app.db.database import reset_engine

LIVE_DB = PROJECT_ROOT / "storage" / "videoforge.db"

BUSINESS_TABLES = {
    "users",
    "projects",
    "assets",
    "task_records",
    "verification_codes",
    "task_logs",
    "director_characters",
    "director_scenes",
    "director_poses",
    "director_custom_animations",
    "director_library_meta",
    "director_agent_logs",
    "director_generations",
    "director_character_tasks",
    "user_wallets",
    "wallet_ledger",
    "user_api_credentials",
    "user_billing_prefs",
}

DATA_COUNT_TABLES = (
    "users",
    "projects",
    "task_records",
    "director_characters",
    "director_scenes",
    "director_agent_logs",
    "director_character_tasks",
)

EXPECTED_COLUMNS = {
    "users": {"id", "email", "hashed_password", "display_name", "created_at", "phone"},
    "projects": {
        "id",
        "user_id",
        "title",
        "description",
        "cover_image",
        "is_series",
        "created_at",
        "updated_at",
        "memory_json",
    },
    "assets": {
        "id",
        "user_id",
        "project_id",
        "name",
        "asset_type",
        "description",
        "file_path",
        "media_type",
        "file_name",
        "storage_key",
        "mime_type",
        "file_size",
        "file_hash",
        "width",
        "height",
        "duration",
        "thumbnail_asset_id",
        "status",
        "metadata_json",
        "created_at",
        "updated_at",
        "deleted_at",
    },
    "task_records": {
        "id",
        "task_id",
        "user_id",
        "user_input",
        "duration",
        "style",
        "aspect_ratio",
        "compliance_enabled",
        "status",
        "video_path",
        "quality_grade",
        "state_json",
        "created_at",
        "updated_at",
        "spec_json",
        "mode",
        "project_id",
        "model_used",
    },
    "verification_codes": {
        "id",
        "target",
        "channel",
        "purpose",
        "code_hash",
        "expires_at",
        "consumed",
        "created_at",
    },
    "task_logs": {"id", "task_id", "status", "message", "timestamp"},
    "director_characters": {
        "id",
        "user_id",
        "project_id",
        "name",
        "template_id",
        "source_type",
        "primary_asset_id",
        "reference_asset_id",
        "thumbnail_asset_id",
        "data_json",
        "created_at",
        "updated_at",
    },
    "director_scenes": {
        "scene_id",
        "user_id",
        "project_id",
        "scene_name",
        "is_current",
        "background_asset_id",
        "reference_asset_id",
        "composition_asset_id",
        "current_generation_id",
        "data_json",
        "created_at",
        "updated_at",
    },
    "director_poses": {
        "id",
        "user_id",
        "project_id",
        "character_id",
        "name",
        "data_json",
        "created_at",
        "updated_at",
    },
    "director_custom_animations": {
        "id",
        "user_id",
        "project_id",
        "character_id",
        "name",
        "data_json",
        "created_at",
        "updated_at",
    },
    "director_library_meta": {
        "id",
        "user_id",
        "project_id",
        "favorites_json",
        "recent_ids_json",
        "current_scene_id",
        "updated_at",
    },
    "director_agent_logs": {
        "id",
        "user_id",
        "project_id",
        "conversation_id",
        "message_id",
        "agent_run_id",
        "user_input",
        "context_json",
        "tool_name",
        "tool_arguments",
        "tool_result",
        "execution_status",
        "error",
        "created_at",
    },
    "director_generations": {
        "id",
        "generation_id",
        "user_id",
        "project_id",
        "scene_id",
        "shot_id",
        "kind",
        "prompt",
        "negative_prompt",
        "model",
        "parameters_json",
        "result_path",
        "result_url",
        "output_asset_id",
        "parent_generation_id",
        "version_number",
        "generation_key",
        "input_snapshot_json",
        "status",
        "error",
        "created_at",
        "title",
    },
    "director_character_tasks": {
        "id",
        "task_id",
        "user_id",
        "project_id",
        "kind",
        "status",
        "progress",
        "error",
        "result_json",
        "stages_json",
        "payload_json",
        "created_at",
        "updated_at",
    },
    "user_wallets": {"user_id", "balance_fen", "updated_at"},
    "wallet_ledger": {
        "id",
        "user_id",
        "delta_fen",
        "balance_after",
        "kind",
        "note",
        "ref_id",
        "created_at",
    },
    "user_api_credentials": {
        "id",
        "user_id",
        "provider",
        "encrypted_key",
        "base_url",
        "last4",
        "enabled",
        "updated_at",
    },
    "user_billing_prefs": {
        "user_id",
        "video_source",
        "video_provider",
        "video_model",
        "updated_at",
    },
}

EXPECTED_PKS = {
    "users": ["id"],
    "projects": ["id"],
    "assets": ["id"],
    "task_records": ["id"],
    "verification_codes": ["id"],
    "task_logs": ["id"],
    "director_characters": ["id"],
    "director_scenes": ["scene_id"],
    "director_poses": ["id"],
    "director_custom_animations": ["id"],
    "director_library_meta": ["id"],
    "director_agent_logs": ["id"],
    "director_generations": ["id"],
    "director_character_tasks": ["id"],
    "user_wallets": ["user_id"],
    "wallet_ledger": ["id"],
    "user_api_credentials": ["id"],
    "user_billing_prefs": ["user_id"],
}

EXPECTED_INDEXES = {
    "users": {"ix_users_email"},
    "projects": {"ix_projects_user_id"},
    "assets": {
        "ix_assets_user_id",
        "ix_assets_asset_type",
        "ix_assets_project_id",
        "ix_assets_file_hash",
        "ix_assets_status",
        "ix_assets_storage_key",
        "ix_assets_user_project_hash",
    },
    "task_records": {"ix_task_records_task_id", "ix_task_records_user_id"},
    "verification_codes": {"ix_verification_codes_target", "ix_verification_codes_purpose"},
    "task_logs": {"ix_task_logs_task_id"},
    "director_characters": {
        "ix_director_characters_source_type",
        "ix_director_characters_user_id",
        "ix_director_characters_project_id",
        "ix_director_characters_user_project",
    },
    "director_scenes": {
        "ix_director_scenes_user_id",
        "ix_director_scenes_project_id",
        "ix_director_scenes_user_project",
    },
    "director_poses": {
        "ix_director_poses_character_id",
        "ix_director_poses_user_id",
        "ix_director_poses_project_id",
        "ix_director_poses_user_project",
    },
    "director_custom_animations": {
        "ix_director_custom_animations_character_id",
        "ix_director_custom_animations_user_id",
        "ix_director_custom_animations_project_id",
        "ix_director_custom_animations_user_project",
    },
    "director_library_meta": {
        "ix_director_library_meta_user_id",
        "ix_director_library_meta_project_id",
        "ix_director_library_meta_user_project",
    },
    "director_agent_logs": {
        "ix_director_agent_logs_conversation_id",
        "ix_director_agent_logs_message_id",
        "ix_director_agent_logs_agent_run_id",
        "ix_director_agent_logs_tool_name",
        "ix_director_agent_logs_user_id",
        "ix_director_agent_logs_project_id",
        "ix_director_agent_logs_user_project",
    },
    "director_generations": {
        "ix_director_generations_generation_id",
        "ix_director_generations_project_id",
        "ix_director_generations_scene_id",
        "ix_director_generations_shot_id",
        "ix_director_generations_user_id",
        "ix_director_generations_user_project",
        "ix_director_generations_parent_generation_id",
        "ix_director_generations_generation_key",
    },
    "director_character_tasks": {
        "ix_director_character_tasks_task_id",
        "ix_director_character_tasks_kind",
        "ix_director_character_tasks_user_id",
        "ix_director_character_tasks_project_id",
        "ix_director_character_tasks_user_project",
    },
    "user_wallets": set(),
    "wallet_ledger": {"ix_wallet_ledger_user_id"},
    "user_api_credentials": {
        "ix_user_api_credentials_user_id",
        "ix_user_api_credentials_user_provider",
    },
    "user_billing_prefs": set(),
}

EXPECTED_UNIQUE_INDEXES = {
    "ix_users_email",
    "ix_task_records_task_id",
    "ix_director_generations_generation_id",
    "ix_director_character_tasks_task_id",
    "ix_assets_storage_key",
    "ix_user_api_credentials_user_provider",
}

EXPECTED_FKS = {
    "projects": {("user_id", "users", "id")},
    "assets": {("user_id", "users", "id"), ("project_id", "projects", "id")},
    "task_records": {("user_id", "users", "id")},
    "task_logs": {("task_id", "task_records", "task_id")},
    "user_wallets": {("user_id", "users", "id")},
    "wallet_ledger": {("user_id", "users", "id")},
    "user_api_credentials": {("user_id", "users", "id")},
    "user_billing_prefs": {("user_id", "users", "id")},
}


def _point_settings(monkeypatch, db_path: Path) -> str:
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setattr(settings, "database_url", url)
    reset_engine()
    return url


def _copy_live_db(dest: Path) -> None:
    if not LIVE_DB.exists():
        pytest.skip(f"live database missing: {LIVE_DB}")
    src = sqlite3.connect(f"file:{LIVE_DB.as_posix()}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(str(dest))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def _row_counts(db_path: Path, tables=DATA_COUNT_TABLES) -> dict[str, int]:
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        return {t: cur.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0] for t in tables}
    finally:
        con.close()


def _named_indexes(insp, table: str) -> list[dict]:
    return [idx for idx in insp.get_indexes(table) if idx.get("name") and not str(idx["name"]).startswith("sqlite_")]


def _fk_set(insp, table: str) -> set[tuple[str, str, str]]:
    found: set[tuple[str, str, str]] = set()
    for fk in insp.get_foreign_keys(table):
        referred = fk.get("referred_table") or ""
        for col, ref in zip(fk.get("constrained_columns") or [], fk.get("referred_columns") or []):
            found.add((col, referred, ref))
    return found


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    path = tmp_path / "fresh.db"
    url = _point_settings(monkeypatch, path)
    yield path, url
    reset_engine()


@pytest.fixture
def existing_copy(tmp_path, monkeypatch):
    path = tmp_path / "existing_copy.db"
    _copy_live_db(path)
    url = _point_settings(monkeypatch, path)
    yield path, url
    reset_engine()


def test_alembic_history_is_valid():
    assert heads() == [HEAD_REVISION]
    assert history_revision_ids() == [
        HEAD_REVISION,
        "005_billing_and_credentials",
        "004_generation_version_chain",
        "003_asset_normalization",
        "002_director_ownership",
        BASELINE_REVISION,
    ]


def test_alembic_can_initialize_fresh_database(fresh_db):
    path, url = fresh_db
    upgrade_head()
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert BUSINESS_TABLES.issubset(tables)
    assert "alembic_version" in tables
    assert current_revision() == HEAD_REVISION


def test_alembic_current_is_correct(fresh_db):
    assert current_revision() is None
    upgrade_head()
    assert current_revision() == HEAD_REVISION


def test_fresh_schema_matches_expected_schema(fresh_db):
    _path, url = fresh_db
    upgrade_head()
    engine = create_engine(url)
    try:
        insp = inspect(engine)
        tables = set(insp.get_table_names()) - {"alembic_version"}
        assert tables == BUSINESS_TABLES
        for table in BUSINESS_TABLES:
            cols = {c["name"] for c in insp.get_columns(table)}
            assert cols == EXPECTED_COLUMNS[table], table
            pk = insp.get_pk_constraint(table).get("constrained_columns") or []
            assert pk == EXPECTED_PKS[table], table
            idx_names = {i["name"] for i in _named_indexes(insp, table)}
            assert idx_names == EXPECTED_INDEXES[table], table
            unique = {i["name"] for i in _named_indexes(insp, table) if i.get("unique")}
            assert unique == (EXPECTED_INDEXES[table] & EXPECTED_UNIQUE_INDEXES), table
            assert _fk_set(insp, table) == EXPECTED_FKS.get(table, set()), table
    finally:
        engine.dispose()


def test_existing_database_can_be_stamped(existing_copy):
    path, _url = existing_copy
    before = _row_counts(path)
    assert current_revision() is None
    stamp_revision(BASELINE_REVISION)
    assert current_revision() == BASELINE_REVISION
    assert _row_counts(path) == before


def test_existing_data_counts_unchanged(existing_copy):
    path, _url = existing_copy
    live_counts = _row_counts(LIVE_DB)
    before = _row_counts(path)
    assert before == live_counts
    stamp_revision(BASELINE_REVISION)
    after = _row_counts(path)
    assert after == before == live_counts
    assert _row_counts(LIVE_DB) == live_counts


def test_alembic_upgrade_downgrade_roundtrip(fresh_db):
    path, url = fresh_db
    upgrade_head()
    assert current_revision() == HEAD_REVISION
    downgrade_base()
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert not BUSINESS_TABLES.intersection(tables)
    assert current_revision() is None
    upgrade_head()
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert BUSINESS_TABLES.issubset(tables)
    assert current_revision() == HEAD_REVISION


def test_baseline_upgrade_refuses_existing_database(existing_copy):
    path, _url = existing_copy
    before = _row_counts(path)
    with pytest.raises(RuntimeError, match="already exist"):
        upgrade_head()
    assert current_revision() is None
    assert _row_counts(path) == before == _row_counts(LIVE_DB)


def test_live_database_has_no_alembic_version():
    if not LIVE_DB.exists():
        pytest.skip(f"live database missing: {LIVE_DB}")
    con = sqlite3.connect(f"file:{LIVE_DB.as_posix()}?mode=ro", uri=True)
    try:
        names = {
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
    finally:
        con.close()
    assert "alembic_version" not in names
    assert BUSINESS_TABLES.issubset(names)

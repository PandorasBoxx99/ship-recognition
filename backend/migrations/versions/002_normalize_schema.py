"""Normalize schema: add ships, images, ml_models and related tables.

Revision ID: 002_normalize
Revises: initial_v1
Create Date: 2026-03-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_normalize"
down_revision: Union[str, None] = "initial_v1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ships
    op.create_table(
        "ships",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("canonical_name", sa.Text),
        sa.Column("ship_type", sa.Text),
        sa.Column("ship_class", sa.Text),
        sa.Column("subtype", sa.Text),
        sa.Column("operator", sa.Text),
        sa.Column("country", sa.Text),
        sa.Column("flag", sa.Text),
        sa.Column("imo", sa.Text),
        sa.Column("mmsi", sa.Text),
        sa.Column("year_built", sa.Integer),
        sa.Column("description", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_ships_imo", "ships", ["imo"])
    op.create_index("idx_ships_mmsi", "ships", ["mmsi"])

    # Ship aliases
    op.create_table(
        "ship_aliases",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ship_id", sa.Integer, sa.ForeignKey("ships.id"), nullable=False),
        sa.Column("alias_name", sa.Text, nullable=False),
        sa.Column("source", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_ship_aliases_ship_id", "ship_aliases", ["ship_id"])

    # Images
    op.create_table(
        "images",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ship_id", sa.Integer, sa.ForeignKey("ships.id")),
        sa.Column("file_path", sa.Text, nullable=False),
        sa.Column("file_name", sa.Text),
        sa.Column("source_url", sa.Text),
        sa.Column("source_name", sa.Text),
        sa.Column("hash_sha256", sa.Text),
        sa.Column("width", sa.Integer),
        sa.Column("height", sa.Integer),
        sa.Column("file_size", sa.Integer),
        sa.Column("mime_type", sa.Text),
        sa.Column("quality_score", sa.Float),
        sa.Column("is_synthetic", sa.Integer, server_default="0"),
        sa.Column("split_type", sa.Text),
        sa.Column("label_status", sa.Text),
        sa.Column("review_status", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_images_ship_id", "images", ["ship_id"])
    op.create_index("idx_images_hash", "images", ["hash_sha256"])

    # Image annotations
    op.create_table(
        "image_annotations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("image_id", sa.Integer, sa.ForeignKey("images.id"), nullable=False),
        sa.Column("annotation_type", sa.Text),
        sa.Column("bbox_json", sa.Text),
        sa.Column("segmentation_json", sa.Text),
        sa.Column("confidence", sa.Float),
        sa.Column("reviewer", sa.Text),
        sa.Column("reviewed_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_image_annotations_image_id", "image_annotations", ["image_id"])

    # Scrape sources
    op.create_table(
        "scrape_sources",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("base_url", sa.Text),
        sa.Column("source_type", sa.Text),
        sa.Column("parser_config_json", sa.Text),
        sa.Column("rate_limit", sa.Integer),
        sa.Column("retry_limit", sa.Integer),
        sa.Column("is_active", sa.Integer, server_default="1"),
        sa.Column("requires_vpn", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Scrape jobs (normalized)
    op.create_table(
        "scrape_jobs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("scrape_sources.id")),
        sa.Column("status", sa.Text),
        sa.Column("started_at", sa.DateTime),
        sa.Column("finished_at", sa.DateTime),
        sa.Column("items_found", sa.Integer, server_default="0"),
        sa.Column("items_saved", sa.Integer, server_default="0"),
        sa.Column("items_failed", sa.Integer, server_default="0"),
        sa.Column("error_log", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_scrape_jobs_source_id", "scrape_jobs", ["source_id"])

    # ML Models registry
    op.create_table(
        "ml_models",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("version", sa.Text, nullable=False),
        sa.Column("model_type", sa.Text, nullable=False),
        sa.Column("framework", sa.Text),
        sa.Column("task_type", sa.Text),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("input_size", sa.Text),
        sa.Column("label_map_json", sa.Text),
        sa.Column("metrics_json", sa.Text),
        sa.Column("is_active", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Training runs
    op.create_table(
        "training_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("model_id", sa.Integer, sa.ForeignKey("ml_models.id")),
        sa.Column("dataset_version", sa.Text),
        sa.Column("config_json", sa.Text),
        sa.Column("metrics_json", sa.Text),
        sa.Column("status", sa.Text),
        sa.Column("started_at", sa.DateTime),
        sa.Column("finished_at", sa.DateTime),
        sa.Column("log_path", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_training_runs_model_id", "training_runs", ["model_id"])

    # Inference logs
    op.create_table(
        "inference_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("model_id", sa.Integer, sa.ForeignKey("ml_models.id")),
        sa.Column("image_id", sa.Integer, sa.ForeignKey("images.id")),
        sa.Column("input_path", sa.Text),
        sa.Column("top_prediction", sa.Text),
        sa.Column("confidence", sa.Float),
        sa.Column("topk_json", sa.Text),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_inference_logs_model_id", "inference_logs", ["model_id"])
    op.create_index("idx_inference_logs_image_id", "inference_logs", ["image_id"])

    # Synthetic jobs
    op.create_table(
        "synthetic_jobs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ship_class", sa.Text),
        sa.Column("source_count", sa.Integer),
        sa.Column("generated_count", sa.Integer),
        sa.Column("method", sa.Text),
        sa.Column("config_json", sa.Text),
        sa.Column("status", sa.Text),
        sa.Column("output_dir", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # --- Data migration: items -> ships + images ---
    # This is done via raw SQL for efficiency
    conn = op.get_bind()

    # Migrate downloaded items to ships (deduplicated by name+imo)
    conn.execute(sa.text("""
        INSERT INTO ships (name, ship_type, imo, mmsi, created_at)
        SELECT DISTINCT
            COALESCE(NULLIF(ship_name, ''), 'Unknown #' || id),
            ship_type,
            imo_number,
            mmsi,
            created_at
        FROM items
        WHERE status = 'downloaded'
        GROUP BY COALESCE(NULLIF(ship_name, ''), 'Unknown #' || id), imo_number
    """))

    # Migrate item images to images table
    conn.execute(sa.text("""
        INSERT INTO images (ship_id, file_path, file_name, source_url, created_at)
        SELECT
            s.id,
            i.local_path,
            REPLACE(i.local_path, RTRIM(i.local_path, REPLACE(i.local_path, '/', '')), ''),
            i.source_url,
            i.created_at
        FROM items i
        LEFT JOIN ships s ON (
            COALESCE(NULLIF(i.ship_name, ''), 'Unknown #' || i.id) = s.name
            AND (i.imo_number IS NULL OR i.imo_number = '' OR i.imo_number = s.imo)
        )
        WHERE i.status = 'downloaded' AND i.local_path IS NOT NULL
    """))

    # Migrate classifications to inference_logs
    conn.execute(sa.text("""
        INSERT INTO inference_logs (input_path, top_prediction, confidence, topk_json, created_at)
        SELECT
            image_path,
            predicted_type,
            confidence,
            all_predictions,
            created_at
        FROM classifications
    """))

    # Seed the default model into the registry
    conn.execute(sa.text("""
        INSERT INTO ml_models (name, version, model_type, framework, task_type, path, input_size, is_active)
        VALUES ('vit-ship-classifier', '1.0.0', 'classification', 'pytorch', 'ship_classification',
                'models/ship_classifier', '224x224', 1)
    """))

    # Migrate predefined_urls to scrape_sources
    conn.execute(sa.text("""
        INSERT INTO scrape_sources (name, base_url, source_type, is_active)
        SELECT name, url, 'html', 1 FROM predefined_urls
    """))


def downgrade() -> None:
    op.drop_table("synthetic_jobs")
    op.drop_table("inference_logs")
    op.drop_table("training_runs")
    op.drop_table("ml_models")
    op.drop_table("scrape_jobs")
    op.drop_table("scrape_sources")
    op.drop_table("image_annotations")
    op.drop_table("images")
    op.drop_table("ship_aliases")
    op.drop_table("ships")

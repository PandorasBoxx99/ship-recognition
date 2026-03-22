#!/usr/bin/env python3
"""
One-time migration script for existing v1 databases.

If a schiffs-scraper.db already exists (from the old Flask app),
this script stamps it with the Alembic version so that future
migrations work correctly.

If no database exists, it creates a fresh one via Alembic.

Usage:
    python scripts/migrate_v1.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import settings


def main():
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    db_exists = os.path.exists(db_path)

    if db_exists:
        print(f"Existing database found: {db_path}")
        print("Stamping Alembic version to mark as up-to-date...")

        # The existing DB was created from schema.sql and matches our ORM models.
        # We just need to create the alembic_version table and stamp it.
        from backend.database import engine
        from sqlalchemy import text

        with engine.connect() as conn:
            # Check if alembic_version table already exists
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
            )
            if result.fetchone():
                print("Already stamped. Nothing to do.")
                return

            # Create the alembic_version table and stamp with 'initial'
            conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('initial_v1')"))
            conn.commit()

        print("Done! Database stamped as 'initial_v1'.")
        print("Future Alembic migrations will work from this baseline.")
    else:
        print(f"No existing database at {db_path}")
        print("Creating fresh database via ORM...")

        from backend.database import Base, engine
        import backend.models  # noqa: F401

        Base.metadata.create_all(bind=engine)
        print(f"Created new database: {db_path}")


if __name__ == "__main__":
    main()

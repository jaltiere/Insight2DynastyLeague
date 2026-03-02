"""Run database migrations.

This script runs Alembic migrations to upgrade the database schema.
Use this for Railway deployments before starting the application.

Usage:
    python backend/migrate.py  (from project root)
    python migrate.py          (from backend directory)
"""
import os
import sys
from pathlib import Path
from alembic.config import Config
from alembic import command


def run_migrations():
    """Run Alembic migrations."""
    # Determine the backend directory
    script_dir = Path(__file__).parent.resolve()

    # Check if we're in the backend directory or need to navigate to it
    if script_dir.name == "backend":
        backend_dir = script_dir
    else:
        backend_dir = script_dir / "backend"

    alembic_ini = backend_dir / "alembic.ini"

    if not alembic_ini.exists():
        print(f"❌ Could not find alembic.ini at {alembic_ini}")
        print(f"Current directory: {Path.cwd()}")
        print(f"Script directory: {script_dir}")
        return 1

    try:
        print(f"Running database migrations from {backend_dir}...")
        print(f"Using alembic.ini: {alembic_ini}")

        # Change to backend directory
        os.chdir(backend_dir)

        # Create Alembic config
        alembic_cfg = Config(str(alembic_ini))

        # Run upgrade
        command.upgrade(alembic_cfg, "head")

        print("✅ Migrations completed successfully")
        return 0
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_migrations())

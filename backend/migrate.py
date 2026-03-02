"""Run database migrations.

This script runs Alembic migrations to upgrade the database schema.
Use this for Railway deployments before starting the application.

Usage:
    python migrate.py
"""
import subprocess
import sys
from pathlib import Path


def run_migrations():
    """Run Alembic migrations."""
    backend_dir = Path(__file__).parent

    try:
        print("Running database migrations...")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_dir,
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print("✅ Migrations completed successfully")
        return 0
    except subprocess.CalledProcessError as e:
        print("❌ Migration failed:")
        print(e.stderr)
        return 1
    except Exception as e:
        print(f"❌ Error running migrations: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_migrations())

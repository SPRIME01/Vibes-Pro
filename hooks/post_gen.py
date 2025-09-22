#!/usr/bin/env python3
"""Post-generation setup hook for Copier."""

from __future__ import annotations

import subprocess
import sys
import asyncio
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> None:
    """Run a subprocess, printing the command for visibility."""
    print(f"   → {' '.join(cmd)} (cwd={cwd})")
    subprocess.run(cmd, check=True, cwd=cwd)


async def setup_temporal_database(target: Path) -> None:
    """Initialize the temporal database for AI-enhanced workflows."""
    print("🔗 Setting up temporal database...")

    # Create temporal_db directory
    temporal_db_dir = target / "temporal_db"
    temporal_db_dir.mkdir(exist_ok=True)

    # Initialize database using Python implementation
    try:
        # Add the temporal_db python module to path
        sys.path.insert(0, str(Path(__file__).parent.parent / "temporal_db"))

        from python.repository import initialize_temporal_database
        from python.types import SpecificationRecord, SpecificationType

        # Initialize the database
        db_path = str(temporal_db_dir / "project_specs.db")
        repo = await initialize_temporal_database(db_path)

        # Create initial specification record for the project
        initial_spec = SpecificationRecord.create(
            spec_type=SpecificationType.ADR,
            identifier="ADR-PROJECT-001",
            title="Project Initialization",
            content="This project was generated using the VibesPro generator framework with temporal database integration for AI-enhanced development workflows.",
            author="VibesPro Generator",
        )

        await repo.store_specification(initial_spec)
        await repo.close()

        print("   ✅ Temporal database initialized successfully")

    except Exception as e:
        print(f"   ⚠️  Temporal database setup failed: {e}")
        print("   📝 You can initialize it later using: just db-init")


def setup_generated_project(target: Path) -> None:
    """Run initial setup commands inside the generated project."""
    print("🔧 Setting up generated project...")
    run(["pnpm", "install"], cwd=target)
    run(["uv", "sync", "--dev"], cwd=target)

    # Initialize temporal database
    asyncio.run(setup_temporal_database(target))

    run(["just", "build"], cwd=target)

    print("✅ Project setup completed successfully!")
    print()
    print("🚀 Next steps:")
    print("  1. cd into your project directory")
    print("  2. Run 'just dev' to start development")
    print("  3. Run 'just test' to execute the full test suite")
    print("  4. Run 'just db-status' to check temporal database")
    print("  5. Review the generated README.md for more guidance")


def main() -> None:
    print("🎉 Project generated successfully!")
    target = Path.cwd()

    try:
        setup_generated_project(target)
    except subprocess.CalledProcessError as exc:
        print(f"❌ Setup failed: {exc}")
        sys.exit(exc.returncode or 1)
    except FileNotFoundError as exc:
        print(f"❌ Required tool not found: {exc}")
        print("Please ensure pnpm, uv, and just are installed in your environment.")
        sys.exit(1)


if __name__ == "__main__":
    main()

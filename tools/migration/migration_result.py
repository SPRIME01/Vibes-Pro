"""Data classes for migration results and related types."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class MigrationResult:
    """Result of a HexDDD project migration."""
    success: bool
    target_path: Path
    migrated_files: List[str]
    preserved_config: List[str]
    migration_plan: List[str]
    errors: List[str]
    warnings: List[str] = field(default_factory=lambda: [])

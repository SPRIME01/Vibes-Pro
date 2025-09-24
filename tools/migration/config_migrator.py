"""Configuration migration utilities for HexDDD migration."""

from __future__ import annotations

import json
import logging
import yaml
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ConfigMigrator:
    """Handles migration of build configurations and setup files."""

    def __init__(self, source_path: Path):
        """Initialize config migrator with source project path."""
        self.source_path = source_path

    def create_copier_config(self, analysis: Any) -> str:
        """Create copier.yml configuration based on the analyzed project."""
        project_name = analysis.package_config.get("name", "migrated-hexddd-project")

        config = {
            "project_name": {
                "type": "str",
                "help": "Name of the project",
                "default": project_name
            },
            "author_name": {
                "type": "str",
                "help": "Author's name",
                "default": "Development Team"
            },
            "include_nx_workspace": {
                "type": "bool",
                "help": "Include Nx workspace configuration",
                "default": True
            },
            "architecture_style": {
                "type": "str",
                "help": "Primary architecture pattern",
                "choices": ["hexagonal", "layered", "microservices"],
                "default": "hexagonal"
            },
            "package_manager": {
                "type": "str",
                "help": "Package manager to use",
                "choices": ["npm", "yarn", "pnpm"],
                "default": analysis.build_config.get("cli", {}).get("packageManager", "pnpm")
            }
        }

        # Add domain-specific configuration
        domain_names = [lib.name for lib in analysis.domain_libraries]
        if domain_names:
            config["domain_libraries"] = {
                "type": "json",
                "help": "List of domain libraries to generate",
                "default": domain_names
            }

        # Convert to YAML format
        return yaml.dump(config, default_flow_style=False, sort_keys=False)

    def migrate_build_configs(self, analysis: Any, target_path: Path) -> List[str]:
        """Migrate build configuration files."""
        preserved_files = []

        # Copy and adapt nx.json
        if analysis.has_nx_config:
            target_nx = target_path / "nx.json"

            # Adapt nx.json for template context
            nx_config = analysis.build_config.copy()
            # Remove project-specific configurations that will be templated
            if "projects" in nx_config:
                # Convert projects to template format
                nx_config["projects"] = {
                    "{{project_name}}": "libs/{{project_name}}"
                }

            with open(target_nx, 'w') as f:
                json.dump(nx_config, f, indent=2)
            preserved_files.append("nx.json")

        # Copy and adapt package.json
        if analysis.package_config:
            package_config = analysis.package_config.copy()
            package_config["name"] = "{{project_name}}"

            target_package = target_path / "package.json"
            with open(target_package, 'w') as f:
                json.dump(package_config, f, indent=2)
            preserved_files.append("package.json")

        return preserved_files

    def create_target_structure(self, target_path: Path) -> None:
        """Create the target directory structure for the migrated project."""
        target_path.mkdir(parents=True, exist_ok=True)

        # Create essential directories
        directories = [
            "templates",
            "hooks",
            "tests",
            "docs",
            "tools/migration",
        ]

        for dir_path in directories:
            (target_path / dir_path).mkdir(parents=True, exist_ok=True)

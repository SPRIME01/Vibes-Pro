"""Documentation generation utilities for HexDDD migration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List


class DocumentationGenerator:
    """Handles generation of migration documentation and guides."""

    def generate_migration_guide(self, analysis: Any, target_path: Path) -> None:
        """Generate migration guide documentation."""
        migration_guide = f"""# HexDDD Migration Guide

This project has been migrated from a HexDDD Nx workspace to the unified generator-first platform.

## Migration Summary

- **Source Project**: {analysis.package_config.get("name", "Unknown")}
- **Architecture**: Hexagonal Architecture + Domain-Driven Design
- **Build System**: Nx Workspace
- **Package Manager**: {analysis.build_config.get("cli", {}).get("packageManager", "pnpm")}

## What Was Migrated

### Build Configuration
- Nx workspace configuration adapted for template generation
- Package.json converted to template format
- Dependencies preserved and categorized

## Migrated Components

### Generators
{self._format_generators_list(analysis.generators)}

### Domain Libraries
{self._format_domain_libraries_list(analysis.domain_libraries)}

## Next Steps

1. Review the generated `copier.yml` configuration
2. Test template generation with: `copier copy . /tmp/test-project`
3. Validate that all domain logic is preserved
4. Customize templates as needed for your use case

## Validation Checklist

- [ ] All original domain entities are present in templates
- [ ] Build configuration works in generated projects
- [ ] Custom business logic is preserved
- [ ] Tests can be run successfully
- [ ] All dependencies are correctly migrated

## Support

If you encounter issues with the migration, please refer to the original project structure and adapt the templates accordingly.
"""

        (target_path / "MIGRATION-GUIDE.md").write_text(migration_guide)

    def _format_generators_list(self, generators: List[Any]) -> str:
        """Format generators list for documentation."""
        if not generators:
            return "None found"

        lines = [
            f"- **{gen.name}**: {len(gen.template_files)} template files"
            for gen in generators
        ]
        return "\n".join(lines)

    def _format_domain_libraries_list(self, domain_libraries: List[Any]) -> str:
        """Format domain libraries list for documentation."""
        if not domain_libraries:
            return "None found"

        lines: List[str] = []
        for lib in domain_libraries:
            components: List[str] = []
            if lib.has_entities:
                components.append("entities")
            if lib.has_value_objects:
                components.append("value objects")
            if lib.has_aggregates:
                components.append("aggregates")
            if lib.has_services:
                components.append("services")

            components_str = ", ".join(components) if components else "custom code"
            lines.append(f"- **{lib.name}**: {len(lib.custom_files)} files ({components_str})")
        return "\n".join(lines)

"""Domain-specific migration utilities for HexDDD projects."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class DomainMigrator:
    """Handles migration of domain libraries and DDD-specific structures."""

    def migrate_domain_libraries(self, domain_libraries: List[Any], target_path: Path) -> Dict[str, List[str]]:
        """Migrate domain libraries to template format."""
        migrated_files: List[str] = []
        warnings: List[str] = []

        for domain_lib in domain_libraries:
            try:
                # Create template directory for this domain
                domain_template_dir = target_path / "templates" / "libs" / domain_lib.name
                domain_template_dir.mkdir(parents=True, exist_ok=True)

                # Create domain subdirectories
                domain_subdirs = ["src", "src/lib", "src/lib/domain", "src/lib/application", "src/lib/infrastructure"]
                for subdir in domain_subdirs:
                    (domain_template_dir / subdir).mkdir(parents=True, exist_ok=True)

                # Create generic entity template if domain has entities
                if domain_lib.has_entities:
                    entity_template_path = domain_template_dir / "src" / "lib" / "domain" / "{{entity_name}}.entity.ts.j2"
                    entity_template_content = self._get_generic_entity_template()
                    entity_template_path.write_text(entity_template_content)
                    migrated_files.append(f"libs/{{{{domain_name}}}}/src/lib/domain/{{{{entity_name}}}}.entity.ts.j2")
                    logger.info(f"Created generic entity template for domain: {domain_lib.name}")

                # Copy and template-ize all files
                for custom_file in domain_lib.custom_files:
                    try:
                        relative_path = custom_file.relative_to(domain_lib.path)
                        target_file = domain_template_dir / relative_path
                        target_file.parent.mkdir(parents=True, exist_ok=True)

                        # Read and convert content
                        content = custom_file.read_text()
                        templated_content = self._convert_code_to_template(content, domain_lib.name)

                        # Add .j2 extension for Jinja2 templates
                        target_file = target_file.with_suffix(f"{target_file.suffix}.j2")
                        target_file.write_text(templated_content)

                        migrated_files.append(f"libs/{{{{domain_name}}}}/{relative_path}.j2")
                        logger.debug(f"Converted domain file: {relative_path}")
                    except Exception as e:
                        logger.warning(f"Failed to convert domain file {custom_file}: {str(e)}")
                        warnings.append(f"Domain file {custom_file}: Conversion failed - {str(e)}. Manual review required.")

                logger.info(f"Successfully migrated domain library: {domain_lib.name}")
            except Exception as e:
                logger.warning(f"Failed to migrate domain library {domain_lib.name}: {str(e)}")
                warnings.append(f"Domain library {domain_lib.name}: Migration failed - {str(e)}. Manual review required.")

        return {"files": migrated_files, "warnings": warnings}

    def _get_generic_entity_template(self) -> str:
        """Get a generic entity template for domains that have entities."""
        return '''export class {{entity_name}} {
  constructor(
    private readonly id: string,
    private readonly email: string
  ) {}
}'''

    def _convert_code_to_template(self, content: str, original_domain_name: str) -> str:
        """Convert domain code to template format."""
        try:
            # Replace domain name in import paths (both kebab-case and camelCase variants)
            # Only replace the actual domain name part, not entity names in the path
            domain_patterns = [
                original_domain_name,
                original_domain_name.replace("-", ""),
                original_domain_name.replace("-", " ").title().replace(" ", "")
            ]

            for pattern in domain_patterns:
                if pattern:
                    # Replace in from imports - only replace the domain name part, not entity names
                    content = re.sub(
                        rf"from\s+['\"](\.\./)?{re.escape(pattern)}['\"]",
                        r"from '\1{{domain_name}}'",
                        content
                    )
                    # Replace in import statements - only replace the domain name part, keep imported names intact
                    content = re.sub(
                        rf"import\s+([^from]+)from\s+['\"](\.\./)?{re.escape(pattern)}['\"]",
                        r"import \1from '\2{{domain_name}}'",
                        content
                    )
            logger.debug(f"Replaced domain name patterns with template variable")
        except Exception as e:
            logger.warning(f"Failed to replace domain name: {e}")

        try:
            # Replace entity class names - only class declarations, not references
            # Replace entity class declarations: replace common domain classes with template variable
            def _replace_class_decl(match):
                clsname = match.group(1)
                # If class seems like a Service/Repository/Aggregate, map suffix to template
                for suffix in ('Service', 'Repository', 'Aggregate', 'Entity'):
                    if clsname.endswith(suffix):
                        return f'export class {{{{entity_name}}}}{suffix} '
                # Otherwise, replace the first class declaration with generic entity
                return 'export class {{entity_name}} '

            content = re.sub(
                r'export\s+class\s+([A-Z][a-zA-Z0-9]*)\s*{',
                _replace_class_decl,
                content,
                count=1
            )

            # Replace interface names - map to interface_name template for first declaration
            content = re.sub(
                r'export\s+interface\s+([A-Z][a-zA-Z0-9]*)\s*{',
                r'export interface {{interface_name}} {',
                content,
                count=1
            )

            logger.debug(f"Replaced class/interface names with template variables")
        except Exception as e:
            logger.warning(f"Failed to replace class/interface names: {e}")

        try:
            # Replace specific DDD patterns
            # Replace repository interface names
            content = re.sub(
                r'([A-Z][a-zA-Z0-9]*)Repository',
                r'{{entity_name}}Repository',
                content
            )

            # Replace service class names
            content = re.sub(
                r'([A-Z][a-zA-Z0-9]*)Service',
                r'{{entity_name}}Service',
                content
            )

            # Replace aggregate root references
            content = re.sub(
                r'([A-Z][a-zA-Z0-9]*)AggregateRoot',
                r'{{entity_name}}AggregateRoot',
                content
            )

            logger.debug(f"Applied DDD-specific template patterns")
        except Exception as e:
            logger.warning(f"Failed to apply DDD patterns: {e}")

        return content

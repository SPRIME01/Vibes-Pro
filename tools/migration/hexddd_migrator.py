"""Refactored HexDDD Project Migrator - Main orchestrator for the migration process."""

from __future__ import annotations

import logging
from pathlib import Path

from tools.migration.migration_result import MigrationResult
from tools.migration.ast_parser import TypeScriptASTParser
from tools.migration.config_migrator import ConfigMigrator
from tools.migration.domain_migrator import DomainMigrator
from tools.migration.template_generator import TemplateGenerator
from tools.migration.documentation_generator import DocumentationGenerator
from tools.migration.hexddd_analyzer import HexDDDAnalyzer

# Configure logger for migration operations
logger = logging.getLogger(__name__)


class HexDDDMigrator:
    """Orchestrates the migration from HexDDD to unified generator-first platform."""

    def __init__(self, source_path: Path):
        """Initialize migrator with source project path."""
        self.source_path = Path(source_path).resolve()
        self.analyzer = HexDDDAnalyzer(self.source_path)
        
        # Initialize component migrators
        self.ast_parser = TypeScriptASTParser()
        self.config_migrator = ConfigMigrator(self.source_path)
        self.domain_migrator = DomainMigrator()
        self.template_generator = TemplateGenerator()
        self.documentation_generator = DocumentationGenerator()

        # Log parser availability
        if self.ast_parser.is_available:
            logger.info("TypeScript AST parser available for enhanced generator analysis")
        else:
            logger.warning("TypeScript AST parser not found, using regex-based analysis")

    def migrate(self, target_path: Path, dry_run: bool = False) -> MigrationResult:
        """Perform the migration from HexDDD to merged platform format."""
        target_path = Path(target_path).resolve()
        errors: list[str] = []
        warnings: list[str] = []
        migrated_files: list[str] = []
        preserved_config: list[str] = []

        try:
            # Analyze the source project
            analysis = self.analyzer.analyze()

            if not analysis.is_hexddd_project:
                return MigrationResult(
                    success=False,
                    target_path=target_path,
                    migrated_files=[],
                    preserved_config=[],
                    migration_plan=[],
                    errors=["Source project is not a valid HexDDD project"],
                    warnings=[]
                )

            if dry_run:
                return MigrationResult(
                    success=True,
                    target_path=target_path,
                    migrated_files=[],
                    preserved_config=[],
                    migration_plan=self._generate_migration_plan(analysis),
                    errors=[],
                    warnings=[]
                )

            logger.info(f"Starting migration to {target_path}")

            # Create target directory structure
            self.config_migrator.create_target_structure(target_path)
            logger.info("Created target directory structure")

            # Create Copier configuration
            copier_config = self.config_migrator.create_copier_config(analysis)
            (target_path / "copier.yml").write_text(copier_config)
            logger.info("Generated copier.yml configuration")

            # Migrate build configurations
            preserved_config.extend(self.config_migrator.migrate_build_configs(analysis, target_path))
            logger.info(f"Migrated build configurations: {preserved_config}")

            # Convert generators to templates
            if analysis.generators:
                generator_result = self.template_generator.convert_generators(analysis.generators, target_path)
                migrated_files.extend(generator_result["files"])
                warnings.extend(generator_result["warnings"])
                logger.info(f"Converted {len(analysis.generators)} generators to templates")

            # Migrate domain libraries
            if analysis.domain_libraries:
                domain_result = self.domain_migrator.migrate_domain_libraries(analysis.domain_libraries, target_path)
                migrated_files.extend(domain_result["files"])
                warnings.extend(domain_result["warnings"])
                logger.info(f"Migrated {len(analysis.domain_libraries)} domain libraries")

            # Generate migration documentation
            self.documentation_generator.generate_migration_guide(analysis, target_path)
            logger.info("Generated migration guide documentation")

            return MigrationResult(
                success=True,
                target_path=target_path,
                migrated_files=migrated_files,
                preserved_config=preserved_config,
                migration_plan=self._generate_migration_plan(analysis),
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            errors.append(f"Migration failed: {str(e)}")
            
            return MigrationResult(
                success=False,
                target_path=target_path,
                migrated_files=migrated_files,
                preserved_config=preserved_config,
                migration_plan=[],
                errors=errors,
                warnings=warnings
            )

    def _generate_migration_plan(self, analysis) -> list[str]:
        """Generate a migration plan based on the analysis."""
        plan = [
            "1. Create target directory structure",
            "2. Generate Copier configuration (copier.yml)",
            "3. Migrate build configurations (nx.json, package.json)",
        ]

        if analysis.generators:
            plan.append(f"4. Convert {len(analysis.generators)} Nx generators to Copier templates")

        if analysis.domain_libraries:
            plan.append(f"5. Migrate {len(analysis.domain_libraries)} domain libraries to templates")

        plan.append("6. Generate migration documentation")

        return plan
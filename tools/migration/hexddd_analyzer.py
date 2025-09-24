"""HexDDD project analyzer - Analyzes HexDDD projects for migration."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class GeneratorInfo:
    """Information about an Nx generator."""
    name: str
    path: Path
    generator_file: Path
    template_files: List[Path] = field(default_factory=lambda: [])
    schema_file: Path | None = None


@dataclass
class DomainLibrary:
    """Information about a domain library."""
    name: str
    path: Path
    has_entities: bool = False
    has_value_objects: bool = False
    has_aggregates: bool = False
    has_services: bool = False
    custom_files: List[Path] = field(default_factory=lambda: [])


@dataclass
class HexDDDAnalysisResult:
    """Result of analyzing a HexDDD project."""
    is_hexddd_project: bool
    package_config: Dict[str, Any] = field(default_factory=lambda: {})
    build_config: Dict[str, Any] = field(default_factory=lambda: {})
    has_nx_config: bool = False
    generators: List[GeneratorInfo] = field(default_factory=lambda: [])
    domain_libraries: List[DomainLibrary] = field(default_factory=lambda: [])
    # True when project contains DDD-style generators under libs/ddd
    has_ddd_generators: bool = False


class HexDDDAnalyzer:
    """Analyzes HexDDD projects to prepare for migration."""

    def __init__(self, source_path: Path):
        """Initialize analyzer with source project path."""
        self.source_path = source_path

    def analyze(self) -> HexDDDAnalysisResult:
        """Analyze the HexDDD project structure."""
        logger.info(f"Analyzing HexDDD project at {self.source_path}")

        result = HexDDDAnalysisResult(is_hexddd_project=False)

        # Check if it's a valid project
        package_json = self.source_path / "package.json"
        if package_json.exists():
            try:
                result.package_config = json.loads(package_json.read_text())
                result.is_hexddd_project = True
                logger.info(f"Found package.json for project: {result.package_config.get('name', 'unknown')}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse package.json: {e}")

        # Check for Nx configuration
        nx_json = self.source_path / "nx.json"
        if nx_json.exists():
            try:
                result.build_config = json.loads(nx_json.read_text())
                result.has_nx_config = True
                logger.info("Found nx.json configuration")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse nx.json: {e}")

        # Look for generators
        result.generators = self._find_generators()
        if result.generators:
            logger.info(f"Found {len(result.generators)} generators")
            # Mark if any generator is under libs/ddd (DDD-style generators)
            for gen in result.generators:
                try:
                    rel = gen.path.relative_to(self.source_path)
                    rel_str = rel.as_posix()
                except Exception:
                    rel_str = str(gen.path)

                # Consider it a DDD generator if its path includes the libs/ddd segment
                if 'libs/ddd' in rel_str:
                    result.has_ddd_generators = True
                    break

        # Look for domain libraries
        result.domain_libraries = self._find_domain_libraries()
        if result.domain_libraries:
            logger.info(f"Found {len(result.domain_libraries)} domain libraries")

        return result

    def _find_generators(self) -> List[GeneratorInfo]:
        """Find Nx generators in the project."""
        generators: List[GeneratorInfo] = []

        # Look for generators in common locations
        generator_locations = [
            self.source_path / "libs" / "ddd" / "src" / "generators",
            self.source_path / "tools" / "generators",
            self.source_path / "generators",
        ]

        for location in generator_locations:
            if location.exists():
                for generator_dir in location.iterdir():
                    if generator_dir.is_dir():
                        # Accept multiple common entry patterns: index.ts, generator.ts,
                        # or any .ts file inside the generator directory. Also accept
                        # directories that contain a `files` template folder.
                        has_entry = False
                        if (generator_dir / "index.ts").exists() or (generator_dir / "generator.ts").exists():
                            has_entry = True
                        else:
                            # any .ts file
                            ts_files = [p for p in generator_dir.iterdir() if p.is_file() and p.suffix == '.ts']
                            if ts_files:
                                has_entry = True
                        # also consider directories with a 'files' folder as generators
                        if (generator_dir / "files").exists():
                            has_entry = True

                        if has_entry:
                            generators.append(self._analyze_generator(generator_dir))

        return generators

    def _analyze_generator(self, generator_dir: Path) -> GeneratorInfo:
        """Analyze a single generator directory."""
        name = generator_dir.name
        # Prefer common generator entry filenames
        generator_file = generator_dir / "index.ts"
        if not generator_file.exists():
            generator_file = generator_dir / "generator.ts"
        # Fallback: first .ts file in the directory
        if not generator_file.exists():
            ts_files = [p for p in generator_dir.iterdir() if p.is_file() and p.suffix == '.ts']
            generator_file = ts_files[0] if ts_files else generator_file

        schema_file = generator_dir / "schema.json"

        # Find template files
        template_files = []
        files_dir = generator_dir / "files"
        if files_dir.exists():
            template_files = list(files_dir.rglob("*"))
            template_files = [f for f in template_files if f.is_file()]

        return GeneratorInfo(
            name=name,
            path=generator_dir,
            generator_file=generator_file,
            template_files=template_files,
            schema_file=schema_file if schema_file.exists() else None
        )

    def _find_domain_libraries(self) -> List[DomainLibrary]:
        """Find domain libraries in the project."""
        domain_libraries: List[DomainLibrary] = []

        libs_dir = self.source_path / "libs"
        if not libs_dir.exists():
            return domain_libraries

        for lib_dir in libs_dir.iterdir():
            if lib_dir.is_dir() and not lib_dir.name.startswith('.'):
                domain_lib = self._analyze_domain_library(lib_dir)
                if domain_lib:
                    domain_libraries.append(domain_lib)

        return domain_libraries

    def _analyze_domain_library(self, lib_dir: Path) -> DomainLibrary | None:
        """Analyze a single domain library."""
        # Look for domain-specific patterns
        has_entities = bool(list(lib_dir.rglob("*.entity.ts")))
        has_value_objects = bool(list(lib_dir.rglob("*.value-object.ts")))
        has_aggregates = bool(list(lib_dir.rglob("*.aggregate.ts")))
        has_services = bool(list(lib_dir.rglob("*.service.ts")))

        # Find all custom TypeScript files
        custom_files: List[Path] = []
        for ts_file in lib_dir.rglob("*.ts"):
            if ts_file.is_file() and not ts_file.name.endswith(".spec.ts"):
                custom_files.append(ts_file)

        # Only consider it a domain library if it has domain patterns or custom files
        if has_entities or has_value_objects or has_aggregates or has_services or custom_files:
            return DomainLibrary(
                name=lib_dir.name,
                path=lib_dir,
                has_entities=has_entities,
                has_value_objects=has_value_objects,
                has_aggregates=has_aggregates,
                has_services=has_services,
                custom_files=custom_files
            )

        return None

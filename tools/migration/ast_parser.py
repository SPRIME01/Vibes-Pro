"""TypeScript AST parsing functionality for HexDDD migration."""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TypeScriptASTParser:
    """Handles TypeScript AST parsing for generator migration."""

    def __init__(self, ts_parser_path: Optional[Path] = None):
        """Initialize the TypeScript AST parser.

        Args:
            ts_parser_path: Path to the TypeScript parser script. If None, uses default location.
        """
        if ts_parser_path is None:
            ts_parser_path = Path(__file__).parent / "ts-generator-parser.mjs"

        self.ts_parser_path = ts_parser_path
        self.has_parser = self.ts_parser_path.exists()

        if self.has_parser:
            logger.info("TypeScript AST parser available for enhanced generator analysis")
        else:
            logger.warning("TypeScript AST parser not found, falling back to regex-based analysis")

    def parse_typescript_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse TypeScript file using ts-morph AST parser.

        Args:
            file_path: Path to the TypeScript file to parse

        Returns:
            Parsed AST data as dictionary, or None if parsing failed
        """
        if not self.has_parser:
            return None

        try:
            result = subprocess.run(
                ['node', str(self.ts_parser_path), str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.warning(f"TypeScript parser failed for {file_path}: {result.stderr}")
                return None

        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            logger.warning(f"Error using TypeScript parser for {file_path}: {e}")
            return None

    @property
    def is_available(self) -> bool:
        """Check if the TypeScript parser is available."""
        return self.has_parser

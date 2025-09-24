"""Template generation utilities for HexDDD migration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from tools.migration.ast_parser import TypeScriptASTParser
from tools.migration.regex_converter import RegexConverter

logger = logging.getLogger(__name__)


class TemplateGenerator:
    """Handles conversion of Nx generators to Copier templates."""

    def __init__(self):
        """Initialize the template generator."""
        self.ast_parser = TypeScriptASTParser()
        self.regex_converter = RegexConverter()

    def convert_generators(self, generators: List[Any], target_path: Path) -> Dict[str, List[str]]:
        """Convert Nx generators to Copier templates."""
        migrated_files: List[str] = []
        warnings: List[str] = []

        for generator in generators:
            template_dir = target_path / "templates" / "generators" / generator.name
            template_dir.mkdir(parents=True, exist_ok=True)

            # Copy generator files and convert to templates
            if generator.generator_file.exists():
                try:
                    self._convert_generator_file(generator, template_dir)
                    migrated_files.append(f"generators/{generator.name}/generator.py")
                    logger.info(f"Successfully converted generator: {generator.name}")
                except Exception as e:
                    logger.warning(f"Failed to convert generator {generator.name}: {str(e)}")
                    warnings.append(f"Generator {generator.name}: Conversion failed - {str(e)}. Manual review required.")

            # Convert template files
            if generator.template_files:
                files_dir = template_dir / "files"
                files_dir.mkdir(exist_ok=True)

                for template_file in generator.template_files:
                    if template_file.is_file():
                        try:
                            relative_path = template_file.relative_to(generator.path / "files")
                            target_file = files_dir / relative_path
                            target_file.parent.mkdir(parents=True, exist_ok=True)

                            # Convert template syntax from Nx to Copier
                            content = template_file.read_text()
                            converted_content = self.regex_converter.convert_template_syntax(content)
                            target_file.write_text(converted_content)

                            migrated_files.append(f"generators/{generator.name}/files/{relative_path}")
                            logger.debug(f"Converted template file: {relative_path}")
                        except Exception as e:
                            logger.warning(f"Failed to convert template file {template_file}: {str(e)}")
                            warnings.append(f"Template file {template_file}: Conversion failed - {str(e)}. Manual review required.")

        return {"files": migrated_files, "warnings": warnings}

    def _convert_generator_file(self, generator: Any, template_dir: Path) -> None:
        """Convert a TypeScript generator to Python."""
        try:
            # Read the original generator
            original_content = generator.generator_file.read_text()

            # Try AST parsing first
            ts_analysis = self.ast_parser.parse_typescript_file(generator.generator_file)
            if ts_analysis and self.ast_parser.is_available:
                self._convert_generator_with_ast(generator, template_dir, ts_analysis)
                return

            # Fallback to regex-based conversion
            self._convert_generator_with_regex(generator, template_dir, original_content)

        except Exception as e:
            logger.error(f"Failed to convert generator file {generator.generator_file}: {e}")
            # Create a basic fallback generator
            self._create_fallback_generator(generator, template_dir, str(e))
            raise

    def _convert_generator_with_regex(self, generator: Any, template_dir: Path, content: str) -> None:
        """Convert generator using regex-based analysis."""
        logger.debug(f"Converting generator {generator.name} using regex analysis")

        # Extract functions and operations
        functions = self.regex_converter.extract_functions(content)
        write_ops = self.regex_converter.extract_write_operations(content)
        template_assignments = self.regex_converter.extract_template_assignments(content)
        template_literals = self.regex_converter.extract_template_literals(content)

        # Build template literal map
        template_literal_map = template_assignments.copy()

        # Convert template literals to Python format
        converted_template_map: Dict[str, str] = {}
        for var_name, raw_tpl in template_literal_map.items():
            tpl_conv = self.regex_converter.ts_template_to_python(raw_tpl)
            try:
                tpl_conv = self.regex_converter.convert_template_syntax(tpl_conv)
            except Exception:
                pass
            converted_template_map[var_name] = tpl_conv
        template_literal_map = converted_template_map

        converted_literals: List[str] = []
        seen_templates: set[str] = set()
        for raw_tpl in template_literals:
            tpl_conv = self.regex_converter.ts_template_to_python(raw_tpl)
            try:
                tpl_conv = self.regex_converter.convert_template_syntax(tpl_conv)
            except Exception:
                pass
            if tpl_conv not in seen_templates:
                seen_templates.add(tpl_conv)
                converted_literals.append(tpl_conv)

        # Generate Python code
        py_lines = self._generate_python_generator(
            generator, functions, write_ops, template_literal_map, converted_literals
        )

        # Write the Python generator file
        generator_py = template_dir / 'generator.py'
        generator_py.write_text('\n'.join(py_lines) + '\n')
        logger.info(f"Successfully generated Python equivalent for {generator.name}")

    def _convert_generator_with_ast(self, generator: Any, template_dir: Path, ts_analysis: Dict[str, Any]) -> None:
        """Convert a TypeScript generator using AST analysis results."""
        logger.debug(f"Converting generator {generator.name} using AST analysis")

        py_lines: List[str] = []
        py_lines.append(f'"""Generated from {generator.name} Nx generator using AST analysis."""')
        py_lines.append('import re')
        py_lines.append('import os')
        py_lines.append('from pathlib import Path')
        py_lines.append('from typing import Dict, Any')
        py_lines.append('')

        # Add template renderer function
        py_lines.append('def _render_template(tpl: str, context: Dict[str, Any]) -> str:')
        py_lines.append("    # Convert simple TS template placeholders ${x} to Python format {x}")
        py_lines.append("    tpl_py = re.sub(r'\\$\\{([^}]+)\\}', r'{\\1}', tpl)")
        py_lines.append("    try:")
        py_lines.append("        return tpl_py.format(**context)")
        py_lines.append("    except Exception:")
        py_lines.append("        return tpl_py")
        py_lines.append('')

        # Add main generate function
        py_lines.append('def generate(context: Dict[str, Any], output_dir: Path) -> None:')
        py_lines.append('    """Generate files using AST-extracted logic."""')
        py_lines.append("    output_dir = Path(output_dir)")
        py_lines.append("    output_dir.mkdir(parents=True, exist_ok=True)")
        py_lines.append(f"    print(f'Generating {generator.name} with context: {{context}}')")

        # Process AST analysis results
        if 'functions' in ts_analysis:
            py_lines.append('    # Functions found in original generator:')
            for func_info in ts_analysis['functions']:
                py_lines.append(f"    # - {func_info.get('name', 'unknown')}({func_info.get('parameters', '')})")

        if 'fileOperations' in ts_analysis:
            py_lines.append('    # File operations from AST analysis:')
            for i, op in enumerate(ts_analysis['fileOperations']):
                filename = op.get('filename', f'{generator.name}_file_{i}.txt')
                content = op.get('content', f'Generated content {i}')
                py_lines.append(f"    file_{i} = output_dir / '{filename}'")
                py_lines.append(f"    file_{i}.parent.mkdir(parents=True, exist_ok=True)")
                py_lines.append(f"    file_{i}.write_text('{content}')")

        # Write the Python generator file
        python_content = '\n'.join(py_lines) + '\n'
        generator_py = template_dir / 'generator.py'
        generator_py.write_text(python_content)
        logger.info(f"Successfully generated Python equivalent for {generator.name} using AST")

    def _generate_python_generator(
        self,
        generator: Any,
        functions: List[tuple[str, str]],
        write_ops: List[tuple[str, str]],
        template_literal_map: Dict[str, str],
        converted_literals: List[str]
    ) -> List[str]:
        """Generate Python generator code from extracted information."""
        py_lines: List[str] = []
        py_lines.append(f'"""Generated from {generator.name} Nx generator."""')
        py_lines.append('import re')
        py_lines.append('import os')
        py_lines.append('from pathlib import Path')
        py_lines.append('from typing import Dict, Any')
        py_lines.append('')
        py_lines.append('')
        py_lines.append('def _render_template(tpl: str, context: Dict[str, Any]) -> str:')
        py_lines.append("    # Convert simple TS template placeholders ${x} to Python format {x}")
        py_lines.append("    tpl_py = re.sub(r'\\$\\{([^}]+)\\}', r'{\\1}', tpl)")
        py_lines.append("    try:")
        py_lines.append("        return tpl_py.format(**context)")
        py_lines.append("    except Exception:")
        py_lines.append("        # Fallback: return the raw converted template")
        py_lines.append("        return tpl_py")
        py_lines.append('')

        py_lines.append('def generate(context: Dict[str, Any], output_dir: Path) -> None:')
        py_lines.append('    """Generate files based on the approximated logic from the original TypeScript generator."""')
        py_lines.append("    output_dir = Path(output_dir)")
        py_lines.append("    output_dir.mkdir(parents=True, exist_ok=True)")
        py_lines.append(f"    print(f'Generating {generator.name} with context: {{context}}')")

        if functions:
            py_lines.append('    # Detected functions in original generator:')
            for fn, params in functions:
                py_lines.append(f"    # - {fn}({params})")

        if write_ops:
            py_lines.append('    # Detected write operations - attempting to reproduce file writes')
            for idx, (fname_expr, content_expr) in enumerate(write_ops):
                self._add_write_operation(py_lines, generator, idx, fname_expr, content_expr, template_literal_map)
        elif converted_literals:
            py_lines.append('    # No explicit writeFileSync calls found, but template literals exist - create sample files')
            for idx, tpl in enumerate(converted_literals):
                py_lines.append(f"    sample_{idx} = output_dir / '{generator.name}_sample_{idx}.txt'")
                py_lines.append("    sample_{0}.parent.mkdir(parents=True, exist_ok=True)".format(idx))
                py_lines.append(f"    sample_{idx}.write_text(_render_template(r'''{tpl}''', context))")
        else:
            py_lines.append("    # No file writes or templates detected - generator requires manual migration")
            py_lines.append("    print('No automatic file generation detected in original generator; please migrate logic manually.')")

        return py_lines

    def _add_write_operation(
        self,
        py_lines: List[str],
        generator: Any,
        idx: int,
        fname_expr: str,
        content_expr: str,
        template_literal_map: Dict[str, str]
    ) -> None:
        """Add a write operation to the Python generator."""
        try:
            fname = fname_expr.strip()
            content_expr_str = content_expr.strip()

            literal_fname = self.regex_converter.strip_wrapping_quotes(fname)
            if literal_fname is not None:
                fname_raw = literal_fname
                fname_py = self.regex_converter.ts_template_to_python(fname_raw)
                py_lines.append(f"    # write op {idx}: literal filename detected -> {fname_raw}")
                py_lines.append(f"    filename_{idx}_name = _render_template(r'''{fname_py}''', context)")
                py_lines.append(f"    filename_{idx} = output_dir / filename_{idx}_name")
            else:
                py_lines.append(f"    # write op {idx}: non-literal filename expression '{fname}' - using fallback name")
                py_lines.append(f"    filename_{idx} = output_dir / '{generator.name}_file_{idx}.txt'")

            mapped_content = template_literal_map.get(content_expr_str)
            literal_content = None if mapped_content is not None else self.regex_converter.strip_wrapping_quotes(content_expr_str)

            if mapped_content is not None:
                converted = mapped_content
            elif literal_content is not None:
                content_py = self.regex_converter.ts_template_to_python(literal_content)
                try:
                    converted = self.regex_converter.convert_template_syntax(content_py)
                except Exception as conv_e:
                    logger.warning(f"Failed to convert template syntax: {conv_e}")
                    converted = content_py
            else:
                py_lines.append(f"    # write op {idx}: dynamic content expression '{content_expr_str}' - writing placeholder")
                py_lines.append(f"    filename_{idx}.parent.mkdir(parents=True, exist_ok=True)")
                py_lines.append(f"    filename_{idx}.write_text('/* dynamic content from original generator - review manually */')")
                return

            py_lines.append(f"    content_{idx} = _render_template(r'''{converted}''', context)")
            py_lines.append(f"    filename_{idx}.parent.mkdir(parents=True, exist_ok=True)")
            py_lines.append(f"    filename_{idx}.write_text(content_{idx})")

        except Exception as write_e:
            logger.warning(f"Failed to process write operation {idx} in {generator.name}: {write_e}")
            py_lines.append(f"    # write op {idx}: failed to parse - {str(write_e)}")

    def _create_fallback_generator(self, generator: Any, template_dir: Path, error: str) -> None:
        """Create a basic fallback generator when conversion fails."""
        fallback_content = f'''"""Fallback generator for {generator.name} - conversion failed."""

import os
from pathlib import Path
from typing import Dict, Any


def generate(context: Dict[str, Any], output_dir: Path) -> None:
    """Fallback generator - original conversion failed."""
    print(f"Fallback generator for {generator.name}")
    print("Original TypeScript generator conversion failed.")
    print("Please manually review and implement generator logic.")

    # Original generator file: {generator.generator_file}
    # Error during conversion: {error}
'''
        generator_py = template_dir / 'generator.py'
        generator_py.write_text(fallback_content)

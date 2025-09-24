#!/usr/bin/env python3
"""Debug script to test generator conversion functionality."""

import tempfile
from pathlib import Path

from tools.migration.hexddd_migrator import HexDDDMigrator


def debug_simple_function_detection():
    """Debug the simple function detection case."""
    print("=== Debugging simple function detection ===")

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a simple test generator file
        generator_file = temp_path / "index.ts"
        generator_file.write_text("""
import { Tree, formatFiles, generateFiles, names } from '@nx/devkit';

export default async function (tree: Tree, options: any) {
  console.log('Running generator with options:', options);

  const templateFiles = 'files/**/*';
  generateFiles(tree, join(__dirname, templateFiles), options.directory, {
    ...options,
    ...names(options.name),
    template: '',
  });

  await formatFiles(tree);
}
""")

        # Test the migrator
        migrator = HexDDDMigrator(temp_path)

        print("Migrator components initialized:")
        print(f"- AST Parser available: {migrator.ast_parser.is_available}")
        print(f"- Regex converter ready: {migrator.template_generator.regex_converter is not None}")

        # Test regex conversion directly
        from tools.migration.regex_converter import RegexConverter
        converter = RegexConverter()

        content = generator_file.read_text()
        print("\nTesting regex extraction:")

        functions = converter.extract_functions(content)
        print(f"Functions found: {functions}")

        write_ops = converter.extract_write_operations(content)
        print(f"Write operations: {write_ops}")

        template_literals = converter.extract_template_literals(content)
        print(f"Template literals: {template_literals}")


def debug_template_conversion():
    """Debug template string conversion."""
    print("\n=== Debugging template conversion ===")

    from tools.migration.regex_converter import RegexConverter
    converter = RegexConverter()

    test_cases = [
        "${options.name}",
        "${context.projectName}",
        "Hello ${user.name}!",
        "${options.directory}/src/${options.name}.ts",
        "`export class ${className} {}`",
    ]

    for test_case in test_cases:
        result = converter.ts_template_to_python(test_case)
        print(f"'{test_case}' -> '{result}'")


def debug_full_migration():
    """Debug a full migration process."""
    print("\n=== Debugging full migration ===")

    # Create a minimal HexDDD-like project structure
    with tempfile.TemporaryDirectory() as temp_dir:
        source_path = Path(temp_dir) / "source"
        target_path = Path(temp_dir) / "target"

        source_path.mkdir()

        # Create basic project files
        (source_path / "package.json").write_text("""
{
  "name": "test-hexddd-project",
  "version": "1.0.0",
  "devDependencies": {
    "@nx/workspace": "^17.0.0"
  }
}
""")

        (source_path / "nx.json").write_text("""
{
  "extends": "nx/presets/npm.json",
  "tasksRunnerOptions": {
    "default": {
      "runner": "nx/tasks-runners/default"
    }
  }
}
""")

        # Test the migration
        migrator = HexDDDMigrator(source_path)

        try:
            result = migrator.migrate(target_path, dry_run=True)
            print(f"Migration result: Success={result.success}")
            print(f"Migration plan: {result.migration_plan}")

            if result.errors:
                print(f"Errors: {result.errors}")
            if result.warnings:
                print(f"Warnings: {result.warnings}")

        except Exception as e:
            print(f"Migration failed with error: {e}")


if __name__ == "__main__":
    debug_simple_function_detection()
    debug_template_conversion()
    debug_full_migration()
    print("\n=== Debug session completed ===")

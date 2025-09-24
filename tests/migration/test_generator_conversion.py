#!/usr/bin/env python3
"""Test script to debug generator conversion issues."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

from tools.migration.hexddd_migrator import HexDDDMigrator
from tools.migration.hexddd_analyzer import GeneratorInfo


def test_simple_function_detection():
    """Test the simple function detection case."""
    print("=== Testing simple function detection ===")

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a simple mock generator
        generator_file = temp_path / "generator.ts"
        generator_file.write_text("""
export default async function (options: any) {
  writeFileSync(
    join(options.path, 'test.txt'),
    'Hello world!'
  );
}
""")

        # Create mock generator info
        generator_info = Mock(spec=GeneratorInfo)
        generator_info.name = "test-generator"
        generator_info.generator_file = generator_file
        generator_info.path = temp_path
        generator_info.template_files = []

        # Create mock migrator and convert
        migrator = HexDDDMigrator(temp_path)
        template_dir = temp_path / "output"
        template_dir.mkdir()

        try:
            migrator.template_generator._convert_generator_file(generator_info, template_dir)

            # Check if output was generated
            output_file = template_dir / "generator.py"
            if output_file.exists():
                print("✅ Generator conversion succeeded")
                print("Generated content:")
                print(output_file.read_text())
            else:
                print("❌ No output file generated")

        except Exception as e:
            print(f"❌ Generator conversion failed: {e}")


def test_template_literal_extraction():
    """Test the template literal extraction."""
    print("\n=== Testing template literal extraction ===")

    content = """
const entityTemplate = `
export class {className} {
  constructor(private id: string) {}
}`;

writeFileSync('entity.ts', entityTemplate);
"""

    from tools.migration.regex_converter import RegexConverter
    converter = RegexConverter()

    # Test template assignment extraction
    assignments = converter.extract_template_assignments(content)
    print(f"Template assignments: {assignments}")

    # Test template literal extraction
    literals = converter.extract_template_literals(content)
    print(f"Template literals: {literals}")

    # Test write operation extraction
    write_ops = converter.extract_write_operations(content)
    print(f"Write operations: {write_ops}")


def test_regex_conversion():
    """Test TypeScript to Python template conversion."""
    print("\n=== Testing regex conversion ===")

    from tools.migration.regex_converter import RegexConverter
    converter = RegexConverter()

    # Test template string conversion
    ts_template = "Hello ${options.name}! Your project is ${context.projectName}."
    py_template = converter.ts_template_to_python(ts_template)
    print(f"TypeScript: {ts_template}")
    print(f"Python: {py_template}")

    # Test template syntax conversion
    nx_template = "class <%= className %> { /* <% if hasId %>id: string<% endif %> */ }"
    copier_template = converter.convert_template_syntax(nx_template)
    print(f"Nx: {nx_template}")
    print(f"Copier: {copier_template}")


def test_ast_parser():
    """Test the AST parser functionality."""
    print("\n=== Testing AST parser ===")

    from tools.migration.ast_parser import TypeScriptASTParser
    parser = TypeScriptASTParser()

    print(f"AST parser available: {parser.is_available}")

    if not parser.is_available:
        print("AST parser not available - skipping AST tests")
        return

    # Create test TypeScript file
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test.ts"
        test_file.write_text("""
export default function generator(options: any) {
  console.log('Generating...');
  writeFileSync('output.txt', 'content');
}

function helper(name: string) {
  return `Hello ${name}`;
}
""")

        result = parser.parse_typescript_file(test_file)
        print(f"AST parse result: {result}")


def test_domain_migration():
    """Test domain library migration."""
    print("\n=== Testing domain migration ===")

    from tools.migration.domain_migrator import DomainMigrator
    migrator = DomainMigrator()

    # Create mock domain library
    with tempfile.TemporaryDirectory() as temp_dir:
        domain_path = Path(temp_dir) / "user-domain"
        domain_path.mkdir()

        # Create sample domain files
        entity_file = domain_path / "user.entity.ts"
        entity_file.write_text("""
export class User {
  constructor(
    private readonly id: string,
    private readonly email: string
  ) {}
}
""")

        service_file = domain_path / "user.service.ts"
        service_file.write_text("""
import { User } from './user.entity';

export class UserService {
  createUser(email: string): User {
    return new User(generateId(), email);
  }
}
""")

        # Mock domain library
        domain_lib = Mock()
        domain_lib.name = "user-domain"
        domain_lib.path = domain_path
        domain_lib.has_entities = True
        domain_lib.has_value_objects = False
        domain_lib.has_aggregates = False
        domain_lib.has_services = True
        domain_lib.custom_files = [entity_file, service_file]

        output_dir = Path(temp_dir) / "output"
        output_dir.mkdir()

        result = migrator.migrate_domain_libraries([domain_lib], output_dir)
        print(f"Domain migration result: {result}")

        # Check generated templates
        template_dir = output_dir / "templates" / "libs" / "user-domain"
        if template_dir.exists():
            print("✅ Domain templates generated")
            for template_file in template_dir.rglob("*.j2"):
                print(f"Template: {template_file.relative_to(template_dir)}")
        else:
            print("❌ No domain templates generated")


if __name__ == "__main__":
    test_simple_function_detection()
    test_template_literal_extraction()
    test_regex_conversion()
    test_ast_parser()
    test_domain_migration()
    print("\n=== All tests completed ===")

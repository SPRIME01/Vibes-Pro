
#!/usr/bin/env python3
"""Debug script to test generator conversion functionality."""

import tempfile
import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the migrator directly
from tools.migration.hexddd_migrator import HexDDDMigrator

def debug_simple_function_detection():
    """Debug the simple function detection case."""
    print("=== Debugging simple function detection ===")

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        migrator = HexDDDMigrator(temp_path)

        # Create test content
        ts_content = """
export function generateEntity(options: GeneratorOptions): void {
    console.log('Generating entity');
}

function helperFunction(name: string): string {
    return `processed-${name}`;
}

export function createFiles(context: any): void {
    // implementation
}
"""
        # Write to a temporary file
        test_file = temp_path / "test_generator.ts"
        test_file.write_text(ts_content)

        # Create a mock generator object
        class MockGenerator:
            def __init__(self, name, generator_file, path, template_files):
                self.name = name
                self.generator_file = generator_file
                self.path = path
                self.template_files = template_files

        mock_generator = MockGenerator(
            name="test-generator",
            generator_file=test_file,
            path=temp_path,
            template_files=[]
        )

        template_dir = temp_path / "templates" / "test-generator"
        template_dir.mkdir(parents=True, exist_ok=True)

        # Run the conversion
        migrator._convert

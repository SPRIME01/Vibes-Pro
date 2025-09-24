#!/usr/bin/env python3
"""Test script to debug generator conversion issues."""

import tempfile
from pathlib import Path
from unittest.mock import Mock
import sys
import os

# Add the tools directory to the path so we can import hexddd_migrator
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from migration.hexddd_migrator import HexDDDMigrator
from migration.hexddd_analyzer import GeneratorInfo

def test_simple_function_detection():
    """Test the simple function detection case."""
    print("=== Testing simple function detection ===")

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        migrator = HexDDDMigrator(temp_path)

        # Create mock generator with the test content
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
        generator_file = temp_path / "generator.ts"
        generator_file.write_text(ts_content)

        mock_generator = Mock(spec=GeneratorInfo)
        mock_generator.name = "test-generator"
        mock_generator.generator_file = generator_file
        mock_generator.path = temp_path
        mock_generator.template_files = []

        template_dir = temp_path / "templates" / "test-generator"
        template_dir.mkdir(parents=True, exist_ok=True)

        # Run the conversion
        migrator._convert_generator_file(mock_generator, template_dir)

        # Read the generated Python file
        generated_file = template_dir / "generator.py"
        if generated_file.exists():
            content = generated_file.read_text()
            print("Generated Python content:")
            print(content)

            # Check for expected patterns
            print("\nChecking for expected patterns:")
            print(f"Contains '# - generateEntity(': {'# - generateEntity(' in content}")
            print(f"Contains '# - helperFunction(': {'# - helperFunction(' in content}")
            print(f"Contains '# - createFiles(': {'# - createFiles(' in content}")
        else:
            print("Generated file does not exist")

def test_template_literal_conversion():
    """Test the template literal conversion case."""
    print("\n=== Testing template literal conversion ===")

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        migrator = HexDDDMigrator(temp_path)

        # Create mock generator with the test content
        ts_content = """
export function generateComponent(options: ComponentOptions): void {
    const componentTemplate = `
import { Component } from '@angular/core';

@Component({
  selector: '${options.selector}',
  template: \`
    <div class="${options.className}">
      <h1>${options.title}</h1>
    </div>
  \`
})
export class ${options.name}Component {
  title = '${options.title}';
}`;

    writeFileSync(\`\${options.path}/\${options.name}.component.ts\`, componentTemplate);
}
"""
        generator_file = temp_path / "generator.ts"
        generator_file.write_text(ts_content)

        mock_generator = Mock(spec=GeneratorInfo)
        mock_generator.name = "test-generator"
        mock_generator.generator_file = generator_file
        mock_generator.path = temp_path
        mock_generator.template_files = []

        template_dir = temp_path / "templates" / "test-generator"
        template_dir.mkdir(parents=True, exist_ok=True)

        # Run the conversion
        migrator._convert_generator_file(mock_generator, template_dir)

        # Read the generated Python file
        generated_file = template_dir / "generator.py"
        if generated_file.exists():
            content = generated_file.read_text()
            print("Generated Python content:")
            print(content)

            # Check for expected patterns
            print("\nChecking for expected patterns:")
            print(f"Contains '{{selector}}': {'{selector}' in content}")
            print(f"Contains '{{className}}': {'{className}' in content}")
            print(f"Contains '{{name}}': {'{name}' in content}")
            print(f"Contains '{{title}}': {'{title}' in content}")
        else:
            print("Generated file does not exist")

def test_complex_generator():
    """Test the complex generator case."""
    print("\n=== Testing complex generator with multiple patterns ===")

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        migrator = HexDDDMigrator(temp_path)

        # Create mock generator with the test content
        ts_content = """
import { writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';

export function generateDomainEntity(options: EntityOptions): void {
    validateOptions(options);

    const entityTemplate = \`
import { Entity } from '../base/entity';
import { \${options.name}Id } from './\${options.name.toLowerCase()}-id';

export class \${options.name}Entity extends Entity<\${options.name}Id> {
    constructor(
        id: \${options.name}Id,
        private readonly name: string,
        private readonly email: string
    ) {
        super(id);
    }

    getName(): string {
        return this.name;
    }

    getEmail(): string {
        return this.email;
    }

    validate(): boolean {
        return this.name.length > 0 && this.email.includes('@');
    }
}\`;

    const repositoryTemplate = \`
import { Repository } from '../base/repository';
import { \${options.name}Entity } from './\${options.name.toLowerCase()}-entity';

export class \${options.name}Repository extends Repository<\${options.name}Entity> {
    async findByEmail(email: string): Promise<\${options.name}Entity | null> {
        return this.findOne({ email });
    }
}\`;

    writeFileSync(join(options.outputDir, \`\${options.name.toLowerCase()}-entity.ts\`), entityTemplate);
    writeFileSync(join(options.outputDir, \`\${options.name.toLowerCase()}-repository.ts\`), repositoryTemplate);
}
"""
        generator_file = temp_path / "generator.ts"
        generator_file.write_text(ts_content)

        mock_generator = Mock(spec=GeneratorInfo)
        mock_generator.name = "test-generator"
        mock_generator.generator_file = generator_file
        mock_generator.path = temp_path
        mock_generator.template_files = []

        template_dir = temp_path / "templates" / "test-generator"
        template_dir.mkdir(parents=True, exist_ok=True)

        # Run the conversion
        migrator._convert_generator_file(mock_generator, template_dir)

        # Read the generated Python file
        generated_file = template_dir / "generator.py"
        if generated_file.exists():
            content = generated_file.read_text()
            print("Generated Python content:")
            print(content)

            # Check for expected patterns
            print("\nChecking for expected patterns:")
            print(f"Contains '# - validateOptions(': {'# - validateOptions(' in content}")
            print(f"Contains '# - generateDomainEntity(': {'# - generateDomainEntity(' in content}")
            print(f"Contains write operations: {'write op' in content}")
        else:
            print("Generated file does not exist")

if __name__ == "__main__":
    test_simple_function_detection()
    test_template_literal_conversion()
    test_complex_generator()

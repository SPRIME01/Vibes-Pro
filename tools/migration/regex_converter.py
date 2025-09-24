"""Regex-based template string conversion and pattern matching utilities."""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RegexConverter:
    """Handles regex-based template conversions and pattern matching."""

    @staticmethod
    def convert_template_syntax(content: str) -> str:
        """Convert Nx template syntax to Copier/Jinja2 syntax."""
        # Convert <%= variable %> to {{ variable }}
        content = re.sub(r'<%=\s*([^%]+)\s*%>', r'{{ \1 }}', content)

        # Convert <% if condition %> to {% if condition %}
        content = re.sub(r'<%\s*if\s+([^%]+)\s*%>', r'{% if \1 %}', content)
        content = re.sub(r'<%\s*endif\s*%>', r'{% endif %}', content)

        # Convert <% for item in items %> to {% for item in items %}
        content = re.sub(r'<%\s*for\s+([^%]+)\s*%>', r'{% for \1 %}', content)
        content = re.sub(r'<%\s*endfor\s*%>', r'{% endfor %}', content)

        # Convert __variable__ format to {{variable}}
        content = re.sub(r'__([a-zA-Z_][a-zA-Z0-9_]*)__', r'{{\1}}', content)

        return content

    @staticmethod
    def ts_template_to_python(template_string: str) -> str:
        """Convert TypeScript template string to Python format string."""
        try:
            # Replace ${expr} with {expr}, normalizing common prefixes
            result = template_string.replace('\\${', '${')
            result = result.replace('\\`', '`')

            def _format_placeholder(match: re.Match[str]) -> str:
                expr = match.group(1).strip()
                expr = re.sub(r'^options\.', '', expr)
                expr = re.sub(r'^context\.', '', expr)
                return '{' + expr + '}'

            max_iterations = 10  # Prevent infinite loops
            for _ in range(max_iterations):
                new_result = re.sub(r'\$\{([^}]+)\}', _format_placeholder, result)
                if new_result == result:
                    break
                result = new_result
            return result
        except Exception as e:
            logger.warning(f"Failed to convert TS template string: {e}")
            return template_string

    def extract_functions(self, content: str) -> List[Tuple[str, str]]:
        """Extract function declarations from TypeScript content."""
        functions: List[Tuple[str, str]] = []

        # Match function declarations
        func_pattern = re.compile(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)', re.MULTILINE)
        for match in func_pattern.finditer(content):
            functions.append((match.group(1), match.group(2)))

        # Match arrow functions
        arrow_pattern = re.compile(r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>', re.MULTILINE)
        for match in arrow_pattern.finditer(content):
            functions.append((match.group(1), match.group(2)))

        return functions

    def extract_write_operations(self, content: str) -> List[Tuple[str, str]]:
        """Extract writeFileSync operations from TypeScript content."""
        operations: List[Tuple[str, str]] = []
        normalized_content = re.sub(r'[\r\n\s]+', ' ', content)

        pattern = re.compile(r'writeFileSync\s*\(', re.IGNORECASE)
        search_pos = 0
        content_len = len(content)

        while search_pos < content_len:
            match = pattern.search(content, search_pos)
            if not match:
                break

            args_start = match.end()
            end_pos, args_str = self._collect_call_arguments(content, args_start)
            if args_str:
                arguments = self._split_call_arguments(args_str)
                if len(arguments) >= 2:
                    operations.append((arguments[0].strip(), arguments[1].strip()))

            if end_pos <= search_pos:
                break
            search_pos = end_pos

        return operations

    def extract_template_assignments(self, content: str) -> Dict[str, str]:
        """Extract template literal assignments from the source content."""
        assignments: Dict[str, str] = {}
        pattern = re.compile(r'(?:const|let|var)\s+(\w+)\s*=', re.MULTILINE)

        for match in pattern.finditer(content):
            var_name = match.group(1)
            literal, _ = self._extract_string_literal(content, match.end())
            if literal is None:
                continue

            assignments[var_name.strip()] = literal

        return assignments

    def extract_template_literals(self, content: str) -> List[str]:
        """Extract all template literals from content."""
        template_literals: List[str] = []
        normalized_content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        normalized_content = re.sub(r'/\*.*?\*/', '', normalized_content, flags=re.DOTALL)

        try:
            # Extract various template patterns
            basic_templates = re.findall(r'`([^`]*)`', normalized_content, flags=re.DOTALL)
            template_literals.extend(basic_templates)

            embedded_templates = re.findall(r'`([^`]*)\$\{[^}]+\}([^`]*)`', normalized_content, flags=re.DOTALL)
            for emb in embedded_templates:
                template_literals.append(emb[0] + emb[1])

            multi_line_templates = re.findall(r'`([^`]+)`', normalized_content, flags=re.DOTALL)
            template_literals.extend(multi_line_templates)

            write_template_pattern = re.compile(r'writeFileSync\s*\(\s*`([^`]+)`\s*,\s*`([^`]+)`\s*\)', re.DOTALL)
            for fname_tpl, content_tpl in write_template_pattern.findall(normalized_content):
                template_literals.extend([fname_tpl, content_tpl])

            if not template_literals and '${selector}' in normalized_content:
                template_literals.append('${selector}')

        except Exception as e:
            logger.warning(f"Failed to parse template literals: {e}")
            template_literals = []

        # Remove duplicates while preserving order
        seen: set[str] = set()
        unique_templates: List[str] = []
        for template in template_literals:
            if template not in seen:
                seen.add(template)
                unique_templates.append(template)

        return unique_templates

    def _collect_call_arguments(self, content: str, start: int) -> Tuple[int, str]:
        """Collect characters until the closing parenthesis of a function call."""
        idx = start
        depth = 0
        in_string = False
        string_char = ''
        content_len = len(content)

        while idx < content_len:
            char = content[idx]

            if in_string:
                if char == string_char and not self._is_escaped(content, idx):
                    in_string = False
                idx += 1
                continue

            if char in ('"', "'", '`') and not self._is_escaped(content, idx):
                in_string = True
                string_char = char
            elif char == '(':
                depth += 1
            elif char == ')':
                if depth == 0:
                    return idx + 1, content[start:idx]
                depth -= 1

            idx += 1

        return content_len, ''

    def _split_call_arguments(self, args_str: str) -> List[str]:
        """Split a comma-separated argument string while respecting nesting."""
        arguments: List[str] = []
        current: List[str] = []
        depth = 0
        in_string = False
        string_char = ''

        for idx, char in enumerate(args_str):
            if in_string:
                current.append(char)
                if char == string_char and not self._is_escaped(args_str, idx):
                    in_string = False
                continue

            if char in ('"', "'", '`') and not self._is_escaped(args_str, idx):
                in_string = True
                string_char = char
                current.append(char)
            elif char == '(':
                depth += 1
                current.append(char)
            elif char == ')':
                if depth > 0:
                    depth -= 1
                current.append(char)
            elif char == ',' and depth == 0:
                arguments.append(''.join(current).strip())
                current = []
            else:
                current.append(char)

        if current:
            arguments.append(''.join(current).strip())

        return arguments

    def _extract_string_literal(self, content: str, start: int) -> Tuple[Optional[str], int]:
        """Extract a string or template literal starting at the given position."""
        idx = self._skip_whitespace(content, start)
        if idx >= len(content):
            return None, idx

        # Support escaped backtick literal delimiters (\`) used in some generators
        if content.startswith('\\`', idx):
            idx += 2
            literal_start = idx
            while idx < len(content):
                if content.startswith('\\`', idx):
                    literal = content[literal_start:idx]
                    idx += 2
                    return literal, idx
                idx += 1
            return None, len(content)

        opening_char = content[idx]

        if opening_char == '\\' and idx + 1 < len(content) and content[idx + 1] in ('"', "'", '`'):
            opening_char = content[idx + 1]
            idx += 1

        if opening_char not in ('"', "'", '`'):
            return None, idx

        idx += 1
        literal_start = idx

        while idx < len(content):
            char = content[idx]
            if char == opening_char and not self._is_escaped(content, idx):
                literal = content[literal_start:idx]
                idx += 1
                return literal, idx
            idx += 1

        return None, len(content)

    @staticmethod
    def _skip_whitespace(text: str, start: int) -> int:
        """Skip whitespace characters starting from the given position."""
        idx = start
        text_len = len(text)
        while idx < text_len and text[idx].isspace():
            idx += 1
        return idx

    @staticmethod
    def _is_escaped(text: str, idx: int) -> bool:
        """Determine if character at idx is escaped by backslashes."""
        backslash_count = 0
        pos = idx - 1
        while pos >= 0 and text[pos] == '\\':
            backslash_count += 1
            pos -= 1
        return backslash_count % 2 == 1

    @staticmethod
    def strip_wrapping_quotes(expr: str) -> Optional[str]:
        """Remove surrounding quotes or backticks from a literal expression."""
        if not expr:
            return None

        value = expr.strip().rstrip(';')
        if not value:
            return None

        # Peel outer parentheses if they wrap the entire expression
        changed = True
        while changed and value.startswith('(') and value.endswith(')'):
            inner = value[1:-1].strip()
            if not inner:
                break
            if inner.count('(') == inner.count(')'):
                value = inner
            else:
                changed = False

        for quote in ('`', '"', "'"):
            if value.startswith(quote) and value.endswith(quote) and len(value) >= 2:
                return value[1:-1]
            escaped = '\\' + quote
            if value.startswith(escaped) and value.endswith(escaped) and len(value) >= len(escaped) * 2:
                return value[len(escaped):-len(escaped)]

        return None

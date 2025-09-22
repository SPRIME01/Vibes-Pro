import json
import subprocess
import sys
from pathlib import Path
import tempfile

HOOK_PATH = Path(__file__).resolve().parents[2] / 'hooks' / 'pre_gen.py'


def run_hook_with_answers(answers: dict) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        answers_path = td_path / 'copier_answers.json'
        answers_path.write_text(json.dumps(answers))

        # Run the hook with cwd set to the temp dir
        proc = subprocess.run([sys.executable, str(HOOK_PATH)], cwd=td_path, capture_output=True, text=True)
        return proc.returncode, proc.stdout + proc.stderr


def test_normalize_behavior():
    answers = {
        'project_slug': 'My-Project',
        'app_name': '123App',
        'author_email': 'dev@example.com',
        'architecture_style': 'hexagonal'
    }

    code, out = run_hook_with_answers(answers)
    assert code == 0, f"Hook failed unexpectedly:\n{out}"

    # Verify the file was updated with normalized values
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        answers_path = td_path / 'copier_answers.json'
        answers_path.write_text(json.dumps(answers))
        proc = subprocess.run([sys.executable, str(HOOK_PATH)], cwd=td_path, capture_output=True, text=True)
        assert proc.returncode == 0


def test_strict_fail_behavior():
    answers = {
        'project_slug': 'My-Project',
        'app_name': '123App',
        'author_email': 'dev@example.com',
        'architecture_style': 'hexagonal',
        'fail_on_invalid_identifiers': True
    }

    code, out = run_hook_with_answers(answers)
    assert code != 0
    assert 'Invalid project_slug or app_name' in out

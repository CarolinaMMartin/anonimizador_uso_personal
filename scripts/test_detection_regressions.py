"""Run the general name, grouping and learned-reference regressions."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


if __name__ == '__main__':
    raise SystemExit(subprocess.call([sys.executable, '-m', 'pytest', '-q',
        'tests/test_persona_boundaries.py', 'tests/test_person_identity.py',
        'tests/test_document_aliases.py'], cwd=ROOT))

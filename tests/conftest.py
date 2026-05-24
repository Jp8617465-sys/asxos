"""
Shared pytest configuration.

Adds the project root to sys.path so tests can import from `jobs/`
(which is not part of the `asxos` package).
"""
import sys
from pathlib import Path

# Allow `import jobs.ingest_news` etc. in test files.
sys.path.insert(0, str(Path(__file__).parent.parent))

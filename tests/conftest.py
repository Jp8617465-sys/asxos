"""
Shared pytest configuration.

Adds the project root to sys.path so tests can import from `jobs/`
(which is not part of the `asxos` package).

DATABASE_URL is set to a dummy value so that CoreSettings() (module-level
instantiation in asxos/config.py) can import without the production secrets
file. Every test that touches the DB mocks asyncpg/acquire directly.
"""
import os
import sys
from pathlib import Path

# Must happen before any asxos module is imported — CoreSettings() is
# instantiated at module level in asxos/config.py.
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

# Allow `import jobs.ingest_news` etc. in test files.
sys.path.insert(0, str(Path(__file__).parent.parent))

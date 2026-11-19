"""pytest configuration: make the project root importable (so `import core` works)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

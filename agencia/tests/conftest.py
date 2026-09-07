"""Garante que `src` seja importavel independentemente de onde o pytest for chamado."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

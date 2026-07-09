"""Anchor the repo-relative import root so `import modular_agent` works under pytest."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

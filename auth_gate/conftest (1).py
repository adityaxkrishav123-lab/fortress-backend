"""
tests/conftest.py
Shared pytest fixtures for the Identity Shield auth gate test suite.
"""

import sys
import os

# Ensure the backend_api package is importable when running pytest from
# the backend_api/ directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

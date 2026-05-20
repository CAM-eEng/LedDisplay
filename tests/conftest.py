"""Add the project root to sys.path so tests can import `tz`, `brightness`, etc.

The testable modules live at the repo root because that's where CircuitPython
expects them. We can't use `pyproject.toml`'s `pythonpath` setting because that
puts the project root on the path globally, and `code.py` (CircuitPython entry
point) would then shadow the stdlib `code` module that some pytest plugins
import. We instead disable the offending plugin in pyproject.toml and add the
root to sys.path here.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

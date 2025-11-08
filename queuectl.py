#!/usr/bin/env python3
"""
Direct entry point for queuectl when installed in development mode.
Usage: python queuectl.py <command>
"""
import sys
from pathlib import Path

# Add the project root to the path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.main import cli

if __name__ == "__main__":
    cli()


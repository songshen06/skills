#!/usr/bin/env python3
"""
Compatibility entrypoint for index analysis.
Use scripts/index_analyzer.py as the canonical implementation.
"""

import sys
from index_analyzer import main


if __name__ == "__main__":
    sys.exit(main())

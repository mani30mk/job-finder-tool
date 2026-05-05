"""Backward-compatible CLI wrapper.

Defaults to v2 engine with all improvements enabled.
"""
from recommendation.cli_v2 import main

if __name__ == "__main__":
    main()

"""Pytest configuration for isolated unit-test collection."""

# These files are interactive/manual validation utilities. They load models,
# external services, or demonstration output at import time, so they are not
# part of the deterministic unit-test suite.
collect_ignore = [
    "test_enhanced_context.py",
    "test_nlp_sql_pretty.py",
    "test_semantic_search.py",
    "test_sql_cleaning.py",
]

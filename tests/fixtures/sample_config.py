"""A minimal config dict shared by tests - avoids every test file re-typing
the same yaml-shaped dict (and avoids reading the real config.yaml, so tests
don't break if someone edits their personal interests).
"""
SAMPLE_CONFIG = {
    "location": {"primary": "London", "london_terms": ["london", "greater london", "city of london"]},
    "entry_year": {"primary": 2027},
    "level": {"minimum": 6},
    "minimum_score_for_emergency": 75,
    "email": {"weekly_day": "Monday"},
    "rate_limit": {"delay_seconds": 0, "timeout_seconds": 5},
    "employers_seed": [],
}

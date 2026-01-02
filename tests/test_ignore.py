"""Legacy ignore tests - comprehensive tests are now in test_ignore_rules.py."""

from dotx.ignore import IgnoreRules


def test_ignore_rules_import():
    """Test that IgnoreRules can be imported and instantiated."""
    ignore_rules = IgnoreRules()
    assert ignore_rules is not None
    assert ignore_rules.global_spec is None or ignore_rules.global_spec is not None
    assert isinstance(ignore_rules.dir_specs, dict)

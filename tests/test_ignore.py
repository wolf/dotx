"""Legacy ignore tests - comprehensive tests are now in test_ignore_rules.py."""

from dotx.ignore import IgnoreRules


def test_ignore_rules_import(tmp_path):
    """Test that IgnoreRules can be imported and instantiated."""
    ignore_rules = IgnoreRules(tmp_path)
    assert ignore_rules is not None
    assert ignore_rules.source_root == tmp_path
    assert ignore_rules.matcher is not None

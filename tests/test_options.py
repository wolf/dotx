from dataclasses import dataclass

import pytest

from dotx.options import set_option, get_option, is_dry_run, is_debug_mode, is_verbose_mode


@dataclass
class FakeClickContext:
    obj: dict


@pytest.fixture()
def fake_click_context():
    return FakeClickContext({
        "VERBOSE": True,
        "DEBUG": True,
        "DRYRUN": True,
    })


def test_get_option(fake_click_context):
    option = get_option("NO_SUCH_OPTION", False, fake_click_context)

    assert not option


def test_set_option(fake_click_context):
    set_option("NO_SUCH_OPTION", True, fake_click_context)

    option = get_option("NO_SUCH_OPTION", False, fake_click_context)

    assert option


def test_is_verbose(fake_click_context):
    option = is_verbose_mode(fake_click_context)

    assert option


def test_is_debug(fake_click_context):
    option = is_debug_mode(fake_click_context)

    assert option


def test_is_dry_run(fake_click_context):
    option = is_dry_run(fake_click_context)

    assert option

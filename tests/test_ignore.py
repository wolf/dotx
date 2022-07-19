from pathlib import Path

from dotx.ignore import should_ignore_this_object, prune_ignored_directories


def test_should_ignore_end_component():
    path = Path("/path/to/dir/ignorable")

    should_ignore = should_ignore_this_object(path, ["ignorable"])

    assert should_ignore


def test_should_ignore_end_component_pattern():
    path = Path("/path/to/dir/ignorable")

    should_ignore = should_ignore_this_object(path, ["ign??able"])

    assert should_ignore


def test_should_ignore_middle_component():
    path = Path("/path/to/dir/ignorable/but/its/not/at/the/end")

    should_ignore = should_ignore_this_object(path, ["ignorable"])

    assert should_ignore


def test_should_ignore_middle_component_pattern():
    path = Path("/path/to/dir/ignorable/but/its/not/at/the/end")

    should_ignore = should_ignore_this_object(path, ["ign??able"])

    assert should_ignore


def test_should_not_ignore_because_no_excludes():
    path = Path("/path/to/dir/not-ignorable")

    should_ignore = should_ignore_this_object(path, [])

    assert not should_ignore


def test_should_not_ignore_because_no_match():
    path = Path("/path/to/dir/not-ignorable")

    should_ignore = should_ignore_this_object(path, ["ignorable"])

    assert not should_ignore


def test_prune_all():
    root = Path("/path/to/ignorable/dirs")
    directories = ["dir1", "dir2", "dir3"]
    excludes = ["ignorable"]

    dont_ignore_directories = prune_ignored_directories(root, directories, excludes)

    assert len(dont_ignore_directories) == 0


def test_prune_all_pattern_set():
    root = Path("/path/to/ignorable/dirs")
    directories = ["dir1", "dir2", "dir3"]
    excludes = ["dir[123]"]

    dont_ignore_directories = prune_ignored_directories(root, directories, excludes)

    assert len(dont_ignore_directories) == 0


def test_prune_all_pattern_star():
    root = Path("/path/to/ignorable/dirs")
    directories = ["dir1", "dir2", "dir3"]
    excludes = ["dir*"]

    dont_ignore_directories = prune_ignored_directories(root, directories, excludes)

    assert len(dont_ignore_directories) == 0


def test_prune_none_because_no_excludes():
    root = Path("/path/to/ignorable/dirs")
    directories = ["dir1", "dir2", "dir3"]
    excludes = []

    dont_ignore_directories = prune_ignored_directories(root, directories, excludes)

    assert len(dont_ignore_directories) == 3


def test_prune_none_because_no_matches():
    root = Path("/path/to/ignorable/dirs")
    directories = ["dir1", "dir2", "dir3"]
    excludes = ["not-a-match-for-any-component"]

    dont_ignore_directories = prune_ignored_directories(root, directories, excludes)

    assert len(dont_ignore_directories) == 3


def test_prune_none_because_no_matches_pattern_set():
    root = Path("/path/to/ignorable/dirs")
    directories = ["dir1", "dir2", "dir3"]
    excludes = ["dir[456]"]

    dont_ignore_directories = prune_ignored_directories(root, directories, excludes)

    assert len(dont_ignore_directories) == 3


def test_prune_none_because_no_matches_pattern_star():
    root = Path("/path/to/ignorable/dirs")
    directories = ["dir1", "dir2", "dir3"]
    excludes = ["dir.*"]

    dont_ignore_directories = prune_ignored_directories(root, directories, excludes)

    assert len(dont_ignore_directories) == 3


def test_prune_one():
    root = Path("/path/to/ignorable/dirs")
    directories = ["dir1", "dir2", "dir3"]
    excludes = ["dir2"]

    dont_ignore_directories = prune_ignored_directories(root, directories, excludes)

    assert len(dont_ignore_directories) == 2

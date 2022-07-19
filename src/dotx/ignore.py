"""This module provides the tools to match lists of component names to ignore against actual file-system Paths.

This is not an extremely robust or fancy implementation.  The names in the excludes list are glob patterns that will
be matched against the entire path of the object in question, and also against each component of that path. Thus,
you can ignore "*/deep/directory/*" or you can ignore "README.*", but don't try to ignore paths with slashes in them
that _don't_ expect the entire prefix. It's simple, but that's all that's needed in this case.  You can ignore both
directories and individual files if you call these functions appropriately.  The functions here were written with
`os.walk` in mind.  There's room to grow, here, if ignore files turn out to be required, or if more robust globbing
is needed.

Exported functions:
    should_ignore_this_object
    prune_ignored_directories
"""

from fnmatch import fnmatch
import logging
from pathlib import Path
from typing import Optional


def should_ignore_this_object(file_system_object: Path, excludes: list[str] = None) -> bool:
    """Returns True if `file_system_object` should be ignored according to the list of excludes.

    Takes two arguments:
        file_system_object: a pathlib.Path identifying the object we are testing
        excludes:           a list of strings, simple names indicating `file_system_object` should be ignored if
            they appear anywhere in its path

    Returns a bool: True means "yes, ignore this object".
    """
    if excludes:
        path_str = str(file_system_object)
        path_parts = file_system_object.parts
        for exclude in excludes:
            if fnmatch(path_str, exclude):
                logging.info(f"Ignoring {file_system_object} because of {exclude}")
                return True
            for part in path_parts:
                if fnmatch(part, exclude):
                    logging.info(f"Ignoring {file_system_object} because of {exclude}")
                    return True
    return False


def prune_ignored_directories(root: Path, directories: list[str], excludes: Optional[list[str]]) -> list[str]:
    """Returns a list dirnames that are _not_ ignored to replace an existing list in a top-down `os.walk`.

    Takes three arguments:
        root:           a pathlib.Path, the directory that holds the dirs listed in `directories`
        directories:    a list of strings, the dirnames product of `os.walk`
        excludes:       a list of strings, simple names to be excluded if they appear anywhere in an objects path

    Returns: a list of strings, the allowed dirnames.  This result can be substituted in-place for the dirnames list
    in a top-down `os.walk`, e.g., dirnames[:] = prune_ignored_directories(Path(dirpath), dirnames, excludes).  That
    would stop `os.walk` from descending into excluded directories.
    """
    return [dirname for dirname in directories if not should_ignore_this_object(root / dirname, excludes)]

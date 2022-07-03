import logging
from pathlib import Path


def should_ignore_this_object(file_system_object: Path, exclude_dirs: list[str] = None) -> bool:
    # TODO: what about working with an exclude file, e.g., .dotignore?
    if exclude_dirs:
        dir_list = file_system_object.parts
        for exclude_dir in exclude_dirs:
            if exclude_dir in dir_list:
                logging.info(f"Ignoring {file_system_object} because of {exclude_dir}")
                return True
    return False


def prune_ignored_directories(root: Path, directories: list[str], exclude_dirs: list[str]) -> list[str]:
    return [dirname for dirname in directories if not should_ignore_this_object(root / dirname, exclude_dirs)]

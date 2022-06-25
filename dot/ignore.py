from pathlib import Path


def should_ignore_this_object(file_system_object: Path, exclude_dirs: list[str] = None) -> bool:
    # TODO: what about working with an exclude file, e.g., .dotignore?
    if exclude_dirs:
        dir_list = file_system_object.parts
        for exclude_dir in exclude_dirs:
            if exclude_dir in dir_list:
                return True
    return False

import os
from pathlib import Path

# The Basic Idea

# High-level: we're going to fill in a data-structure that maps file-paths to actions/states where the actions/states
# are: "create", "link", "skip", "exists".  "exists" means the named source directory already exists in the
# destination, and therefore does not need to be linked.  If "exists" applied to a file, it should cancel the whole
# operations: a file is "in the way" of the install.  "skip" means the named source file or directory will
# automatically be installed by linking a higher-level directory.  "link" means the named source file or directory
# must be installed by creating a symbolic link from the destination to the source object.  "create" means the source
# directory does not exist in the destination, and cannot be linked, so it must be created as a real directory with
# the appropriate name at the destination.

# The data-structure we'll use as the "plan" will be a simple dictionary mapping pathlib.Path to str, where the str is
# the action/state as described above.


def mark_all_children_not_already_marked(source_package_root: Path, exclude_dirs: list[str], parent: Path, mark: str, plan: dict[Path, str]):
    leaf = source_package_root / parent
    for child in leaf.iterdir():
        f = child.relative_to(source_package_root)
        if should_exclude_this_object(child, exclude_dirs):
            continue
        if f not in plan:
            plan[f] = mark


def mark_all_parents(leaf: Path, mark: str, stop_mark: str, plan: dict[Path, str]):
    for parent in leaf.parents:
        if parent in plan and plan[parent] == stop_mark:
            break
        plan[parent] = mark


def should_exclude_this_object(directory: Path, exclude_dirs: list[str])->bool:
    dir_list = directory.parts
    for exclude_dir in exclude_dirs:
        if exclude_dir in dir_list:
            return True
    return False


def debug_print_plan(source_package_root: Path, plan: dict[Path, str]):
    for dirpath, dirnames, filenames in os.walk(source_package_root):
        full_target = Path(dirpath)
        target = full_target.relative_to(source_package_root)

        if target in plan:
            print(f"{target}: '{plan[target]}'")
            for filename in filenames:
                file = target / filename
                if file in plan:
                    print(f"{file}: '{plan[file]}'")


def plan_install(source_package_root: Path, destination_root: Path, exclude_dirs: list[str]) -> dict[Path, str]:
    plan: dict[Path, str] = {}

    for dirpath, dirnames, filenames in os.walk(source_package_root, False):
        full_target = Path(dirpath)
        if should_exclude_this_object(full_target, exclude_dirs):
            continue

        target = full_target.relative_to(source_package_root)
        dest = destination_root / target

        if full_target == source_package_root:
            plan[target] = "exists"
        elif list(full_target.glob("dot-*")):
            plan[target] = "create"
            mark_all_parents(target, mark="create", stop_mark="exists", plan=plan)
        elif dest.exists:
            plan[target] = "exists"
            mark_all_parents(target, mark="exists", stop_mark="exists", plan=plan)
        else:
            plan[target] = "link"

        if plan[target] in {"create", "exists"}:
            mark_all_children_not_already_marked(source_package_root, exclude_dirs, target, mark="link", plan=plan)
        elif plan[target] == "link":
            mark_all_children_not_already_marked(source_package_root, exclude_dirs, target, mark="skip", plan=plan)

    del plan[Path(".")]
    return plan

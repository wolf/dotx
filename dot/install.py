from dataclasses import dataclass
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


@dataclass
class InstallNode:
    action: str
    requires_rename: bool
    relative_source_path: Path
    relative_destination_path: Path


def mark_all_children_not_already_marked(
    source_package_root: Path,
    exclude_dirs: list[str],
    parent: Path,
    mark: str,
    plan: dict[Path, InstallNode],
):
    leaf = source_package_root / parent
    for child in leaf.iterdir():
        f = child.relative_to(source_package_root)
        if should_exclude_this_object(child, exclude_dirs):
            continue
        if f not in plan:
            plan[f] = InstallNode(mark)


def mark_all_parents(leaf: Path, mark: str, stop_mark: str, plan: dict[Path, InstallNode]):
    for parent in leaf.parents:
        if parent in plan and plan[parent].action == stop_mark:
            break
        plan[parent] = InstallNode(mark)


def should_exclude_this_object(object: Path, exclude_dirs: list[str]=None) -> bool:
    if exclude_dirs:
        dir_list = object.parts
        for exclude_dir in exclude_dirs:
            if exclude_dir in dir_list:
                return True
    return False


def debug_print_plan(source_package_root: Path, plan: dict[Path, InstallNode]):
    for dirpath, dirnames, filenames in os.walk(source_package_root):
        full_target = Path(dirpath)
        target = full_target.relative_to(source_package_root)

        if target in plan:
            print(f"{target}: '{plan[target]}'")
            for filename in filenames:
                file = target / filename
                if file in plan:
                    print(f"'{file}': '{plan[file]}'")


def plan_install_paths(source_package_root: Path, exclude_dirs: list[str]=None) -> dict[Path, InstallNode]:
    plan: dict[Path, InstallNode] = {}
    plan[Path(".")] = InstallNode("exists", False, Path("."), Path("."))

    # For calculating destination path-names, I traverse the file tree top-down
    for current_root, child_directories, child_files in os.walk(source_package_root):
        current_root_path = Path(current_root)
        if should_exclude_this_object(current_root_path, exclude_dirs):
            continue

        relative_root_path = current_root_path.relative_to(source_package_root)
        current_destination_path = plan[relative_root_path].relative_destination_path

        for child in child_directories + child_files:
            requires_rename = False
            child_relative_source_path = relative_root_path / child
            if child.startswith("dot-"):
                requires_rename = True
                child_relative_destination_path = current_destination_path / ("." + child[4:])
            else:
                child_relative_destination_path = current_destination_path / child
            plan[child_relative_source_path] = InstallNode("none", requires_rename, child_relative_source_path, child_relative_destination_path)

    return plan


def plan_install(source_package_root: Path, destination_root: Path, exclude_dirs: list[str]=None) -> dict[Path, InstallNode]:
    plan: dict[Path, InstallNode] = plan_install_paths(source_package_root, exclude_dirs)

    for dirpath, dirnames, filenames in os.walk(source_package_root, False):
        full_target = Path(dirpath)
        if should_exclude_this_object(full_target, exclude_dirs):
            continue

        target = full_target.relative_to(source_package_root)

        found_files_to_rename = False
        for object in full_target.glob("dot-*"):
            found_files_to_rename = True
            plan[object.relative_to(source_package_root)].action = "link-rename"

        if full_target == source_package_root:
            plan[target].action = "exists"
        elif found_files_to_rename:
            plan[target].action = "create"
            mark_all_parents(target, mark="create", stop_mark="exists", plan=plan)
        elif (destination_root / target).exists():
            plan[target].action = "exists"
            mark_all_parents(target, mark="exists", stop_mark="exists", plan=plan)
        else:
            plan[target].action = "link"

        if plan[target].action in {"create", "exists"}:
            mark_all_children_not_already_marked(source_package_root, exclude_dirs, target, mark="link", plan=plan)
        elif plan[target].action == "link":
            mark_all_children_not_already_marked(source_package_root, exclude_dirs, target, mark="skip", plan=plan)

    del plan[Path(".")]
    debug_print_plan(source_package_root, plan)
    return plan

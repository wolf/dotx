import os
from pathlib import Path

import click

from dotfiles.ignore import should_ignore_this_object
from dotfiles.plan import Action, PlanNode, Plan, mark_all_parents, mark_immediate_children


def plan_install_paths(source_package_root: Path, exclude_dirs: list[str] = None) -> Plan:
    plan: Plan = {Path("."): PlanNode(Action.EXISTS, False, Path("."), Path("."), True)}

    # For calculating destination path-names, I traverse the file tree top-down
    for current_root, child_directories, child_files in os.walk(source_package_root):
        current_root_path = Path(current_root)
        if should_ignore_this_object(current_root_path, exclude_dirs):
            continue

        relative_root_path = current_root_path.relative_to(source_package_root)
        current_destination_path = plan[relative_root_path].relative_destination_path

        for child in child_directories + child_files:
            requires_rename = False
            child_relative_source_path = relative_root_path / child
            if should_ignore_this_object(child_relative_source_path, exclude_dirs):
                continue
            if child.startswith("dot-"):
                requires_rename = True
                child_relative_destination_path = current_destination_path / ("." + child[4:])
            else:
                child_relative_destination_path = current_destination_path / child
            plan[child_relative_source_path] = PlanNode(
                Action.NONE,
                requires_rename,
                child_relative_source_path,
                child_relative_destination_path,
                (source_package_root / child_relative_source_path).is_dir(),
            )

    return plan


def plan_install(source_package_root: Path, destination_root: Path, exclude_dirs: list[str] = None) -> Plan:
    plan: Plan = plan_install_paths(source_package_root, exclude_dirs)

    for current_root, child_directories, child_files in os.walk(source_package_root, topdown=False):
        current_root_path = Path(current_root)
        relative_root_path = current_root_path.relative_to(source_package_root)
        if relative_root_path not in plan:
            continue

        found_children_to_rename = False
        for child in child_directories + child_files:
            child_relative_source_path = relative_root_path / child
            if child_relative_source_path not in plan:
                continue
            if plan[child_relative_source_path].requires_rename:
                found_children_to_rename = True
            destination_path = destination_root / plan[child_relative_source_path].relative_destination_path
            if destination_path.exists() and destination_path.is_file():
                plan[child_relative_source_path].action = Action.FAIL

        if current_root_path == source_package_root:
            plan[relative_root_path].action = Action.EXISTS
        elif found_children_to_rename:
            plan[relative_root_path].action = Action.CREATE
            mark_all_parents(relative_root_path, mark=Action.CREATE, stop_mark=Action.EXISTS, plan=plan)
        elif (destination_root / relative_root_path).exists():
            plan[relative_root_path].action = Action.EXISTS
            mark_all_parents(relative_root_path, mark=Action.EXISTS, stop_mark=Action.EXISTS, plan=plan)
        else:
            plan[relative_root_path].action = Action.LINK

        if plan[relative_root_path].action in {Action.CREATE, Action.EXISTS}:
            mark_immediate_children(
                source_package_root, relative_root_path, mark=Action.LINK, plan=plan, allow_overwrite={Action.NONE}
            )
        elif plan[relative_root_path].action == Action.LINK:
            mark_immediate_children(
                source_package_root,
                relative_root_path,
                mark=Action.SKIP,
                plan=plan,
                allow_overwrite={Action.NONE, Action.LINK},
            )

    del plan[Path(".")]
    return plan


# TODO: def execute_plan

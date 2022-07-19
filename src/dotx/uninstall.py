"""This module provides the tools to plan an uninstall

Builds a `dotx.plan.Plan` designed to uninstall (mostly by unlinking) the files present in the destination root
that link into the source package.  That plan can then be executed by `dotx.plan.execute_plan`.

Exported functions:
    plan_uninstall
"""


import os
from pathlib import Path

from dotx.plan import Action, Plan, mark_all_descendents
from dotx.install import plan_install_paths


def plan_uninstall(source_package_root: Path, destination_root: Path, excludes: list[str] = None) -> Plan:
    plan: Plan = plan_install_paths(source_package_root, excludes)

    for current_root, child_directories, child_files in os.walk(source_package_root):
        current_root_path = Path(current_root)
        relative_root_path = current_root_path.relative_to(source_package_root)
        if relative_root_path not in plan or plan[relative_root_path].action == Action.SKIP:
            continue

        for child in child_files:
            child_relative_source_path = relative_root_path / child
            if child_relative_source_path not in plan:
                continue
            destination_path = destination_root / plan[child_relative_source_path].relative_destination_path
            if destination_path.is_symlink():
                plan[child_relative_source_path].action = Action.UNLINK

        destination_path = destination_root / plan[relative_root_path].relative_destination_path
        action = None
        if not destination_path.exists():
            action = Action.SKIP
        elif destination_path.is_symlink():
            action = Action.UNLINK

        if action is not None:
            plan[relative_root_path].action = action
            if (source_package_root / plan[relative_root_path].relative_source_path).is_dir():
                mark_all_descendents(relative_root_path, Action.SKIP, {Action.NONE}, source_package_root, plan)

    del plan[Path(".")]
    return plan

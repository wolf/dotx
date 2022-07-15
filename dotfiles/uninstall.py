"""This module provides the tools to plan an uninstall

Builds a `dotfiles.plan.Plan` designed to uninstall (mostly by unlinking) the files present in the destination root
that link into the source package.  That plan can then be executed by `dotfiles.plan.execute_plan`.

Exported functions:
    plan_uninstall
"""


import logging
import os
from pathlib import Path

from dotfiles.plan import Action, Plan, PlanNode, log_extracted_plan, mark_all_children
from dotfiles.install import plan_install_paths


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

        relative_destination_root_path = plan[relative_root_path].relative_destination_path
        destination_path = destination_root / relative_destination_root_path
        if destination_path.is_symlink():
            plan[relative_root_path].action = Action.UNLINK
            if destination_path.is_dir():
                mark_all_children(source_package_root, relative_root_path, Action.SKIP, plan, {Action.NONE})

    del plan[Path(".")]
    return plan

"""
This module provides the tools to plan an uninstall

Builds a `dotx.plan.Plan` designed to uninstall (mostly by unlinking) the files present in the destination root
that link into the source package.  That plan can then be executed by `dotx.plan.execute_plan`.

Exported functions:
    plan_uninstall
"""

import os
from pathlib import Path

from dotx.options import is_xdg_mode
from dotx.plan import Action, Plan, mark_all_descendents, resolve_destination
from dotx.install import plan_install_paths


def plan_uninstall(source_package_root: Path, destination_root: Path) -> Plan:
    """
    Create a plan to uninstall files from destination_root that link to source_package_root.

    Respects XDG mode: when enabled, .config/*, .local/share/*, .cache/* are resolved to their
    respective XDG Base Directory paths when checking for symlinks to remove.

    Returns: a `Plan` with actions set to UNLINK for symlinks pointing to the source package
    """
    plan: Plan = plan_install_paths(source_package_root)
    xdg_mode = is_xdg_mode()

    for current_root, _, child_files in os.walk(source_package_root):
        current_root_path = Path(current_root)
        relative_root_path = current_root_path.relative_to(source_package_root)
        if (
            relative_root_path not in plan
            or plan[relative_root_path].action == Action.SKIP
        ):
            continue

        for child in child_files:
            child_relative_source_path = relative_root_path / child
            if child_relative_source_path not in plan:
                continue
            destination_path = resolve_destination(
                plan[child_relative_source_path].relative_destination_path,
                destination_root,
                xdg_mode,
            )
            if destination_path.is_symlink():
                plan[child_relative_source_path].action = Action.UNLINK

        destination_path = resolve_destination(
            plan[relative_root_path].relative_destination_path,
            destination_root,
            xdg_mode,
        )
        action = None
        if not destination_path.exists():
            action = Action.SKIP
        elif destination_path.is_symlink():
            action = Action.UNLINK

        if action is not None:
            plan[relative_root_path].action = action
            if (
                source_package_root / plan[relative_root_path].relative_source_path
            ).is_dir():
                mark_all_descendents(
                    relative_root_path,
                    Action.SKIP,
                    {Action.NONE},
                    source_package_root,
                    plan,
                )

    del plan[Path(".")]
    return plan

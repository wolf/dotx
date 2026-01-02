"""
This module provides the tools to plan an install

Builds a `dotx.plan.Plan` designed to install (mostly by linking) the files present in the source package root
into the destination root.  That plan can then be executed by `dotx.plan.execute_plan`.

Exported functions:
    plan_install
    plan_install_paths
"""


# TODO: update docstrings for functions to list parameters and return values

import logging
import os
from pathlib import Path

from dotx.ignore import IgnoreRules
from dotx.plan import (
    Action,
    Plan,
    PlanNode,
    log_extracted_plan,
    mark_all_ancestors,
    mark_immediate_children,
)


def plan_install(source_package_root: Path, destination_root: Path) -> Plan:
    """
    Create a plan to install the contents of `source_package_root` into `destination_root`.

    The algorithm is to traverse, with a bottom-up call to `os.walk`, the source package, determining which paths
    already exists at the destination, which must be created, renamed, linked, or already exist in a way that causes
    a failure.

    Returns: a `Plan` with all the information needed to complete an install, or to fail
    """
    plan: Plan = plan_install_paths(source_package_root)

    # TODO: add comments, this loop looks impenetrable
    for current_root, child_directories, child_files in os.walk(
        source_package_root, topdown=False
    ):
        current_root_path = Path(current_root)
        relative_root_path = current_root_path.relative_to(source_package_root)
        if relative_root_path not in plan:
            continue

        relative_destination_root_path = plan[
            relative_root_path
        ].relative_destination_path

        found_children_to_rename = False
        for child in child_directories + child_files:
            child_relative_source_path = relative_root_path / child
            if child_relative_source_path not in plan:
                continue
            if plan[child_relative_source_path].requires_rename:
                found_children_to_rename = True
            destination_path = (
                destination_root
                / plan[child_relative_source_path].relative_destination_path
            )
            if destination_path.exists() and destination_path.is_file():
                plan[child_relative_source_path].action = Action.FAIL

        if current_root_path == source_package_root:
            plan[relative_root_path].action = Action.EXISTS
        elif found_children_to_rename:
            plan[relative_root_path].action = Action.CREATE
            mark_all_ancestors(
                relative_root_path,
                mark=Action.CREATE,
                stop_mark=Action.EXISTS,
                plan=plan,
            )
        elif (destination_root / relative_destination_root_path).exists():
            plan[relative_root_path].action = Action.EXISTS
            mark_all_ancestors(
                relative_root_path,
                mark=Action.EXISTS,
                stop_mark=Action.EXISTS,
                plan=plan,
            )
        else:
            plan[relative_root_path].action = Action.LINK

        if plan[relative_root_path].action in {Action.CREATE, Action.EXISTS}:
            mark_immediate_children(
                relative_root_path,
                mark=Action.LINK,
                allow_overwrite={Action.NONE},
                source_package_root=source_package_root,
                plan=plan,
            )
        elif plan[relative_root_path].action == Action.LINK:
            mark_immediate_children(
                relative_root_path,
                mark=Action.SKIP,
                allow_overwrite={Action.NONE, Action.LINK},
                source_package_root=source_package_root,
                plan=plan,
            )

    del plan[Path(".")]
    return plan


def plan_install_paths(source_package_root: Path) -> Plan:
    """
    Construct an initial `Plan` that contains only the affected paths.

    The algorithm is to traverse, with a top-down call to `os.walk`, the file-system objects within
    `source_package_root`, deciding along the way which ones are directories, and independent of that, which ones
    need to be renamed to be installed correctly.  The `plan.Action` for all of these nodes is `Action.NONE` so they
    can easily be overwritten later by code that figures out exactly what needs to be done.  No nodes are created for
    file-system objects that are ignored according to .dotxignore files.  Files or directories whose source name
    begins with "dot-", e.g., "dot-bashrc", are marked as needing to be renamed on the way to installation and the
    destination name is calculated here, substituting an actual "." for the "dot-" prefix.  Because the paths are
    visited top-down, renamed parents already have their correct destination path recorded, so the complete path is
    always known.  Because the destination paths are all relative to the destination root, the actual destination
    root is not needed.

    Returns: a `Plan` with correct paths, `is_dir`, and `requires_rename` in every node.
    """
    logging.info(f"Planning install paths for source package {source_package_root}")

    # Initialize ignore rules (loads global ignore and will load .dotxignore files during traversal)
    ignore_rules = IgnoreRules()

    plan: Plan = {
        Path("."): PlanNode(
            action=Action.EXISTS,
            requires_rename=False,
            relative_source_path=Path("."),
            relative_destination_path=Path("."),
            is_dir=True,
        )
    }

    # TODO: more comments; another impenetrable loop
    for current_root, child_directories, child_files in os.walk(source_package_root):
        current_root_path = Path(current_root)

        # Load .dotxignore from current directory if it exists
        ignore_rules.load_ignore_file(current_root_path)

        # Prune ignored directories to prevent descending into them
        child_directories[:] = ignore_rules.prune_directories(
            current_root_path, child_directories, source_package_root
        )

        # Skip this directory if it should be ignored
        if ignore_rules.should_ignore(current_root_path, source_package_root):
            continue

        relative_root_path = current_root_path.relative_to(source_package_root)
        current_destination_path = plan[relative_root_path].relative_destination_path

        for child in child_directories + child_files:
            requires_rename = False
            child_source_path = source_package_root / relative_root_path / child
            child_relative_source_path = relative_root_path / child

            # Skip ignored files and directories
            if ignore_rules.should_ignore(child_source_path, source_package_root):
                continue
            if child.startswith("dot-"):
                requires_rename = True
                child_relative_destination_path = current_destination_path / (
                    "." + child[4:]
                )
            else:
                child_relative_destination_path = current_destination_path / child
            plan[child_relative_source_path] = PlanNode(
                action=Action.NONE,
                requires_rename=requires_rename,
                relative_source_path=child_relative_source_path,
                relative_destination_path=child_relative_destination_path,
                is_dir=(source_package_root / child_relative_source_path).is_dir(),
            )

    log_extracted_plan(
        plan,
        description="planned (un)install paths",
        key=lambda node: str(node.relative_source_path)
        + "->"
        + str(node.relative_destination_path),
        actions_to_extract={Action.NONE},
    )
    return plan

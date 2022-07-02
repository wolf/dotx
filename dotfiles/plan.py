from dataclasses import dataclass
from enum import Enum
import logging
import os
from pathlib import Path

import click


class Action(Enum):
    FAIL = "fail"
    NONE = "none"
    SKIP = "skip"
    LINK = "link"
    UNLINK = "unlink"
    CREATE = "create"
    EXISTS = "exists"


@dataclass
class PlanNode:
    action: Action
    requires_rename: bool
    relative_source_path: Path
    relative_destination_path: Path
    is_dir: bool


Plan = dict[Path, PlanNode]


def mark_immediate_children(
    source_package_root: Path, parent: Path, mark: Action, plan: Plan, allow_overwrite: set[Action]
):
    this_directory = source_package_root / parent
    for child in this_directory.iterdir():
        child_relative_path = child.relative_to(source_package_root)
        if child_relative_path in plan and plan[child_relative_path].action in allow_overwrite:
            plan[child_relative_path].action = mark


def mark_all_parents(leaf: Path, mark: Action, stop_mark: Action, plan: Plan):
    for parent in leaf.parents:
        if parent in plan and plan[parent].action == stop_mark:
            break
        plan[parent].action = mark


def extract_plan(plan: Plan, actions: set[Action]) -> list[PlanNode]:
    return [
        node for node in sorted(plan.values(), key=lambda node: node.relative_source_path) if node.action in actions
    ]


def debug_print_plan(source_package_root: Path, plan: Plan):
    for current_root, child_directories, child_files in os.walk(source_package_root):
        current_root_path = Path(current_root)
        relative_root_path = current_root_path.relative_to(source_package_root)

        if relative_root_path in plan or relative_root_path == Path("."):
            for child in child_directories + child_files:
                child_relative_source_path = relative_root_path / child
                if child_relative_source_path in plan:
                    print(plan[child_relative_source_path])


def log_extracted_plan(plan: Plan, *, log_level=logging.INFO, key=None, actions_to_extract=None):
    logger = logging.getLogger()
    if logger.isEnabledFor(log_level):
        if key is None:
            key = lambda node: node
        if actions_to_extract is None:
            actions_to_extract = {Action.LINK, Action.UNLINK, Action.CREATE}
        logger.log(log_level, "---BEGIN PLAN---")
        for node in extract_plan(plan, actions_to_extract):
            logger.log(log_level, key(node))
        logger.log(log_level, "---END PLAN---")


def log_extracted_failures(plan: Plan, *, log_level=logging.INFO, key=None):
    log_extracted_plan(plan, log_level=log_level, key=key, actions_to_extract={Action.FAIL})


def execute_plan(source_package_root: Path, destination_root: Path, plan: Plan):
    click.echo(f"Installing from {source_package_root} into {destination_root}:")
    log_extracted_plan(plan)

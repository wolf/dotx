from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path


class Action(Enum):
    NONE = "none"
    SKIP = "skip"
    LINK = "link"
    CREATE = "create"
    EXISTS = "exists"
    UNLINK = "unlink"


@dataclass
class PlanNode:
    action: Action
    requires_rename: bool
    relative_source_path: Path
    relative_destination_path: Path


Plan = dict[Path, PlanNode]


def mark_immediate_children_not_already_marked(
        source_package_root: Path,
        parent: Path,
        mark: Action,
        plan: Plan,
):
    this_directory = source_package_root / parent
    for child in this_directory.iterdir():
        child_relative_path = child.relative_to(source_package_root)
        if child_relative_path in plan and plan[child_relative_path].action == Action.NONE:
            plan[child_relative_path].action = mark


def mark_all_parents(leaf: Path, mark: Action, stop_mark: Action, plan: Plan):
    for parent in leaf.parents:
        if parent in plan and plan[parent].action == stop_mark:
            break
        plan[parent].action = mark


def debug_print_plan(source_package_root: Path, plan: Plan):
    for current_root, child_directories, child_files in os.walk(source_package_root):
        current_root_path = Path(current_root)
        relative_root_path = current_root_path.relative_to(source_package_root)

        if relative_root_path in plan or relative_root_path == Path("."):
            for child in child_directories + child_files:
                child_relative_source_path = relative_root_path / child
                if child_relative_source_path in plan:
                    print(f"'{child_relative_source_path}': '{plan[child_relative_source_path]}'")

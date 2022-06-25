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


def mark_immediate_children_not_already_marked(
        source_package_root: Path,
        parent: Path,
        mark: Action,
        plan: dict[Path, PlanNode],
):
    this_directory = source_package_root / parent
    for child in this_directory.iterdir():
        child_relative_path = child.relative_to(source_package_root)
        if child_relative_path in plan and plan[child_relative_path].action == Action.NONE:
            plan[child_relative_path].action = mark


def mark_all_parents(leaf: Path, mark: Action, stop_mark: Action, plan: dict[Path, PlanNode]):
    for parent in leaf.parents:
        if parent in plan and plan[parent].action == stop_mark:
            break
        plan[parent].action = mark


def debug_print_plan(source_package_root: Path, plan: dict[Path, PlanNode]):
    for dirpath, dirnames, filenames in os.walk(source_package_root):
        full_target = Path(dirpath)
        target = full_target.relative_to(source_package_root)

        if target in plan:
            print(f"{target}: '{plan[target]}'")
            for filename in filenames:
                file = target / filename
                if file in plan:
                    print(f"'{file}': '{plan[file]}'")

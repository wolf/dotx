from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path


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


def debug_print_extracted_plan(plan: Plan):
    for node in extract_plan(plan, {Action.LINK, Action.UNLINK, Action.CREATE}):
        print(node)


def debug_print_extracted_failures(plan: Plan):
    for node in extract_plan(plan, {Action.FAIL}):
        print(node)

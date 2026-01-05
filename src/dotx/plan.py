"""
This module provides the tools to describe and manipulate a (un)install plan.

The basic idea is the clients investigate a file-system tree (hierarchy) building a dictionary of `PlanNode`s along
the way.  Each `PlanNode` describes in detail what to do to a single file-system object.  As the client makes
decisions about the actions they want to take, they "mark" various `PlanNode`s in their plan with `Action`s like
`Action.LINK` or `Action.CREATE` to say how they intend to handle that object.  Marking a parent may have
consequences for the children, or marking a child may have consequences for all its parents up the line.  This module
provides functions to mark accordingly.  Which nodes to mark and what to mark them with is the responsibility of the
client. Actually doing complex marking operations belongs here.

Exported types:
    Action:     an Enum describing what the plan wants to _do_ to a specific file-system object
    PlanNode:   a class that gives the complete details for handling a specific file-system object
    Plan:       a type alias for a dict of PlanNodes keyed by pathlib.Paths relative to the source package root

Exported functions:
    execute_plan
    extract_plan
    log_extracted_failures
    log_extracted_plan
    mark_all_ancestors
    mark_all_descendents
    mark_immediate_children
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from dotx.database import NoOpDB
from dotx.options import is_dry_run

if TYPE_CHECKING:
    from dotx.database import InstallationDB


class Action(Enum):
    """
    An `Enum` to describe what is or will happen to a given file-system object in a plan.

    Values:
        FAIL:   a file that already exists in the destination cannot be replaced, the install fails
        NONE:   an empty initial value for a `PlanNode`
        SKIP:   an object whose parent (somewhere along the chain) is linked needs no further work done
        LINK:   a file or directory that should be installed with a direct symlink
        UNLINK: the object exists at the destination and the plan is to remove it
        CREATE: a directory that cannot be linked must be created
        EXISTS: a directory that already exists in the destination
    """

    FAIL = "fail"
    NONE = "none"
    SKIP = "skip"
    LINK = "link"
    UNLINK = "unlink"
    CREATE = "create"
    EXISTS = "exists"


@dataclass
class PlanNode:
    """
    Provides all the information needed to install or uninstall a single file-system object

    Attributes:
        action:                     what this `PlanNode` indicates about the underlying file-system object, e.g.,
                                    `Action.EXISTS` if it exists already in the destination, or `Action.LINK` if
                                    installing it requires making a symlink
        requires_rename:            `True` when the source object and destination object have different names, e.g.,
                                    a source of "dot-bashrc" and a destination of ".bashrc".
        relative_source_path:       the `pathlib.Path` of the origin file-system object relative to the source package
                                    root
        relative_destination_path:  the `pathlib.Path` of the installed file-system object relative to the destination
                                    location root
        is_dir:                     `True` when this file-system object is a directory
    """

    action: Action
    requires_rename: bool
    relative_source_path: Path
    relative_destination_path: Path
    is_dir: bool


Plan = dict[Path, PlanNode]


def execute_plan(
    source_package_root: Path,
    destination_root: Path,
    plan: Plan,
    db: InstallationDB | NoOpDB | None = None,
):
    """
    Create, link, or unlink files and directories as indicated by the plan.

    If this is a dry-run, prints the shell commands. Otherwise, actually creates,
    links, or unlinks files using pathlib native functions.

    If a database is provided, records installations (CREATE, LINK) and removals (UNLINK).
    """
    # Use NoOpDB if no database provided
    working_db = db if db is not None else NoOpDB()

    # Extract package info for database tracking
    package_root = source_package_root.parent
    package_name = source_package_root.name

    def build_shell_command(step: PlanNode):
        """Print the shell command corresponding to exactly one `PlanNode`"""
        command = None
        destination = destination_root / step.relative_destination_path
        source = (source_package_root / step.relative_source_path).resolve()
        try:
            source = source.relative_to(destination.parent)
        except ValueError:
            pass

        match step.action:
            case Action.CREATE:
                command = f"mkdir {destination}"
            case Action.LINK:
                command = f"ln -s {source} {destination}"
            case Action.UNLINK if destination.is_symlink():
                command = f"rm {destination}"
            case Action.UNLINK:
                command = f"rm {'-rf ' if step.is_dir else ''}{destination}"
        return command

    def execute_plan_step(step: PlanNode):
        """
        Make the change specified by a single `PlanNode` happen using `pathlib` functions.

        Records installations and removals in database.
        """
        destination = destination_root / step.relative_destination_path
        source = (source_package_root / step.relative_source_path).resolve()
        try:
            source = source.relative_to(destination.parent)
        except ValueError:
            pass

        match step.action:
            case Action.CREATE:
                destination.mkdir()
                # Record directory creation in database
                working_db.record_installation(
                    package_root, package_name, source_package_root, destination, "created_dir"
                )
            case Action.LINK:
                destination.symlink_to(source, step.is_dir)
                # Record symlink in database
                link_type = "directory" if step.is_dir else "file"
                working_db.record_installation(
                    package_root, package_name, source_package_root, destination, link_type
                )
            case Action.UNLINK if destination.is_symlink():
                destination.unlink()
                # Remove from database
                working_db.remove_installation(destination)
            case _:
                logger.critical(f"Bad step: {step}")
                exit(2)

    steps = extract_plan(plan, actions={Action.CREATE, Action.LINK, Action.UNLINK})

    # Check dry-run once before the loop rather than on every iteration for better performance.
    # This does duplicate the loop code, but avoids thousands of repeated is_dry_run() calls
    # in installations with many files.
    if is_dry_run():
        for step in steps:
            command = build_shell_command(step)
            if command is not None:
                logger.info(command)
                print(command)
    else:
        for step in steps:
            command = build_shell_command(step)
            if command is not None:
                logger.info(command)
            execute_plan_step(step)


def extract_plan(plan: Plan, actions: set[Action]) -> list[PlanNode]:
    """
    Converts a Plan into an ordered list, extracting just the nodes you care about.

    Sorts by relative_source_path (top-down order) and includes only PlanNodes
    whose action is in the provided set. This makes it easy to grab just failures,
    or just the actions for which actual work is needed (e.g., {Action.LINK, Action.CREATE}).
    """
    return [
        node
        for node in sorted(plan.values(), key=lambda node: node.relative_source_path)
        if node.action in actions
    ]


def log_extracted_failures(
    plan: Plan, *, description: str | None = None, log_level="INFO", key=None
):
    """Convenience function to call log_extracted_plan looking only for failures."""
    log_extracted_plan(
        plan,
        description=description,
        log_level=log_level,
        key=key,
        actions_to_extract={Action.FAIL},
    )


def log_extracted_plan(
    plan: Plan,
    *,
    description: str | None = None,
    log_level="INFO",
    key=None,
    actions_to_extract=None,
):
    """
    Extract steps from a plan and log them at the specified level.

    The key function customizes what to print for each PlanNode.
    The actions_to_extract set controls which PlanNodes to include (defaults to LINK, UNLINK, CREATE).
    """
    if key is None:
        key = lambda node: node  # noqa: E731
    if actions_to_extract is None:
        actions_to_extract = {Action.LINK, Action.UNLINK, Action.CREATE}
    if description is None:
        logger.log(log_level, "---BEGIN PLAN---")
    else:
        logger.log(log_level, f"---BEGIN PLAN: {description}---")
    for node in extract_plan(plan, actions_to_extract):
        logger.log(log_level, key(node))
    logger.log(log_level, "---END PLAN---")


def mark_all_ancestors(child: Path, mark: Action, stop_mark: Action, plan: Plan):
    """
    Mark each parent of child up the chain until hitting one with stop_mark.

    Climbs up the directory tree marking parent PlanNodes with the given Action,
    stopping when it encounters a parent whose action is already stop_mark (typically Action.EXISTS).
    """
    for parent in child.parents:
        if parent in plan:
            if plan[parent].action == stop_mark:
                break
            plan[parent].action = mark


def mark_all_descendents(
    parent: Path,
    mark: Action,
    allow_overwrite: set[Action],
    source_package_root: Path,
    plan: Plan,
):
    """
    Recursively mark every descendent of parent with the given Action.

    Only overwrites PlanNodes whose current action is in the allow_overwrite set.
    For example, if marking with Action.LINK, allow_overwrite might be {Action.NONE}
    to only mark unmarked nodes.
    """
    this_directory = source_package_root / parent
    for child in this_directory.iterdir():
        child_relative_path = child.relative_to(source_package_root)
        if (
            child_relative_path in plan
            and plan[child_relative_path].action in allow_overwrite
        ):
            plan[child_relative_path].action = mark
        if child.is_dir():
            mark_all_descendents(
                child_relative_path, mark, allow_overwrite, source_package_root, plan
            )


def mark_immediate_children(
    parent: Path,
    mark: Action,
    allow_overwrite: set[Action],
    source_package_root: Path,
    plan: Plan,
):
    """
    Mark each immediate child of parent with the given Action (non-recursive).

    Only overwrites PlanNodes whose current action is in the allow_overwrite set.
    For example, if marking with Action.LINK, allow_overwrite might be {Action.NONE}
    to only mark unmarked nodes.
    """
    this_directory = source_package_root / parent
    for child in this_directory.iterdir():
        child_relative_path = child.relative_to(source_package_root)
        if (
            child_relative_path in plan
            and plan[child_relative_path].action in allow_overwrite
        ):
            plan[child_relative_path].action = mark

"""This module provides the tools to describe and manipulate a (un)install plan.

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


import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from dotx.options import is_dry_run


class Action(Enum):
    """An `Enum` to describe what is or will happen to a given file-system object in a plan.

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
    """Provides all the information needed to install or uninstall a single file-system object

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


def execute_plan(source_package_root: Path, destination_root: Path, plan: Plan):
    """Create, link, or unlink files and directories as indicated by the supplied `plan`.

    This function is used to actually make an install or an uninstall happen.  If this is a dry-run,
    then just print the shell commands it would take to do the install or uninstall.  Otherwise,
    actually create, link, or unlink actual files using `pathlib` native functions.
    """

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
        """Make the change specified by a single `PlanNode` happen using `pathlib` functions"""
        destination = destination_root / step.relative_destination_path
        source = (source_package_root / step.relative_source_path).resolve()
        try:
            source = source.relative_to(destination.parent)
        except ValueError:
            pass

        match step.action:
            case Action.CREATE:
                destination.mkdir()
            case Action.LINK:
                destination.symlink_to(source, step.is_dir)
            case Action.UNLINK if destination.is_symlink():
                destination.unlink()
            case _:
                logging.critical(f"Bad step: {step}")
                exit(2)

    steps = extract_plan(plan, actions={Action.CREATE, Action.LINK, Action.UNLINK})
    if is_dry_run():
        for step in steps:
            command = build_shell_command(step)
            if command is not None:
                logging.info(command)
                print(command)
    else:
        for step in steps:
            command = build_shell_command(step)
            if command is not None:
                logging.info(command)
            execute_plan_step(step)


def extract_plan(plan: Plan, actions: set[Action]) -> list[PlanNode]:
    """Converts a `Plan` into an ordered list, extracting just the nodes you care about (according to `Action`).

    The key features of this function are how it sorts the resulting list, and how it chooses which `PlanNode`s go
    into the list.  It sorts according `relative_source_path`, automatically giving you a list of nodes which allow
    you to execute top-down.  It decides which nodes participate in the list by testing if their `action` is in the
    set of `Action`s you provide.  Thus it's easy to grab just the failures, or just the `Action`s for which actual
    work is needed, say `{Action.LINK, Action.CREATE}` during an install.

    Takes two arguments:
        plan:       a `Plan`, the plan from which to grab individual nodes
        actions:    a set of `Action`s defining with `PlanNode`s to include in the result

    Returns: an ordered list of `PlanNode`s.
    """
    return [
        node for node in sorted(plan.values(), key=lambda node: node.relative_source_path) if node.action in actions
    ]


def log_extracted_failures(plan: Plan, *, description: str = None, log_level=logging.INFO, key=None):
    """Convenience function to call `log_extracted_plan` looking only for failures."""
    log_extracted_plan(plan, description=description, log_level=log_level, key=key, actions_to_extract={Action.FAIL})


def log_extracted_plan(
    plan: Plan, *, description: str = None, log_level=logging.INFO, key=None, actions_to_extract=None
):
    """Extract the steps of a plan according to `actions_to_extract` and log them at the given log level.

    Takes one positional argument:
        plan:               the plan to (extract from and then) log

    Takes up to four keyword-only arguments:
        description:        a string to be printed before the plan
        log_level:          the level at which to make all this happen.  If logging is not set to show this level,
                            nothing is logged
        key:                a function to build what you want to print for each individual `PlanNode`
        actions_to_extract: as in other functions, a set of `Action`s controlling exactly which `PlanNode`s will be logged
    """
    logger = logging.getLogger()
    if key is None:
        key = lambda node: node
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
    """Mark each parent of `leaf` up the chain with the given `Action` until you hit one whose `action` is `stop_mark`.

    Takes four arguments:
        leaf:       the object whose parents you care about
        mark:       the `Action` to set inside the `PlanNode`s for the found parents
        stop_mark:  the `Action` that will stop the climb.  Typically `Action.EXISTS`
        plan:       the `Plan` in which this all takes place
    """
    for parent in child.parents:
        if parent in plan:
            if plan[parent].action == stop_mark:
                break
            plan[parent].action = mark


def mark_all_descendents(
    parent: Path, mark: Action, allow_overwrite: set[Action], source_package_root: Path, plan: Plan
):
    """Mark every descendent of `parent` with the given `Action`, both files and directories.

    `allow_overwrite` is key, here.  For instance, `PlanNode`s start with an `action` of `Action.NONE`. If you were
    marking the children with `Action.LINK`, you'd want to be allowed to overwrite those whose `action` was still
    `Action.NONE`.

    Takes four arguments:
        source_package_root:    a `pathlib.Path` needed to build paths to key into the `Plan`
        parent:                 the `pathlib.Path` to a directory whose descendents you wish to mark
        mark:                   the `Action` with which to mark the children
        allow_overwrite:        ...but only if they are currently marked with an `Action` from this set
    """
    this_directory = source_package_root / parent
    for child in this_directory.iterdir():
        child_relative_path = child.relative_to(source_package_root)
        if child_relative_path in plan and plan[child_relative_path].action in allow_overwrite:
            plan[child_relative_path].action = mark
        if child.is_dir():
            mark_all_descendents(child_relative_path, mark, allow_overwrite, source_package_root, plan)


def mark_immediate_children(
    parent: Path, mark: Action, allow_overwrite: set[Action], source_package_root: Path, plan: Plan
):
    """Mark each child of `parent` with the given `Action`, both files and directories.

    `allow_overwrite` is key, here.  For instance, `PlanNode`s start with an `action` of `Action.NONE`. If you were
    marking the children with `Action.LINK`, you'd want to be allowed to overwrite those whose `action` was still
    `Action.NONE`.

    Takes four arguments:
        source_package_root:    a `pathlib.Path` needed to build paths to key into the `Plan`
        parent:                 the `pathlib.Path` to a directory whose children you wish to mark
        mark:                   the `Action` with which to mark the children
        allow_overwrite:        ...but only if they are currently marked with an `Action` from this set
    """
    this_directory = source_package_root / parent
    for child in this_directory.iterdir():
        child_relative_path = child.relative_to(source_package_root)
        if child_relative_path in plan and plan[child_relative_path].action in allow_overwrite:
            plan[child_relative_path].action = mark

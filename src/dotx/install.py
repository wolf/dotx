"""
This module provides the tools to plan an install

Builds a `dotx.plan.Plan` designed to install (mostly by linking) the files present in the source package root
into the destination root.  That plan can then be executed by `dotx.plan.execute_plan`.

Exported functions:
    plan_install
    plan_install_paths
"""

import os
from pathlib import Path

from loguru import logger

from dotx.hierarchy import HierarchicalPatternMatcher
from dotx.ignore import IgnoreRules
from dotx.plan import (
    Action,
    Plan,
    PlanNode,
    log_extracted_plan,
    mark_all_ancestors,
    mark_immediate_children,
)


def _matches_always_create_at_exact_depth(
    path: Path, matcher: HierarchicalPatternMatcher
) -> bool:
    """
    Check if path has an explicit always-create pattern at its depth.

    Gitignore patterns match subdirectories by default, but we only want to mark
    directories as always-create if there's a pattern explicitly for that depth.

    Examples with patterns [/.config, /.local, /.local/share]:
    - ".config" → True (matches /.config at depth 1)
    - ".config/myapp" → False (no pattern at depth 2 for this path)
    - ".local" → True (matches /.local at depth 1)
    - ".local/share" → True (matches /.local/share at depth 2)
    - ".local/share/apps" → False (no pattern at depth 3)

    Args:
        path: Relative destination path to check
        matcher: HierarchicalPatternMatcher with always-create patterns loaded

    Returns:
        True if there's an explicit pattern at this path's depth
    """
    # Check if this path matches any pattern
    if not matcher.matches(path, is_dir=True):
        return False

    # Check if there's a pattern with the same depth as this path
    if matcher.spec is None:
        return False

    path_depth = len(path.parts)

    # Check each pattern to see if any have the same depth
    for pattern_obj in matcher.spec.patterns:
        # PathSpec.patterns returns Pattern objects, access pattern string
        pattern = pattern_obj.pattern if hasattr(pattern_obj, "pattern") else str(pattern_obj)
        # Normalize pattern: strip leading/trailing slashes
        pattern_clean = pattern.strip("/")
        if not pattern_clean:
            continue

        # Calculate pattern depth
        pattern_parts = pattern_clean.split("/")
        pattern_depth = len(pattern_parts)

        # If this pattern has the same depth, check if it matches this path
        if pattern_depth == path_depth:
            # Create a single-pattern spec to test just this pattern
            import pathspec
            test_spec = pathspec.PathSpec.from_lines("gitwildmatch", [pattern])
            path_str = str(path) + "/"
            if test_spec.match_file(path_str):
                return True

    return False


def plan_install(source_package_root: Path, destination_root: Path) -> Plan:
    """
    Create a plan to install the contents of `source_package_root` into `destination_root`.

    The algorithm is to traverse, with a bottom-up call to `os.walk`, the source package, determining which paths
    already exists at the destination, which must be created, renamed, linked, or already exist in a way that causes
    a failure.

    Returns: a `Plan` with all the information needed to complete an install, or to fail
    """
    plan: Plan = plan_install_paths(source_package_root)

    # Load always-create patterns to determine which directories must be real (never symlinked)
    always_create_matcher = HierarchicalPatternMatcher(".always-create")
    builtin_file = Path(__file__).parent / "always-create"
    config_home = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    user_config = Path(config_home) / "dotx" / "always-create"
    package_file = source_package_root / ".always-create"
    package_files = [package_file] if package_file.exists() else []

    always_create_matcher.load_patterns(
        builtin_file=builtin_file,
        user_config=user_config,
        package_files=package_files,
    )

    # Walk the source package bottom-up to determine what action to take for each path.
    # Bottom-up traversal ensures we know about children before deciding on parents.
    # This algorithm decides whether to:
    #   - LINK: Create a symlink to the whole directory/file
    #   - CREATE: Make a real directory (needed when children require renaming)
    #   - EXISTS: Directory already exists at destination
    #   - FAIL: Would overwrite an existing regular file
    #   - SKIP: Parent will be linked, so children need no action
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

        # First pass: check children for renaming needs and conflicts
        found_children_to_rename = False
        for child in child_directories + child_files:
            child_relative_source_path = relative_root_path / child
            if child_relative_source_path not in plan:
                continue
            # If any child needs renaming (e.g., dot-bashrc → .bashrc),
            # we can't link the whole directory - must CREATE it instead
            if plan[child_relative_source_path].requires_rename:
                found_children_to_rename = True
            # Fail if we would overwrite an existing regular file
            destination_path = (
                destination_root
                / plan[child_relative_source_path].relative_destination_path
            )
            if destination_path.exists() and destination_path.is_file():
                plan[child_relative_source_path].action = Action.FAIL

        # Second pass: decide action for current directory based on children and destination state
        if current_root_path == source_package_root:
            # Package root always EXISTS (it's the target directory)
            plan[relative_root_path].action = Action.EXISTS
        elif (destination_root / relative_destination_root_path).exists():
            # Directory already exists at destination - merge into it
            # This takes precedence over always-create because we can't create what exists
            plan[relative_root_path].action = Action.EXISTS
            # Mark ancestors as existing too
            mark_all_ancestors(
                relative_root_path,
                mark=Action.EXISTS,
                stop_mark=Action.EXISTS,
                plan=plan,
            )
        elif found_children_to_rename:
            # Can't link whole directory if children need renaming - must CREATE it
            plan[relative_root_path].action = Action.CREATE
            # Parent directories must also be created up to one that already exists
            mark_all_ancestors(
                relative_root_path,
                mark=Action.CREATE,
                stop_mark=Action.EXISTS,
                plan=plan,
            )
        elif _matches_always_create_at_exact_depth(relative_destination_root_path, always_create_matcher):
            # Directory matches always-create pattern AT ITS SPECIFIED DEPTH
            # This ensures shared directories like .config are real directories,
            # but subdirectories like .config/myapp can still be linked
            plan[relative_root_path].action = Action.CREATE
            # Parent directories must also be created up to one that already exists
            mark_all_ancestors(
                relative_root_path,
                mark=Action.CREATE,
                stop_mark=Action.EXISTS,
                plan=plan,
            )
            logger.debug(f"Directory {relative_destination_root_path} matches always-create pattern, will CREATE")
        else:
            # Directory doesn't exist and has no rename conflicts - we can link it
            plan[relative_root_path].action = Action.LINK

        # Third pass: mark children based on what we decided for this directory
        if plan[relative_root_path].action in {Action.CREATE, Action.EXISTS}:
            # Directory will exist (created or already there) - children should be linked
            mark_immediate_children(
                relative_root_path,
                mark=Action.LINK,
                allow_overwrite={Action.NONE},
                source_package_root=source_package_root,
                plan=plan,
            )
        elif plan[relative_root_path].action == Action.LINK:
            # Whole directory will be linked - children should be skipped
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
    logger.info(f"Planning install paths for source package {source_package_root}")

    # Initialize ignore rules (loads global ignore and will load .dotxignore files during traversal)
    ignore_rules = IgnoreRules(source_package_root)

    plan: Plan = {
        Path("."): PlanNode(
            action=Action.EXISTS,
            requires_rename=False,
            relative_source_path=Path("."),
            relative_destination_path=Path("."),
            is_dir=True,
        )
    }

    # Walk the source package top-down to build initial plan with all paths and rename info.
    # Top-down traversal ensures parent directories are processed before children,
    # which is critical for correctly calculating destination paths when renaming.
    # At this stage, we:
    #   - Create a PlanNode for every non-ignored file/directory
    #   - Determine which items need renaming (dot-foo → .foo)
    #   - Calculate correct destination paths considering parent renames
    #   - Mark everything as Action.NONE (actual actions decided later)
    for current_root, child_directories, child_files in os.walk(source_package_root):
        current_root_path = Path(current_root)

        # Prune ignored directories to prevent descending into them
        # This modifies child_directories in-place so os.walk won't recurse into them
        child_directories[:] = ignore_rules.prune_directories(
            current_root_path, child_directories
        )

        # Skip this directory if it should be ignored
        if ignore_rules.should_ignore(current_root_path):
            continue

        relative_root_path = current_root_path.relative_to(source_package_root)
        current_destination_path = plan[relative_root_path].relative_destination_path

        # Process each child (files and directories)
        for child in child_directories + child_files:
            requires_rename = False
            child_source_path = source_package_root / relative_root_path / child
            child_relative_source_path = relative_root_path / child

            # Skip ignored files and directories
            if ignore_rules.should_ignore(child_source_path):
                continue

            # Handle dot- prefix renaming: "dot-bashrc" → ".bashrc"
            # This allows tracking dotfiles in version control without hiding them
            if child.startswith("dot-"):
                requires_rename = True
                child_relative_destination_path = current_destination_path / (
                    "." + child[4:]
                )
            else:
                child_relative_destination_path = current_destination_path / child

            # Create PlanNode with path info and initial Action.NONE
            # The actual action (LINK, CREATE, etc.) will be determined in plan_install()
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

from pathlib import Path
from tempfile import TemporaryDirectory

from dotfiles.plan import Action, PlanNode
from dotfiles.install import plan_install


def test_install_nothing():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:

        plan = plan_install(Path(source_package_root), Path(destination_root))

        assert len(plan) == 0


def test_install_one_normal_file():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        file_path = Path("SIMPLE-FILE")
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 1
        assert plan[file_path] == PlanNode(Action.LINK, False, file_path, file_path)


def test_install_one_hidden_file():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        file_path = Path(".HIDDEN-FILE")
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 1
        assert plan[file_path] == PlanNode(Action.LINK, False, file_path, file_path)


def test_install_one_file_with_renaming():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        file_path = Path("dot-SIMPLE-FILE")
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 1
        assert plan[file_path] == PlanNode(Action.LINK, True, file_path, Path(".SIMPLE-FILE"))


def test_install_one_directory():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        dir_path = Path("SIMPLE-DIR")
        file_path = dir_path / "SIMPLE-FILE"
        (source_package_root_path / dir_path).mkdir()
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 2
        assert plan[dir_path] == PlanNode(Action.LINK, False, dir_path, dir_path)
        assert plan[file_path].action == Action.SKIP


def test_install_one_directory_with_hidden_file():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        dir_path = Path("SIMPLE-DIR")
        file_path = dir_path / ".HIDDEN-FILE"
        (source_package_root_path / dir_path).mkdir()
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 2
        assert plan[dir_path] == PlanNode(Action.LINK, False, dir_path, dir_path)
        assert plan[file_path].action == Action.SKIP


def test_install_one_directory_with_renamed_file():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        dir_path = Path("SIMPLE-DIR")
        file_path = dir_path / "dot-SIMPLE-FILE"
        (source_package_root_path / dir_path).mkdir()
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 2
        assert plan[dir_path] == PlanNode(Action.CREATE, False, dir_path, dir_path)
        assert plan[file_path] == PlanNode(Action.LINK, True, file_path, dir_path / ".SIMPLE-FILE")


def test_install_one_hidden_directory():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        dir_path = Path(".HIDDEN-DIR")
        file_path = dir_path / "SIMPLE-FILE"
        (source_package_root_path / dir_path).mkdir()
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 2
        assert plan[dir_path] == PlanNode(Action.LINK, False, dir_path, dir_path)
        assert plan[file_path].action == Action.SKIP


def test_install_one_renamed_directory():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        dir_path = Path("dot-SIMPLE-DIR")
        file_path = dir_path / "SIMPLE-FILE"
        (source_package_root_path / dir_path).mkdir()
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 2
        assert plan[dir_path] == PlanNode(Action.LINK, True, dir_path, Path(".SIMPLE-DIR"))
        assert plan[file_path].action == Action.SKIP


# TODO: More tests...
#   test that _multiple_ children of a Action.CREATE directory are all Action.LINK
#   test renamed director inside a renamed directory

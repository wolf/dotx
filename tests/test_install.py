from pathlib import Path
from tempfile import TemporaryDirectory

from dotx.install import plan_install
from dotx.plan import Action, PlanNode


def test_install_nothing():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:

        plan = plan_install(Path(source_package_root), Path(destination_root))

        assert len(plan) == 0


def test_install_normal_file():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        file_path = Path("SIMPLE-FILE")
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 1
        assert plan[file_path] == PlanNode(Action.LINK, False, file_path, file_path, False)


def test_install_normal_file_fail():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        destination_root_path = Path(destination_root)
        file_path = Path("SIMPLE-FILE")
        (source_package_root_path / file_path).touch()
        (destination_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 1
        assert plan[file_path] == PlanNode(Action.FAIL, False, file_path, file_path, False)


def test_install_hidden_file():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        file_path = Path(".HIDDEN-FILE")
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 1
        assert plan[file_path] == PlanNode(Action.LINK, False, file_path, file_path, False)


def test_install_file_with_renaming():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        file_path = Path("dot-SIMPLE-FILE")
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 1
        assert plan[file_path] == PlanNode(Action.LINK, True, file_path, Path(".SIMPLE-FILE"), False)


def test_install_dir():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        dir_path = Path("SIMPLE-DIR")
        file_path = dir_path / "SIMPLE-FILE"
        (source_package_root_path / dir_path).mkdir()
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 2
        assert plan[dir_path] == PlanNode(Action.LINK, False, dir_path, dir_path, True)
        assert plan[file_path].action == Action.SKIP


def test_install_dir_inside_dir():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        dir1_path = Path("SIMPLE-DIR1")
        dir2_path = dir1_path / "SIMPLE-DIR2"
        file_path = dir2_path / "SIMPLE-FILE"
        (source_package_root_path / dir2_path).mkdir(parents=True)
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 3
        assert plan[dir1_path] == PlanNode(Action.LINK, False, dir1_path, dir1_path, True)
        assert plan[dir2_path] == PlanNode(Action.SKIP, False, dir2_path, dir2_path, True)
        assert plan[file_path].action == Action.SKIP


def test_install_dir_with_hidden_file():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        dir_path = Path("SIMPLE-DIR")
        file_path = dir_path / ".HIDDEN-FILE"
        (source_package_root_path / dir_path).mkdir()
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 2
        assert plan[dir_path] == PlanNode(Action.LINK, False, dir_path, dir_path, True)
        assert plan[file_path].action == Action.SKIP


def test_install_dir_with_renamed_file():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        dir_path = Path("SIMPLE-DIR")
        file_path = dir_path / "dot-SIMPLE-FILE"
        (source_package_root_path / dir_path).mkdir()
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 2
        assert plan[dir_path] == PlanNode(Action.CREATE, False, dir_path, dir_path, True)
        assert plan[file_path] == PlanNode(Action.LINK, True, file_path, dir_path / ".SIMPLE-FILE", False)


def test_install_hidden_dir():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        dir_path = Path(".HIDDEN-DIR")
        file_path = dir_path / "SIMPLE-FILE"
        (source_package_root_path / dir_path).mkdir()
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 2
        assert plan[dir_path] == PlanNode(Action.LINK, False, dir_path, dir_path, True)
        assert plan[file_path].action == Action.SKIP


def test_install_renamed_dir():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        dir_path = Path("dot-SIMPLE-DIR")
        file_path = dir_path / "SIMPLE-FILE"
        (source_package_root_path / dir_path).mkdir()
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 2
        assert plan[dir_path] == PlanNode(Action.LINK, True, dir_path, Path(".SIMPLE-DIR"), True)
        assert plan[file_path].action == Action.SKIP


def test_install_several_normal_files():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        file1_path = Path("SIMPLE-FILE1")
        file2_path = Path("SIMPLE-FILE2")
        file3_path = Path("SIMPLE-FILE3")
        (source_package_root_path / file1_path).touch()
        (source_package_root_path / file2_path).touch()
        (source_package_root_path / file3_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 3
        assert plan[file1_path] == PlanNode(Action.LINK, False, file1_path, file1_path, False)
        assert plan[file2_path] == PlanNode(Action.LINK, False, file2_path, file2_path, False)
        assert plan[file3_path] == PlanNode(Action.LINK, False, file3_path, file3_path, False)


def test_install_dir_containing_several_files():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        dir_path = Path("SIMPLE-DIR")
        file1_path = dir_path / "SIMPLE-FILE1"
        file2_path = dir_path / "SIMPLE-FILE2"
        file3_path = dir_path / "SIMPLE-FILE3"
        (source_package_root_path / dir_path).mkdir()
        (source_package_root_path / file1_path).touch()
        (source_package_root_path / file2_path).touch()
        (source_package_root_path / file3_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 4
        assert plan[dir_path] == PlanNode(Action.LINK, False, dir_path, dir_path, True)
        assert plan[file1_path].action == Action.SKIP
        assert plan[file2_path].action == Action.SKIP
        assert plan[file3_path].action == Action.SKIP


def test_install_dir_containing_several_files_including_rename():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        dir_path = Path("SIMPLE-DIR")
        file1_path = dir_path / "dot-SIMPLE-FILE1"
        file2_path = dir_path / "SIMPLE-FILE2"
        file3_path = dir_path / "SIMPLE-FILE3"
        (source_package_root_path / dir_path).mkdir()
        (source_package_root_path / file1_path).touch()
        (source_package_root_path / file2_path).touch()
        (source_package_root_path / file3_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 4
        assert plan[dir_path] == PlanNode(Action.CREATE, False, dir_path, dir_path, True)
        assert plan[file1_path].action == Action.LINK
        assert plan[file1_path].requires_rename
        assert plan[file2_path].action == Action.LINK
        assert plan[file3_path].action == Action.LINK


def test_install_renamed_dir_inside_renamed_dir():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        dir1_path = Path("dot-SIMPLE-DIR1")
        dir2_path = dir1_path / "dot-SIMPLE-DIR2"
        file_path = dir2_path / "SIMPLE-FILE"
        (source_package_root_path / dir2_path).mkdir(parents=True)
        (source_package_root_path / file_path).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))

        assert len(plan) == 3
        assert plan[dir1_path] == PlanNode(Action.CREATE, True, dir1_path, Path(".SIMPLE-DIR1"), True)
        assert plan[dir2_path] == PlanNode(Action.LINK, True, dir2_path, Path(".SIMPLE-DIR1/.SIMPLE-DIR2"), True)
        assert plan[file_path].action == Action.SKIP

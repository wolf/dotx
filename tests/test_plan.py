from pathlib import Path
from tempfile import TemporaryDirectory

from dotx.install import plan_install
from dotx.plan import Action, extract_plan


def test_extract_dir_inside_dir_failures():
    with TemporaryDirectory() as source_package_root, TemporaryDirectory() as destination_root:
        source_package_root_path = Path(source_package_root)
        destination_root_path = Path(destination_root)
        dir1_path = Path("SIMPLE-DIR1")
        dir2_path = dir1_path / "SIMPLE-DIR2"
        file_path1 = dir2_path / "SIMPLE-FILE1"
        file_path2 = dir2_path / "SIMPLE-FILE2"
        file_path3 = dir1_path / "SIMPLE-FILE3"  # Note: this is at the higher level
        (source_package_root_path / dir2_path).mkdir(parents=True)
        (source_package_root_path / file_path1).touch()
        (source_package_root_path / file_path2).touch()
        (source_package_root_path / file_path3).touch()
        (destination_root_path / dir2_path).mkdir(parents=True)
        (destination_root_path / file_path1).touch()
        (destination_root_path / file_path2).touch()
        (destination_root_path / file_path3).touch()

        plan = plan_install(source_package_root_path, Path(destination_root))
        failures = extract_plan(plan, {Action.FAIL})

        assert len(failures) == 3
        assert plan[dir1_path].action == Action.EXISTS
        assert plan[dir2_path].action == Action.EXISTS
        assert plan[file_path1].action == Action.FAIL
        assert plan[file_path2].action == Action.FAIL
        assert plan[file_path3].action == Action.FAIL

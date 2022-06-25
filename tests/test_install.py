from pathlib import Path
import pytest
import tempfile

from dot.install import *


# TODO: figure out how to use TemporaryDirectory as a context manager

def test_install_nothing():
    source_package_root_dir = tempfile.TemporaryDirectory()
    destination_root_dir = tempfile.TemporaryDirectory()
    source_package_root = Path(source_package_root_dir.name)
    destination_root = Path(destination_root_dir.name)

    plan = plan_install(source_package_root, destination_root)
    assert len(plan) == 0

    source_package_root_dir.cleanup()
    destination_root_dir.cleanup()


def test_install_one_normal_file():
    source_package_root_dir = tempfile.TemporaryDirectory()
    destination_root_dir = tempfile.TemporaryDirectory()
    source_package_root = Path(source_package_root_dir.name)
    destination_root = Path(destination_root_dir.name)

    (source_package_root / "SIMPLE-FILE").touch()

    plan = plan_install(source_package_root, destination_root)
    assert len(plan) == 1
    assert plan[Path("SIMPLE-FILE")].action == "link"

    source_package_root_dir.cleanup()
    destination_root_dir.cleanup()


def test_install_one_hidden_file():
    source_package_root_dir = tempfile.TemporaryDirectory()
    destination_root_dir = tempfile.TemporaryDirectory()
    source_package_root = Path(source_package_root_dir.name)
    destination_root = Path(destination_root_dir.name)

    (source_package_root / ".HIDDEN-FILE").touch()

    plan = plan_install(source_package_root, destination_root)
    assert len(plan) == 1
    assert plan[Path(".HIDDEN-FILE")].action == "link"

    source_package_root_dir.cleanup()
    destination_root_dir.cleanup()


def test_install_one_file_with_renaming():
    source_package_root_dir = tempfile.TemporaryDirectory()
    destination_root_dir = tempfile.TemporaryDirectory()
    source_package_root = Path(source_package_root_dir.name)
    destination_root = Path(destination_root_dir.name)

    (source_package_root / "dot-SIMPLE-FILE").touch()

    plan = plan_install(source_package_root, destination_root)
    assert len(plan) == 1
    assert plan[Path("dot-SIMPLE-FILE")].action == "link-rename"

    source_package_root_dir.cleanup()
    destination_root_dir.cleanup()


def test_install_one_directory():
    source_package_root_dir = tempfile.TemporaryDirectory()
    destination_root_dir = tempfile.TemporaryDirectory()
    source_package_root = Path(source_package_root_dir.name)
    destination_root = Path(destination_root_dir.name)

    (source_package_root / "SIMPLE-DIR").mkdir()
    (source_package_root / "SIMPLE-DIR/SIMPLE-FILE").touch()

    plan = plan_install(source_package_root, destination_root)
    assert len(plan) == 2
    assert plan[Path("SIMPLE-DIR")].action == "link"
    assert plan[Path("SIMPLE-DIR/SIMPLE-FILE")].action == "skip"

    source_package_root_dir.cleanup()
    destination_root_dir.cleanup()


def test_install_one_directory_with_hidden_file():
    source_package_root_dir = tempfile.TemporaryDirectory()
    destination_root_dir = tempfile.TemporaryDirectory()
    source_package_root = Path(source_package_root_dir.name)
    destination_root = Path(destination_root_dir.name)

    (source_package_root / "SIMPLE-DIR").mkdir()
    (source_package_root / "SIMPLE-DIR/.HIDDEN-FILE").touch()

    plan = plan_install(source_package_root, destination_root)
    assert len(plan) == 2
    assert plan[Path("SIMPLE-DIR")].action == "link"
    assert plan[Path("SIMPLE-DIR/.HIDDEN-FILE")].action == "skip"

    source_package_root_dir.cleanup()
    destination_root_dir.cleanup()


def test_install_one_directory_with_renamed_file():
    source_package_root_dir = tempfile.TemporaryDirectory()
    destination_root_dir = tempfile.TemporaryDirectory()
    source_package_root = Path(source_package_root_dir.name)
    destination_root = Path(destination_root_dir.name)

    (source_package_root / "SIMPLE-DIR").mkdir()
    (source_package_root / "SIMPLE-DIR/dot-SIMPLE-FILE").touch()

    plan = plan_install(source_package_root, destination_root)
    assert len(plan) == 2
    assert plan[Path("SIMPLE-DIR")].action == "create"
    assert plan[Path("SIMPLE-DIR/dot-SIMPLE-FILE")].action == "link-rename"

    source_package_root_dir.cleanup()
    destination_root_dir.cleanup()


def test_install_one_hidden_directory():
    source_package_root_dir = tempfile.TemporaryDirectory()
    destination_root_dir = tempfile.TemporaryDirectory()
    source_package_root = Path(source_package_root_dir.name)
    destination_root = Path(destination_root_dir.name)

    (source_package_root / ".HIDDEN-DIR").mkdir()
    (source_package_root / ".HIDDEN-DIR/SIMPLE-FILE").touch()

    plan = plan_install(source_package_root, destination_root)
    assert len(plan) == 2
    assert plan[Path(".HIDDEN-DIR")].action == "link"
    assert plan[Path(".HIDDEN-DIR/SIMPLE-FILE")].action == "skip"

    source_package_root_dir.cleanup()
    destination_root_dir.cleanup()


def test_install_one_renamed_directory():
    source_package_root_dir = tempfile.TemporaryDirectory()
    destination_root_dir = tempfile.TemporaryDirectory()
    source_package_root = Path(source_package_root_dir.name)
    destination_root = Path(destination_root_dir.name)

    (source_package_root / "dot-SIMPLE-DIR").mkdir()
    (source_package_root / "dot-SIMPLE-DIR/SIMPLE-FILE").touch()

    plan = plan_install(source_package_root, destination_root)
    assert len(plan) == 2
    assert plan[Path("dot-SIMPLE-DIR")].action == "link-rename"
    assert plan[Path("dot-SIMPLE-DIR/SIMPLE-FILE")].action == "skip"

    source_package_root_dir.cleanup()
    destination_root_dir.cleanup()

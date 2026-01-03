"""dotx - A command-line tool to install a link-farm to your dotfiles."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("dotx")
except PackageNotFoundError:
    __version__ = "unknown"

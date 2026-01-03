"""dotx - A command-line tool to install a link-farm to your dotfiles."""

from importlib.metadata import version, metadata, PackageNotFoundError

try:
    __version__ = version("dotx")
    __metadata__ = metadata("dotx")
    __homepage__ = __metadata__.get("Home-page") or "https://github.com/wolf/dotx"
except PackageNotFoundError:
    __version__ = "unknown"
    __homepage__ = "https://github.com/wolf/dotx"

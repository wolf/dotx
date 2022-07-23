## The Basic Idea

### What `dotx` does; what it's _for_
#### The problem

You're a software developer with tons of _dotfiles_: `.bashrc`, `.vimrc`, `.tmux.conf`, `.inputrc`, and things living in
`.config` just to name a few.  You have to install these on every system you work on **and** keep them up-to-date as
they change.  Without some special setup, there's no one source of truth, no easy deploy, no version control.  The
obvious answer is to keep them in a `git` repo, but making your home directory _be_ that repo is no good.  And maybe you
don't even want them to live together.  Your `bash` files should be in a group, your `vim` files in a group, etc.

#### A solution

The solution is obvious: keep them in a git repo, divided up into packages (or multiple `git` repos if you prefer), and
install links in your home directory (or the _target_ directory) that point _into_ your `git` repo, at the source of
truth files.

The solution is so obvious in fact that of course there is already a `perl` tool called GNU `stow` that helps you do
exactly that.  GNU `stow` has a feature that you can ask it to rename files that look like this: `"dot-bashrc"` to this
`".bashrc"`.  This is incredibly helpful if, for instance, you want to edit your dotfiles on your iPad and your editor
of choice can't see files or directories that start with a  `"."`.  Keeping your files in this form means no invisible
files in your source repo so you can edit anywhere with anything.

Unfortunately, GNU `stow` has a bug that its renaming feature doesn't work on directories.  And it's also a very general
purpose tool.  It's made for installing a link-farm to any kind of package from anywhere to anywhere.

`dotx` is a simple tool with a simple goal: manage a link-farm of possibly renamed links to dotfiles.  Yes, you can use
it for other purposes, but it's tuned for its goal.  It does the renaming task if you want it, but if your source files
are named simply `.bashrc` it works just as well.

### The user interface
```
Usage: dotx [OPTIONS] COMMAND [ARGS]...

  Manage a link farm: (un)install groups of links from "source packages".

Options:
  --debug / --no-debug
  --verbose / --quiet
  --log FILE                Where to write the log (defaults to stderr)
  --target DIRECTORY        Where to install (defaults to $HOME)
  --dry-run / --no-dry-run  Just echo; don't actually (un)install.
  -i, --ignore TEXT         a pattern to exclude from installation
  --help                    Show this message and exit.

Commands:
  install    install [source-package...]
  uninstall  uninstall [source-package...]
```
So if you had a source package (a directory containing files) named `"bash"` containing `"dot-bashrc"` and
`"dot-bash_profile"` you could install links to those two files (named `".bashrc"` and `".bash_profile"`) into your
`${HOME}` directory by being in the parent of the source package and saying:
```bash
+$ pwd
/Users/wolf/builds/dotfiles

+$ ls -1
bash
tmux
vim

+$ tree -aL 1 bash
bash
├── README.md
├── dot-bash_profile
├── dot-bash_tools.bin
├── dot-bash_topics.d
└── dot-bashrc


+$ dotx --ignore=README.* install bash

+$ ls -al ~
...
lrwxr--r--    37 wolf 19 Jul 11:01 .bash_profile -> builds/dotfiles/bash/dot-bash_profile
lrwxr--r--    39 wolf 19 Jul 11:01 .bash_tools.bin -> builds/dotfiles/bash/dot-bash_tools.bin/
lrwxr--r--    38 wolf 19 Jul 11:01 .bash_topics.d -> builds/dotfiles/bash/dot-bash_topics.d/
lrwxr--r--    31 wolf 19 Jul 11:01 .bashrc -> builds/dotfiles/bash/dot-bashrc
...
```
If you've got some files in your source package that don't need to be linked, you can use the `--ignore` option (even
multiple times), like so:
```bash
dotx --ignore=README.* --ignore=.mypy_cache install bash tmux vim
```
You typically don't need the `--ignore` options during uninstall, which looks almost just like install:
```bash
dotx uninstall bash vim tmux
```
### How it works



### What's next
* ignore files that collect together patterns, a la `.gitignore` and the like
* ...

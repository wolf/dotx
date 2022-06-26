## The Basic Idea

High-level: we're going to fill in a data-structure that maps file-paths to actions/states where the actions/states
are: "create", "link", "skip", "exists".  "exists" means the named source directory already exists in the
destination, and therefore does not need to be linked.  If "exists" applied to a file, it should cancel the whole
operations: a file is "in the way" of the install.  "skip" means the named source file or directory will
automatically be installed by linking a higher-level directory.  "link" means the named source file or directory
must be installed by creating a symbolic link from the destination to the source object.  "create" means the source
directory does not exist in the destination, and cannot be linked, so it must be created as a real directory with
the appropriate name at the destination.

The data-structure we'll use as the "plan" will be a simple dictionary mapping pathlib.Path to str, where the str is
the action/state as described above.

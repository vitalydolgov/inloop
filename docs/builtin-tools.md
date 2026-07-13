# Built-in tools

The runtime gives the agent a small set of local filesystem tools in addition to installed extensions and configured [MCP servers](mcp.md). These tools operate relative to the process's current working directory unless a path is absolute.

## Filesystem tools

These tools inspect or change files and directories.

### `read`

Reads a text file and returns numbered lines. `path` is required. `offset` is an optional 1-based starting line, and `limit` caps the number of returned lines. It reads one file only and does not fetch URLs or search other files.

### `search`

Searches one text file for a regular expression and returns each matching line with its 1-based line number. `path` and `pattern` are required; `ignore_case: true` makes the search case-insensitive. It searches one file only, does not search file names or directory trees, and does not modify the file.

### `write`

Creates a text file or replaces the entire contents of an existing one. It requires `path` and `content`. Parent directories must already exist; use `mkdir` first when necessary.

### `append`

Appends text to the end of a file, creating it when it does not exist. It requires `path` and `content`. Parent directories must already exist; use `mkdir` first when necessary. It preserves all existing content and does not insert a separator, so include a newline in `content` when one is needed.

### `edit`

Replaces one exact text span in an existing text file. It requires `path`, `old`, and `new`. The `old` text must be non-empty and occur exactly once; an empty `new` value deletes the matched text. The file is left unchanged when the match is missing or ambiguous.

### `list`

Lists the entries in one directory, sorted by name and returned one entry per line. The optional `path` argument defaults to the current directory. It does not recurse, read file contents, or modify the filesystem.

### `find`

Finds files recursively below a directory by matching their names against a glob pattern. `pattern` is required and `path` defaults to the current directory; patterns such as `*.py` and `README.md` are supported. It searches file names rather than file contents and does not modify the filesystem.

### `mkdir`

Creates a directory at `path`. It refuses to replace an existing path. Pass `parents: true` to create missing parent directories; by default, parent directories must already exist.

### `move`

Moves a file or directory from `source` to `destination`. It can also rename a path. The destination must not already exist, and its parent directory must already exist.

### `copy`

Copies a file or directory from `source` to `destination`. File copies support binary content and preserve file metadata. Directory copies require `recursive: true`. The destination must not already exist, and its parent directory must already exist.

### `delete`

Deletes a file or directory at `path`. Files and empty directories can be deleted without additional arguments. Non-empty directories require `recursive: true`; deletion cannot be undone.

## Errors and safety

Filesystem failures are returned as tool results so the agent can respond or try another action without ending the conversation. Mutating tools do not silently overwrite destinations, and recursive operations must be requested explicitly where applicable.

The current local adapter does not restrict paths to a configured workspace. It can access any path permitted by the process, so filesystem tools should not be exposed to untrusted users until a workspace or permission policy is added.

## Implementation

The tool adapters live under `app/builtin/filesystem/`. They depend on the `FileSystem` port in `app/filesystem.py`, while `LocalFileSystem` in `infra/local_filesystem.py` provides the disk-backed implementation. The composition roots add these tools to both the terminal and Telegram runtimes.

# patch-notes

A [semantic-release](https://github.com/semantic-release/semantic-release) plugin that lets a single
commit carry several patch notes. Each `Patch-Note:` line in a commit message becomes a release-note
line, exactly as if it were a commit of its own.

It wraps `@semantic-release/commit-analyzer` and `@semantic-release/release-notes-generator`, so
regular conventional commits are analyzed and rendered by the very same code as before.

## Usage

List the plugin where the two standard plugins used to be, and move their options under `analyzer`
and `notes`. The path is relative to the repository root.

```json
{
  "plugins": [
    [
      "./.github/patch-notes-plugin/patch-notes.js",
      {
        "analyzer": { "preset": "conventionalcommits" },
        "notes": { "preset": "conventionalcommits" }
      }
    ]
  ]
}
```

Both standard plugins, and the preset they use, must be installed alongside semantic-release. The
plugin has no dependencies of its own.

### Options

| Option | Description |
|---|---|
| `analyzer` | Options for `@semantic-release/commit-analyzer`, forwarded as they are. |
| `notes` | Options for `@semantic-release/release-notes-generator`, forwarded as they are. |

Global semantic-release options reach both plugins the same way they would if each were listed on its
own.

## Writing patch notes

Add one line per note to the commit message:

```text
chore: Constructors decide which type hints they handle

Free text can go here.

Patch-Note: feat!: Pluggable constructors with Cli(constructors=...)
Patch-Note: feat: FlagConstructor
Patch-Note: fix(help): Subcommand help hides the type
```

A line is a patch note when:

- it is not the first line of the message (the subject is never a note);
- and it starts with `patch-note:`, ignoring case and surrounding whitespace.

What follows the prefix is handed to the standard plugins as the message of a commit, so it should be
a conventional commit header, `type(scope)!: description`. Those plugins skip anything that is not
one, so a malformed note silently produces no line; the pull request preview shows what was
recognized. Notes may be anywhere after the subject, and values are a single line.

### What a note does

A note behaves exactly like a commit with that header:

| Note | Release notes section | Version bump |
|---|---|---|
| `feat: ...` | Features | minor |
| `fix: ...` / `perf: ...` | Bug Fixes / Performance | patch |
| `feat!: ...` (any type with `!`) | its section, plus BREAKING CHANGES | major |
| hidden types (`chore`, `docs`, ...) | not shown | none |

Notes link to the commit that carries them. The commit's own subject still counts as usual, so a
commit that only exists to hold notes should use a hidden type such as `chore:`.

## Limitations

- Notes cannot be nested, and a note cannot carry a body or a `BREAKING CHANGE:` footer of its own;
  use `!` in the header instead.

## How it works

semantic-release gives every plugin a deep copy of the context, so one plugin cannot change the
commits that another plugin sees. The only way to feed the standard plugins extra commits is to call
them, which is why this plugin replaces them in the list and delegates to them. For every note it adds
a virtual commit, a copy of the real commit with the note as its message, right after the real one,
and hands the expanded list to the standard plugins.

The standard plugins are looked up from the working directory and from the directory of the script
that runs semantic-release (on top of the usual search paths, which include `NODE_PATH`), so they are
found when they are installed next to the script that runs semantic-release as well as when they are
installed in the repository.

## Development

The tests need the standard plugins and the preset to be resolvable from the working directory. They
are installed by the [semantic-release runner](../semantic-release-runner/README.md), which pins the
versions, so run the tests from there (Node 22.12 or later, which can `require` the ESM-only
standard plugins):

```bash
cd .github/semantic-release-runner
npm ci
npm test
```

`npm test` runs the tests of the runner as well. To run only these:

```bash
node --test "../patch-notes-plugin/*.test.js"
```

The tests only use the exported hooks and compare the results with what the standard plugins produce
for equivalent real commits, so they should keep passing through any refactor that keeps the behavior
described above.

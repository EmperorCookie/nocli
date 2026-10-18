# semantic-release-runner

A local GitHub Action that runs [semantic-release](https://github.com/semantic-release/semantic-release)
for the workflows of this repository, in two stages: a **plan** stage that analyzes the commits and
decides the release, and an **apply** stage that makes that release without analyzing anything again.

It installs semantic-release and the plugins that `.releaserc` uses from its own `package.json` and
`package-lock.json` (`npm ci`), on the latest Node, so the versions are pinned and reviewable in one
place. The patch-notes plugin is not part of it; it is a separate package that `.releaserc` lists by
path, see [patch-notes-plugin](../patch-notes-plugin/README.md).

## Usage

The repository must be checked out first, because the action reads `.releaserc` from it and is itself
loaded from it.

```yaml
- uses: ./.github/semantic-release-runner
  id: plan
  with:
    dry-run: true         # plan stage: analyze only, publish nothing
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

- uses: ./.github/semantic-release-runner
  with:
    plan: ${{ steps.plan.outputs.plan }}   # apply stage: follow the plan
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

The credentials and the git identity are the ones of the step that uses the action, as for any
semantic-release run.

### Stages

| Inputs | What happens |
|---|---|
| `dry-run: true` | **Plan.** The commits are analyzed and the release is decided, but nothing is published. |
| `plan: <plan>` | **Apply.** The release type and the notes come from the plan; the commits are not analyzed and the notes are not generated again. |
| neither | Both in one go, like running semantic-release directly. |

The plan is only meant for a run in the same workflow run as the plan stage. It is not checked against
the repository, so the workflow should be configured to run again when a commit lands in between.

An empty plan (`{}`) means there is nothing to release, and applying it does nothing.

### Inputs

| Input | Description |
|---|---|
| `dry-run` | `"true"` to analyze only. |
| `plan` | The `plan` output of an earlier run. |
| `ci` | `"true"` or `"false"` to override semantic-release's CI detection. |
| `branches` | A JSON array that replaces the `branches` option of `.releaserc`. |
| `unset-gha-env` | `"true"` to hide GitHub Actions from semantic-release. |

### Outputs

| Output | Description |
|---|---|
| `plan` | What would be (or was) released, as JSON, to give to a later run. |
| `published` | `"true"` when there is a release to make (or made), `"false"` otherwise. |
| `version` | The version of the release, empty when there is none. |
| `notes` | The release notes, empty when there is none. |

## Running on a pull request

semantic-release is built to run on the branches it releases from, and this is what a pull request
needs for it to analyze anything, as the patch-notes preview does:

- **`unset-gha-env: true`.** On a `pull_request` event semantic-release detects a pull request and
  stops before analyzing: it only analyzes the branches in `branches`, and the branch it sees is
  `refs/pull/N/merge`. Hiding GitHub Actions makes it use the branch that is checked out.
- **`ci: false`.** Without GitHub Actions to detect, semantic-release no longer finds a CI environment
  and would stop; this skips that check.
- **A local branch named after the pull request's branch.** The checkout of a pull request is
  detached, and semantic-release only analyzes a checked out branch that is listed in `branches`.
  The workflow creates it (`git switch -c "$HEAD_REF"`) and lists it in `branches`. The branch must
  also exist on the remote, which is why `branches` keeps `main` next to it.
- **`branches` is data.** The branch name is given as a JSON string (`toJSON(github.head_ref)`) and read
  with `JSON.parse`, and everything the runner takes goes through the environment, so a hostile branch
  name cannot become code.

Pull requests from forks are not supported by the preview: they get a read-only token.

## How it works

`run.js` calls semantic-release's API instead of its command line, which is what gives it the release
as a value to turn into outputs. In the apply stage it replaces the `analyzeCommits` and
`generateNotes` steps with functions that return the plan's type and notes, and everything else
(`verifyConditions`, `prepare`, `publish`, the plugins of `.releaserc`) runs as usual. The next version
is worked out by semantic-release from the last release and the planned type, so it matches the plan.

Outputs are written to `$GITHUB_OUTPUT` with a random delimiter, because the notes derive from commit
messages.

## Development

The tests are contract tests, and `npm test` also runs the ones of the patch-notes plugin, because
this is where its dependencies are installed (Node 22.12 or later):

```bash
cd .github/semantic-release-runner
npm ci
npm test
```

To run the runner locally against a repository, run `node run.js` from that repository with the
inputs in the environment (`INPUT_DRY_RUN`, `INPUT_PLAN`, `INPUT_CI`, `INPUT_BRANCHES`,
`INPUT_UNSET_GHA_ENV`); without `GITHUB_OUTPUT` the outputs are printed.

"use strict";

// Contract tests for the plugin: they only call the exported hooks and compare the results with what
// the standard plugins produce for equivalent real commits, so they do not depend on how the plugin
// is implemented. See README.md for how to run them.

const test = require("node:test");
const assert = require("node:assert/strict");

const plugin = require("./patch-notes.js");

const PRESET = { preset: "conventionalcommits" };
const CONFIG = { analyzer: PRESET, notes: PRESET };

const standard = (name) => require(require.resolve(name, { paths: [process.cwd()] }));
const analyzer = standard("@semantic-release/commit-analyzer");
const generator = standard("@semantic-release/release-notes-generator");

let counter = 0;
const nextHash = () => (++counter).toString(16).padStart(40, "0");

/** A commit as semantic-release hands it to plugins. */
function commit(message, hash = nextHash()) {
  const [subject, ...body] = message.split(/\r?\n/);
  return {
    hash,
    message,
    subject,
    body: body.join("\n"),
    gitTags: "",
    commit: { long: hash, short: hash.slice(0, 7) },
    committerDate: new Date("2026-01-01T00:00:00Z"),
  };
}

function contextFor(commits) {
  return {
    commits,
    logger: { log() {}, warn() {}, error() {}, success() {} },
    cwd: process.cwd(),
    env: {},
    options: { repositoryUrl: "https://github.com/example/repo.git" },
    lastRelease: { gitTag: "v1.0.0", gitHead: "a".repeat(40) },
    nextRelease: { version: "2.0.0", gitTag: "v2.0.0", gitHead: "b".repeat(40) },
  };
}

/** What the plugin yields for these commits. */
const ours = (commits) => ({
  type: plugin.analyzeCommits(CONFIG, contextFor(commits)),
  notes: plugin.generateNotes(CONFIG, contextFor(commits)),
});

/** What the standard plugins yield for these commits, listed on their own. */
const reference = (commits) => ({
  type: analyzer.analyzeCommits(PRESET, contextFor(commits)),
  notes: generator.generateNotes(PRESET, contextFor(commits)),
});

async function assertSame(actualCommits, expectedCommits) {
  const actual = ours(actualCommits);
  const expected = reference(expectedCommits);
  assert.equal(await actual.type, await expected.type);
  assert.equal(await actual.notes, await expected.notes);
}

test("commits without patch notes give exactly the standard results", async () => {
  const messages = [
    "feat: Add A",
    "fix(scope): Fix B",
    "chore: Tidy C",
    "feat!: Break D",
    "feat: E\n\nSome body\n\nBREAKING CHANGE: details",
    "docs: F\n\nMentions patch-note without a colon",
  ];
  const commits = messages.map((message) => commit(message));
  await assertSame(commits, commits);
});

test("a patch note behaves like a commit with that header", async () => {
  const hash = nextHash();
  const container = commit("chore: Container\n\nPatch-Note: feat: Add X", hash);
  await assertSame([container], [container, commit("feat: Add X", hash)]);
});

test("several patch notes each behave like their own commit, in order", async () => {
  const hash = nextHash();
  const container = commit(
    "chore: Container\n\nPatch-Note: feat: Add X\nPatch-Note: fix(core): Fix Y\nPatch-Note: feat!: Z",
    hash
  );
  await assertSame(
    [container],
    [container, commit("feat: Add X", hash), commit("fix(core): Fix Y", hash), commit("feat!: Z", hash)]
  );
});

test("patch notes decide the release type like commits do", async () => {
  const cases = [
    ["Patch-Note: feat!: Break", "major"],
    ["Patch-Note: feat: Add", "minor"],
    ["Patch-Note: fix: Fix", "patch"],
    ["Patch-Note: fix: Fix\nPatch-Note: feat: Add", "minor"],
    ["Patch-Note: chore: Tidy\nPatch-Note: docs: Explain", null],
  ];
  for (const [notes, expected] of cases) {
    const result = await ours([commit(`chore: Container\n\n${notes}`)]).type;
    assert.equal(result ?? null, expected, notes);
  }
});

test("a breaking patch note appears among the breaking changes", async () => {
  const notes = await ours([commit("chore: Container\n\nPatch-Note: feat!: Pluggable constructors")]).notes;
  assert.match(notes, /BREAKING CHANGES/);
  assert.match(notes, /Pluggable constructors/);
});

test("patch notes link to the commit they came from", async () => {
  const hash = nextHash();
  const notes = await ours([commit("chore: Container\n\nPatch-Note: feat: Add X", hash)]).notes;
  assert.ok(notes.includes(hash.slice(0, 7)));
});

test("patch notes are found anywhere after the subject", async () => {
  const hash = nextHash();
  const expected = [commit("chore: C", hash), commit("feat: Add X", hash)];
  const bodies = [
    "chore: C\nPatch-Note: feat: Add X",
    "chore: C\n\nPatch-Note: feat: Add X\n\nTrailing paragraph",
    "chore: C\n\nIntro paragraph\nPatch-Note: feat: Add X\nmore text",
  ];
  for (const message of bodies) {
    await assertSame([commit(message, hash)], expected);
  }
});

test("the prefix is case-insensitive and whitespace is trimmed", async () => {
  const hash = nextHash();
  const expected = [commit("chore: C", hash), commit("feat: Add X", hash)];
  const variants = [
    "PATCH-NOTE: feat: Add X",
    "patch-note:feat: Add X",
    "   Patch-Note:    feat: Add X   ",
    "\tpatch-NOTE: feat: Add X\t",
  ];
  for (const line of variants) {
    await assertSame([commit(`chore: C\n\n${line}`, hash)], expected);
    await assertSame([commit(`chore: C\r\n\r\n${line}\r\n`, hash)], expected);
  }
});

test("the subject line is never a patch note", async () => {
  const single = commit("Patch-Note: feat: Add X");
  await assertSame([single], [single]);
});

test("a value that is not a conventional header is ignored", async () => {
  const container = commit("chore: C\n\nPatch-Note: not a header\nPatch-Note: feat\nPatch-Note:");
  const actual = ours([container]);
  const expected = reference([container]);
  assert.equal((await actual.type) ?? null, (await expected.type) ?? null);
  assert.equal(await actual.notes, await expected.notes);
});

// Contract tests for the plan: they only use the exported functions. See README.md for how to run
// them.

import test from "node:test";
import assert from "node:assert/strict";

import { parsePlan, stepsFor, toPlan } from "./plan.js";

const RELEASE = {
  type: "minor",
  version: "1.1.0",
  notes: "# 1.1.0\n\n* feat: Add X",
};

const logger = { log() {} };

test("a result without a release gives an empty plan", () => {
  assert.deepEqual(toPlan(false), {});
  assert.deepEqual(toPlan({ lastRelease: {} }), {});
});

test("a plan survives being written and read", () => {
  const plan = toPlan({ nextRelease: { ...RELEASE, gitTag: "v1.1.0", gitHead: "a".repeat(40) } });
  assert.deepEqual(plan, RELEASE);
  assert.deepEqual(parsePlan(JSON.stringify(plan)), RELEASE);
  assert.deepEqual(parsePlan("{}"), {});
});

test("a plan that is not a plan is rejected", () => {
  const texts = [
    "not json",
    "null",
    "[]",
    '"text"',
    JSON.stringify({ ...RELEASE, version: "" }),
    JSON.stringify({ ...RELEASE, notes: 1 }),
    JSON.stringify({ version: "1.1.0" }),
  ];
  for (const text of texts) assert.throws(() => parsePlan(text), Error, text);
});

test("following a plan gives the planned type and notes without looking at commits", async () => {
  const steps = stepsFor(RELEASE);
  assert.equal(await steps.analyzeCommits[0]({}, { logger }), RELEASE.type);
  assert.equal(await steps.generateNotes[0]({}, {}), RELEASE.notes);
  assert.equal(await steps.generateNotes[0]({}, {}), RELEASE.notes);
});

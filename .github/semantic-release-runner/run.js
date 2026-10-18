/**
 * Runs semantic-release for the workflows, in the stage that the inputs ask for. See README.md.
 *
 * Inputs come from the environment, so values that derive from the pull request or from commit
 * messages are never part of a command line or a script text:
 *
 * - `INPUT_DRY_RUN`: "true" to analyze only; nothing is published.
 * - `INPUT_PLAN`: a plan from an earlier run; when given, nothing is analyzed again.
 * - `INPUT_CI`: "true" or "false" to override semantic-release's CI detection.
 * - `INPUT_BRANCHES`: a JSON array that replaces the `branches` option.
 * - `INPUT_UNSET_GHA_ENV`: "true" to hide GitHub Actions from semantic-release.
 *
 * Outputs go to `$GITHUB_OUTPUT`, or to the console when that is not set.
 */

import { appendFileSync } from "node:fs";
import { randomUUID } from "node:crypto";

import { parsePlan, stepsFor, toPlan } from "./plan.js";

/**
 * Reads a boolean input.
 *
 * @param {string} name The name of the environment variable.
 * @returns {boolean|undefined} The value, or undefined when the input is empty.
 */
function flag(name) {
  const value = process.env[name] ?? "";
  if (value === "") return undefined;
  if (value !== "true" && value !== "false") {
    throw new Error(`Expected ${name} to be "true" or "false"; got ${value}`);
  }
  return value === "true";
}

/**
 * Reads the `branches` input.
 *
 * @returns {Array|undefined} The branches, or undefined when the input is empty.
 */
function branches() {
  const text = process.env.INPUT_BRANCHES ?? "";
  if (text === "") return undefined;
  let value;
  try {
    value = JSON.parse(text);
  } catch (error) {
    throw new Error(`Expected INPUT_BRANCHES to be JSON; got ${error.message}`);
  }
  if (!Array.isArray(value)) {
    throw new Error(`Expected INPUT_BRANCHES to be a JSON array; got ${text}`);
  }
  return value;
}

/**
 * Publishes outputs for the steps that come after this one.
 *
 * @param {Object<string, string>} outputs The value of each output.
 */
function publish(outputs) {
  for (const [name, value] of Object.entries(outputs)) {
    if (!process.env.GITHUB_OUTPUT) {
      console.log(`${name}=${value}`);
      continue;
    }
    // Values derive from commit messages, so the delimiter must not be guessable
    const delimiter = `output_${randomUUID()}`;
    appendFileSync(process.env.GITHUB_OUTPUT, `${name}<<${delimiter}\n${value}\n${delimiter}\n`);
  }
}

/**
 * Runs the stage that the inputs ask for.
 */
async function main() {
  const planText = process.env.INPUT_PLAN ?? "";
  const given = planText === "" ? undefined : parsePlan(planText);

  if (given && Object.keys(given).length === 0) {
    console.log("The plan has nothing to release.");
    publish({ plan: "{}", published: "false", version: "", notes: "" });
    return;
  }

  const options = {};
  if (flag("INPUT_DRY_RUN")) options.dryRun = true;
  const ci = flag("INPUT_CI");
  if (ci !== undefined) options.ci = ci;
  const replacement = branches();
  if (replacement) options.branches = replacement;
  if (given) Object.assign(options, stepsFor(given));

  const env = { ...process.env };
  if (flag("INPUT_UNSET_GHA_ENV")) delete env.GITHUB_ACTIONS;

  const { default: semanticRelease } = await import("semantic-release");
  const plan = toPlan(await semanticRelease(options, { env }));

  publish({
    plan: JSON.stringify(plan),
    published: plan.version ? "true" : "false",
    version: plan.version ?? "",
    notes: plan.notes ?? "",
  });
}

main().catch((error) => {
  for (const each of error.errors ?? [error]) {
    console.error(`::error::${each.message.replace(/\r?\n/g, "%0A")}`);
  }
  process.exitCode = 1;
});

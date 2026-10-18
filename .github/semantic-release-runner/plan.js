/**
 * The release plan: what the plan stage decided, in a form the apply stage can follow without
 * analyzing the commits again. See README.md for the stages.
 */

const FIELDS = ["type", "version", "notes"];

/**
 * Reduces the result of semantic-release to a plan.
 *
 * @param {object|false} result What semantic-release resolved with.
 * @returns {object} The plan, which is empty when there is nothing to release.
 */
export function toPlan(result) {
  if (!result || !result.nextRelease) return {};
  return Object.fromEntries(FIELDS.map((field) => [field, result.nextRelease[field]]));
}

/**
 * Reads a plan produced by `toPlan`.
 *
 * @param {string} text The plan as JSON.
 * @returns {object} The plan, which is empty when there is nothing to release.
 * @throws {Error} When the text is not JSON, or is neither an empty plan nor a full one.
 */
export function parsePlan(text) {
  let plan;
  try {
    plan = JSON.parse(text);
  } catch (error) {
    throw new Error(`Expected \`plan\` to be JSON; got ${error.message}`);
  }
  if (plan === null || typeof plan !== "object" || Array.isArray(plan)) {
    throw new Error(`Expected \`plan\` to be a JSON object; got ${text}`);
  }
  if (Object.keys(plan).length === 0) return plan;
  const invalid = FIELDS.filter((field) => typeof plan[field] !== "string" || !plan[field]);
  if (invalid.length > 0) {
    throw new Error(`Expected \`plan\` to have non-empty ${invalid.join(", ")}; got ${text}`);
  }
  return Object.fromEntries(FIELDS.map((field) => [field, plan[field]]));
}

/**
 * Builds the semantic-release steps that replace the analysis and the notes generation with the
 * plan, so the apply stage publishes what the plan stage decided.
 *
 * The plan is not checked against the repository: it is meant for a run of the same workflow as the
 * plan, and the workflow should be configured to run again when a commit lands in between.
 *
 * @param {object} plan A full plan, not an empty one.
 * @returns {object} Step options to merge into the options given to semantic-release.
 */
export function stepsFor(plan) {
  async function plannedAnalysis(_pluginConfig, { logger }) {
    logger.log("Following the plan: a %s release", plan.type);
    return plan.type;
  }

  async function plannedNotes() {
    return plan.notes;
  }

  return { analyzeCommits: [plannedAnalysis], generateNotes: [plannedNotes] };
}

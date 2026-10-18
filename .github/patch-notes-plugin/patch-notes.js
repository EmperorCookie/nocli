"use strict";

/**
 * semantic-release plugin that lets one commit carry several patch notes.
 *
 * Every line of a commit message (after the subject) that starts with `Patch-Note:`, e.g.
 * `Patch-Note: feat!: Pluggable constructors`, is treated as if its value were a commit of its own.
 * Whether that value is a conventional commit is left to the standard plugins, which skip commits
 * that are not. This plugin wraps `@semantic-release/commit-analyzer` and
 * `@semantic-release/release-notes-generator`, so it replaces both in the plugin list; the options
 * for each go under `analyzer` and `notes`. See README.md for the rules and for why it wraps them.
 */

const path = require("path");

const NOTE_PREFIX = /^patch-note:/i;

/**
 * Finds the patch notes in a commit message.
 *
 * @param {string} message The full commit message.
 * @returns {string[]} The value of every line that starts with the prefix.
 */
function notesOf(message) {
  const [, ...lines] = message.split(/\r?\n/); // The first line is the subject
  return lines
    .map((line) => line.trim())
    .filter((line) => NOTE_PREFIX.test(line))
    .map((line) => line.replace(NOTE_PREFIX, "").trim());
}

/**
 * Adds a virtual commit right after each commit that carries patch notes.
 *
 * A virtual commit is a copy of the real one with the note as its message, so it shares the hash
 * (and therefore the link) of the commit it came from.
 *
 * @param {object[]} commits The commits of the release.
 * @returns {object[]} The commits, with their notes expanded.
 */
function expand(commits) {
  return commits.flatMap((commit) => {
    const virtuals = notesOf(commit.message || "").map((note) => ({
      ...commit,
      message: note,
      subject: note,
      body: "",
      gitTags: "",
    }));
    return [commit, ...virtuals];
  });
}

/**
 * Loads a standard plugin from wherever semantic-release itself was installed.
 *
 * Tools that run semantic-release often install plugins next to themselves and not next to this
 * file, so the usual `require` would not find them. The lookup therefore starts from the working
 * directory and from the script that is running (semantic-release), on top of the usual search
 * paths, which include `NODE_PATH`.
 *
 * @param {string} name The package name of the plugin.
 * @returns {object} The plugin module.
 */
function load(name) {
  const paths = [process.cwd()];
  if (process.argv[1]) paths.push(path.dirname(path.resolve(process.argv[1])));
  try {
    return require(require.resolve(name, { paths }));
  } catch (error) {
    throw new Error(`Expected \`${name}\` to be installed; got ${error.message}`);
  }
}

/**
 * Builds the options a standard plugin would have received had it been listed on its own.
 *
 * @param {object} pluginConfig The options of this plugin, including the global ones.
 * @param {"analyzer"|"notes"} key Which standard plugin the options are for.
 * @returns {object} The options for that plugin.
 */
function optionsFor(pluginConfig, key) {
  const { analyzer, notes, ...shared } = pluginConfig;
  return { ...shared, ...pluginConfig[key] };
}

async function analyzeCommits(pluginConfig, context) {
  const commits = expand(context.commits);
  return load("@semantic-release/commit-analyzer").analyzeCommits(
    optionsFor(pluginConfig, "analyzer"),
    { ...context, commits }
  );
}

async function generateNotes(pluginConfig, context) {
  const commits = expand(context.commits);
  return load("@semantic-release/release-notes-generator").generateNotes(
    optionsFor(pluginConfig, "notes"),
    { ...context, commits }
  );
}

module.exports = { analyzeCommits, generateNotes };

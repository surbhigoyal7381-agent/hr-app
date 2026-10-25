/* Slice 064: run the Positions page checks as part of the DOM tests in CI.
 * The checks themselves are in scripts/check_positions_tree.js, where they
 * can also be run on their own: node scripts/check_positions_tree.js */
require("../../scripts/check_positions_tree.js");

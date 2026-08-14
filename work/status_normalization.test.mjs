import test from "node:test";
import assert from "node:assert/strict";

import { normalizeFinalStatus } from "./status_normalization.mjs";

test("closure labels are normalized without changing active statuses", () => {
  assert.equal(normalizeFinalStatus("Closed"), "closed");
  assert.equal(normalizeFinalStatus("종결"), "closed");
  assert.equal(normalizeFinalStatus("In Progress"), "In Progress");
});

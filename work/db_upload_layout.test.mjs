import test from "node:test";
import assert from "node:assert/strict";

import { DB_HEADERS, toUploadRows } from "./db_upload_layout.mjs";

test("upload rows use 24 snake_case headers and remove blank rows", () => {
  const sourceHeaders = ["Case ID", ...Array(23).fill("source")];
  const blankRow = Array(24).fill(null);
  const dataRow = ["COM-001", ...Array(23).fill("value")];

  const result = toUploadRows([sourceHeaders, blankRow, dataRow]);

  assert.equal(DB_HEADERS.length, 24);
  assert.equal(result.length, 2);
  assert.equal(result[0][0], "case_id");
  assert.equal(result[0][23], "original_mail_body_embedding");
  assert.equal(result[1][0], "COM-001");
  assert.ok(DB_HEADERS.every((header) => /^[a-z][a-z0-9_]*$/.test(header)));
});

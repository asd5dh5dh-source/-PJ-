import test from "node:test";
import assert from "node:assert/strict";

import { rowsToCsv } from "./csv_serialization.mjs";

test("CSV serialization preserves commas, quotes, newlines, and blank cells", () => {
  const csv = rowsToCsv([
    ["name", "mail", "note", "blank"],
    ["A, Inc.", "say \"hello\"", "line 1\nline 2", null],
  ]);

  assert.equal(
    csv,
    '\uFEFFname,mail,note,blank\r\n"A, Inc.","say ""hello""","line 1\nline 2",\r\n',
  );
});

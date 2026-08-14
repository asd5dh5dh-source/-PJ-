# DB Upload Sheets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add immediately uploadable 135-row production and 15-row test sheets with English `snake_case` headers to the existing embedding workbook.

**Architecture:** Extend the existing artifact-tool workbook builder. Reuse the completed `DB 135` and `Test 15` sheets as data sources, remove the intentional blank second row, replace only the headers through a fixed mapping, and append two formatted sheets.

**Tech Stack:** JavaScript, Node.js, `@oai/artifact-tool`, Node built-in test runner

## Global Constraints

- Preserve `Total 150`, `DB 135`, and `Test 15` unchanged.
- Add only `DB Upload 135` and `Test Upload 15`.
- Use 24 lowercase English `snake_case` headers.
- Keep source values, `closed` status normalization, and pgvector-compatible 384-dimensional vector strings.
- Keep `Y/N` values and department strings unchanged.

---

### Task 1: Header Mapping and Upload Rows

**Files:**
- Create: `work/db_upload_layout.test.mjs`
- Create: `work/db_upload_layout.mjs`

**Interfaces:**
- Consumes: source worksheet rows shaped as 24-cell arrays.
- Produces: `DB_HEADERS: string[]` and `toUploadRows(rows: unknown[][]): unknown[][]`.

- [ ] **Step 1: Write the failing test**

```js
test("upload rows use 24 snake_case headers and remove blank rows", () => {
  const rows = [["Case ID", ...Array(23).fill("x")], Array(24).fill(null), ["COM-001", ...Array(23).fill("v")]];
  const result = toUploadRows(rows);
  assert.equal(DB_HEADERS.length, 24);
  assert.equal(result.length, 2);
  assert.equal(result[0][0], "case_id");
  assert.equal(result[1][0], "COM-001");
});
```

- [ ] **Step 2: Run the test and confirm failure because the module is absent**

Run: `node --test work/db_upload_layout.test.mjs`

- [ ] **Step 3: Implement the fixed 24-column mapping and blank-row removal**

```js
export const DB_HEADERS = ["case_id", "customer_name", "country", "voc_type", "voc_subtype", "priority", "customer_request", "original_mail_body", "responsible_departments", "received_at", "first_response_at", "containment_at", "root_cause_action_5d_at", "customer_reply_at", "final_status", "delay_stage", "delay_reason", "auto_close", "reactivated", "due_6d_at", "result_6d", "full_response_history", "customer_request_embedding", "original_mail_body_embedding"];
export const toUploadRows = (rows) => [DB_HEADERS, ...rows.slice(1).filter((row) => row[0])];
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `node --test work/db_upload_layout.test.mjs`

### Task 2: Workbook Sheets and Verification

**Files:**
- Modify: `work/build_embedding_workbook.mjs`
- Modify: `work/verify_embedding_workbook.mjs`
- Output: `outputs/Raw_data_임베딩_WX_DB적재용.xlsx`

**Interfaces:**
- Consumes: `DB_HEADERS` and `toUploadRows` from Task 1.
- Produces: a five-sheet Excel workbook.

- [ ] **Step 1: Add `DB Upload 135` and `Test Upload 15` from the completed source sheets**

```js
for (const [sourceName, targetName] of [["DB 135", "DB Upload 135"], ["Test 15", "Test Upload 15"]]) {
  const sourceRows = workbook.worksheets.getItem(sourceName).getUsedRange(true).values;
  const target = workbook.worksheets.add(targetName);
  target.getRange("A1").write(toUploadRows(sourceRows));
}
```

- [ ] **Step 2: Apply the existing navy header style, freeze row 1, and set practical widths without wrapping vector cells**

- [ ] **Step 3: Export and verify 135/15 rows, 24 columns, unique nonblank case IDs, and 384-dimensional vectors**

Run: `node work/verify_embedding_workbook.mjs`

- [ ] **Step 4: Render both new sheets and visually confirm headers and values are legible**

- [ ] **Step 5: Run all mapping, status, and embedding serialization tests**

Run: `node --test work/db_upload_layout.test.mjs work/status_normalization.test.mjs` and `python -m unittest discover -s work -p 'test_embedding_pipeline.py'`

## Repository Note

The workspace is not a Git repository, so commit steps are not applicable. The final workbook and fresh verification output are the completion evidence.

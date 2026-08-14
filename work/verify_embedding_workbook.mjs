import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workbookPath = "outputs/Raw_data_임베딩_WX_DB적재용.xlsx";
const previewDir = "work/final_previews";
const expectedCounts = { "Total 150": 150, "DB 135": 135, "Test 15": 15 };
const expectedUploadCounts = { "DB Upload 135": 135, "Test Upload 15": 15 };

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(workbookPath));
await fs.mkdir(previewDir, { recursive: true });
const report = {};

function vectorDimension(value) {
  if (typeof value !== "string" || !value.startsWith("[") || !value.endsWith("]")) return 0;
  return value.slice(1, -1).split(",").length;
}

for (const [sheetName, expectedCount] of Object.entries(expectedUploadCounts)) {
  const sheet = workbook.worksheets.getItem(sheetName);
  const rows = sheet.getUsedRange(true).values;
  const headers = rows[0];
  const dataRows = rows.slice(1).filter((row) => row[0]);
  const caseIds = dataRows.map((row) => row[0]);
  const wDimensions = dataRows.map((row) => vectorDimension(row[22]));
  const xDimensions = dataRows.map((row) => vectorDimension(row[23]));

  if (headers.length !== 24) throw new Error(`${sheetName}: expected 24 columns`);
  if (headers[0] !== "case_id" || headers[23] !== "original_mail_body_embedding") {
    throw new Error(`${sheetName}: DB headers mismatch`);
  }
  if (dataRows.length !== expectedCount) throw new Error(`${sheetName}: expected ${expectedCount}, got ${dataRows.length}`);
  if (new Set(caseIds).size !== expectedCount) throw new Error(`${sheetName}: blank or duplicate case_id`);
  if (wDimensions.some((dimension) => dimension !== 384)) throw new Error(`${sheetName}: invalid W vector`);
  if (xDimensions.some((dimension) => dimension !== 384)) throw new Error(`${sheetName}: invalid X vector`);

  report[sheetName] = {
    records: dataRows.length,
    columns: headers.length,
    uniqueCaseIds: new Set(caseIds).size,
    wDimension: [...new Set(wDimensions)],
    xDimension: [...new Set(xDimensions)],
  };

  for (const [label, range] of [["left", "A1:J6"], ["vectors", "V1:X6"]]) {
    const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
    await fs.writeFile(
      `${previewDir}/${sheetName.replace(/\s+/g, "_")}_${label}.png`,
      new Uint8Array(await preview.arrayBuffer()),
    );
  }
}

for (const [sheetName, expectedCount] of Object.entries(expectedCounts)) {
  const sheet = workbook.worksheets.getItem(sheetName);
  const rows = sheet.getUsedRange(true).values;
  const headers = rows[0];
  const dataRows = rows.slice(1).filter((row) => row[0]);
  const wDimensions = dataRows.map((row) => vectorDimension(row[22]));
  const xDimensions = dataRows.map((row) => vectorDimension(row[23]));
  const finalStatuses = [...new Set(dataRows.map((row) => row[14]))];

  if (headers[22] !== "customer_request_embedding") throw new Error(`${sheetName}: W header mismatch`);
  if (headers[23] !== "original_mail_body_embedding") throw new Error(`${sheetName}: X header mismatch`);
  if (dataRows.length !== expectedCount) throw new Error(`${sheetName}: expected ${expectedCount}, got ${dataRows.length}`);
  if (wDimensions.some((dimension) => dimension !== 384)) throw new Error(`${sheetName}: invalid W vector`);
  if (xDimensions.some((dimension) => dimension !== 384)) throw new Error(`${sheetName}: invalid X vector`);

  report[sheetName] = {
    records: dataRows.length,
    wDimension: [...new Set(wDimensions)],
    xDimension: [...new Set(xDimensions)],
    finalStatuses,
  };

  for (const [label, range] of [["left", "A1:J6"], ["vectors", "V1:X6"]]) {
    const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
    await fs.writeFile(
      `${previewDir}/${sheetName.replace(/\s+/g, "_")}_${label}.png`,
      new Uint8Array(await preview.arrayBuffer()),
    );
  }
}

const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 50 },
  maxChars: 3000,
});

console.log(JSON.stringify({ report, formulaErrors: formulaErrors.ndjson }, null, 2));

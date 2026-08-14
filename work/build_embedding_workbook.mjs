import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";
import { normalizeFinalStatus } from "./status_normalization.mjs";
import { toUploadRows } from "./db_upload_layout.mjs";

const sourcePath = "C:/Users/POSCOFUTUREM/Downloads/프로젝트/Raw data/Raw data.xlsx";
const embeddingsPath = "work/embeddings.json";
const outputPath = "outputs/Raw_data_임베딩_WX_DB적재용.xlsx";

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(sourcePath));
const embeddings = JSON.parse(await fs.readFile(embeddingsPath, "utf8"));

for (const sheetName of ["Total 150", "DB 135", "Test 15"]) {
  const sheet = workbook.worksheets.getItem(sheetName);
  const sourceRange = sheet.getUsedRange(true);
  const rows = sourceRange.values;
  const lastRow = rows.length;

  sheet.getRange(`O2:O${lastRow}`).values = rows.slice(1).map((row) => [
    row[0] ? normalizeFinalStatus(row[14]) : null,
  ]);

  sheet.getRange(`W1:X${lastRow}`).copyFrom(
    sheet.getRange(`U1:V${lastRow}`),
    "all",
  );
  sheet.getRange("W1:X1").values = [[
    "customer_request_embedding",
    "original_mail_body_embedding",
  ]];
  sheet.getRange("W1:X1").format = {
    fill: "#163A5F",
    font: { bold: true, color: "#FFFFFF", typeface: "Carlito", fontSize: 11 },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#D9E2F3" },
  };

  const values = rows.slice(1).map((row) => {
    const caseId = row[0] ? String(row[0]) : "";
    if (!caseId) return [null, null];
    const entry = embeddings[caseId];
    if (!entry) throw new Error(`${sheetName}: missing embeddings for ${caseId}`);
    return [entry.customer_request_embedding, entry.original_mail_body_embedding];
  });
  sheet.getRange(`W2:X${lastRow}`).values = values;
  sheet.getRange(`W2:X${lastRow}`).format.wrapText = false;
  sheet.getRange(`W2:X${lastRow}`).format.horizontalAlignment = "left";
  if (sheetName === "Test 15") {
    sheet.getRange(`W3:X${lastRow}`).format.fill = "#FFFF00";
  }
  sheet.getRange("W:X").format.columnWidth = 28;
}

for (const [sourceName, targetName] of [
  ["DB 135", "DB Upload 135"],
  ["Test 15", "Test Upload 15"],
]) {
  const sourceRows = workbook.worksheets.getItem(sourceName).getUsedRange(true).values;
  const uploadRows = toUploadRows(sourceRows);
  const sheet = workbook.worksheets.add(targetName);
  sheet.getRange("A1").write(uploadRows);
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  sheet.getRange("A1:X1").format = {
    fill: "#163A5F",
    font: { bold: true, color: "#FFFFFF", typeface: "Carlito", fontSize: 10 },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#D9E2F3" },
    rowHeight: 32,
  };
  sheet.getRange(`A2:X${uploadRows.length}`).format = {
    font: { typeface: "Carlito", fontSize: 10 },
    verticalAlignment: "center",
    wrapText: false,
    rowHeight: 20,
    borders: {
      insideHorizontal: { style: "thin", color: "#E5E7EB" },
      bottom: { style: "thin", color: "#E5E7EB" },
    },
  };
  sheet.getRange("A:F").format.columnWidth = 16;
  sheet.getRange("G:H").format.columnWidth = 38;
  sheet.getRange("I:I").format.columnWidth = 22;
  sheet.getRange("J:U").format.columnWidth = 18;
  sheet.getRange("V:V").format.columnWidth = 42;
  sheet.getRange("W:X").format.columnWidth = 28;
}

await fs.mkdir("outputs", { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(JSON.stringify({ outputPath, sheets: 5, embeddings: Object.keys(embeddings).length }));

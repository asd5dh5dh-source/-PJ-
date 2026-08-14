import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const sourcePath = "C:/Users/POSCOFUTUREM/Downloads/프로젝트/Raw data/Raw data.xlsx";
const outputPath = "work/embedding_inputs.json";

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(sourcePath));
const sheet = workbook.worksheets.getItem("Total 150");
const rows = sheet.getUsedRange(true).values;
const headers = rows[0];
const index = Object.fromEntries(headers.map((header, column) => [header, column]));

const records = rows.slice(1)
  .filter((row) => row[index["Case ID"]])
  .map((row) => ({
    case_id: String(row[index["Case ID"]]),
    customer_request: String(row[index["Customer Request"]] ?? ""),
    original_mail_body: String(row[index["Original Mail Body"]] ?? ""),
  }));

if (records.length !== 150) {
  throw new Error(`Expected 150 records, got ${records.length}`);
}

await fs.writeFile(outputPath, JSON.stringify(records), "utf8");
console.log(JSON.stringify({ records: records.length, outputPath }));

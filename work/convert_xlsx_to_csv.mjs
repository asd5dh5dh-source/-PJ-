import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";
import { rowsToCsv } from "./csv_serialization.mjs";

const jobs = [
  {
    input: "C:/Users/POSCOFUTUREM/Downloads/프로젝트/Raw data/DB업데이트/DB 업데이트 Test용.xlsx",
    output: "outputs/DB 업데이트 Test용.csv",
  },
  {
    input: "C:/Users/POSCOFUTUREM/Downloads/프로젝트/Raw data/DB업데이트/DB 업데이트 학습용.xlsx",
    output: "outputs/DB 업데이트 학습용.csv",
  },
];

await fs.mkdir("outputs", { recursive: true });
await fs.mkdir("work/csv_previews", { recursive: true });

const report = [];
for (const job of jobs) {
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(job.input));
  if (workbook.worksheets.items.length !== 1) {
    throw new Error(`${job.input}: expected exactly one worksheet`);
  }

  const sourceSheet = workbook.worksheets.getItemAt(0);
  const sourceRows = sourceSheet.getUsedRange(true).values;
  const csv = rowsToCsv(sourceRows);
  await fs.writeFile(job.output, csv, "utf8");

  const csvWorkbook = await Workbook.fromCSV(csv, { sheetName: sourceSheet.name });
  const csvRows = csvWorkbook.worksheets.getItemAt(0).getUsedRange(true).values;
  if (csvRows.length !== sourceRows.length || csvRows[0].length !== sourceRows[0].length) {
    throw new Error(`${job.output}: row or column count changed during conversion`);
  }
  const normalizedCsvHeader = [...csvRows[0]];
  normalizedCsvHeader[0] = String(normalizedCsvHeader[0]).replace(/^\uFEFF/, "");
  if (JSON.stringify(normalizedCsvHeader) !== JSON.stringify(sourceRows[0])) {
    throw new Error(`${job.output}: header changed during conversion`);
  }

  const preview = await csvWorkbook.render({
    sheetName: sourceSheet.name,
    range: "A1:J6",
    scale: 1,
    format: "png",
  });
  const previewName = job.output.split("/").at(-1).replace(/\.csv$/i, ".png");
  await fs.writeFile(
    `work/csv_previews/${previewName}`,
    new Uint8Array(await preview.arrayBuffer()),
  );

  report.push({
    input: job.input,
    output: job.output,
    sheet: sourceSheet.name,
    rows: sourceRows.length,
    columns: sourceRows[0].length,
  });
}

console.log(JSON.stringify(report, null, 2));

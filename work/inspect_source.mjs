import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const sourcePath = "C:/Users/POSCOFUTUREM/Downloads/프로젝트/Raw data/Raw data.xlsx";
const outputDir = "work/source_previews";

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(sourcePath));
await fs.mkdir(outputDir, { recursive: true });

const sheetSummary = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 4000,
});
console.log(sheetSummary.ndjson);

for (const sheetName of ["Total 150", "DB 135", "Test 15"]) {
  const region = await workbook.inspect({
    kind: "region",
    sheetId: sheetName,
    range: "A1:V6",
    maxChars: 5000,
    tableMaxRows: 6,
    tableMaxCols: 22,
    tableMaxCellChars: 80,
  });
  console.log(region.ndjson);

  const style = await workbook.inspect({
    kind: "computedStyle",
    sheetId: sheetName,
    range: "A1:V3",
    maxChars: 2500,
  });
  console.log(style.ndjson);

  const preview = await workbook.render({
    sheetName,
    range: "A1:J6",
    scale: 1,
    format: "png",
  });
  await fs.writeFile(
    `${outputDir}/${sheetName.replace(/\s+/g, "_")}.png`,
    new Uint8Array(await preview.arrayBuffer()),
  );
}

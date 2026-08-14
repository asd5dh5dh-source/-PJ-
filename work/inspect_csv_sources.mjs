import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const sources = [
  "C:/Users/POSCOFUTUREM/Downloads/프로젝트/Raw data/DB업데이트/DB 업데이트 Test용.xlsx",
  "C:/Users/POSCOFUTUREM/Downloads/프로젝트/Raw data/DB업데이트/DB 업데이트 학습용.xlsx",
];

for (const source of sources) {
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(source));
  const sheets = await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 3000 });
  console.log(JSON.stringify({ source, sheets: sheets.ndjson }));
  for (let index = 0; index < workbook.worksheets.items.length; index += 1) {
    const sheet = workbook.worksheets.getItemAt(index);
    const rows = sheet.getUsedRange(true)?.values ?? [];
    console.log(JSON.stringify({ source, sheet: sheet.name, rows: rows.length, columns: rows[0]?.length ?? 0 }));
  }
}
